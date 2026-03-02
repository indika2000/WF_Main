import api from "./api";
import type { UserPermissions } from "../types";

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
