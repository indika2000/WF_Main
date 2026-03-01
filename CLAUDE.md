# WildernessFriends - Project Instructions

## Project Overview
WildernessFriends is a collectible card mobile app built with React Native and Expo Go. Players scan barcodes/QR codes to collect wildlife-themed cards with varying rarities. The app features animated flip-cards with rarity-based shimmer effects.

## Repository Structure
```
WF_Main/
├── CLAUDE.md                  # This file - project truths and guidelines
├── documents/                 # Project planning docs, specs, and design docs
│   └── Planning/              # Architecture plans (00-06)
├── WildernessFriends/         # React Native / Expo Go front-end app
│   ├── app/                   # Expo Router file-based routing
│   │   ├── _layout.tsx        # Root layout with auth guard
│   │   ├── index.tsx          # Splash/loading screen with auth redirect
│   │   ├── login.tsx          # Login/register screen with video background
│   │   ├── scanner.tsx        # Camera barcode/QR scanner (VisionCamera)
│   │   ├── globals.css        # Tailwind CSS entry
│   │   └── (tabs)/            # Authenticated tab navigator
│   │       ├── _layout.tsx    # Tab bar config
│   │       └── index.tsx      # Home screen - card display, scan results
│   ├── components/            # FlipCard, CardShimmer, ScanResultDisplay, VideoBackground
│   ├── config/firebase.ts     # Firebase init with AsyncStorage persistence
│   ├── context/AuthContext.tsx # Firebase auth context provider
│   ├── types/index.ts         # Shared TypeScript types
│   ├── assets/                # images/card_designs/, videos/
│   ├── app.config.js          # Expo config
│   ├── tailwind.config.js     # NativeWind / Tailwind theme
│   └── .env                   # Firebase keys (EXPO_PUBLIC_FIREBASE_*)
└── services/                  # Backend services (Docker)
    ├── docker-compose.yml     # Base: MongoDB 7, Redis 7, gateway, all services
    ├── docker-compose.dev.yml # Dev overrides: hot-reload, host ports, volume mounts
    ├── .env / .env.example    # Environment config (gitignored / template)
    ├── shared/python/         # Shared Python utils (auth, config, responses, middleware)
    ├── node-gateway/          # Express API Gateway (:3000)
    │   ├── src/               # server, app, config/, middleware/, routes/, utils/
    │   └── tests/             # Jest + supertest
    ├── permissions-service/   # FastAPI Permissions & Entitlements (:5003)
    │   ├── app/               # main, config, database, models/, routes/, services/
    │   └── tests/             # pytest + httpx + mongomock-motor
    ├── llm-service/           # FastAPI Multi-Provider AI Service (:5000)
    │   ├── app/               # main, config, database
    │   │   ├── providers/     # base (Protocol), anthropic, openai, gemini, factory
    │   │   ├── models/        # conversations, generation, providers
    │   │   ├── services/      # generation_service, chat_service, provider_service
    │   │   └── routes/        # health, generate, chat, providers
    │   ├── config/            # providers.yml (provider models, fallback chains)
    │   └── tests/             # pytest + httpx + mongomock-motor
    └── image-service/         # FastAPI Image Upload & Processing (:5001)
        ├── app/               # main, config, database
        │   ├── storage/       # base (Protocol), local (filesystem)
        │   ├── processing/    # image_processor (Pillow variants)
        │   ├── models/        # images (records, presets, variants)
        │   ├── services/      # image_service, generation_proxy
        │   └── routes/        # health, images, user_images, generate
        └── tests/             # pytest + httpx + mongomock-motor
```

## Tech Stack — Mobile
- **Framework:** React Native 0.76 + Expo SDK 52 (Expo Go / dev client)
- **Routing:** Expo Router v4 (file-based)
- **Styling:** NativeWind v4 (Tailwind CSS for RN)
- **Animations:** React Native Reanimated v3
- **Auth:** Firebase Auth (email/password) with AsyncStorage persistence
- **Camera/Scanner:** React Native Vision Camera v4
- **State:** React Context (AuthContext), AsyncStorage for scan result passing
- **TypeScript:** Yes, throughout

## Tech Stack — Backend
- **Gateway:** Node.js 20 + Express, Firebase Admin SDK, jsonwebtoken (HS256), http-proxy-middleware
- **Python Services:** Python 3.12 + FastAPI, motor (async MongoDB), Pydantic v2, PyJWT
- **LLM Providers:** anthropic SDK (Claude), openai SDK (GPT-4o, DALL-E 3), google-genai SDK (Gemini, Imagen)
- **Image Processing:** Pillow (resize variants), aiofiles (async storage), python-magic (MIME validation)
- **Streaming:** sse-starlette (EventSourceResponse for SSE text streaming)
- **Databases:** MongoDB 7.0 (primary store), Redis 7 Alpine (cache, rate limiting)
- **Containerization:** Docker + docker-compose (dev uses volume mounts + hot-reload)
- **Testing:** Jest + supertest (Node), pytest + httpx + mongomock-motor (Python)
- **Shared Python utils:** Imported as `from shared.python.auth import ...` (PYTHONPATH=/app)

