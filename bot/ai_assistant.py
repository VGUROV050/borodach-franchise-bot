# AI Assistant for handling unexpected user messages

import logging
from typing import Optional
from openai import AsyncOpenAI

from config.settings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Описание доступных функций бота для AI
BOT_CAPABILITIES = """
Ты — помощник бота для франчайзи барбершопов BORODACH. 

Доступные разделы главного меню:
1. 📋 Задачи — создание задач в управляющую компанию, просмотр своих задач
2. 📚 Полезное — полезная информация по отделам (Развитие, Маркетинг, Дизайн), контакты отделов
3. 📊 Статистика — выручка барбершопов, рейтинг в сети, за разные периоды (сегодня, вчера, месяц)
4. 👤 Аккаунт — информация о профиле, список барбершопов, добавление барбершопа
5. 🤖 AI-ассистент — помощник для вопросов по обучающим материалам (KPI, планирование, мотивация и др.)

Внутри раздела "Задачи":
- 🆕 Новая задача — создать задачу в отдел (Развитие, Маркетинг, Дизайн)
- 📋 Мои задачи — посмотреть свои задачи и их статусы

Внутри раздела "Статистика":
- Можно выбрать период: Сегодня, Вчера, Текущий месяц, Прошлый месяц

Внутри раздела "Аккаунт":
- ➕ Добавить барбершоп — запросить привязку нового барбершопа

Внутри раздела "AI-ассистент":
- Можно задать любой вопрос по материалам обучения
- AI ответит на основе видео-уроков

Отвечай КРАТКО (1-3 предложения). Направь пользователя к нужной кнопке меню.
Если вопрос касается обучения, KPI, показателей, планирования, мотивации — направь в «🤖 AI-ассистент».
Используй emoji из меню в ответе.
"""

# Ключевые слова для определения вопросов к базе знаний
KNOWLEDGE_KEYWORDS = [
    "как", "почему", "зачем", "когда", "где", "что такое",
    "сколько", "какой", "какая", "какие",
    "расскажи", "объясни", "подскажи",
    "делать", "работать", "оформить", "получить",
    "клиент", "сотрудник", "касса", "выручка", "зарплата",
    "обучение", "стандарт", "процедура", "регламент",
]


def is_knowledge_question(text: str) -> bool:
    """Check if the text looks like a question for knowledge base."""
    text_lower = text.lower()
    
    # Question mark is a strong indicator
    if "?" in text:
        return True
    
    # Check for knowledge-related keywords
    return any(keyword in text_lower for keyword in KNOWLEDGE_KEYWORDS)


async def get_knowledge_answer(user_message: str, detailed: bool = False) -> str | None:
    """
    Try to answer from knowledge base using RAG.
    Returns answer or None if KB is empty or no relevant info found.
    """
    try:
        from knowledge_base.rag import knowledge_rag
        from knowledge_base.db_manager import get_knowledge_stats
        
        # Check if KB has data
        stats = await get_knowledge_stats()
        if stats["embedded_count"] == 0:
            logger.info("📚 [KB] Knowledge base is empty, skipping RAG")
            return None
        
        logger.info(f"📚 [KB] Searching knowledge base for: '{user_message[:50]}...' (detailed={detailed})")
        answer = await knowledge_rag.answer(user_message, detailed=detailed)
        return answer
        
    except ImportError:
        logger.warning("📚 [KB] Knowledge base module not available")
        return None
    except Exception as e:
        logger.error(f"📚 [KB] Error querying knowledge base: {e}")
        return None


