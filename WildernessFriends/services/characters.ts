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
