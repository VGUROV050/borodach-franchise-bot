#!/usr/bin/env python3
"""
Check what's in the Knowledge Base.
Run on server: python scripts/check_knowledge_base.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from database.connection import AsyncSessionLocal
from database.models import KnowledgeModule, KnowledgeLesson, KnowledgeChunk


async def check_db():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(KnowledgeModule).order_by(KnowledgeModule.order)
        )
        modules = result.scalars().all()
        
        print('=' * 65)
        print('📚 БАЗА ЗНАНИЙ - ТЕКУЩЕЕ СОСТОЯНИЕ')
        print('=' * 65)
        
        total_lessons = 0
        total_chunks = 0
        
        for module in modules:
            lessons_result = await db.execute(
                select(KnowledgeLesson)
                .where(KnowledgeLesson.module_id == module.id)
                .order_by(KnowledgeLesson.order)
            )
            lessons = lessons_result.scalars().all()
            
            print(f'\n📁 Модуль {module.order + 1}: {module.title}')
            print('-' * 60)
            
            for lesson in lessons:
                # Count chunks
                chunks_result = await db.execute(
                    select(func.count(KnowledgeChunk.id))
                    .where(KnowledgeChunk.lesson_id == lesson.id)
                )
                chunk_count = chunks_result.scalar()
                
                # Check for summary chunk
                summary_result = await db.execute(
                    select(KnowledgeChunk)
                    .where(KnowledgeChunk.lesson_id == lesson.id)
                    .where(KnowledgeChunk.chunk_index == -1)
                )
                has_summary = summary_result.scalar_one_or_none() is not None
                
                # Format status
                status = '✅' if lesson.is_embedded else '⏳'
                summary_icon = '📋' if has_summary else '  '
                
                # Clean title for display
                title = lesson.title
                if len(title) > 45:
                    title = title[:42] + '...'
                
                print(f'  {status} {summary_icon} Урок {lesson.order + 1}: {title} ({chunk_count} чанков)')
                
                total_lessons += 1
                total_chunks += chunk_count
        
        print()
        print('=' * 65)
        print(f'📊 ИТОГО: {len(modules)} модулей, {total_lessons} уроков, {total_chunks} чанков')
        print('=' * 65)
        print()
        print('Легенда: ✅ = embedded, ⏳ = в процессе, 📋 = есть summary')


if __name__ == "__main__":
    asyncio.run(check_db())

