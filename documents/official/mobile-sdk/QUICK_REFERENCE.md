# Mobile SDK — Quick Reference

TypeScript SDK layer for the React Native/Expo mobile app. Axios-based HTTP client with automatic JWT management, request/response interceptors, and typed service modules for all backend APIs.

---

## Environment Variables

| Variable | Description |
|---|---|
| `EXPO_PUBLIC_API_URL` | Base URL for the API gateway |

---

## SDK Modules

### tokenManager.ts

| Function | Returns | Purpose |
|---|---|---|
| `exchangeToken()` | `Promise<AuthTokenResponse>` | Exchange Firebase token for gateway JWT |
| `getToken()` | `Promise<string \| null>` | Get cached JWT (auto-refresh if expiring) |
| `refreshToken()` | `Promise<string>` | Force refresh JWT |
| `clearToken()` | `void` | Clear cached JWT (on logout) |
| `getCachedUserData()` | `AuthTokenResponse["user"] \| null` | Last user data from exchange |

---

### permissions.ts

| Function | Returns |
|---|---|
| `getPermissions(userId)` | `Promise<UserPermissions>` |
| `checkPermission(userId, permission)` | `Promise<{ allowed: boolean }>` |

---

### cart.ts

| Function | Returns |
|---|---|
| `getCart(userId)` | `Promise<Cart \| null>` |
| `addItem(userId, item)` | `Promise<Cart>` |
| `updateItem(userId, itemId, quantity)` | `Promise<Cart>` |
| `removeItem(userId, itemId)` | `Promise<Cart>` |
| `clearCart(userId)` | `Promise<void>` |

---

### commerce.ts

| Function | Returns |
|---|---|
| `validateCart(userId)` | `Promise<{ valid: boolean }>` |
| `createPayment(userId)` | `Promise<PaymentCreation>` |
| `confirmPayment(userId, piId)` | `Promise<OrderConfirmation>` |
| `getSubscription(userId)` | `Promise<Subscription \| null>` |
| `createSubscription(userId, tier)` | `Promise<SubscriptionCreation>` |
| `cancelSubscription(userId)` | `Promise<Subscription>` |
| `reactivateSubscription(userId)` | `Promise<Subscription>` |
| `changeTier(userId, newTier)` | `Promise<Subscription>` |
| `getOrders(userId, page?, pageSize?)` | `Promise<PaginatedData<Order>>` |
| `getOrder(userId, orderId)` | `Promise<Order>` |
| `getProfile(userId)` | `Promise<CommerceProfile>` |
| `addAddress(userId, address)` | `Promise<CommerceProfile>` |
| `updateAddress(userId, addressId, address)` | `Promise<CommerceProfile>` |
| `deleteAddress(userId, addressId)` | `Promise<CommerceProfile>` |

---

### images.ts

| Function | Returns | Notes |
|---|---|---|
| `uploadImage(formData)` | `Promise<ImageRecord>` | multipart/form-data, 60s timeout |
| `getImage(imageId)` | `Promise<ImageRecord>` | |
| `deleteImage(imageId)` | `Promise<void>` | |
| `getUserImages(userId, category?)` | `Promise<ImageRecord[]>` | |
| `generateImage(prompt, options?)` | `Promise<ImageRecord>` | 60s timeout |
| `getImageFileUrl(imageId, variant?)` | `string` | Sync URL builder, no network call |

---

### llm.ts

| Function | Returns | Notes |
|---|---|---|
| `generateText(prompt, options?)` | `Promise<GenerateTextResponse>` | 120s timeout |
| `generateImage(prompt, options?)` | `Promise<GenerateImageResponse>` | 120s timeout |
| `getProviders()` | `Promise<LLMProvider[]>` | |
| `getProviderStatus(name)` | `Promise<LLMProvider>` | |

---

### chat.ts

| Function | Returns |
|---|---|
| `sendMessage(message, options?)` | `Promise<Conversation>` |
| `getConversation(id)` | `Promise<Conversation>` |
| `listConversations(userId)` | `Promise<Conversation[]>` |
| `deleteConversation(id)` | `Promise<void>` |
| `updateConversation(id, updates)` | `Promise<Conversation>` |

---

### devTools.ts (DEV only)

| Function | Returns |
|---|---|
| `simulateWebhook(eventType, userId?, overrides?)` | `Promise<{ event_type, simulated }>` |
| `listWebhookEvents()` | `Promise<{ events: string[] }>` |

> These functions are only available when `__DEV__` is true. Do not call them in production code paths.

---

## Hooks

### useApi\<T\>(fetcher)

For data fetching. Fires automatically on mount.

```ts
const { data, loading, error, refetch } = useApi(() => getCart(userId));
```

| Return | Type | Description |
|---|---|---|
| `data` | `T \| null` | Fetched data |
| `loading` | `boolean` | True while request is in flight |
| `error` | `string \| null` | Error message if request failed |
| `refetch` | `() => void` | Manually re-trigger the fetch |

**Important:** Stabilize `fetcher` with `useCallback` to avoid infinite re-fetch loops.

---

### useMutation\<T, A\>(mutator)

For actions that modify state. Does NOT fetch on mount.

```ts
const { execute, data, loading, error, reset } = useMutation((item) => addItem(userId, item));
```

| Return | Type | Description |
|---|---|---|
| `execute` | `(args: A) => Promise<T>` | Trigger the mutation; re-throws on error |
| `data` | `T \| null` | Result of last successful execution |
| `loading` | `boolean` | True while mutation is in flight |
| `error` | `string \| null` | Error message from last failure |
| `reset` | `() => void` | Clear data, error, and loading state |

---

## AuthContext

Import from `context/AuthContext.tsx`.

### Exports

| Name | Type | Description |
|---|---|---|
| `user` | `FirebaseUser \| null` | Current Firebase user |
| `loading` | `boolean` | True during auth state initialization |
| `error` | `string \| null` | Auth error message |
| `apiReady` | `boolean` | True after JWT exchange succeeds |
| `permissions` | `UserPermissions \| null` | Resolved user permissions |
| `login(email, password)` | `Promise<void>` | Sign in with email and password |
| `register(email, password)` | `Promise<void>` | Create new account |
| `logout()` | `Promise<void>` | Clear token and sign out |
| `refreshToken()` | `Promise<void>` | Force JWT refresh |
| `setError(msg)` | `void` | Manually set error state |

### Usage

```tsx
const { user, apiReady, permissions, logout } = useAuth();

if (!apiReady) return <LoadingScreen />;
```

---

## Important Notes

- SDK functions return **unwrapped data** — the `{success, data, message}` envelope is stripped by the response interceptor. Do not access `.data.data`.
- On 401 responses, the client automatically retries once after refreshing the JWT. If the retry also fails, the error is propagated normally.
- All errors are normalized to `{ success: false, message, error_code }` shape before being thrown.
- The 60-second pre-expiry buffer on `getToken()` means tokens are proactively refreshed before they actually expire.