async def get_smart_answer(
    user_message: str, 
    telegram_id: int,
    detailed: bool = False,
) -> str:
    """
    Умный ответ AI с учётом данных партнёра и базы знаний.
    
    1. Получает данные партнёра (метрики салонов)
    2. Определяет проблемные зоны
    3. Ищет релевантную информацию в базе знаний
    4. Формирует персонализированный ответ
    
    Args:
        user_message: Вопрос пользователя
        telegram_id: Telegram ID для получения данных
        detailed: Подробный ответ
    
    Returns:
        Персонализированный ответ
    """
    if not client:
        logger.warning("⚠️ [AI] OpenAI not available")
        return await get_knowledge_answer(user_message, detailed) or "AI-ассистент временно недоступен."
    
    try:
        # 1. Получаем данные партнёра
        from bot.partner_analytics import (
            get_partner_analytics, 
            format_analytics_for_ai,
            get_partner_issues,
            get_partner_strengths,
            get_company_trends,
            format_trends_for_ai,
            get_trend_insights,
        )
        
        analytics = await get_partner_analytics(telegram_id)
        partner_context = ""
        issues_context = ""
        trends_context = ""
        
        if analytics and analytics.companies:
            partner_context = format_analytics_for_ai(analytics)
            issues = get_partner_issues(analytics)
            strengths = get_partner_strengths(analytics)
            
            if issues:
                issues_context = "\n⚠️ ПРОБЛЕМНЫЕ ЗОНЫ:\n" + "\n".join(f"• {i}" for i in issues)
            if strengths:
                issues_context += "\n\n✅ СИЛЬНЫЕ СТОРОНЫ:\n" + "\n".join(f"• {s}" for s in strengths)
            
            # Получаем тренды для каждого салона
            all_trend_insights = []
            
            # Получаем средние тренды по сети для сравнения
            try:
                from bot.partner_analytics import get_network_average_trends, compare_with_network_trends
                network_trends = await get_network_average_trends()
            except Exception as e:
                logger.warning(f"Failed to get network trends: {e}")
                network_trends = None
            
            for company in analytics.companies:
                try:
                    trends = await get_company_trends(company.company_id, company)
                    if trends:
                        trends_context += "\n" + format_trends_for_ai(trends)
                        all_trend_insights.extend(get_trend_insights(trends))
                        
                        # Сравниваем с сетью
                        if network_trends and trends.revenue:
                            network_comparison = compare_with_network_trends(trends.revenue, network_trends)
                            all_trend_insights.extend(network_comparison)
                except Exception as e:
                    logger.warning(f"Failed to get trends for {company.company_id}: {e}")
            
            if all_trend_insights:
                issues_context += "\n\n📊 ИНСАЙТЫ ПО ДИНАМИКЕ:\n" + "\n".join(f"• {i}" for i in all_trend_insights)
        
        # 2. Ищем в базе знаний
        kb_context = ""
        try:
            from knowledge_base.rag import knowledge_rag
            from knowledge_base.db_manager import get_knowledge_stats
            
            stats = await get_knowledge_stats()
            if stats["embedded_count"] > 0:
                chunks = await knowledge_rag.search(user_message, limit=5)
                if chunks:
                    kb_context = "\n📚 ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ:\n"
                    for chunk in chunks:
                        kb_context += f"\n[{chunk.get('lesson_title', 'Урок')}]\n{chunk.get('text', '')[:500]}\n"
        except Exception as e:
            logger.warning(f"KB search error: {e}")
        
        # 3. Формируем системный промпт
        system_prompt = f"""Ты — AI-ассистент для франчайзи барбершопов BORODACH.

У тебя есть доступ к:
1. Реальным данным салонов партнёра (выручка, средний чек, рейтинг, клиенты)
2. Базе знаний из обучающих видео

Твоя задача:
- Анализировать данные партнёра
- Сравнивать с средними показателями по сети и городу
- Давать конкретные рекомендации на основе базы знаний
- Указывать конкретные цифры и проценты

{partner_context}
{trends_context}
{issues_context}
{kb_context}

{"Дай ПОДРОБНЫЙ развёрнутый ответ с конкретными рекомендациями." if detailed else "Дай КРАТКИЙ ответ (3-5 предложений) с главной рекомендацией."}

ВАЖНО по форматированию:
- Используй HTML-теги: <b>жирный</b> и <i>курсив</i>
- НЕ используй Markdown (**, ##, ### и т.д.)
- Используй эмодзи для визуального выделения (💰📈📉🔄 и т.д.)
- НЕ пиши ЗАГЛАВНЫМИ БУКВАМИ — это некрасиво
- Числа форматируй с пробелами: 1 234 567 ₽
- Проценты со знаком: +15.3% или -8.2%
- Пиши структурировано, но не перегружай

Если нет данных партнёра — ответь на основе базы знаний.

ВАЖНО: Если выше есть раздел "📚 ИНФОРМАЦИЯ ИЗ БАЗЫ ЗНАНИЙ" — значит вопрос релевантный!
Отвечай на основе этого контекста, даже если слова кажутся необычными (например, "человек-романтик" — это тип сотрудника из обучения, а не про романтические отношения).

Отклоняй ТОЛЬКО вопросы, которые явно не связаны с бизнесом барбершопов и для которых НЕТ контекста из базы знаний.
"""

        # 4. Запрос к GPT
        logger.info(f"🤖 [AI] Smart answer request: '{user_message[:50]}...'")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1000 if detailed else 400,
            temperature=0.5,
        )
        
        answer = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else "?"
        logger.info(f"✅ [AI] Smart answer ready (tokens: {tokens})")
        
        return answer.strip() if answer else "Не удалось сформировать ответ."
        
    except Exception as e:
        logger.error(f"❌ [AI] Smart answer error: {e}")
        # Фоллбэк на обычный ответ из базы знаний
        kb_answer = await get_knowledge_answer(user_message, detailed)
        return kb_answer or "Произошла ошибка. Попробуйте позже."


