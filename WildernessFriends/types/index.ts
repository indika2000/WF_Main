// ===== Existing types =====

export interface ScanResult {
  value: string;
  type: string;
  timestamp: number;
}

export interface User {
  uid: string;
  email: string | null;
}

// ===== API Response types =====

export interface ApiResponse<T = unknown> {
  success: boolean;
  message: string;
  data: T;
}

export interface ApiError {
  success: false;
  message: string;
  error_code: string;
  detail?: string;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ===== Auth =====

export interface AuthTokenResponse {
  token: string;
  user: {
    uid: string;
    email: string;
    role: string;
    is_premium: boolean;
    permissions: Record<string, boolean>;
    subscription: {
      tier: string;
      status: string;
    };
  };
}

// ===== Permissions =====

export interface UserPermissions {
  user_id: string;
  role: string;
  is_premium: boolean;
  permissions: Record<string, boolean>;
  subscription_tier: string;
  created_at: string;
  updated_at: string;
}

// ===== Commerce — Cart =====

export interface CartItem {
  item_id: string;
  item_type: string;
  name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  metadata?: Record<string, unknown>;
}

export interface Cart {
  user_id: string;
  items: CartItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  updated_at: string;
}

export interface CartItemAdd {
  item_id: string;
  item_type: string;
  name: string;
  description?: string;
  quantity: number;
  unit_price: number;
  metadata?: Record<string, unknown>;
}

// ===== Commerce — Checkout =====

export interface PaymentCreation {
  client_secret: string;
  ephemeral_key: string;
  customer_id: string;
  payment_intent_id: string;
  amount: number;
}

export interface OrderConfirmation {
  order_id: string;
  status: string;
  total: number;
  items: OrderItem[];
  created_at: string;
}

// ===== Commerce — Orders =====

export interface OrderItem {
  item_id: string;
  item_type: string;
  name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
  metadata?: Record<string, unknown>;
}

export interface Order {
  order_id: string;
  user_id: string;
  stripe_payment_intent_id?: string;
  stripe_subscription_id?: string;
  order_type: string;
  status: string;
  items: OrderItem[];
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
  shipping_address?: Address;
  payment_method_summary?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// ===== Commerce — Subscriptions =====

export interface Subscription {
  user_id: string;
  stripe_subscription_id: string;
  stripe_customer_id: string;
  tier: string;
  status: string;
  current_period_start?: string;
  current_period_end?: string;
  cancel_at_period_end: boolean;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionCreation {
  subscription_id: string;
  client_secret: string;
  status: string;
}

// ===== Commerce — Profile =====

export interface Address {
  id: string;
  label: string;
  line1: string;
  line2?: string;
  city: string;
  state: string;
  postal_code: string;
  country: string;
  is_default: boolean;
}

export interface CommerceProfile {
  user_id: string;
  stripe_customer_id?: string;
  default_payment_method_id?: string;
  addresses: Address[];
  created_at: string;
  updated_at: string;
}

// ===== Images =====

export interface ImageRecord {
  image_id: string;
  user_id: string;
  filename: string;
  content_type: string;
  size: number;
  category: string;
  variants: Record<string, string>;
  metadata?: Record<string, unknown>;
  created_at: string;
}

// ===== LLM =====

export interface GenerateTextResponse {
  text: string;
  provider: string;
  model: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
  };
}

export interface GenerateImageResponse {
  image_url?: string;
  image_base64?: string;
  provider: string;
  model: string;
}

export interface LLMProvider {
  name: string;
  available: boolean;
  models: string[];
}

// ===== Chat =====

export interface ChatMessage {
  role: string;
  content: string;
  timestamp?: string;
}

export interface Conversation {
  conversation_id: string;
  user_id: string;
  title?: string;
  messages: ChatMessage[];
  provider?: string;
  model?: string;
  created_at: string;
  updated_at: string;
}
