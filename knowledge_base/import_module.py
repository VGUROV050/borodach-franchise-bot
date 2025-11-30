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
    
    processor = VideoProcessor()
    
    async with async_session_maker() as session:
        # Create or get module
        module = await get_or_create_module(
            session,
            title=module_title,
            description=f"Автоимпорт из {videos_path.name}",
            order=0
        )
        
        total_processed = 0
        total_chunks = 0
        
        for i, video_path in enumerate(videos):
            logger.info(f"\n[{i+1}/{len(videos)}] Processing: {video_path.name}")
            
            # Create lesson title from filename
            # Remove extension and clean up
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
        logger.info(f"Module: {module_title}")
        logger.info(f"Videos processed: {total_processed}/{len(videos)}")
        logger.info(f"Total chunks: {total_chunks}")
        logger.info(f"{'='*50}")
        
        return True


async def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print("\nКак использовать:")
        print("1. Положи видео в папку knowledge_base/videos/module1/")
        print("2. Запусти: python -m knowledge_base.import_module 'Название модуля' knowledge_base/videos/module1/")
        return
    
    module_title = sys.argv[1]
    videos_path = Path(sys.argv[2])
    
    # Optional: --no-embeddings flag
    create_embeddings = "--no-embeddings" not in sys.argv
    
    if not create_embeddings:
        logger.warning("⚠️ Embeddings disabled - RAG search won't work")
    
    await import_module(module_title, videos_path, create_embeddings)


if __name__ == "__main__":
    asyncio.run(main())

