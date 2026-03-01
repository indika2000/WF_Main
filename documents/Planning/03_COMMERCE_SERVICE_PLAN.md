# Commerce Service - Planning Document

## 1. Purpose

A generic commerce service handling all monetary transactions through Stripe. It manages:
- **Subscription billing** — recurring charges via Stripe Billing
- **One-time purchases** — individual item purchases via Stripe PaymentIntents
- **Shopping cart** — Redis-backed cart with item management
- **Checkout flow** — validation, payment creation, order confirmation
- **Order management** — order records, status tracking, history

This service is **application-agnostic** — it processes payments and manages orders without knowing what the items represent.

## 2. Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Python 3.12 + FastAPI |
| Database | MongoDB (orders, profiles) |
| Cache | Redis (carts, sessions) |
| Payments | Stripe API (stripe-python) |
| Validation | Pydantic v2 |
| Auth | Internal JWT + API key |
| Testing | pytest + httpx |

## 3. Stripe Integration Architecture

### 3.1 Stripe Products & Prices

Created and managed via Stripe Dashboard or API:

```
Stripe Products:
├── Subscription: "WF Premium"
│   └── Price: $4.99/month (recurring)
├── Subscription: "WF Ultra"
│   └── Price: $9.99/month (recurring)
└── One-time items (created dynamically as needed)
    └── Price: variable (one_time)
```

### 3.2 Stripe Customer Lifecycle

```
User signs up (Firebase Auth)
    │
    First purchase/subscription attempt
    │
    ├─ Check: Stripe Customer exists for this user_id?
    │   ├─ Yes → use existing customer
    │   └─ No → stripe.Customer.create({ metadata: { firebase_uid } })
    │
    └─ Store stripe_customer_id in user profile
```

### 3.3 Payment Methods

- Managed entirely by Stripe (tokenized, PCI-compliant)
- Mobile app uses Stripe SDK for card collection
- Service only stores: card brand, last 4 digits, expiry (for display)

## 4. Data Models

### 4.1 UserProfile (Commerce)

```python
class CommerceProfile(BaseModel):
    user_id: str                           # Firebase UID
    stripe_customer_id: str | None
    default_payment_method_id: str | None
    addresses: list[Address]
    created_at: datetime
    updated_at: datetime

class Address(BaseModel):
    id: str                                # UUID
    label: str                             # "Home", "Work"
    line1: str
    line2: str | None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    is_default: bool = False
```

### 4.2 Cart (Redis)

```python
class Cart(BaseModel):
    user_id: str
    items: list[CartItem]
    subtotal: float
    tax: float
    shipping: float
    total: float
    updated_at: datetime

class CartItem(BaseModel):
    item_id: str                           # Generic item identifier
    item_type: str                         # "subscription" | "one_time" | "pack" etc.
    name: str
    description: str | None
    quantity: int
    unit_price: float
    metadata: dict                         # Flexible — app-specific data
```

Redis key: `cart:{user_id}`, TTL: 7 days

### 4.3 Order

```python
class Order(BaseModel):
    order_id: str                          # ORD-YYYYMMDDHHMMSS-XXXXXX
    user_id: str
    stripe_payment_intent_id: str | None
    stripe_subscription_id: str | None
    order_type: str                        # "one_time" | "subscription"
    status: str                            # PENDING | CONFIRMED | PROCESSING | COMPLETED | FAILED | REFUNDED
    items: list[OrderItem]                 # Snapshot at time of purchase
    subtotal: float
    tax: float
    shipping: float
    total: float
    shipping_address: Address | None       # Snapshot
    payment_method_summary: str | None     # "Visa ****4242"
    metadata: dict                         # Flexible app-specific data
    created_at: datetime
    updated_at: datetime

class OrderItem(BaseModel):
    item_id: str
    item_type: str
    name: str
    quantity: int
    unit_price: float
    total_price: float
    metadata: dict                         # Immutable snapshot
```

### 4.4 SubscriptionRecord

```python
class SubscriptionRecord(BaseModel):
    user_id: str
    stripe_subscription_id: str
    stripe_customer_id: str
    tier: str                              # "premium" | "ultra"
    status: str                            # active | past_due | cancelled | expired
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    created_at: datetime
    updated_at: datetime
```

## 5. API Endpoints

### 5.1 Cart

| Method | Path | Description |
|--------|------|-------------|
| GET | `/cart/{user_id}` | Get current cart |
| POST | `/cart/{user_id}/items` | Add item to cart |
| PATCH | `/cart/{user_id}/items/{item_id}` | Update item quantity |
| DELETE | `/cart/{user_id}/items/{item_id}` | Remove item from cart |
| DELETE | `/cart/{user_id}` | Clear entire cart |

### 5.2 Checkout

| Method | Path | Description |
|--------|------|-------------|
| POST | `/checkout/{user_id}/validate` | Validate cart is ready for checkout |
| POST | `/checkout/{user_id}/create-payment` | Create Stripe PaymentIntent, return client_secret |
| POST | `/checkout/{user_id}/confirm` | Confirm payment succeeded, create order |

### 5.3 Subscriptions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/subscriptions/{user_id}` | Get current subscription |
| POST | `/subscriptions/{user_id}/create` | Create new subscription via Stripe |
| POST | `/subscriptions/{user_id}/cancel` | Cancel subscription (at period end) |
| POST | `/subscriptions/{user_id}/reactivate` | Reactivate cancelled subscription |
| POST | `/subscriptions/{user_id}/change-tier` | Up/downgrade subscription tier |

