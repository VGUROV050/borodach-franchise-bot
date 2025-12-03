#!/usr/bin/env python
"""
Import a module with videos into the Knowledge Base.

Usage:
    python -m knowledge_base.import_module "Название модуля" path/to/videos/

Example:
    python -m knowledge_base.import_module "Модуль 1: Введение" knowledge_base/videos/module1/
"""

import sys
import asyncio
import logging
from pathlib import Path

from knowledge_base.processor import VideoProcessor
from knowledge_base.db_manager import (
    get_or_create_module,
    get_or_create_lesson,
    save_chunks,
    mark_lesson_transcribed,
    mark_lesson_embedded,
)
from database.connection import AsyncSessionLocal as async_session_maker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Промпт для генерации саммари
SUMMARY_PROMPT = """На основе транскрипта видеоурока напиши КРАТКОЕ СОДЕРЖАНИЕ (3-5 предложений):
1. Основная тема урока
2. Ключевые понятия (через запятую)
3. Практическая польза для франчайзи барбершопа

Пиши кратко и информативно!"""


async def generate_lesson_summary(session, lesson, chunks: list, processor) -> bool:
    """Generate summary for a lesson and save as special chunk."""
    import json
    from openai import AsyncOpenAI
    from config.settings import OPENAI_API_KEY
    from database.models import KnowledgeChunk
    from sqlalchemy import select
    
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured, skipping summary")
        return False
    
    try:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        # Concatenate all chunk texts
        full_text = " ".join([c["text"] for c in chunks])[:16000]
        
        # Generate summary
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": f"Урок: {lesson.title}\n\nТранскрипт:\n{full_text}"}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        
        summary = response.choices[0].message.content.strip()
        tokens = response.usage.total_tokens if response.usage else "?"
        logger.info(f"  ✅ Summary generated ({tokens} tokens)")
        
        # Save summary to lesson
        lesson.summary = summary
        
        # Create summary chunk text
        summary_text = f"📋 КРАТКОЕ СОДЕРЖАНИЕ УРОКА: {lesson.title}\n\n{summary}"
        
        # Create embedding for summary
        embedding = await processor.create_embedding(summary_text)
        embedding_json = json.dumps(embedding) if embedding else None
        
        # Check if summary chunk exists
        existing = await session.execute(
            select(KnowledgeChunk).where(
                KnowledgeChunk.lesson_id == lesson.id,
                KnowledgeChunk.chunk_index == -1
            )
        )
        existing_chunk = existing.scalar_one_or_none()
        
        if existing_chunk:
            existing_chunk.text = summary_text
            existing_chunk.embedding_json = embedding_json
            logger.info("  🔄 Updated summary chunk")
        else:
            summary_chunk = KnowledgeChunk(
                lesson_id=lesson.id,
                text=summary_text,
                start_time=0,
                end_time=0,
                chunk_index=-1,
                embedding_json=embedding_json,
            )
            session.add(summary_chunk)
            logger.info("  ➕ Created summary chunk")
        
        return True
        
    except Exception as e:
        logger.error(f"  ❌ Failed to generate summary: {e}")
        return False


