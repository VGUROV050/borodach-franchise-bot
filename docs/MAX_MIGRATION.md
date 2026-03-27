# Миграция бота на мессенджер MAX

> **Статус:** Планирование  
> **Дата:** 2026-03-27  
> **Цель:** Параллельный запуск бота в MAX наряду с Telegram

---

## 1. Обзор

Текущий бот работает на **Telegram** через фреймворк **aiogram 3.x**.  
Планируется запуск параллельного бота в мессенджере **MAX** (dev.max.ru) с использованием **maxapi-sdk**.

### Стратегия: Dual-Messenger Architecture

Вместо полной миграции создаём **абстрактный transport layer**, позволяющий
одной бизнес-логике работать с обоими мессенджерами одновременно.

```
┌─────────────┐  ┌─────────────┐
│  Telegram    │  │    MAX      │
│  (aiogram)   │  │ (maxapi-sdk)│
└──────┬───────┘  └──────┬──────┘
       │                 │
       ▼                 ▼
┌──────────────────────────────┐
│     Messenger Abstraction    │
│  (общие интерфейсы/адаптеры) │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Business Logic         │
│  handlers, FSM, keyboards    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│     Shared Services          │
│  DB, Bitrix, YClients, AI    │
└──────────────────────────────┘
```

---

## 2. Сравнение SDK: aiogram vs maxapi-sdk

| Концепция | aiogram 3.x (Telegram) | maxapi-sdk 0.12+ (MAX) |
|---|---|---|
| Инициализация | `Bot(token=...)` | `Bot(token=...)` |
| Диспетчер | `Dispatcher(storage=MemoryStorage())` | `Dispatcher(storage=MemoryStorage())` |
| Роутер | `Router()` | `Router()` (через `Dispatcher`) |
| FSM | `StatesGroup`, `State`, `FSMContext` | `StatesGroup`, `State`, `FSMContext` |
| FSM Storage | `MemoryStorage()` | `MemoryStorage()` |
| Команды | `CommandStart()` | `Command("start")` |
| Фильтры текста | `F.text == "..."` | Через декоратор / фильтр |
| Состояния | `@router.message(MyState.step)` | `@dp.message_created(StateFilter(MyState.step))` |
| Middleware | `BaseMiddleware` | Middleware через `Router` |
| Callback-кнопки | `InlineKeyboardMarkup` + `CallbackQuery` | `InlineKeyboardBuilder` + `message_callback` |
| Polling | `dp.start_polling(bot)` | `dp.start_polling(bot)` |
| Webhook | Поддерживается | `dp.handle_webhook(...)` |
| Отправка сообщений | `message.answer(text, reply_markup=...)` | `message.answer(text, keyboard=...)` |
| Редактирование | `message.edit_text(...)` | `PUT /messages/{messageId}` |
| Удаление | `message.delete()` | `DELETE /messages/{messageId}` |
| Файлы | `bot.get_file()` + `bot.download_file()` | Upload API (multipart/resumable) |

---

## 3. Матрица совместимости функций

### 3.1. Полная поддержка (минимальные изменения)

| Функция | Файлы | Комментарий |
|---|---|---|
| FSM (все flow) | `handlers.py`, `registration.py` | maxapi-sdk FSM "like aiogram" — аналогичный API |
| Команда /start | `handlers.py` | `Command("start")` в maxapi-sdk |
| HTML-форматирование | Все handlers | MAX поддерживает HTML (format="html") |
| Inline-кнопки (callback) | — | MAX поддерживает `callback`, `link`, `request_contact` и др. |
| Middleware (rate limit, logging) | `middleware.py` | maxapi-sdk поддерживает middleware |
| Long Polling | `main.py` | `dp.start_polling(bot)` — идентичный API |
| Webhook | — | Поддерживается (HTTPS only) |

### 3.2. Требуют переработки (MEDIUM)

