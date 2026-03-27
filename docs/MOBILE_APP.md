# BORODACH Mobile App — Architecture & Dev Guide

## Overview

Native iOS/Android app for franchise partners built with **React Native (Expo)**.
Full-featured app with statistics, tasks, AI assistant, polls, and more.
Light theme (Wio-inspired) with green accent, floating menu, stories, and notification banners.
Distributed via **TestFlight** (iOS). Current build: **#3**.

> The Telegram bot and admin panel remain unchanged.

---

## Architecture

```
┌──────────────────────────┐       ┌─────────────────────────┐
│  React Native (Expo)     │       │  Existing Server        │
│  mobile/                 │       │                         │
│  ┌────────────────────┐  │  REST │  ┌──────────────────┐   │
│  │ Stack + FloatingMenu│──┼──────▶│  │ mobile_api :8001 │   │
│  └────────────────────┘  │       │  └────────┬─────────┘   │
└──────────────────────────┘       │           │             │
                                   │  ┌────────▼─────────┐   │
                                   │  │ services/ layer   │   │
                                   │  └──┬───┬───┬───┬───┘   │
                                   │     │   │   │   │       │
                                   │  ┌──▼┐ ┌▼──┐ ┌▼─┐ ┌▼──┐│
                                   │  │DB │ │YCl│ │Bx│ │AI ││
                                   │  └───┘ └───┘ └──┘ └───┘│
                                   │                         │
                                   │  admin:app :8000  (unchanged)
                                   │  main.py bot      (unchanged)
                                   └─────────────────────────┘
```

### Key decisions

1. **Shared services layer** (`services/`) — business logic extracted from `bot/handlers.py`
   into reusable async functions that return plain dataclasses.
   Both the bot and mobile API call the same services.

2. **Separate FastAPI process** (`mobile_api/`) — runs on port `8001`,
   does not interfere with the admin panel (`:8000`) or bot.

3. **Temporary auth** — `X-Partner-ID` header (hardcoded in the app config).
   Will be replaced with JWT once auth flow is implemented.

---

## Backend

### services/

| File | Functions |
|------|-----------|
| `partner_service.py` | `get_partner_profile(partner_id)`, `get_contact_office_text()`, `request_add_barbershop()` |
| `stats_service.py` | `get_statistics(partner_id, period)` |
| `rating_service.py` | `get_network_rating(partner_id, period)` |
| `useful_service.py` | `get_departments()`, `get_department_content(dept_key)` |
| `task_service.py` | `get_departments_list()`, `get_tasks()`, `create_new_task()`, `cancel_user_task()` |
| `ai_service.py` | `ask_question(question, telegram_id, detailed)` |
| `poll_service.py` | `get_active_polls()`, `vote_in_poll()` |

All functions return dataclasses (not Telegram messages or HTTP responses).

### mobile_api/

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app with lifespan, CORS, router inclusion |
| `deps.py` | `get_current_partner_id()` — dependency (header → int) |
| `schemas.py` | Pydantic response models (30+ schemas) |
| `routes/health.py` | `GET /health` |
| `routes/account.py` | `GET /me`, `GET /companies`, `GET /contact-office`, `POST /barbershop-request` |
| `routes/stats.py` | `GET /stats/{period}` |
| `routes/rating.py` | `GET /rating/{period}` |
| `routes/useful.py` | `GET /useful/departments`, `GET /useful/departments/{key}/buttons` |
| `routes/tasks.py` | `GET /tasks/departments`, `GET /tasks`, `POST /tasks`, `POST /tasks/{id}/cancel` |
| `routes/ai.py` | `POST /ai/ask` |
| `routes/polls.py` | `GET /polls`, `POST /polls/{id}/vote` |

All endpoints prefixed with `/api/v1`.

### Running

```bash
python run_mobile_api.py
# → http://0.0.0.0:8001
# → Swagger: http://localhost:8001/docs
```

---

## Mobile App

### Tech stack

- **Expo SDK 55** (React Native 0.83)
- **Expo Router** — file-based routing (Stack navigator, no tabs)
- **TypeScript** — strict mode

### Project structure

```
mobile/
  src/
    app/
      _layout.tsx              Root layout (Stack, no back buttons)
      index.tsx                Dashboard (stories, notifications, barbershop carousel)
      stats.tsx                Statistics screen
      tasks.tsx                Tasks screen (Bitrix)
      rating.tsx               Rating screen
      create-task.tsx          Multi-step task creation wizard
      useful.tsx               Useful info by department
      ai-chat.tsx              AI assistant chat
      contact.tsx              Contact office info
      polls.tsx                Active polls with voting
      profile-screen.tsx       Partner profile
    components/
      FloatingMenu.tsx         Full-screen menu overlay (replaces tabs)
      StoriesRow.tsx           Horizontal scrollable story circles
      NotificationBanners.tsx  Dismissible notification cards
      ui/                      Reusable atoms (Card, Badge, Skeleton, etc.)
      stats/                   StatsCard, PeriodSelector
      rating/                  RatingRow, RatingTable
    lib/
      api.ts                   Typed fetch wrapper (GET + POST)
      config.ts                API_URL, PARTNER_ID
      types.ts                 TypeScript types (mirrors backend schemas)
      formatters.ts            Currency, date, number formatting
      theme.ts                 Light theme: #F2F2F7 bg, #5CAE5D accent, Helvetica
    hooks/
      useApi.ts                Generic data-fetching hook
  app.json                     Expo config (bundleIdentifier, buildNumber)
  eas.json                     EAS Build config
  tsconfig.json
```

