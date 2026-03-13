import api from "./api";
import type {
  GenerateCreatureResponse,
  CreatureCard,
  SupplyStatus,
  CollectionResponse,
} from "../types";

/**
 * Character Service SDK — Creature generation, collection, supply status
 * Gateway path: /api/characters/*
 */

// ===== Generate =====

export async function generateCreature(
  codeType: string,
  rawValue: string
): Promise<GenerateCreatureResponse> {
  return api.post("/characters/generate", {
    code_type: codeType,
    raw_value: rawValue,
  });
}

// ===== Creatures =====

export async function getCreature(
  creatureId: string
): Promise<{ creature: CreatureCard; is_owner: boolean }> {
  return api.get(`/characters/creatures/${creatureId}`);
}

// ===== Collection =====

export async function getMyCollection(
  skip: number = 0,
  limit: number = 50
): Promise<CollectionResponse> {
  return api.get(`/characters/collection?skip=${skip}&limit=${limit}`);
}

export async function getUserCollection(
  userId: string,
  skip: number = 0,
  limit: number = 50
): Promise<CollectionResponse> {
  return api.get(
    `/characters/collection/${userId}?skip=${skip}&limit=${limit}`
  );
}

// ===== Supply =====

export async function getSupplyStatus(): Promise<SupplyStatus> {
  return api.get("/characters/supply");
}

// ===== Image Status =====

export interface ImageJobStatus {
  job_id: string;
  image_type: "card" | "headshot_color" | "headshot_pencil";
  status: "pending" | "processing" | "completed" | "failed";
  result_image_id: string | null;
  attempts: number;
  error: string | null;
}

export async function getImageStatus(
  creatureId: string
): Promise<{ creature_id: string; jobs: ImageJobStatus[] }> {
  return api.get(`/characters/creatures/${creatureId}/images`);
}

/**
 * Subscribe to real-time image generation events via SSE.
 * Returns an EventSource-like controller with an abort method.
 */
export function subscribeToImageStream(
  creatureId: string,
  token: string,
  callbacks: {
    onImageReady?: (imageType: string, imageId: string) => void;
    onComplete?: () => void;
    onError?: (error: string) => void;
  }
): { abort: () => void } {
  const base =
    process.env.EXPO_PUBLIC_API_URL || "http://localhost:3000/api";
  const url = `${base}/characters/creatures/${creatureId}/images/stream`;

  // React Native doesn't support EventSource natively with auth headers,
  // so we use fetch with ReadableStream
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "text/event-stream",
        },
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        callbacks.onError?.(`SSE connection failed: ${response.status}`);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        let currentData = "";

        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            currentData = line.slice(5).trim();
          } else if (line === "" && currentData) {
            // End of event
            try {
              const parsed = JSON.parse(currentData);
              if (currentEvent === "status" || parsed.event === "status") {
                // Seed any images that already completed before we connected
                const jobs: any[] = parsed.jobs || [];
                for (const job of jobs) {
                  if (job.status === "completed" && job.result_image_id) {
                    callbacks.onImageReady?.(job.image_type, job.result_image_id);
                  }
                }
              } else if (currentEvent === "image_ready" || parsed.event === "image_ready") {
                callbacks.onImageReady?.(parsed.image_type, parsed.image_id);
              } else if (currentEvent === "complete") {
                callbacks.onComplete?.();
              }
            } catch {
              // ignore malformed events
            }
            currentEvent = "";
            currentData = "";
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        callbacks.onError?.(err.message || "SSE error");
      }
    }
  })();

  return { abort: () => controller.abort() };
}
