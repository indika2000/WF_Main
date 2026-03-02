# Mobile SDK — System Guide

Detailed reference for the architecture, behavior, and internal mechanics of the WildernessFriends mobile SDK layer.

---

## File Structure

```
WildernessFriends/
├── .env                      # EXPO_PUBLIC_* env vars
├── services/
│   ├── api.ts                # Axios instance + interceptors
│   ├── tokenManager.ts       # JWT lifecycle management
│   ├── permissions.ts        # Permissions SDK
│   ├── cart.ts               # Cart SDK
│   ├── commerce.ts           # Commerce/checkout/subscriptions/profile SDK
│   ├── images.ts             # Image SDK
│   ├── llm.ts                # LLM generation SDK
│   ├── chat.ts               # Chat SDK
│   └── devTools.ts           # Dev webhook simulator SDK
├── hooks/
│   └── useApi.ts             # useApi + useMutation hooks
├── context/
│   └── AuthContext.tsx       # Firebase auth + token exchange integration
├── types/
│   └── index.ts              # All TypeScript type definitions
└── app/(tabs)/
    ├── _layout.tsx           # Tab config (dev-tools hidden in prod)
    └── dev-tools.tsx         # Dev tools testing screen
```

---

## API Client (services/api.ts)

### Axios Instance Configuration

- `baseURL`: read from `process.env.EXPO_PUBLIC_API_URL`
- `timeout`: 30 seconds (30000ms)
- Default headers: `Content-Type: application/json`

### Request Interceptor

On every outbound request:

1. Calls `tokenManager.getToken()` to retrieve the cached JWT (auto-refreshing if within 60 seconds of expiry).
2. If a token is returned, injects `Authorization: Bearer <token>` into the request headers.
3. If no token is available (user not authenticated), the request proceeds without an authorization header.

### Response Interceptor — Success Path

The gateway wraps all responses in a `{ success, data, message }` envelope. The success interceptor unwraps this automatically:

- Returns `response.data.data` directly to the calling SDK function.
- The caller never sees the envelope — it receives the inner payload only.

**Critical:** Because of this unwrapping, SDK consumers must never access `.data.data` on a result. The data is already unwrapped.

### Response Interceptor — Error Path

**401 Unauthorized:**

1. If the request has not already been retried (`_retry` flag not set), marks `config._retry = true`.
2. Calls `tokenManager.refreshToken()` to force a new JWT via `exchangeToken()`.
3. Retries the original request with the fresh token injected.
4. If the retry also fails with 401, the error propagates normally (no infinite loop).

**All other errors:**

Normalized to a consistent shape before being thrown:

```ts
{
  success: false,
  message: string,   // human-readable error description
  error_code: string // machine-readable error code from gateway
}
```

---

## Token Manager (services/tokenManager.ts)

### Module-Level State

The token manager maintains three module-level (singleton) variables:

| Variable | Type | Description |
|---|---|---|
| `cachedToken` | `string \| null` | The current JWT string |
| `tokenExpiry` | `number` | Unix timestamp (seconds) when the token expires |
| `cachedUserData` | `AuthTokenResponse["user"] \| null` | Last user object returned by token exchange |

Because these are module-level, they persist across component re-renders for the lifetime of the app process.

### exchangeToken()

Full token acquisition flow:

1. Gets the current Firebase user from `auth.currentUser`. Throws if no user is authenticated.
2. Calls `getIdToken(true)` on the Firebase user to force-refresh the Firebase ID token.
3. POSTs the Firebase ID token to `/auth/token` on the gateway.
4. On success, stores the returned JWT in `cachedToken` and the user object in `cachedUserData`.
5. Decodes the JWT payload using `atob()` (client-side base64 decode only — no signature verification) to extract the `exp` claim.
6. Stores the extracted `exp` value in `tokenExpiry`.

### getToken()

Cached token retrieval with proactive refresh:

```
if cachedToken exists AND Date.now()/1000 < tokenExpiry - 60:
    return cachedToken  // still valid, 60+ seconds remaining
else:
    return exchangeToken()  // expired or expiring soon, fetch fresh
```

The 60-second buffer ensures tokens are refreshed before they actually expire, preventing race conditions where a token expires between the check and the API call.

### refreshToken()

Always calls `exchangeToken()` unconditionally. Used by the 401 retry path in the response interceptor, where a cached-but-apparently-invalid token must be replaced regardless of its claimed expiry.

### clearToken()

Sets all three module-level variables to `null` / `0`. Called on logout to ensure no stale credentials remain.

### getCachedUserData()

Returns `cachedUserData` directly. No network call. Returns `null` if `exchangeToken()` has never successfully run in the current session.

---

## Auth Context (context/AuthContext.tsx)

### AuthContextType

```ts
interface AuthContextType {
  user: FirebaseUser | null;
  loading: boolean;
  error: string | null;
  apiReady: boolean;
  permissions: UserPermissions | null;
  setError: (msg: string | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}
```

### exchangeAndSetToken()

Internal helper called after Firebase auth state confirms a user is signed in:

