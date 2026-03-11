import api from "./api";
import type { UserPermissions, UsageCheckResponse, FeatureUsage } from "../types";

/**
 * Permissions Service SDK
 * Gateway path: /api/permissions/*
 */

export async function getPermissions(userId: string): Promise<UserPermissions> {
  return api.get(`/permissions/${userId}`);
}

export async function checkPermission(
  userId: string,
  permission: string
): Promise<{ allowed: boolean }> {
  return api.get(`/permissions/${userId}/check/${permission}`);
}

// ===== Usage =====
// Gateway path: /api/usage/* → Permissions Service /usage/*

export async function getUsage(
  userId: string,
  feature: string
): Promise<FeatureUsage> {
  return api.get(`/usage/${userId}/${feature}`);
}

export async function checkUsage(
  userId: string,
  feature: string
): Promise<UsageCheckResponse> {
  return api.post(`/usage/${userId}/${feature}/check`);
}