async def get_ai_suggestion(user_message: str) -> str | None:
    """
    Получить AI-подсказку для пользователя на основе его сообщения.
    
    Returns:
        Текст подсказки или None если AI недоступен
    """
    if not client:
        logger.warning("⚠️ [AI] OpenAI API key not configured - using fallback")
        return None
    
    try:
        logger.info(f"🤖 [AI] Sending request to OpenAI: '{user_message[:50]}...'")
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Быстрая и дешёвая модель
            messages=[
                {"role": "system", "content": BOT_CAPABILITIES},
                {"role": "user", "content": f"Пользователь написал: \"{user_message}\"\n\nПомоги ему найти нужный раздел в боте."}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        
        suggestion = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else "?"
        
        logger.info(f"✅ [AI] OpenAI response received (tokens: {tokens_used})")
        return suggestion.strip() if suggestion else None
        
    except Exception as e:
        logger.error(f"❌ [AI] OpenAI API error: {e}")
        return None


def get_fallback_suggestion(user_message: str) -> str:
    """
    Простая подсказка на основе ключевых слов (без AI).
    Используется если OpenAI недоступен.
    """
    message_lower = user_message.lower()
    
    # Ключевые слова для разных разделов
    keywords = {
        "tasks": ["задач", "заявк", "создать", "поставить", "отправить", "проблем"],
        "statistics": ["статистик", "выручк", "доход", "заработ", "рейтинг", "место", "денег", "денежн"],
        "account": ["аккаунт", "профиль", "барбершоп", "салон", "добавить", "привязать"],
        "useful": ["полезн", "информац", "связаться", "контакт", "офис", "маркетинг", "развити", "дизайн"],
        "learning": ["обучен", "kpi", "показател", "план", "мотивац", "сотрудник", "персонал", 
                     "как делать", "как считать", "что такое", "расскажи", "объясни"],
    }
    
    for section, words in keywords.items():
        if any(word in message_lower for word in words):
            if section == "tasks":
                return "💡 Для работы с задачами нажмите «📋 Задачи» в главном меню."
            elif section == "statistics":
                return "💡 Для просмотра статистики нажмите «📊 Статистика» в главном меню."
            elif section == "account":
                return "💡 Для управления аккаунтом и барбершопами нажмите «👤 Аккаунт»."
            elif section == "useful":
                return "💡 Полезная информация и контакты отделов — в разделе «📚 Полезное»."
            elif section == "learning":
                return "💡 Для вопросов по обучению нажмите «🤖 AI-ассистент» — он ответит на ваши вопросы."
    
    # Общая подсказка
    return (
        "🤔 Не совсем понял, что вы хотите сделать.\n\n"
        "Используйте кнопки меню:\n"
        "• 📋 Задачи — создать или посмотреть задачи\n"
        "• 📊 Статистика — выручка и рейтинг\n"
        "• 📚 Полезное — информация и контакты\n"
        "• 👤 Аккаунт — ваш профиль\n"
        "• 🤖 AI-ассистент — вопросы по обучению"
    )