1. Calls `tokenManager.exchangeToken()` to get gateway JWT and user data.
2. Extracts from the returned user object:
   - `role`
   - `is_premium`
   - `permissions` map
   - `subscription` details
3. Constructs a `UserPermissions` object and sets it in context state.
4. Sets `apiReady = true` on success.
5. On any failure, sets `apiReady = false` and logs the error. Does not throw — the app continues in a degraded state where API calls cannot be made.

### onAuthStateChanged Handler

Firebase's auth state listener drives all session lifecycle:

**When a user is detected (sign-in or app resume):**

1. Calls `await exchangeAndSetToken()` to complete the full token setup.
2. Only calls `setLoading(false)` after token exchange resolves (success or failure).
3. This ensures `apiReady` is in its final state before the app renders authenticated screens.

**When no user is detected (sign-out or session expired):**

1. Calls `tokenManager.clearToken()` to wipe cached JWT.
2. Sets `user = null`, `permissions = null`, `apiReady = false`.
3. Calls `setLoading(false)`.
4. The root `_layout.tsx` auth guard redirects to `/login`.

### login(email, password)

Calls Firebase `signInWithEmailAndPassword`. The `onAuthStateChanged` listener handles the rest (token exchange, permissions, apiReady).

### register(email, password)

Calls Firebase `createUserWithEmailAndPassword`. Same post-registration flow via `onAuthStateChanged`.

### logout()

Explicit three-step logout to ensure clean state:

1. `tokenManager.clearToken()` — wipe JWT before Firebase sign-out.
2. `auth.signOut()` — sign out of Firebase.
3. Clear all local context state (user, permissions, apiReady, error).

### Firebase Error Translation

Raw Firebase error codes are translated to user-readable strings before being stored in `error` state:

| Firebase Code | User-Facing Message |
|---|---|
| `auth/invalid-email` | "Invalid email address." |
| `auth/wrong-password` | "Incorrect password." |
| `auth/user-not-found` | "No account found with this email." |
| `auth/email-already-in-use` | "An account with this email already exists." |
| `auth/weak-password` | "Password must be at least 6 characters." |
| `auth/too-many-requests` | "Too many attempts. Please try again later." |
| *(other)* | "An authentication error occurred." |

---

## Hooks (hooks/useApi.ts)

### useApi\<T\>(fetcher)

Data fetching hook. Fires on mount and whenever `refetch` is called.

**Internal behavior:**

1. Creates a `mountedRef` with `useRef(true)`, set to `false` in the cleanup function of the `useEffect`.
2. All `setState` calls are guarded by `if (mountedRef.current)` to prevent memory leaks and React warnings when components unmount before a fetch resolves.
3. `refetch` is wrapped in `useCallback([fetcher])` — it only changes identity if `fetcher` changes identity.
4. **Callers must stabilize `fetcher` with their own `useCallback`** to avoid triggering an infinite re-fetch loop. Passing an inline arrow function as `fetcher` will cause the hook to re-fetch on every render.

**Returns:**

```ts
{
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}
```

### useMutation\<T, A\>(mutator)

Action hook for write operations. Does not fetch on mount.

**Internal behavior:**

1. `execute(args)` sets `loading = true`, clears previous `error`, calls `mutator(args)`.
2. On success: sets `data`, clears `error`, sets `loading = false`.
3. On failure: sets `error`, sets `loading = false`, then **re-throws the error** so callers can handle it inline if needed.
4. `reset()` sets `data = null`, `error = null`, `loading = false` — useful for resetting a form after submission.

**Returns:**

```ts
{
  execute: (args: A) => Promise<T>;
  data: T | null;
  loading: boolean;
  error: string | null;
  reset: () => void;
}
```

---

## Type System (types/index.ts)

### Core Types

| Type | Description |
|---|---|
| `ApiResponse<T>` | Gateway envelope: `{ success: boolean, data: T, message: string }` |
| `ApiError` | Normalized error: `{ success: false, message: string, error_code: string }` |
| `PaginatedData<T>` | Paginated list: `{ items: T[], total: number, page: number, page_size: number }` |

### Auth Types

| Type | Key Fields |
|---|---|
| `AuthTokenResponse` | `token: string`, `user: { id, email, role, is_premium, permissions, subscription }` |

### Permissions Types

| Type | Description |
|---|---|
| `UserPermissions` | Map of permission keys to boolean values, plus `role` and `is_premium` |

### Cart Types

| Type | Key Fields |
|---|---|
| `CartItem` | `id`, `product_id`, `name`, `quantity`, `unit_price`, `subtotal` |
| `Cart` | `user_id`, `items: CartItem[]`, `total` |
| `CartItemAdd` | Input shape for `addItem()`: `product_id`, `quantity` |

### Commerce Types

| Type | Description |
|---|---|
| `PaymentCreation` | Stripe payment intent details: `client_secret`, `payment_intent_id`, `amount` |
| `OrderConfirmation` | Confirmed order summary post-payment |
| `OrderItem` | Line item within an order |
| `Order` | Full order record with items, status, timestamps |
| `Subscription` | Subscription record: `tier`, `status`, `current_period_end`, `cancel_at_period_end` |
| `SubscriptionCreation` | Stripe subscription setup details |
| `Address` | Shipping/billing address fields |
| `CommerceProfile` | User profile with saved addresses and payment preferences |

