#!/usr/bin/env python3
"""
Generate summaries for all lessons in knowledge base.
This improves RAG search by adding high-level context.

Usage:
    python scripts/generate_summaries.py
    python scripts/generate_summaries.py --module 5  # Only module 5
    python scripts/generate_summaries.py --lesson-id 12  # Only lesson 12
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from config.settings import OPENAI_API_KEY
from database.connection import AsyncSessionLocal
from database.models import KnowledgeModule, KnowledgeLesson, KnowledgeChunk

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

SUMMARY_PROMPT = """Ты — помощник для создания кратких содержаний видеоуроков.

На основе транскрипта урока напиши КРАТКОЕ СОДЕРЖАНИЕ (3-5 предложений), которое:
1. Описывает основную тему урока
2. Перечисляет ключевые понятия и термины
3. Указывает практическую пользу для франчайзи барбершопа

Формат:
```
[Тема урока в одном предложении]

Ключевые понятия: [список через запятую]

[2-3 предложения о содержании и пользе]
```

Пиши кратко и информативно!
"""


async def generate_summary(lesson_title: str, chunks_text: str) -> str | None:
    """Generate summary for a lesson using GPT."""
    if not client:
        logger.error("OpenAI client not configured")
        return None
    
    try:
        # Limit text to ~4000 tokens (~16000 chars)
        truncated_text = chunks_text[:16000]
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": f"Урок: {lesson_title}\n\nТранскрипт:\n{truncated_text}"}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        
        summary = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else "?"
        logger.info(f"  ✅ Summary generated ({tokens} tokens)")
        return summary.strip()
        
    except Exception as e:
        logger.error(f"  ❌ Error generating summary: {e}")
        return None


async def create_summary_embedding(text: str) -> list[float] | None:
    """Create embedding for summary text."""
    if not client:
        return None
    
    try:
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error creating embedding: {e}")
        return None


async def process_lesson(db, lesson: KnowledgeLesson, force: bool = False) -> bool:
    """Process a single lesson: generate summary and create summary chunk."""
    
    # Skip if already has summary (unless force)
    if lesson.summary and not force:
        logger.info(f"  ⏭️  Already has summary, skipping")
        return False
    
    # Get all chunks for this lesson
    result = await db.execute(
        select(KnowledgeChunk)
        .where(KnowledgeChunk.lesson_id == lesson.id)
        .order_by(KnowledgeChunk.chunk_index)
    )
    chunks = result.scalars().all()
    
    if not chunks:
        logger.warning(f"  ⚠️  No chunks found for lesson")
        return False
    
    # Concatenate all chunk texts
    full_text = " ".join([c.text for c in chunks])
    logger.info(f"  📝 Processing {len(chunks)} chunks, {len(full_text)} chars")
    
    # Generate summary
    summary = await generate_summary(lesson.title, full_text)
    if not summary:
        return False
    
    # Save summary to lesson
    lesson.summary = summary
    
    # Check if summary chunk already exists
    existing = await db.execute(
        select(KnowledgeChunk)
        .where(
            KnowledgeChunk.lesson_id == lesson.id,
            KnowledgeChunk.chunk_index == -1  # Summary chunks have index -1
        )
    )
    existing_chunk = existing.scalar_one_or_none()
    
    # Create or update summary chunk
    summary_text = f"📋 КРАТКОЕ СОДЕРЖАНИЕ УРОКА: {lesson.title}\n\n{summary}"
    embedding = await create_summary_embedding(summary_text)
    
    if existing_chunk:
        existing_chunk.text = summary_text
        if embedding:
            existing_chunk.embedding = embedding
        logger.info(f"  🔄 Updated existing summary chunk")
    else:
        # Create new summary chunk with index -1 (before regular chunks)
        summary_chunk = KnowledgeChunk(
            lesson_id=lesson.id,
            text=summary_text,
            start_time=0,
            end_time=0,
            chunk_index=-1,  # Special index for summary
            embedding=embedding,
        )
        db.add(summary_chunk)
        logger.info(f"  ➕ Created new summary chunk")
    
    return True


async def main(module_order: int | None = None, lesson_id: int | None = None, force: bool = False):
    """Main function to generate summaries."""
    
    logger.info("=" * 50)
    logger.info("📚 GENERATING LESSON SUMMARIES")
    logger.info("=" * 50)
    
    async with AsyncSessionLocal() as db:
        # Build query
        query = select(KnowledgeLesson).options(
            selectinload(KnowledgeLesson.module)
        )
        
        if lesson_id:
            query = query.where(KnowledgeLesson.id == lesson_id)
        elif module_order is not None:
            # Get module by order
            module_result = await db.execute(
                select(KnowledgeModule).where(KnowledgeModule.order == module_order)
            )
            module = module_result.scalar_one_or_none()
            if not module:
                logger.error(f"Module with order {module_order} not found")
                return
            query = query.where(KnowledgeLesson.module_id == module.id)
        
        result = await db.execute(query.order_by(KnowledgeLesson.id))
        lessons = result.scalars().all()
        
        logger.info(f"Found {len(lessons)} lessons to process")
        
        processed = 0
        skipped = 0
        errors = 0
        
        for i, lesson in enumerate(lessons):
            module_title = lesson.module.title if lesson.module else "Unknown"
            logger.info(f"\n[{i+1}/{len(lessons)}] {module_title} / {lesson.title}")
            
            try:
                if await process_lesson(db, lesson, force):
                    processed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"  ❌ Error: {e}")
                errors += 1
            
            # Rate limiting
            await asyncio.sleep(0.5)
        
        # Commit all changes
        await db.commit()
        
        logger.info("\n" + "=" * 50)
        logger.info(f"✅ DONE!")
        logger.info(f"   Processed: {processed}")
        logger.info(f"   Skipped: {skipped}")
        logger.info(f"   Errors: {errors}")
        logger.info("=" * 50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate summaries for lessons")
    parser.add_argument("--module", type=int, help="Process only specific module (by order)")
    parser.add_argument("--lesson-id", type=int, help="Process only specific lesson (by ID)")
    parser.add_argument("--force", action="store_true", help="Regenerate existing summaries")
    
    args = parser.parse_args()
    
    asyncio.run(main(
        module_order=args.module,
        lesson_id=args.lesson_id,
        force=args.force
    ))