### Navigation

No tab bar. All navigation goes through the **FloatingMenu** — a green circular
button at the bottom of every screen. Pressing it opens a full-screen white overlay
with a 3×3 grid of menu items. Back buttons are disabled on all screens.

### Dashboard (index.tsx)

1. **Greeting** — "Здравствуйте, {name} 👋"
2. **Stories row** — horizontal scroll of circular thumbnails (mock data, admin management planned)
3. **Notification banners** — colored cards (info/warning/success) with dismiss button (mock data, admin management planned)
4. **Barbershop carousel** — swipeable cards, one per barbershop:
   - Barbershop name + city
   - Revenue (big green number)
   - Period label
   - Metrics row: records, avg check, rank position with change arrow
   - **Toggle button** "месяц"/"сегодня" in top-right corner — flips between today and monthly stats with animation
   - Dot indicators for multiple barbershops

### Screens

| Screen | Route | Description |
|--------|-------|-------------|
| Dashboard | `/` | Stories, notifications, barbershop cards carousel |
| Statistics | `/stats` | Period selector, per-salon revenue/records/rank cards |
| Tasks | `/tasks` | Active/all toggle, grouped task list, create/cancel |
| Rating | `/rating` | Network leaderboard, partner salons highlighted |
| Create Task | `/create-task` | 5-step wizard (modal) |
| Useful | `/useful` | Expandable department cards with content |
| AI Chat | `/ai-chat` | Chat bubbles, "Подробнее" button |
| Contact | `/contact` | Office contact info from settings |
| Polls | `/polls` | Radio buttons, vote submission |
| Profile | `/profile-screen` | Name, phone, role, dates, salon list |

### Theme

Light theme (Wio-inspired):
- Background: `#F2F2F7`
- Cards: `#FFFFFF`
- Accent (green): `#5CAE5D`
- Text: `#1A1A1A`
- All borders: `0.5` width (thin lines)
- Font: system default (Helvetica-like)

### Config

Edit `src/lib/config.ts`:

```typescript
export const API_URL = "https://api-franchise-app.borodach.com";
export const PARTNER_ID = 12;
```

---

## Development

### Local dev with iOS Simulator

```bash
# Prerequisites: Xcode + iOS Simulator runtime installed
cd mobile
npx expo start
# Press 'i' to open iOS simulator
```

Hot reload is automatic — any code change reflects instantly.

### Server deployment

Auto-deploy via GitHub Actions on push to `main`:
- Pulls latest code on Beget server
- Runs migrations
- Restarts bot + mobile API

Manual deploy (SSH):
```bash
ssh borodachdev@193.168.48.97
cd /home/borodachdev/apps/borodach-franchise-bot
git pull origin main
bash scripts/run.sh
```

If `git pull` fails due to local changes:
```bash
git stash
git pull origin main
bash scripts/run.sh
```

---

## TestFlight / Build

### Prerequisites

- Apple Developer account
- `eas-cli` installed (`npm install -g eas-cli`)
- Run `eas login`

### Build commands

```bash
cd mobile

# 1. Increment buildNumber in app.json
# 2. Build
eas build --platform ios --profile preview --non-interactive

# 3. Submit to TestFlight (interactive — needs Apple ID)
eas submit --platform ios --latest
```

### Current state

- Bundle ID: `com.borodach.partner`
- App Store Connect: https://appstoreconnect.apple.com/apps/6761262674/testflight/ios
- EAS Project: `ae220f6e-d335-4845-a41c-95917e2b543d`
- Current buildNumber: **3**

---

## Roadmap

1. ✅ Backend API (services + mobile_api)
2. ✅ React Native app (Stack navigator, floating menu, light theme)
3. ✅ TestFlight build & distribution (build #3)
4. ✅ Statistics, Rating, Profile
5. ✅ Tasks (Bitrix: create, view, cancel)
6. ✅ Useful info (departments + content)
7. ✅ AI assistant (chat with RAG + OpenAI)
8. ✅ Contact office
9. ✅ Polls (voting)
10. ✅ Add barbershop request
11. ✅ iOS Simulator dev workflow
12. ✅ UI redesign — light Wio-style theme, floating menu, thin borders
13. ✅ Dashboard: barbershop carousel with today/month toggle
14. ✅ Dashboard: stories row (mock data — admin upload planned)
15. ✅ Dashboard: notification banners (mock data — admin management planned)
16. ⬜ Stories: admin panel for uploading stories content
17. ⬜ Notifications: admin panel for managing notification banners
18. ⬜ JWT authentication (login screen, refresh tokens)
19. ⬜ Push notifications (Expo Push + FCM)
20. ⬜ Chat between partners (отложено — отдельная задача)
