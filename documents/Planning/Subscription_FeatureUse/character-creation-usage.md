# Character Creation Usage Tracking

## Overview
Character creation is a metered feature tracked via the permissions service's usage system. The character service checks and records usage server-to-server, so mobile clients cannot bypass limits.

## Subscription Limits

| Tier | Monthly Limit | Price |
|------|--------------|-------|
| Free | 5 | $0 |
| Premium | 25 | $4.99 |
| Ultra | 50 | $9.99 |

No tier has unlimited creations (LLM cost constraint). Extra creations will be sold as purchasable "packs" in a future phase via the bonus system.

## Feature Key
`character_creation` — added to `SUBSCRIPTION_TIERS` in `permissions-service/app/models/subscriptions.py`

## Architecture: Server-to-Server

```
Mobile App                Character Service           Permissions Service
    |                          |                              |
    |-- POST /generate ------->|                              |
    |                          |-- POST /usage/check -------->|
    |                          |<-- {allowed, used, limit} ---|
    |                          |                              |
    |                          | [if allowed: generate]       |
    |                          |                              |
    |                          |-- POST /usage/record ------->|
    |                          |<-- {used, limit, remaining} -|
    |                          |                              |
    |<-- creature + usage -----|                              |
```

- Character service authenticates to permissions service via `X-Api-Key` header (`INTERNAL_API_KEY`)
- Mobile reads usage data for display only (usage bar on creator screen)
- 429 response if limit reached

## Usage Client
`services/character-service/app/services/usage_client.py`
- `check_character_usage(user_id)` — calls `POST /usage/{user_id}/character_creation/check`
- `record_character_usage(user_id)` — calls `POST /usage/{user_id}/character_creation/record`

## Mobile Display
- Creator screen shows usage bar: "X of Y creations this month"
- "Create" button disabled + shows "Limit reached" when remaining = 0
- Usage refreshed after each creation and on screen focus

## Pack Purchases (Future)
The permissions service already supports bonus uses via `POST /usage/{user_id}/{feature}/bonus`. Future commerce integration will add bonus uses when packs are purchased.