| Функция | Файлы | Проблема | Решение для MAX |
|---|---|---|---|
| **Reply-клавиатуры** | `keyboards.py` (все ~25 функций) | MAX **не имеет ReplyKeyboardMarkup** — нет постоянной клавиатуры внизу экрана | Использовать `InlineKeyboardBuilder` с кнопками типа `message` (отправляют текст боту) или `callback` (отправляют callback event) |
| **Получение контакта** | `registration.py`, `keyboards.py` | В Telegram — `KeyboardButton(request_contact=True)` в ReplyKeyboard. В MAX — inline-кнопка типа `request_contact` | Переделать на inline-кнопку `request_contact` |
| **Получение фото/документов** | `handlers.py` (задачи) | В Telegram: `message.photo[-1].file_id`, `bot.get_file()`, `bot.download_file()`. В MAX: другой API вложений | Адаптировать под MAX attachment API |
| **Загрузка файлов в Bitrix** | `handlers.py` (`_create_task_final`) | Скачивание через Telegram File API → нужно через MAX Upload API | Абстрагировать download в messenger adapter |
| **Редактирование сообщений** | `handlers.py` (loading → edit_text) | В MAX: `PUT /messages/{messageId}` | Адаптировать — нужно сохранять message_id |
| **Удаление сообщений** | `handlers.py` (loading_msg.delete()) | В MAX: `DELETE /messages/{messageId}` | Аналогично — адаптировать API вызов |
| **disable_web_page_preview** | `handlers.py` (Полезное, Контакты) | Не документировано в MAX API | Возможно не поддерживается — проверить |
| **input_field_placeholder** | `keyboards.py` | Специфика Telegram ReplyKeyboard | Не применимо в MAX (нет Reply-клавиатур) |

### 3.3. Требуют полной переделки (MAJOR)

| Функция | Файлы | Проблема | Решение для MAX |
|---|---|---|---|
| **Опросы (Polls)** | `polls.py`, `admin/routes.py` | Telegram: нативные `sendPoll` + `PollAnswer`. MAX: **нет нативных опросов** | Эмулировать через inline-клавиатуру с callback-кнопками. Каждый вариант — callback-кнопка. Ответы ловить через `message_callback`. Хранить в той же таблице `poll_responses` |
| **Рассылки из админки** | `admin/routes.py` (`send_telegram_notification`, `send_broadcast`, `send_poll`) | Все через `api.telegram.org` напрямую | Добавить параллельную отправку через MAX API (`platform-api.max.ru/messages`) |

### 3.4. Не требуют изменений

| Компонент | Почему |
|---|---|
| `database/` (models, crud, connection) | Не зависит от мессенджера |
| `bitrix/` (client, tasks) | Не зависит от мессенджера |
| `yclients/` (client) | Не зависит от мессенджера |
| `knowledge_base/` (RAG, embeddings) | Не зависит от мессенджера |
| `scheduler/` (rating_updater) | Не зависит от мессенджера |
| `cache/` (redis) | Не зависит от мессенджера |
| `config/` (settings, logging) | Добавить MAX_BOT_TOKEN в .env |
| `admin/` (app, auth, templates) | Не зависит (кроме routes — отправка) |
| `bot/ai_assistant.py` | Не зависит — чистая бизнес-логика |
| `bot/partner_analytics.py` | Не зависит — DB + YClients |

---

## 4. Архитектура: Dual-Messenger

### 4.1. Новая структура файлов

```
bot/
├── __init__.py              # Текущий (Telegram)
├── handlers.py              # Текущий (Telegram)
├── keyboards.py             # Текущий (Telegram)
├── registration.py          # Текущий (Telegram)
├── polls.py                 # Текущий (Telegram)
├── middleware.py             # Текущий (Telegram)
├── ai_assistant.py          # Общий (не зависит от мессенджера)
├── partner_analytics.py     # Общий (не зависит от мессенджера)
├── utils.py                 # Общий
│
├── core/                    # НОВОЕ: общая бизнес-логика
│   ├── __init__.py
│   ├── menu.py              # Тексты меню, структура навигации
│   ├── task_flow.py         # Логика создания задачи (без привязки к мессенджеру)
│   ├── registration_flow.py # Логика регистрации
│   ├── stats_flow.py        # Логика статистики
│   └── poll_flow.py         # Логика опросов (абстрактная)
│
└── max/                     # НОВОЕ: MAX-адаптер
    ├── __init__.py
    ├── main.py              # Entry point для MAX бота
    ├── handlers.py          # Хендлеры для MAX
    ├── keyboards.py         # Inline-клавиатуры для MAX
    ├── registration.py      # Регистрация в MAX
    ├── polls.py             # Эмуляция опросов через inline-кнопки
    └── middleware.py         # Middleware для MAX
```

### 4.2. Точки входа

