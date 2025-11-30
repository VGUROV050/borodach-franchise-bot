# Database manager for Knowledge Base
# Handles saving transcripts and embeddings to PostgreSQL

import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import KnowledgeModule, KnowledgeLesson, KnowledgeChunk
from database.connection import AsyncSessionLocal as async_session_maker

logger = logging.getLogger(__name__)


async def get_or_create_module(
    session: AsyncSession,
    title: str,
    description: Optional[str] = None,
    order: int = 0
) -> KnowledgeModule:
    """Get existing module or create new one."""
    stmt = select(KnowledgeModule).where(KnowledgeModule.title == title)
    result = await session.execute(stmt)
    module = result.scalar_one_or_none()
    
    if module:
        logger.info(f"Found existing module: {title}")
        return module
    
    module = KnowledgeModule(
        title=title,
        description=description,
        order=order,
        is_active=True
    )
    session.add(module)
    await session.flush()
    logger.info(f"Created module: {title}")
    return module


async def get_or_create_lesson(
    session: AsyncSession,
    module_id: int,
    title: str,
    video_filename: str,
    duration_seconds: int = 0,
    order: int = 0
) -> KnowledgeLesson:
    """Get existing lesson or create new one."""
    stmt = select(KnowledgeLesson).where(
        KnowledgeLesson.module_id == module_id,
        KnowledgeLesson.video_filename == video_filename
    )
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()
    
    if lesson:
        logger.info(f"Found existing lesson: {title}")
        return lesson
    
    lesson = KnowledgeLesson(
        module_id=module_id,
        title=title,
        video_filename=video_filename,
        duration_seconds=duration_seconds,
        order=order,
        is_transcribed=False,
        is_embedded=False
    )
    session.add(lesson)
    await session.flush()
    logger.info(f"Created lesson: {title}")
    return lesson


async def save_chunks(
    session: AsyncSession,
    lesson_id: int,
    chunks: list[dict],
    embeddings: Optional[list[list[float]]] = None
) -> int:
    """Save transcript chunks to database."""
    # Delete existing chunks for this lesson
    stmt = select(KnowledgeChunk).where(KnowledgeChunk.lesson_id == lesson_id)
    result = await session.execute(stmt)
    existing = result.scalars().all()
    for chunk in existing:
        await session.delete(chunk)
    
    # Create new chunks
    count = 0
    for i, chunk_data in enumerate(chunks):
        embedding_json = None
        if embeddings and i < len(embeddings):
            embedding_json = json.dumps(embeddings[i])
        
        chunk = KnowledgeChunk(
            lesson_id=lesson_id,
            text=chunk_data["text"],
            start_time=chunk_data["start_time"],
            end_time=chunk_data["end_time"],
            chunk_index=chunk_data.get("chunk_index", i),
            embedding_json=embedding_json
        )
        session.add(chunk)
        count += 1
    
    await session.flush()
    logger.info(f"Saved {count} chunks for lesson {lesson_id}")
    return count


async def mark_lesson_transcribed(
    session: AsyncSession,
    lesson_id: int,
    duration_seconds: int
) -> None:
    """Mark lesson as transcribed."""
    stmt = select(KnowledgeLesson).where(KnowledgeLesson.id == lesson_id)
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()
    
    if lesson:
        lesson.is_transcribed = True
        lesson.transcribed_at = datetime.utcnow()
        lesson.duration_seconds = duration_seconds
        logger.info(f"Marked lesson {lesson_id} as transcribed")


async def mark_lesson_embedded(
    session: AsyncSession,
    lesson_id: int
) -> None:
    """Mark lesson as having embeddings."""
    stmt = select(KnowledgeLesson).where(KnowledgeLesson.id == lesson_id)
    result = await session.execute(stmt)
    lesson = result.scalar_one_or_none()
    
    if lesson:
        lesson.is_embedded = True
        logger.info(f"Marked lesson {lesson_id} as embedded")


