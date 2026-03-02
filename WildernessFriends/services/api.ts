import axios from "axios";
import * as tokenManager from "./tokenManager";

/**
 * Axios instance configured for the WF backend gateway.
 *
 * Request interceptor: injects JWT Authorization header.
 * Response interceptor: unwraps { success, data, message } envelope,
 * auto-retries once on 401 after refreshing the token.
 */
const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL || "http://localhost:3000/api",
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// --- Request interceptor: attach JWT ---
api.interceptors.request.use(async (config) => {
  const token = await tokenManager.getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Response interceptor: unwrap envelope + 401 retry ---
api.interceptors.response.use(
  (response) => {
    // The gateway returns { success, message, data } — unwrap to just data
    const body = response.data;
    if (body && typeof body === "object" && "data" in body) {
      return body.data;
    }
    return body;
  },
  async (error) => {
    const original = error.config;

    // On 401, try refreshing the token once
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        await tokenManager.refreshToken();
        const token = await tokenManager.getToken();
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        // Refresh failed — propagate the 401
      }
    }

    // Normalize error shape
    const apiError = error.response?.data ?? {
      success: false,
      message: error.message || "Network error",
      error_code: "NETWORK_ERROR",
    };

    return Promise.reject(apiError);
  }
);

export default api;