```python
# main.py — Telegram бот (без изменений)
asyncio.run(main())

# main_max.py — MAX бот (новый файл)
asyncio.run(main_max())
```

Оба процесса работают параллельно, используя **одну БД** PostgreSQL.

### 4.3. Конфигурация (.env)

```env
# Telegram (существующие)
TELEGRAM_BOT_TOKEN=...

# MAX (новые)
MAX_BOT_TOKEN=...
MAX_WEBHOOK_URL=...          # Для production
MAX_WEBHOOK_SECRET=...       # Для webhook
```

---

## 5. Детальный план по файлам

### 5.1. `bot/max/keyboards.py` — Клавиатуры для MAX

Все 25+ функций клавиатур из `bot/keyboards.py` нужно переписать.

**Telegram (текущий):**
```python
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Задачи"), KeyboardButton(text="📚 Полезное")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🤖 AI-ассистент")],
            [KeyboardButton(text="👤 Аккаунт"), KeyboardButton(text="📞 Связаться")],
        ],
        resize_keyboard=True,
    )
```

**MAX (новый):**
```python
from maxapi import InlineKeyboardBuilder

def main_menu_keyboard() -> InlineKeyboardBuilder:
    return (
        InlineKeyboardBuilder()
        .message("📋 Задачи", "📋 Задачи")
        .message("📚 Полезное", "📚 Полезное")
        .message("📊 Статистика", "📊 Статистика")
        .message("🤖 AI-ассистент", "🤖 AI-ассистент")
        .message("👤 Аккаунт", "👤 Аккаунт")
        .message("📞 Связаться", "📞 Связаться")
        .adjust(2, 2, 2)
    )
```

> **Ключевое отличие UX:** В Telegram Reply-клавиатура **постоянна** внизу экрана.
> В MAX inline-кнопки привязаны к конкретному сообщению.
> Это значит, что после каждого ответа бота нужно заново отправлять кнопки.
> Кнопки типа `message` при нажатии отправляют текстовое сообщение боту — 
> это ближайший аналог Reply-кнопок в Telegram.

### 5.2. `bot/max/handlers.py` — Хендлеры для MAX

**Основные отличия:**

1. Декоратор `@dp.message_created()` вместо `@router.message()`
2. Фильтр `StateFilter(...)` вместо передачи состояния первым аргументом
3. `event.message.answer()` вместо `message.answer()`
4. `keyboard=...` вместо `reply_markup=...`
5. Формат сообщений: нужно добавлять `format="html"` для HTML

**Telegram (текущий):**
```python
@router.message(F.text == BTN_TASKS)
async def tasks_menu_handler(message: types.Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "📋 <b>Задачи</b>\n\nВыберите действие:",
        reply_markup=tasks_menu_keyboard(),
    )
```

**MAX (новый):**
```python
@dp.message_created()
async def tasks_menu_handler(event, state):
    if event.message.body.text != BTN_TASKS:
        return
    await state.clear()
    await event.message.answer(
        "📋 <b>Задачи</b>\n\nВыберите действие:",
        keyboard=tasks_menu_keyboard(),
        format="html",
    )
```

### 5.3. `bot/max/registration.py` — Регистрация

**Запрос контакта:**

Telegram: `KeyboardButton(text="📱 Поделиться контактом", request_contact=True)` в ReplyKeyboard.

MAX: inline-кнопка типа `request_contact`:
```python
keyboard = (
    InlineKeyboardBuilder()
    .request_contact("📱 Поделиться контактом")
    .adjust(1)
)
```

Событие получения контакта в MAX приходит иначе — нужно обработать 
соответствующий callback от кнопки `request_contact`.

### 5.4. `bot/max/polls.py` — Эмуляция опросов

В MAX нет нативных опросов. Эмулируем через inline-клавиатуру:

