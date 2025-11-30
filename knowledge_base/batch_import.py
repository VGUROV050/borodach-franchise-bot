"""
Batch import script for processing videos from CSV/JSON files.

Usage:
    python -m knowledge_base.batch_import data.csv
    python -m knowledge_base.batch_import data.json

CSV format:
    module,lesson,title,url
    4,1,Пирамида планирования,https://...
    4,2,Целевые и плановые значения,https://...

JSON format:
    [
        {"module": 4, "lesson": 1, "title": "Пирамида планирования", "url": "https://..."},
        {"module": 4, "lesson": 2, "title": "Целевые и плановые значения", "url": "https://..."}
    ]
"""

import asyncio
import csv
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from database.connection import AsyncSessionLocal
from database.models import KnowledgeModule, KnowledgeLesson
from sqlalchemy import select, update

from .processor import VideoProcessor
from .db_manager import (
    get_or_create_module,
    get_or_create_lesson,
    mark_lesson_transcribed,
    mark_lesson_embedded,
    save_chunks,
    get_knowledge_stats,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Directories
BASE_DIR = Path(__file__).parent
VIDEOS_DIR = BASE_DIR / "videos" / "batch"
AUDIO_DIR = BASE_DIR / "audio"


def download_video(url: str, output_path: Path) -> bool:
    """Download video from URL using wget."""
    try:
        logger.info(f"Downloading: {output_path.name}")
        result = subprocess.run(
            ["wget", "-q", "--show-progress", "-O", str(output_path), url],
            capture_output=False,
            timeout=1800  # 30 minutes timeout
        )
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"Downloaded: {output_path.name} ({output_path.stat().st_size / 1024 / 1024:.1f} MB)")
            return True
        else:
            logger.error(f"Download failed: {output_path.name}")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"Download timeout: {output_path.name}")
        return False
    except Exception as e:
        logger.error(f"Download error: {e}")
        return False


def cleanup_files(*paths: Path):
    """Remove files to free disk space."""
    for path in paths:
        try:
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up: {path.name}")
        except Exception as e:
            logger.warning(f"Failed to cleanup {path}: {e}")


def load_data(file_path: str) -> list[dict]:
    """Load data from CSV or JSON file."""
    path = Path(file_path)
    
    if path.suffix.lower() == '.csv':
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    elif path.suffix.lower() == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


async def process_lesson(
    processor: VideoProcessor,
    session,
    module: KnowledgeModule,
    lesson_data: dict,
    lesson_order: int
) -> bool:
    """Process a single lesson: download, transcribe, embed, cleanup."""
    
    title = lesson_data.get('title', f"Урок {lesson_data.get('lesson', lesson_order)}")
    url = lesson_data.get('url', '')
    
    if not url:
        logger.error(f"No URL for lesson: {title}")
        return False
    
    # Create safe filename
    safe_name = f"module{lesson_data.get('module', 0)}_lesson{lesson_data.get('lesson', lesson_order)}"
    video_path = VIDEOS_DIR / f"{safe_name}.mp4"
    audio_path = AUDIO_DIR / f"{safe_name}.mp3"
    
    try:
        # Check if lesson already processed
        lesson = await get_or_create_lesson(
            session,
            module_id=module.id,
            title=f"Модуль {lesson_data.get('module')}, Урок {lesson_data.get('lesson')}: {title}",
            video_filename=f"{safe_name}.mp4",
            order=lesson_order
        )
        
        if lesson.is_embedded:
            logger.info(f"Lesson already processed: {title}")
            return True
        
        # Download video
        if not download_video(url, video_path):
            return False
        
        # Extract audio
        extracted_audio = await processor.extract_audio(video_path)
        if not extracted_audio:
            logger.error(f"Failed to extract audio: {title}")
            cleanup_files(video_path)
            return False
        
        # Delete video immediately to save space
        cleanup_files(video_path)
        
        # Transcribe
        transcript = await processor.transcribe_audio(extracted_audio)
        if not transcript:
            logger.error(f"Failed to transcribe: {title}")
            cleanup_files(extracted_audio)
            return False
        
        # Mark as transcribed
        await mark_lesson_transcribed(session, lesson.id, int(transcript.get("duration", 0)))
        
        # Create chunks
        chunks_data = processor.chunk_transcript(transcript)
        if not chunks_data:
            logger.warning(f"No chunks for: {title}")
            cleanup_files(extracted_audio)
            return False
        
        # Create embeddings
        for chunk in chunks_data:
            embedding = await processor.create_embedding(chunk["text"])
            if embedding:
                chunk["embedding"] = embedding
        
        # Save to database
        saved = await save_chunks(session, lesson.id, chunks_data)
        await mark_lesson_embedded(session, lesson.id)
        await session.commit()
        
        logger.info(f"✅ Processed: {title} ({saved} chunks)")
        
        # Cleanup audio
        cleanup_files(extracted_audio)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing {title}: {e}")
        cleanup_files(video_path, audio_path)
        return False


