import api from "./api";
import type { Cart, CartItemAdd } from "../types";

/**
 * Cart Service SDK
 * Gateway path: /api/commerce/cart/*
 */

export async function getCart(userId: string): Promise<Cart | null> {
  return api.get(`/commerce/cart/${userId}`);
}

export async function addItem(
  userId: string,
  item: CartItemAdd
): Promise<Cart> {
  return api.post(`/commerce/cart/${userId}/items`, item);
}

export async function updateItem(
  userId: string,
  itemId: string,
  quantity: number
): Promise<Cart> {
  return api.patch(`/commerce/cart/${userId}/items/${itemId}`, { quantity });
}

export async function removeItem(
  userId: string,
  itemId: string
): Promise<Cart> {
  return api.delete(`/commerce/cart/${userId}/items/${itemId}`);
}

export async function clearCart(userId: string): Promise<void> {
  return api.delete(`/commerce/cart/${userId}`);
}