async def import_module(module_title: str, videos_path: Path, create_embeddings: bool = True):
    """
    Import a module with all its videos.
    
    Args:
        module_title: Human-readable title for the module
        videos_path: Path to directory with video files
        create_embeddings: Whether to create embeddings (costs money)
    """
    if not videos_path.exists():
        logger.error(f"Directory not found: {videos_path}")
        return False
    
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    videos = sorted([
        f for f in videos_path.iterdir() 
        if f.is_file() and f.suffix.lower() in video_extensions
    ])
    
    if not videos:
        logger.error(f"No videos found in {videos_path}")
        return False
    
    logger.info(f"Found {len(videos)} videos in {videos_path}")
    
    # Load metadata.json for Russian titles if exists
    metadata = {}
    lessons_meta = {}
    actual_module_title = module_title
    metadata_path = videos_path / "metadata.json"
    if metadata_path.exists():
        try:
            import json
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            # Use module_title from metadata if available
            if "module_title" in metadata:
                actual_module_title = metadata["module_title"]
                logger.info(f"Using module title from metadata: {actual_module_title}")
            # Get lessons mapping
            if "lessons" in metadata:
                lessons_meta = metadata["lessons"]
                logger.info(f"Loaded metadata for {len(lessons_meta)} lessons")
        except Exception as e:
            logger.warning(f"Failed to load metadata.json: {e}")
    
    processor = VideoProcessor()
    
    async with async_session_maker() as session:
        # Create or get module
        module = await get_or_create_module(
            session,
            title=actual_module_title,
            description=f"Автоимпорт из {videos_path.name}",
            order=0
        )
        
        total_processed = 0
        total_chunks = 0
        
        for i, video_path in enumerate(videos):
            logger.info(f"\n[{i+1}/{len(videos)}] Processing: {video_path.name}")
            
            # Get lesson title from metadata.json or generate from filename
            # Try to extract lesson number from filename (e.g., "lesson1.mp4" -> "1")
            import re
            lesson_num_match = re.search(r'(\d+)', video_path.stem)
            lesson_num = lesson_num_match.group(1) if lesson_num_match else str(i + 1)
            
            if lesson_num in lessons_meta:
                lesson_title = lessons_meta[lesson_num]
                logger.info(f"Using title from metadata: {lesson_title}")
            elif video_path.name in metadata:
                lesson_title = metadata[video_path.name]
                logger.info(f"Using title from metadata: {lesson_title}")
            else:
                # Fallback: create lesson title from filename
                lesson_title = video_path.stem.replace("_", " ").replace("-", " ")
                # Capitalize first letter
                lesson_title = lesson_title[0].upper() + lesson_title[1:] if lesson_title else video_path.name
            
            # Create or get lesson
            lesson = await get_or_create_lesson(
                session,
                module_id=module.id,
                title=lesson_title,
                video_filename=video_path.name,
                order=i
            )
            
            # Process video
            result = await processor.process_video(video_path)
            
            if not result:
                logger.error(f"Failed to process: {video_path.name}")
                continue
            
            # Create embeddings if requested
            embeddings = None
            if create_embeddings and result["chunks"]:
                logger.info(f"Creating embeddings for {len(result['chunks'])} chunks...")
                embeddings = []
                for chunk in result["chunks"]:
                    emb = await processor.create_embedding(chunk["text"])
                    embeddings.append(emb)
                    await asyncio.sleep(0.1)  # Rate limiting
            
            # Save chunks
            chunk_count = await save_chunks(
                session,
                lesson_id=lesson.id,
                chunks=result["chunks"],
                embeddings=embeddings
            )
            
            # Update lesson status
            await mark_lesson_transcribed(
                session,
                lesson_id=lesson.id,
                duration_seconds=int(result["duration"])
            )
            
            if embeddings:
                await mark_lesson_embedded(session, lesson_id=lesson.id)
            
            total_processed += 1
            total_chunks += chunk_count
            
            logger.info(f"✅ {video_path.name}: {chunk_count} chunks, {result['duration']:.0f}s")
        
        await session.commit()
        
        logger.info(f"\n{'='*50}")
        logger.info(f"✅ Import complete!")
        logger.info(f"Module: {actual_module_title}")
        logger.info(f"Videos processed: {total_processed}/{len(videos)}")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"{'='*50}")
        
        return True


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Import videos into Knowledge Base')
    parser.add_argument('--module-dir', '-d', type=str, required=True,
                        help='Path to directory with videos and metadata.json')
    parser.add_argument('--lesson', '-l', type=str, default=None,
                        help='Process only specific lesson file (e.g., lesson1)')
    parser.add_argument('--no-embeddings', action='store_true',
                        help='Skip creating embeddings')
    parser.add_argument('--module-title', '-t', type=str, default=None,
                        help='Module title (overrides metadata.json)')
    
    args = parser.parse_args()
    
    videos_path = Path(args.module_dir)
    module_title = args.module_title or "Auto-imported module"
    
    # If specific lesson requested, filter to just that file
    if args.lesson:
        # Find the specific lesson file
        lesson_file = None
        for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.mp3']:
            candidate = videos_path / f"{args.lesson}{ext}"
            if candidate.exists():
                lesson_file = candidate
                break
        
        if not lesson_file:
            logger.error(f"Lesson file not found: {args.lesson}")
            return
        
        # Process single lesson
        await import_single_lesson(module_title, videos_path, lesson_file, not args.no_embeddings)
    else:
        # Process all videos in directory
        await import_module(module_title, videos_path, not args.no_embeddings)


