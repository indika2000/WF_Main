import api from "./api";
import type {
  GenerateTextResponse,
  GenerateImageResponse,
  LLMProvider,
} from "../types";

/**
 * LLM Service SDK
 * Gateway path: /api/llm/*
 */

export async function generateText(
  prompt: string,
  options?: {
    provider?: string;
    model?: string;
    max_tokens?: number;
    temperature?: number;
    system_prompt?: string;
  }
): Promise<GenerateTextResponse> {
  return api.post("/llm/generate/text", { prompt, ...options }, {
    timeout: 120000,
  });
}

export async function generateImage(
  prompt: string,
  options?: {
    provider?: string;
    model?: string;
    size?: string;
  }
): Promise<GenerateImageResponse> {
  return api.post("/llm/generate/image", { prompt, ...options }, {
    timeout: 120000,
  });
}

export async function getProviders(): Promise<LLMProvider[]> {
  return api.get("/llm/providers");
}

export async function getProviderStatus(
  providerName: string
): Promise<LLMProvider> {
  return api.get(`/llm/providers/${providerName}/status`);
}
