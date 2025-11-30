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
        
        self.system_prompt = """Ты — помощник для франчайзи барбершопов BORODACH. 
У тебя есть доступ к базе знаний из обучающих видео.

Твоя задача:
1. Отвечать на вопросы, используя предоставленный контекст из видео
2. Если информация есть в видео — указывать название урока
3. Отвечать кратко и по делу
4. Если в контексте нет ответа — честно сказать об этом

Формат ответа:
- Краткий ответ на вопрос
- Ссылка на видео: "📹 Подробнее: {название урока}"

Если не нашёл ответ в контексте:
"К сожалению, в базе знаний нет информации по этому вопросу. Попробуйте связаться с офисом через раздел 'Полезное'."
"""
    
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
    
    async def answer(self, question: str) -> str:
        """
        Answer a question using RAG.
        Returns formatted answer with video references.
        """
        if not self.client:
            return "⚠️ Система ответов временно недоступна. Попробуйте позже."
        
        # Check if knowledge base has data
        stats = await get_knowledge_stats()
        if stats["embedded_count"] == 0:
            return "📚 База знаний пока пуста. Скоро здесь появятся обучающие материалы!"
        
        # Search for relevant chunks
        chunks = await self.search(question, limit=3)
        
        if not chunks:
            return (
                "К сожалению, не нашёл подходящей информации в базе знаний.\n\n"
                "💡 Попробуйте переформулировать вопрос или обратитесь в офис "
                "через раздел «📚 Полезное»."
            )
        
        # Format context
        context = self.format_context(chunks)
        
        try:
            logger.info(f"[RAG] Generating answer for: {question[:50]}...")
            
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Контекст из видео:\n\n{context}\n\nВопрос: {question}"}
                ],
                temperature=0.3,
                max_tokens=500,
                timeout=15.0
            )
            
            answer = response.choices[0].message.content
            logger.info(f"[RAG] Answer generated (tokens: {response.usage.total_tokens})")
            
            return answer
            
        except Exception as e:
            logger.error(f"[RAG] Error generating answer: {e}")
            return "⚠️ Произошла ошибка при формировании ответа. Попробуйте позже."
    
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

