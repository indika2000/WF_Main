import api from "./api";
import type {
  PaymentCreation,
  OrderConfirmation,
  Subscription,
  SubscriptionCreation,
  Order,
  PaginatedData,
  CommerceProfile,
  Address,
} from "../types";

/**
 * Commerce Service SDK — Checkout, Subscriptions, Orders, Profile
 * Gateway path: /api/commerce/*
 */

// ===== Checkout =====

export async function validateCart(userId: string): Promise<{ valid: boolean }> {
  return api.post(`/commerce/checkout/${userId}/validate`);
}

export async function createPayment(userId: string): Promise<PaymentCreation> {
  return api.post(`/commerce/checkout/${userId}/create-payment`);
}

export async function confirmPayment(
  userId: string,
  paymentIntentId: string
): Promise<OrderConfirmation> {
  return api.post(`/commerce/checkout/${userId}/confirm`, {
    payment_intent_id: paymentIntentId,
  });
}

// ===== Subscriptions =====

export async function getSubscription(userId: string): Promise<Subscription | null> {
  return api.get(`/commerce/subscriptions/${userId}`);
}

export async function createSubscription(
  userId: string,
  tier: string
): Promise<SubscriptionCreation> {
  return api.post(`/commerce/subscriptions/${userId}/create`, { tier });
}

export async function cancelSubscription(userId: string): Promise<Subscription> {
  return api.post(`/commerce/subscriptions/${userId}/cancel`);
}

export async function reactivateSubscription(userId: string): Promise<Subscription> {
  return api.post(`/commerce/subscriptions/${userId}/reactivate`);
}

export async function changeTier(
  userId: string,
  newTier: string
): Promise<Subscription> {
  return api.post(`/commerce/subscriptions/${userId}/change-tier`, {
    new_tier: newTier,
  });
}

// ===== Orders =====

export async function getOrders(
  userId: string,
  page = 1,
  pageSize = 20
): Promise<PaginatedData<Order>> {
  return api.get(`/commerce/orders/${userId}`, {
    params: { page, page_size: pageSize },
  });
}

export async function getOrder(
  userId: string,
  orderId: string
): Promise<Order> {
  return api.get(`/commerce/orders/${userId}/${orderId}`);
}

// ===== Profile =====

export async function getProfile(userId: string): Promise<CommerceProfile> {
  return api.get(`/commerce/profile/${userId}`);
}

export async function addAddress(
  userId: string,
  address: Omit<Address, "id">
): Promise<CommerceProfile> {
  return api.post(`/commerce/profile/${userId}/addresses`, address);
}

export async function updateAddress(
  userId: string,
  addressId: string,
  address: Partial<Address>
): Promise<CommerceProfile> {
  return api.patch(
    `/commerce/profile/${userId}/addresses/${addressId}`,
    address
  );
}

export async function deleteAddress(
  userId: string,
  addressId: string
): Promise<CommerceProfile> {
  return api.delete(`/commerce/profile/${userId}/addresses/${addressId}`);
}