### 5.4 Orders

| Method | Path | Description |
|--------|------|-------------|
| GET | `/orders/{user_id}` | List user's orders (paginated) |
| GET | `/orders/{user_id}/{order_id}` | Get specific order details |

### 5.5 Stripe Webhooks

| Method | Path | Description |
|--------|------|-------------|
| POST | `/webhooks/stripe` | Handle Stripe webhook events |

Handled events:
- `payment_intent.succeeded` — confirm order
- `payment_intent.payment_failed` — mark order failed
- `customer.subscription.created` — new subscription
- `customer.subscription.updated` — tier change, renewal
- `customer.subscription.deleted` — subscription ended
- `invoice.payment_succeeded` — subscription renewal payment
- `invoice.payment_failed` — subscription payment failed

### 5.6 User Profile

| Method | Path | Description |
|--------|------|-------------|
| GET | `/profile/{user_id}` | Get commerce profile |
| POST | `/profile/{user_id}/addresses` | Add shipping address |
| PATCH | `/profile/{user_id}/addresses/{address_id}` | Update address |
| DELETE | `/profile/{user_id}/addresses/{address_id}` | Delete address |

## 6. Key Flows

### 6.1 One-Time Purchase Checkout

```
1. POST /cart/{user_id}/items        → Add items to cart
2. POST /checkout/{user_id}/validate → Verify cart, address, stock
3. POST /checkout/{user_id}/create-payment
   │
   ├─ Get/create Stripe Customer
   ├─ Create PaymentIntent
   │   ├─ amount: cart total (cents)
   │   ├─ customer: stripe_customer_id
   │   ├─ metadata: { user_id, order_type }
   │   └─ automatic_payment_methods: enabled
   ├─ Create EphemeralKey (for mobile Stripe SDK)
   └─ Return: { client_secret, ephemeral_key, customer_id }
   │
4. Mobile app: Stripe SDK completes payment
5. POST /checkout/{user_id}/confirm
   │
   ├─ Verify PaymentIntent status == "succeeded"
   ├─ Create Order record (immutable snapshot)
   ├─ Clear cart
   └─ Return: { order_id, status }
```

### 6.2 Subscription Purchase

```
1. POST /subscriptions/{user_id}/create
   │   Body: { tier: "premium" }
   │
   ├─ Get/create Stripe Customer
   ├─ Create Stripe Subscription
   │   ├─ customer: stripe_customer_id
   │   ├─ items: [{ price: price_id_for_tier }]
   │   └─ payment_behavior: "default_incomplete"
   │
   ├─ Return: { client_secret, subscription_id }
   │
2. Mobile app: Stripe SDK completes payment
3. Stripe Webhook: customer.subscription.created
   │
   ├─ Save SubscriptionRecord
   ├─ Call Permissions Service: POST /subscriptions/{user_id}
   │   └─ Triggers permission sync to match new tier
   └─ Create Order record (type: "subscription")
```

### 6.3 Subscription Cancellation

```
POST /subscriptions/{user_id}/cancel
    │
    ├─ stripe.Subscription.modify(cancel_at_period_end=True)
    ├─ Update local SubscriptionRecord
    └─ Return: { cancel_at: period_end_date }

Stripe Webhook: customer.subscription.deleted (at period end)
    │
    ├─ Update SubscriptionRecord status → "expired"
    ├─ Call Permissions Service: downgrade to free tier
    └─ Return
```

## 7. Stripe Test Mode

- All development uses Stripe **test mode** keys
- Test card numbers: `4242 4242 4242 4242` (success), `4000 0000 0000 0002` (decline)
- Webhooks: use Stripe CLI `stripe listen --forward-to localhost:3004/webhooks/stripe`
- No real charges in development

## 8. MongoDB Collections

```
commerce_profiles:
  - user_id (unique)
  - stripe_customer_id (unique, sparse)

orders:
  - order_id (unique)
  - user_id (index)
  - created_at (index, descending)
  - status (index)

subscription_records:
  - user_id (unique)
  - stripe_subscription_id (unique)
  - status (index)
```

## 9. Security

- Stripe webhook signature verification on all webhook endpoints
- User can only access their own cart, orders, and subscriptions
- Payment secrets (client_secret) are short-lived and scoped
- No raw card data ever touches our servers (Stripe tokenization)
- Price validation: server always calculates totals, never trusts client prices
- Idempotency keys on PaymentIntent creation to prevent duplicate charges

## 10. Integration Points

| Service | Direction | Purpose |
|---------|-----------|---------|
| Permissions Service | → calls | Sync permissions on subscription change |
| Node Gateway | ← called by | All client requests proxied through gateway |
| Stripe API | → calls | Payment processing, subscription management |

## 11. Testing Strategy

### Unit Tests
- Cart CRUD operations (Redis mocked)
- Order creation and validation logic
- Price calculation (subtotal, tax, shipping)
- Webhook event handling logic

### Integration Tests
- Full checkout flow with Stripe test mode
- Subscription lifecycle (create → renew → cancel → expire)
- Cart persistence and expiry in Redis
- Webhook signature verification
- Permission sync after subscription changes
