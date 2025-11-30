# RAG (Retrieval-Augmented Generation) for Knowledge Base
# Answers questions using video transcripts

import logging
from typing import Optional

from openai import AsyncOpenAI

from config.settings import OPENAI_API_KEY
from knowledge_base.db_manager import search_chunks, get_knowledge_stats

logger = logging.getLogger(__name__)


class KnowledgeRAG:
    """RAG system for answering questions from video knowledge base."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4o-mini"
        
        # Промпт для краткого ответа
        self.brief_prompt = """Ты — помощник для франчайзи барбершопов BORODACH.

Твоя задача — дать КРАТКИЙ ответ (2-4 предложения) на основе контекста из видео.

Правила:
1. Отвечай кратко и по существу
2. Укажи название урока в конце: "📹 Урок: {название}"
3. Если ответа нет в контексте — честно скажи об этом

НЕ ПИШИ длинные объяснения — только суть!
"""
        
        # Промпт для подробного ответа
        self.detailed_prompt = """Ты — помощник для франчайзи барбершопов BORODACH.

Твоя задача — дать ПОДРОБНЫЙ и развёрнутый ответ на основе контекста из видео.

Правила:
1. Объясни тему максимально полно
2. Используй структуру: тезисы, примеры, шаги
3. Если есть несколько аспектов — раскрой каждый
4. В конце укажи источники: "📹 Источники: {названия уроков}"

Отвечай развёрнуто, как преподаватель на лекции!
"""
        
        # Старый промпт для обратной совместимости
        self.system_prompt = self.brief_prompt
    
    async def create_query_embedding(self, query: str) -> Optional[list[float]]:
        """Create embedding for search query."""
        if not self.client:
            logger.error("[RAG] OpenAI client not configured")
            return None
        
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=query
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"[RAG] Error creating embedding: {e}")
            return None
    
    async def search(self, query: str, limit: int = 3) -> list[dict]:
        """Search for relevant chunks in knowledge base."""
        embedding = await self.create_query_embedding(query)
        if not embedding:
            return []
        
        results = await search_chunks(embedding, limit=limit)
        logger.info(f"[RAG] Found {len(results)} relevant chunks for query: {query[:50]}...")
        return results
    
    def format_context(self, chunks: list[dict]) -> str:
        """Format search results as context for GPT."""
        if not chunks:
            return "Контекст не найден."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Источник {i}]\n"
                f"Урок: {chunk.get('lesson_title', 'Неизвестно')}\n"
                f"Текст: {chunk.get('text', '')}\n"
            )
        
        return "\n---\n".join(context_parts)
    
    async def answer_question_brief(self, question: str) -> Optional[dict]:
        """
        Answer a question briefly, returning answer and context for follow-up.
        
        Returns:
            dict with 'answer' and 'context' keys, or None if failed
        """
        if not self.client:
            return None
        
        # Check if knowledge base has data
        stats = await get_knowledge_stats()
        if stats["embedded_count"] == 0:
            return None
        
        # Search for relevant chunks
        chunks = await self.search(question, limit=3)
        
        if not chunks:
            return None
        
        # Format context
        context = self.format_context(chunks)
        
        try:
            logger.info(f"[RAG] Generating BRIEF answer for: {question[:50]}...")
            
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": self.brief_prompt},
                    {"role": "user", "content": f"Контекст из видео:\n\n{context}\n\nВопрос: {question}"}
                ],
                temperature=0.3,
                max_tokens=200,  # Краткий ответ
                timeout=15.0
            )
            
            answer = response.choices[0].message.content
            logger.info(f"[RAG] Brief answer generated (tokens: {response.usage.total_tokens})")
            
            return {
                "answer": answer,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"[RAG] Error generating brief answer: {e}")
            return None
    
    async def answer_question_detailed(self, question: str, context: str) -> Optional[str]:
        """
        Answer a question in detail using pre-saved context.
        
        Args:
            question: Original question
            context: Pre-saved context from brief answer
            
        Returns:
            Detailed answer string or None if failed
        """
        if not self.client:
            return None
        
        try:
            logger.info(f"[RAG] Generating DETAILED answer for: {question[:50]}...")
            
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": self.detailed_prompt},
                    {"role": "user", "content": f"Контекст из видео:\n\n{context}\n\nВопрос: {question}"}
                ],
                temperature=0.4,
                max_tokens=1000,  # Подробный ответ
                timeout=30.0
            )
            
            answer = response.choices[0].message.content
            logger.info(f"[RAG] Detailed answer generated (tokens: {response.usage.total_tokens})")
            
            return answer
            
        except Exception as e:
            logger.error(f"[RAG] Error generating detailed answer: {e}")
            return None
    
    async def answer(self, question: str) -> str:
        """
        Answer a question using RAG (legacy method for compatibility).
        Returns formatted answer with video references.
        """
        result = await self.answer_question_brief(question)
        if result:
            return result["answer"]
        return (
            "К сожалению, не нашёл подходящей информации в базе знаний.\n\n"
            "💡 Попробуйте переформулировать вопрос или обратитесь в офис "
            "через раздел «📚 Полезное»."
        )
    
    async def is_knowledge_question(self, text: str) -> bool:
        """
        Check if the text is a question that should be answered from knowledge base.
        Returns True if it looks like a question about franchise operations.
        """
        # Keywords that suggest a knowledge question
        knowledge_keywords = [
            "как", "почему", "зачем", "когда", "где", "что такое",
            "сколько", "какой", "какая", "какие",
            "расскажи", "объясни", "подскажи", "помоги",
            "делать", "работать", "оформить", "получить",
            "клиент", "сотрудник", "касса", "выручка", "зарплата",
            "обучение", "стандарт", "процедура", "регламент",
            "yclients", "битрикс", "bitrix",
        ]
        
        text_lower = text.lower()
        
        # Check for question marks or keywords
        if "?" in text:
            return True
        
        for keyword in knowledge_keywords:
            if keyword in text_lower:
                return True
        
        return False


# Singleton instance
knowledge_rag = KnowledgeRAG()