```python
async def send_poll_to_user(bot, chat_id: int, poll, partner_id: int):
    """Отправить опрос через inline-кнопки."""
    keyboard = InlineKeyboardBuilder()
    
    for i, option in enumerate(poll.options):
        keyboard.callback(
            option.text,
            f"poll:{poll.id}:{i}:{partner_id}"
        )
    
    keyboard.adjust(1)  # По одной кнопке в ряд
    
    await bot.send_message(
        chat_id=chat_id,
        text=f"📊 <b>{poll.question}</b>\n\nВыберите вариант:",
        keyboard=keyboard,
        format="html",
    )


@dp.message_callback()
async def handle_poll_callback(callback_event, state):
    """Обработка голоса в опросе."""
    payload = callback_event.callback.payload
    
    if not payload.startswith("poll:"):
        return
    
    _, poll_id, option_idx, partner_id = payload.split(":")
    
    # Сохраняем ответ в БД (та же таблица poll_responses)
    async with AsyncSessionLocal() as db:
        await save_poll_response(
            db,
            poll_id=int(poll_id),
            partner_id=int(partner_id),
            option_ids=[poll.options[int(option_idx)].id],
        )
    
    await callback_event.answer(notification="✅ Ваш голос учтён!")
```

### 5.5. `admin/routes.py` — Рассылки и уведомления

Добавить параллельную отправку через MAX:

```python
from config.settings import MAX_BOT_TOKEN

async def send_max_notification(chat_id: int, text: str) -> bool:
    """Отправить уведомление через MAX Bot API."""
    if not MAX_BOT_TOKEN:
        return False
    
    url = "https://platform-api.max.ru/messages"
    headers = {"Authorization": MAX_BOT_TOKEN}
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "format": "html",
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers)
            return response.status_code == 200
    except Exception:
        return False
```

> **Важно:** Пользователи в MAX и Telegram имеют **разные ID**.
> В модели `Partner` нужно добавить поле `max_user_id` (nullable)
> для хранения ID пользователя в MAX.

### 5.6. `database/models.py` — Изменения моделей

```python
class Partner(Base):
    # ... существующие поля ...
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    max_user_id = Column(BigInteger, unique=True, nullable=True)  # НОВОЕ
    
    # При отправке уведомлений проверяем оба ID
```

Миграция Alembic:
```python
# migrations/versions/xxx_add_max_user_id.py
op.add_column('partners', sa.Column('max_user_id', sa.BigInteger(), nullable=True))
op.create_index('ix_partners_max_user_id', 'partners', ['max_user_id'], unique=True)
```

### 5.7. `bot/max/main.py` — Точка входа MAX бота

```python
import asyncio
import os
from maxapi import Bot, Dispatcher, MemoryStorage

from config.settings import MAX_BOT_TOKEN
from database import init_db, close_db
from cache import init_cache, close_cache

async def main_max():
    if not MAX_BOT_TOKEN:
        raise RuntimeError("MAX_BOT_TOKEN не задан в .env")
    
    await init_db()
    await init_cache()
    
    bot = Bot(token=MAX_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    # Регистрируем хендлеры MAX
    from bot.max.handlers import setup_handlers
    from bot.max.registration import setup_registration
    from bot.max.polls import setup_polls
    
    setup_registration(dp)
    setup_handlers(dp)
    setup_polls(dp)
    
    try:
        await dp.start_polling(bot)
    finally:
        await close_cache()
        await close_db()

if __name__ == "__main__":
    asyncio.run(main_max())
```

---

## 6. Модификации в `admin/routes.py` для dual-messenger

### 6.1. Отправка уведомлений

Текущая функция `send_telegram_notification()` вызывается из ~10 мест.
Нужно создать универсальную обёртку:

```python
async def send_notification(partner, text: str, **kwargs) -> dict:
    """Отправить уведомление партнёру во все его мессенджеры."""
    results = {"telegram": False, "max": False}
    
    if partner.telegram_id:
        results["telegram"] = await send_telegram_notification(
            partner.telegram_id, text, **kwargs
        )
    
    if partner.max_user_id:
        results["max"] = await send_max_notification(
            partner.max_user_id, text
        )
    
    return results
```

### 6.2. Отправка опросов

В admin/routes.py функция `send_poll` использует Telegram `sendPoll` API.
Для MAX нужно отправлять inline-клавиатуру с вариантами.

```python
# В send_poll():
# Для каждого партнёра:
if partner.telegram_id:
    # Отправляем нативный Telegram poll (как сейчас)
    ...
if partner.max_user_id:
    # Отправляем эмулированный poll через MAX inline-кнопки
    await send_max_poll(partner.max_user_id, poll)
```

### 6.3. Рассылки (broadcast)

Аналогично — рассылать в оба мессенджера:
```python
for partner in partners:
    if partner.telegram_id:
        result = await send_telegram_notification(partner.telegram_id, message, ...)
    if partner.max_user_id:
        result = await send_max_notification(partner.max_user_id, message)
```