## Design System
- **Primary background:** `#0F1A14` (deep forest dark)
- **Secondary background:** `#1A2E22`
- **Forest green:** `#1B3A2D` (DEFAULT), `#2D5A45` (light), `#0F2218` (dark)
- **Accent green:** `#8BB174`
- **Muted text:** `#7A9B88`
- **Light text:** `#D4E8DA`
- **Error red:** `#E53935`
- **Card rarity tiers:** common, uncommon, rare, epic, legendary
- **Orientation:** Portrait-locked
- All custom colors defined in `tailwind.config.js`

## Card Rarity System
Cards have 5 rarity tiers, each with distinct visual shimmer effects:
- **Common** - No shimmer effect
- **Uncommon** - Subtle white light sweep + few motes
- **Rare** - Gold-tinted sweep + gold motes + edge glow
- **Epic** - Multi-color motes (rainbow-ish) + purple edge
- **Legendary** - Full rainbow motes + intense gold edge + fast sweep

Card front artwork files follow the naming pattern: `card-front-{rarity}.png`

## Key Conventions
- Use NativeWind (className) for styling where possible; use StyleSheet for complex/animated styles
- Firebase config loaded from environment variables (`EXPO_PUBLIC_FIREBASE_*` in `.env`)
- File-based routing via Expo Router - route structure mirrors the `app/` directory
- Image assets for cards live in `assets/images/card_designs/`
- Auth guard lives in root `_layout.tsx` - unauthenticated users are redirected to `/login`
- Scanner passes results back to home screen via AsyncStorage (key: `WILDERNESS_LAST_SCAN`)

## Development — Mobile
- Run with: `npx expo start` (Expo Go) or `npx expo start --dev-client`
- Android package: `com.wildernessfriends.app`
- iOS bundle: `com.wildernessfriends.app`
- EAS project ID: `97df2d47-8487-45d4-a058-f5990de6677d`

## Development — Backend
- Start all services: `cd services && docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
- Dev ports: Gateway 3000, LLM 5000, Image 5001, Permissions 5003, MongoDB 27017, Redis 6379
- Dev bypass auth: `Authorization: Bearer dev-bypass` (skips Firebase in non-production)
- Hot-reload: gateway uses nodemon (watches src/), Python services use `uvicorn --reload`
- Note: On Windows/Docker, nodemon may not detect volume-mounted file changes — restart the container with `docker-compose restart gateway` if needed

## Rules for AI Assistants
- Always read files before editing them
- Do not modify `.env` or commit secrets
- Keep card artwork paths consistent: `assets/images/card_designs/card-front-{rarity}.png`
- Preserve the dark forest aesthetic in all UI work
- Use the existing color tokens from `tailwind.config.js` rather than hardcoded hex values where possible
- New screens should follow Expo Router file-based patterns
- Project documents (planning, specs, design docs) go in the `documents/` directory
- Front-end code lives in `WildernessFriends/`, backend code lives in `services/`

### Backend-Specific Rules
- **Docker build context:** Python services that need shared utils must use `services/` as build context (not their own directory), so `COPY shared/ /app/shared/` works. Set `context: .` and `dockerfile: <service>/Dockerfile` in docker-compose.yml
- **Shared Python imports:** Always `from shared.python.<module> import ...` — the `PYTHONPATH=/app` env var in Dockerfiles makes this resolve
- **JSON responses with datetime:** Use the custom `_DateTimeEncoder` in `shared/python/responses.py` — never pass raw datetime objects to `JSONResponse` directly
- **FastAPI route ordering:** Place static routes (e.g., `/tiers`) before parameterized routes (e.g., `/{user_id}`) in the same router to avoid path conflicts
- **Gateway proxy path prefix:** Express strips the router mount prefix, so `http-proxy-middleware` receives only the sub-path. Use `config.pathPrefix` in the `proxyReq` handler to prepend the backend route prefix (see `services.js` and `proxy.js`)
- **Gateway Dockerfile:** Uses `npm install` (not `npm ci`) since no package-lock.json is committed
- **.dockerignore files:** Exist at `services/` (for Python service builds) and `services/node-gateway/` (for gateway builds) — keep these updated when adding new services
- **google-genai SDK:** `types.Part.from_text()` requires keyword arg: `Part.from_text(text="...")`, not positional. Model names may deprecate — `gemini-2.0-flash` was retired, use `gemini-2.5-flash` or later
- **Provider factory pattern:** Providers are Protocol-based (structural subtyping), instantiated only when API keys are present. The factory supports primary/fallback chains — if primary fails, falls back automatically. Config lives in `llm-service/config/providers.yml`
- **Gateway proxy for multi-route services:** If a service has no common route prefix (LLM has `/generate/*`, `/providers/*`, `/health`), set `pathPrefix: ''`. For sub-paths like `/chat/*`, add a separate SERVICE_CONFIG entry with its own `pathPrefix`
- **docker-compose env reload:** `docker-compose restart` does NOT reload `.env` changes — use `docker-compose up -d <service>` to recreate the container with new env vars
- **Image service storage:** Uses `StorageBackend` Protocol with `LocalStorage` impl. Docker volume `image_storage` persists data at `/storage`. Storage is extensible to S3 by implementing the protocol