### Image Types

| Type | Key Fields |
|---|---|
| `ImageRecord` | `id`, `user_id`, `url`, `category`, `metadata`, `created_at` |

### LLM Types

| Type | Description |
|---|---|
| `GenerateTextResponse` | `text: string`, `provider`, `model`, `usage` |
| `GenerateImageResponse` | `image_id`, `url`, `prompt`, `provider` |
| `LLMProvider` | `name`, `status`, `models: string[]`, `capabilities` |

### Chat Types

| Type | Key Fields |
|---|---|
| `ChatMessage` | `role: "user" \| "assistant"`, `content`, `timestamp` |
| `Conversation` | `id`, `user_id`, `messages: ChatMessage[]`, `created_at`, `updated_at` |

---

## Dev Tools Screen (app/(tabs)/dev-tools.tsx)

### Visibility

The dev tools tab is conditionally shown based on the `__DEV__` flag. In `app/(tabs)/_layout.tsx`, the tab's `href` is set to `null` when `!__DEV__`, which removes it from the tab bar entirely in production builds. The route file itself is still bundled but is inaccessible without the tab entry.

### Sections

The screen is organized into five testing sections:

**1. Cart**

- Add a hardcoded test item to the cart.
- View current cart state (displays as JSON).
- Clear the entire cart.

**2. Checkout**

- Validate the current cart against inventory/pricing rules.
- Create a payment intent (Stripe) for the current cart.

**3. Subscriptions**

- View the current subscription record.
- Create a new premium-tier subscription.
- Cancel the active subscription.

**4. Webhook Simulator**

- Dropdown/picker with 7 predefined event types (e.g., `payment.succeeded`, `subscription.created`, `subscription.cancelled`).
- Fire button sends the selected event type to `devTools.simulateWebhook()`.
- Accepts optional `userId` and `overrides` to customize the simulated payload.
- Results displayed inline.

**5. State Viewer**

- Reads live from AuthContext: `apiReady`, `role`, `is_premium`, `tier`.
- Fetches and displays permissions, order history, and commerce profile as formatted JSON.

### API Readiness Gate

Every action button in the dev tools screen checks `apiReady` from AuthContext before executing. If `apiReady` is false, an `Alert` is shown ("API not connected") and the action is aborted. This prevents confusing errors during auth initialization or token exchange failures.

### Result Display

All API responses are displayed using `JSON.stringify(result, null, 2)` in a monospace-styled `<Text>` component. This makes it easy to inspect raw shapes without a separate inspector tool.

### Context State Panel

A persistent panel at the top (or bottom) of the screen shows live context values:

```
apiReady: true
role: "premium"
is_premium: true
tier: "premium"
```

This updates in real time as context state changes, making it useful for observing permission changes after webhook simulation.

---

## Request Flow Diagram

```
Component
    |
    | calls SDK function (e.g., getCart(userId))
    v
services/cart.ts
    |
    | calls apiClient.get('/cart/...')
    v
services/api.ts — Request Interceptor
    |
    | tokenManager.getToken()
    |    |
    |    | cached & valid?  ──yes──> return cachedToken
    |    |
    |    no
    |    |
    |    | tokenManager.exchangeToken()
    |    |    |
    |    |    | Firebase getIdToken(true)
    |    |    | POST /auth/token
    |    |    | cache JWT + expiry + user data
    |    |    v
    |    | return new token
    |    v
    | inject Authorization: Bearer <token>
    v
HTTP Request to Gateway
    |
    v
services/api.ts — Response Interceptor
    |
    | success? ──> unwrap envelope, return data
    |
    | 401?    ──> refreshToken() + retry once
    |
    | other?  ──> normalize error, throw
    v
SDK function returns unwrapped data to component
```

---

## Common Pitfalls

**Double `.data` access:**
SDK functions return the inner payload. Do not write `result.data` — it is already unwrapped.

```ts
// Wrong
const cart = await getCart(userId);
console.log(cart.data.items); // undefined

// Correct
const cart = await getCart(userId);
console.log(cart.items);
```

**Unstabilized fetcher in useApi:**
Passing a new function reference on every render causes infinite fetching.

```ts
// Wrong — new arrow function every render
const { data } = useApi(() => getCart(userId));

// Correct — stable reference
const fetcher = useCallback(() => getCart(userId), [userId]);
const { data } = useApi(fetcher);
```

**Checking apiReady before API calls:**
Always verify `apiReady` is true before calling SDK functions in components. During auth initialization, `apiReady` is false even if the user object is set.

```ts
const { apiReady } = useAuth();
if (!apiReady) return <LoadingScreen />;
```

**Calling devTools in production:**
The `devTools.ts` functions make requests to dev-only gateway endpoints. Always guard with `__DEV__` or rely on the tab visibility gating.
