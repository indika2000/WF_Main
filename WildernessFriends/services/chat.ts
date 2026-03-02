import api from "./api";
import type { Conversation } from "../types";

/**
 * Chat Service SDK
 * Gateway path: /api/chat/*
 */

export async function sendMessage(
  message: string,
  options?: {
    conversation_id?: string;
    user_id?: string;
    provider?: string;
    model?: string;
    system_prompt?: string;
  }
): Promise<Conversation> {
  return api.post("/chat", { message, ...options });
}

export async function getConversation(
  conversationId: string
): Promise<Conversation> {
  return api.get(`/chat/conversations/detail/${conversationId}`);
}

export async function listConversations(
  userId: string
): Promise<Conversation[]> {
  return api.get(`/chat/conversations/${userId}`);
}

export async function deleteConversation(
  conversationId: string
): Promise<void> {
  return api.delete(`/chat/conversations/detail/${conversationId}`);
}

export async function updateConversation(
  conversationId: string,
  updates: { title?: string }
): Promise<Conversation> {
  return api.patch(`/chat/conversations/detail/${conversationId}`, updates);
}