async def get_all_modules() -> list[dict]:
    """Get all modules with lesson counts."""
    async with async_session_maker() as session:
        stmt = select(KnowledgeModule).order_by(KnowledgeModule.order)
        result = await session.execute(stmt)
        modules = result.scalars().all()
        
        return [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "order": m.order,
                "is_active": m.is_active,
                "lesson_count": len(m.lessons) if m.lessons else 0
            }
            for m in modules
        ]


async def get_module_with_lessons(module_id: int) -> Optional[dict]:
    """Get module with all lessons."""
    async with async_session_maker() as session:
        stmt = select(KnowledgeModule).where(KnowledgeModule.id == module_id)
        result = await session.execute(stmt)
        module = result.scalar_one_or_none()
        
        if not module:
            return None
        
        return {
            "id": module.id,
            "title": module.title,
            "description": module.description,
            "lessons": [
                {
                    "id": l.id,
                    "title": l.title,
                    "video_filename": l.video_filename,
                    "duration_seconds": l.duration_seconds,
                    "is_transcribed": l.is_transcribed,
                    "is_embedded": l.is_embedded,
                    "chunk_count": len(l.chunks) if l.chunks else 0
                }
                for l in sorted(module.lessons, key=lambda x: x.order)
            ]
        }


async def search_chunks(query_embedding: list[float], limit: int = 5) -> list[dict]:
    """
    Search for most similar chunks using cosine similarity.
    Note: This is a basic implementation. For production, use pgvector extension.
    """
    import numpy as np
    
    async with async_session_maker() as session:
        # Get all chunks with embeddings
        stmt = select(KnowledgeChunk).where(KnowledgeChunk.embedding_json.isnot(None))
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        if not chunks:
            return []
        
        # Calculate similarities
        query_vec = np.array(query_embedding)
        similarities = []
        
        for chunk in chunks:
            try:
                chunk_vec = np.array(json.loads(chunk.embedding_json))
                # Cosine similarity
                sim = np.dot(query_vec, chunk_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec))
                similarities.append((chunk, float(sim)))
            except Exception:
                continue
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Get lesson info for top results
        results = []
        for chunk, sim in similarities[:limit]:
            # Load lesson
            stmt = select(KnowledgeLesson).where(KnowledgeLesson.id == chunk.lesson_id)
            lesson_result = await session.execute(stmt)
            lesson = lesson_result.scalar_one_or_none()
            
            if lesson:
                # Load module
                stmt = select(KnowledgeModule).where(KnowledgeModule.id == lesson.module_id)
                module_result = await session.execute(stmt)
                module = module_result.scalar_one_or_none()
                
                results.append({
                    "chunk_id": chunk.id,
                    "text": chunk.text,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                    "timestamp": chunk.timestamp_formatted,
                    "similarity": sim,
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title,
                    "video_filename": lesson.video_filename,
                    "module_id": module.id if module else None,
                    "module_title": module.title if module else None,
                })
        
        return results


async def get_knowledge_stats() -> dict:
    """Get statistics about knowledge base."""
    async with async_session_maker() as session:
        # Count modules
        module_count = await session.scalar(
            select(func.count(KnowledgeModule.id))
        )
        
        # Count lessons
        lesson_count = await session.scalar(
            select(func.count(KnowledgeLesson.id))
        )
        
        # Count transcribed lessons
        transcribed_count = await session.scalar(
            select(func.count(KnowledgeLesson.id)).where(
                KnowledgeLesson.is_transcribed == True
            )
        )
        
        # Count chunks
        chunk_count = await session.scalar(
            select(func.count(KnowledgeChunk.id))
        )
        
        # Count chunks with embeddings
        embedded_count = await session.scalar(
            select(func.count(KnowledgeChunk.id)).where(
                KnowledgeChunk.embedding_json.isnot(None)
            )
        )
        
        # Total duration
        total_duration = await session.scalar(
            select(func.sum(KnowledgeLesson.duration_seconds))
        ) or 0
        
        return {
            "module_count": module_count or 0,
            "lesson_count": lesson_count or 0,
            "transcribed_count": transcribed_count or 0,
            "chunk_count": chunk_count or 0,
            "embedded_count": embedded_count or 0,
            "total_duration_minutes": total_duration // 60,
        }