---

## 7. Особенности UX в MAX

### 7.1. Навигация без Reply-клавиатур

| Telegram | MAX |
|---|---|
| Постоянная клавиатура внизу экрана | Inline-кнопки под каждым сообщением |
| Пользователь всегда видит меню | Кнопки видны только под последним сообщением |
| Можно нажать "🏠 Главное меню" в любой момент | Нужно скроллить к последнему сообщению |

**Решение:** Отправлять кнопку "🏠 Главное меню" с **каждым** ответом бота.
Использовать кнопку типа `message` (отправляет текст) для навигационных кнопок,
и `callback` для действий, не требующих нового сообщения.

### 7.2. Текстовая навигация

Текущий бот сильно полагается на фильтры `F.text == "📋 Задачи"` и т.д.
В MAX можно сохранить эту логику:

- Кнопки типа `message` отправляют текст → бот получает `message_created` event
- Фильтруем по `event.message.body.text` — та же логика, что и в Telegram

Это **ключевое архитектурное решение**: кнопки `message` вместо `callback`
позволяют сохранить большую часть логики обработки текстовых команд.

### 7.3. Ограничения inline-клавиатуры MAX

- Максимум 210 кнопок (30 рядов × 7 кнопок)
- Для `request_contact` — максимум 3 кнопки в ряду
- Кнопка `message` отправляет текст в чат (видимый для пользователя)

---

## 8. План работ (этапы)

### Этап 0: Подготовка (1-2 дня)

- [ ] Зарегистрировать бота в MAX через Master Bot на max.ru
- [ ] Получить `MAX_BOT_TOKEN`
- [ ] Добавить `MAX_BOT_TOKEN` в `.env` и `config/settings.py`
- [ ] Установить `maxapi-sdk`: `pip install maxapi-sdk`
- [ ] Добавить в `requirements.txt`
- [ ] Создать миграцию Alembic: добавить `max_user_id` в `Partner`

### Этап 1: Минимальный бот MAX (3-5 дней)

- [ ] Создать `bot/max/` пакет
- [ ] `bot/max/main.py` — entry point с polling
- [ ] `bot/max/keyboards.py` — все клавиатуры через `InlineKeyboardBuilder`
- [ ] `bot/max/handlers.py` — `/start`, главное меню, навигация
- [ ] `bot/max/middleware.py` — rate limit, logging
- [ ] `main_max.py` — запускаемый файл
- [ ] Тест: /start → главное меню → навигация по разделам

### Этап 2: Регистрация (2-3 дня)

- [ ] `bot/max/registration.py` — полный flow регистрации
- [ ] Обработка `request_contact` через inline-кнопку MAX
- [ ] FSM-переходы: контакт → ФИО → барбершоп → владелец → должность
- [ ] Проверка статуса верификации
- [ ] Тест: полный цикл регистрации в MAX

### Этап 3: Задачи (2-3 дня)

- [ ] Создание задач: выбор отдела → барбершоп → заголовок → описание → файлы
- [ ] Обработка фото/документов через MAX attachment API
- [ ] Скачивание файлов из MAX и загрузка в Bitrix
- [ ] Просмотр задач (мои / все)
- [ ] Отмена задачи
- [ ] Тест: полный цикл задач

### Этап 4: Статистика и рейтинг (1-2 дня)

- [ ] Выбор периода статистики
- [ ] Отображение статистики YClients
- [ ] Рейтинг сети (текущий / прошлый месяц)
- [ ] Тест: просмотр всех периодов

### Этап 5: Полезное + AI-ассистент (1-2 дня)

- [ ] Раздел "Полезное" — навигация по отделам
- [ ] Динамические кнопки из БД
- [ ] AI-ассистент — вопросы и ответы
- [ ] Кнопка "Подробнее"
- [ ] Тест: все разделы

### Этап 6: Опросы (2-3 дня)

- [ ] `bot/max/polls.py` — эмуляция опросов через inline callback-кнопки
- [ ] Обработка `message_callback` для голосования
- [ ] `admin/routes.py` — отправка опросов партнёрам MAX
- [ ] Закрытие опросов (обновление сообщения, убирая кнопки)
- [ ] Тест: создание → отправка → голосование → результаты