async def import_single_lesson(module_title: str, videos_path: Path, lesson_file: Path, create_embeddings: bool = True):
    """Import a single lesson from a module."""
    import json
    import re
    
    # Load metadata
    metadata_path = videos_path / "metadata.json"
    lessons_meta = {}
    actual_module_title = module_title
    module_num = None
    
    if metadata_path.exists():
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            if "module_title" in metadata:
                actual_module_title = metadata["module_title"]
            if "module_num" in metadata:
                module_num = int(metadata["module_num"])
            if "lessons" in metadata:
                lessons_meta = metadata["lessons"]
            logger.info(f"Loaded metadata: {actual_module_title}")
        except Exception as e:
            logger.warning(f"Failed to load metadata: {e}")
    
    # Try to extract module number from folder name if not in metadata
    if module_num is None:
        folder_match = re.search(r'module(\d+)', videos_path.name, re.IGNORECASE)
        if folder_match:
            module_num = int(folder_match.group(1))
            logger.info(f"Extracted module number from folder: {module_num}")
    
    # Get lesson number and title
    lesson_num_match = re.search(r'(\d+)', lesson_file.stem)
    lesson_num = lesson_num_match.group(1) if lesson_num_match else "1"
    lesson_num_int = int(lesson_num)
    
    if lesson_num in lessons_meta:
        lesson_title = lessons_meta[lesson_num]
    else:
        lesson_title = lesson_file.stem.replace("_", " ").title()
    
    # Create proper lesson title with module and lesson numbers
    if module_num and not lesson_title.startswith("Модуль"):
        lesson_title = f"Модуль {module_num}, Урок {lesson_num}: {lesson_title}"
    
    logger.info(f"Processing: {lesson_title}")
    
    processor = VideoProcessor()
    
    async with async_session_maker() as session:
        # Get or create module
        module = await get_or_create_module(
            session,
            title=actual_module_title,
            description=f"Модуль из {videos_path.name}",
            order=module_num - 1 if module_num else 0
        )
        
        # Standardized video filename
        if module_num:
            standard_video_filename = f"module{module_num}_lesson{lesson_num}.mp4"
        else:
            standard_video_filename = lesson_file.name
        
        # Get or create lesson
        lesson = await get_or_create_lesson(
            session,
            module_id=module.id,
            title=lesson_title,
            video_filename=standard_video_filename,
            order=lesson_num_int - 1
        )
        
        # Process video/audio with standardized naming
        result = await processor.process_video(
            lesson_file,
            module_num=module_num,
            lesson_num=lesson_num_int
        )
        
        if not result:
            logger.error(f"Failed to process: {lesson_file.name}")
            return
        
        # Create embeddings
        embeddings = None
        if create_embeddings and result["chunks"]:
            logger.info(f"Creating embeddings for {len(result['chunks'])} chunks...")
            embeddings = []
            for chunk in result["chunks"]:
                emb = await processor.create_embedding(chunk["text"])
                embeddings.append(emb)
                await asyncio.sleep(0.1)
        
        # Save chunks
        chunk_count = await save_chunks(
            session,
            lesson_id=lesson.id,
            chunks=result["chunks"],
            embeddings=embeddings
        )
        
        # Update lesson status
        await mark_lesson_transcribed(
            session,
            lesson_id=lesson.id,
            duration_seconds=int(result["duration"])
        )
        
        if embeddings:
            await mark_lesson_embedded(session, lesson_id=lesson.id)
        
        # Generate summary for better RAG search
        if create_embeddings and result["chunks"]:
            logger.info("Generating lesson summary...")
            await generate_lesson_summary(session, lesson, result["chunks"], processor)
        
        await session.commit()
        
        logger.info(f"{'='*50}")
        logger.info(f"✅ Import complete!")
        logger.info(f"Module: {actual_module_title}")
        logger.info(f"Lesson: {lesson_title}")
        logger.info(f"Total chunks: {chunk_count}")
        logger.info(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())

