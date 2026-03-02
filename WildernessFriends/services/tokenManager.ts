import axios from "axios";
import { auth } from "../config/firebase";
import type { ApiResponse, AuthTokenResponse } from "../types";

const API_URL =
  process.env.EXPO_PUBLIC_API_URL || "http://localhost:3000/api";

let cachedToken: string | null = null;
let tokenExpiry = 0;
let cachedUserData: AuthTokenResponse["user"] | null = null;

/**
 * Decode JWT expiry without verification (client-side only).
 * JWTs are base64url-encoded: header.payload.signature
 */
function decodeExpiry(token: string): number {
  try {
    const payload = token.split(".")[1];
    const decoded = JSON.parse(atob(payload));
    return decoded.exp ?? 0;
  } catch {
    return 0;
  }
}

/**
 * Exchange a Firebase ID token for a gateway internal JWT.
 * Called on login and when the cached token expires.
 */
export async function exchangeToken(): Promise<AuthTokenResponse> {
  const firebaseUser = auth.currentUser;
  if (!firebaseUser) throw new Error("Not authenticated");

  const idToken = await firebaseUser.getIdToken(true);

  const res = await axios.post<ApiResponse<AuthTokenResponse>>(
    `${API_URL}/auth/token`,
    null,
    { headers: { Authorization: `Bearer ${idToken}` } }
  );

  const data = res.data.data;
  cachedToken = data.token;
  tokenExpiry = decodeExpiry(cachedToken);
  cachedUserData = data.user;

  return data;
}

/**
 * Get a valid JWT, refreshing if expired or about to expire (60s buffer).
 */
export async function getToken(): Promise<string | null> {
  if (!auth.currentUser) return null;

  if (cachedToken && Date.now() / 1000 < tokenExpiry - 60) {
    return cachedToken;
  }

  const data = await exchangeToken();
  return data.token;
}

/**
 * Force-refresh the token (e.g. after a 401).
 */
export async function refreshToken(): Promise<string> {
  const data = await exchangeToken();
  return data.token;
}

/**
 * Clear cached token and user data (on logout).
 */
export function clearToken(): void {
  cachedToken = null;
  tokenExpiry = 0;
  cachedUserData = null;
}

/**
 * Get cached user data from the last token exchange.
 */
export function getCachedUserData(): AuthTokenResponse["user"] | null {
  return cachedUserData;
}