### Этап 7: Админ-панель (1-2 дня)

- [ ] `send_max_notification()` — отправка уведомлений через MAX API
- [ ] Универсальная обёртка `send_notification()` для обоих мессенджеров
- [ ] Рассылки в MAX
- [ ] Диагностика: проверка MAX API
- [ ] Тест: верификация → уведомление в MAX

### Этап 8: Тестирование и production (2-3 дня)

- [ ] E2E тестирование всех сценариев в MAX
- [ ] Нагрузочное тестирование (30 rps лимит MAX)
- [ ] Настройка webhook для production (HTTPS)
- [ ] Мониторинг: Sentry, Prometheus метрики для MAX
- [ ] Обновить `scripts/run.sh` для запуска обоих ботов
- [ ] Обновить CI/CD (`deploy.yml`)
- [ ] Документация для администраторов

---

## 9. Риски и ограничения

### 9.1. Зрелость maxapi-sdk

| Метрика | Значение |
|---|---|
| Версия | 0.12.2 (Beta) |
| Скачиваний / месяц | ~388 |
| GitHub stars | 44 |
| Python | >= 3.10 |
| Зависимости | aiohttp, pydantic, aiofiles |

**Риск:** Возможны баги, неполная документация, breaking changes в минорных версиях.
**Митигация:** Зафиксировать версию в requirements.txt, покрыть тестами критические пути.

### 9.2. Rate Limiting MAX API

MAX ограничивает 30 rps на `platform-api.max.ru`.
При рассылке 100+ партнёрам нужна задержка между запросами.

**Митигация:** Добавить `asyncio.sleep(0.05)` между отправками в broadcast.

### 9.3. UX деградация

Отсутствие постоянной клавиатуры — самый заметный UX-difference.
Пользователи привыкли к Reply-кнопкам Telegram.

**Митигация:** Тщательно протестировать с реальными пользователями,
подобрать оптимальный layout inline-кнопок.

### 9.4. Два ID у одного партнёра

Один партнёр может иметь аккаунт в Telegram и MAX одновременно.
Нужна привязка `max_user_id` к существующему `Partner`.

**Решение:** При регистрации в MAX проверять по телефону — если партнёр
уже есть (зарегистрирован через Telegram), привязывать `max_user_id`
к существующей записи.

### 9.5. Файлы: processing delay

MAX API требует паузу после загрузки файла перед отправкой сообщения
с вложением (`attachment.not.ready`). Нужно реализовать retry-логику.

---

## 10. Оценка трудозатрат

| Этап | Трудозатраты | Зависимости |
|---|---|---|
| 0. Подготовка | 1-2 дня | Регистрация бота в MAX |
| 1. Минимальный бот | 3-5 дней | Этап 0 |
| 2. Регистрация | 2-3 дня | Этап 1 |
| 3. Задачи | 2-3 дня | Этап 2 |
| 4. Статистика | 1-2 дня | Этап 1 |
| 5. Полезное + AI | 1-2 дня | Этап 1 |
| 6. Опросы | 2-3 дня | Этап 1 |
| 7. Админ-панель | 1-2 дня | Этап 1 |
| 8. Production | 2-3 дня | Все этапы |
| **Итого** | **~15-23 рабочих дня** | |

> Этапы 4, 5, 6, 7 можно выполнять параллельно после завершения этапа 1.

---

## 11. Чеклист перед началом

- [ ] Получен доступ к MAX для организации (верифицированный профиль)
- [ ] Создан бот через Master Bot в MAX
- [ ] Получен `MAX_BOT_TOKEN`
- [ ] maxapi-sdk установлен и протестирован (`pip install maxapi-sdk`)
- [ ] Проведён smoke-test: echo-бот в MAX работает
- [ ] Решение по UX: `message` кнопки vs `callback` кнопки
- [ ] Миграция БД: `max_user_id` добавлен в Partner

---

## 12. Полезные ссылки

- [MAX API Documentation](https://dev.max.ru/docs-api)
- [maxapi-sdk на PyPI](https://pypi.org/project/maxapi-sdk/)
- [maxapi-sdk на GitHub](https://github.com/Maxi-online/maxapi-sdk)
- [MAX Bot API Schema](https://github.com/max-messenger/max-bot-api-schema)
- [Регистрация бота в MAX](https://dev.max.ru/help/chatbots)
