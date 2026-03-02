import api from "./api";

/**
 * Dev Tools SDK — only used in __DEV__ mode.
 * Calls the Commerce Service /dev/* endpoints.
 */

export async function simulateWebhook(
  eventType: string,
  userId?: string,
  overrides?: Record<string, unknown>
): Promise<{ event_type: string; simulated: boolean }> {
  return api.post("/commerce/dev/simulate-webhook", {
    event_type: eventType,
    user_id: userId,
    overrides,
  });
}

export async function listWebhookEvents(): Promise<{ events: string[] }> {
  return api.get("/commerce/dev/webhook-events");
}
