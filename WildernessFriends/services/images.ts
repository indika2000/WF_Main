import api from "./api";
import type { ImageRecord } from "../types";

/**
 * Image Service SDK
 * Gateway path: /api/images/*
 */

export async function uploadImage(
  formData: FormData
): Promise<ImageRecord> {
  return api.post("/images/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
}

export async function getImage(imageId: string): Promise<ImageRecord> {
  return api.get(`/images/${imageId}`);
}

export async function deleteImage(imageId: string): Promise<void> {
  return api.delete(`/images/${imageId}`);
}

export async function getUserImages(
  userId: string,
  category?: string
): Promise<ImageRecord[]> {
  const path = category
    ? `/images/user/${userId}/${category}`
    : `/images/user/${userId}`;
  return api.get(path);
}

export async function generateImage(
  prompt: string,
  options?: { provider?: string; model?: string; size?: string }
): Promise<ImageRecord> {
  return api.post("/images/generate", { prompt, ...options }, {
    timeout: 60000,
  });
}

/**
 * Get the direct URL for an image file (for use in <Image source={{ uri }}>).
 */
export function getImageFileUrl(
  imageId: string,
  variant?: string
): string {
  const base =
    process.env.EXPO_PUBLIC_API_URL || "http://localhost:3000/api";
  const path = variant
    ? `/images/${imageId}/file/${variant}`
    : `/images/${imageId}/file`;
  return `${base}${path}`;
}