async def batch_import(file_path: str, module_name: Optional[str] = None):
    """Import lessons from CSV/JSON file."""
    
    # Create directories
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load data
    try:
        lessons = load_data(file_path)
        logger.info(f"Loaded {len(lessons)} lessons from {file_path}")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return False
    
    if not lessons:
        logger.error("No lessons to process")
        return False
    
    # Group by module
    modules = {}
    for lesson in lessons:
        mod_num = int(lesson.get('module', 0))
        if mod_num not in modules:
            modules[mod_num] = []
        modules[mod_num].append(lesson)
    
    logger.info(f"Found {len(modules)} modules: {list(modules.keys())}")
    
    processor = VideoProcessor()
    total_processed = 0
    total_failed = 0
    
    async with AsyncSessionLocal() as session:
        for mod_num in sorted(modules.keys()):
            mod_lessons = modules[mod_num]
            
            # Determine module name
            if module_name and len(modules) == 1:
                mod_title = module_name
            else:
                mod_title = f"Модуль {mod_num}"
            
            logger.info(f"\n{'='*50}")
            logger.info(f"Processing: {mod_title} ({len(mod_lessons)} lessons)")
            logger.info(f"{'='*50}")
            
            # Create module
            module = await get_or_create_module(
                session,
                title=mod_title,
                description=f"Автоимпорт из {Path(file_path).name}",
                order=mod_num
            )
            
            # Process lessons
            for i, lesson_data in enumerate(mod_lessons):
                lesson_num = int(lesson_data.get('lesson', i + 1))
                logger.info(f"\n[{i+1}/{len(mod_lessons)}] Processing lesson {lesson_num}...")
                
                success = await process_lesson(
                    processor, session, module, lesson_data, lesson_num
                )
                
                if success:
                    total_processed += 1
                else:
                    total_failed += 1
        
        await session.commit()
    
    # Print summary
    logger.info(f"\n{'='*50}")
    logger.info(f"IMPORT COMPLETE")
    logger.info(f"{'='*50}")
    logger.info(f"Processed: {total_processed}")
    logger.info(f"Failed: {total_failed}")
    
    # Print stats
    stats = await get_knowledge_stats()
    logger.info(f"\n📊 Knowledge Base Stats:")
    logger.info(f"  Modules: {stats['module_count']}")
    logger.info(f"  Lessons: {stats['lesson_count']}")
    logger.info(f"  Chunks: {stats['chunk_count']}")
    logger.info(f"  Total duration: {stats['total_duration_minutes']} min")
    
    return total_failed == 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m knowledge_base.batch_import <file.csv|file.json> [module_name]")
        print("\nCSV format:")
        print("  module,lesson,title,url")
        print("  4,1,Пирамида планирования,https://...")
        print("\nJSON format:")
        print('  [{"module": 4, "lesson": 1, "title": "...", "url": "..."}]')
        sys.exit(1)
    
    file_path = sys.argv[1]
    module_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    asyncio.run(batch_import(file_path, module_name))

