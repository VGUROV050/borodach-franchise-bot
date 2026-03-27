# BORODACH Mobile App — Architecture & Dev Guide

## Overview

Native iOS/Android app for franchise partners built with **React Native (Expo)**.
MVP scope: read-only statistics, network rating, partner profile.
Distributed via **TestFlight** (iOS) and internal builds (Android).

> The Telegram bot and admin panel remain unchanged.

---

## Architecture

```
┌──────────────────────────┐       ┌─────────────────────────┐
│  React Native (Expo)     │       │  Existing Server        │
│  mobile/                 │       │                         │
│  ┌────────────────────┐  │  REST │  ┌──────────────────┐   │
│  │  4 screens + tabs  │──┼──────▶│  │ mobile_api :8001 │   │
│  └────────────────────┘  │       │  └────────┬─────────┘   │
└──────────────────────────┘       │           │             │
                                   │  ┌────────▼─────────┐   │
                                   │  │ services/ layer   │   │
                                   │  └──┬─────────┬─────┘   │
                                   │     │         │         │
                                   │  ┌──▼──┐  ┌──▼──────┐  │
                                   │  │ DB  │  │ YClients │  │
                                   │  └─────┘  └─────────┘  │
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
| `partner_service.py` | `get_partner_profile(partner_id)` |
| `stats_service.py` | `get_statistics(partner_id, period)` |
| `rating_service.py` | `get_network_rating(partner_id, period)` |

All functions return dataclasses (not Telegram messages or HTTP responses).

### mobile_api/

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app with lifespan, CORS, router inclusion |
| `deps.py` | `get_current_partner_id()` — dependency (header → int) |
| `schemas.py` | Pydantic response models |
| `routes/health.py` | `GET /api/v1/health` |
| `routes/account.py` | `GET /api/v1/me`, `GET /api/v1/companies` |
| `routes/stats.py` | `GET /api/v1/stats/{period}` (today, yesterday, current_month, prev_month) |
| `routes/rating.py` | `GET /api/v1/rating/{period}` (current, previous) |

### Running

```bash
python run_mobile_api.py
# → http://0.0.0.0:8001
# → Swagger: http://localhost:8001/docs
```

### Example request

```bash
curl -H "X-Partner-ID: 1" http://localhost:8001/api/v1/me
curl -H "X-Partner-ID: 1" http://localhost:8001/api/v1/stats/current_month
curl -H "X-Partner-ID: 1" http://localhost:8001/api/v1/rating/current
```

---

## Mobile App

### Tech stack

- **Expo SDK 55** (React Native 0.83)
- **Expo Router** — file-based routing
- **TypeScript** — strict mode

### Project structure

```
mobile/
  src/
    app/
      _layout.tsx              Root layout (Stack)
      (tabs)/
        _layout.tsx            Tab navigator (4 tabs)
        index.tsx              Dashboard screen
        stats.tsx              Statistics screen
        rating.tsx             Rating screen
        profile.tsx            Profile screen
    components/
      ui/                      Reusable atoms (Card, Badge, Skeleton, etc.)
      stats/                   StatsCard, PeriodSelector
      rating/                  RatingRow, RatingTable
    lib/
      api.ts                   Typed fetch wrapper
      config.ts                API_URL, PARTNER_ID
      types.ts                 TypeScript types (mirrors backend schemas)
      formatters.ts            Currency, date, number formatting
      theme.ts                 Dark theme colors, spacing, typography
    hooks/
      useApi.ts                Generic data-fetching hook
  app.json                     Expo config
  eas.json                     EAS Build config
  tsconfig.json
```

### Screens

| Screen | Tab | Description |
|--------|-----|-------------|
| Dashboard | 🏠 | Partner greeting, current month revenue, salon list |
| Statistics | 📊 | Period selector, per-salon revenue/records/rank cards |
| Rating | 🏆 | Network leaderboard, partner salons highlighted, period toggle |
| Profile | 👤 | Read-only info: name, phone, role, dates, salon list |

### Theme

Dark theme with barbershop aesthetic:
- Background: `#0F0F1A`
- Cards: `#1A1A2E`
- Accent (gold): `#C9A84C`
- Text: `#EAEAEA`

### Config (TestFlight)

Edit `src/lib/config.ts`:

```typescript
export const API_URL = "https://your-server.com";
export const PARTNER_ID = 1;  // partner DB id for testing
```

---

## TestFlight / Build

### Prerequisites

- Apple Developer account
- `eas-cli` installed (`npm install -g eas-cli`)
- Run `eas login` and `eas build:configure`

### Build commands

```bash
cd mobile

# iOS TestFlight build
eas build --platform ios --profile preview

# Android internal APK
eas build --platform android --profile preview
```

### Updating `eas.json`

Fill in your Apple credentials in `eas.json` → `submit.production.ios`.

---

## Roadmap

1. ✅ Backend API (services + mobile_api)
2. ✅ React Native app (4 screens, dark theme)
3. ⬜ TestFlight build & distribution
4. ⬜ JWT authentication (login screen, refresh tokens)
5. ⬜ Push notifications (Expo Push + FCM)
6. ⬜ Task management (Bitrix integration)
7. ⬜ AI assistant (chat screen)
