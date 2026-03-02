const express = require('express');
const { createProxyMiddleware, fixRequestBody } = require('http-proxy-middleware');
const { SERVICE_CONFIG } = require('../config/services');
const { authMiddleware } = require('../middleware/auth');
const { permissionsMiddleware } = require('../middleware/permissions');
const { errorResponse } = require('../utils/responses');

const router = express.Router();

/**
 * Create a proxy middleware for a backend service.
 * Injects internal JWT and API key headers before forwarding.
 *
 * Express strips the router mount prefix, so req.url = /{id}/...
 * We prepend config.pathPrefix to restore the backend route.
 *
 * fixRequestBody re-serializes req.body onto the proxy request when
 * express.json() has already consumed the body stream.
 */
function createServiceProxy(serviceName, config) {
  return createProxyMiddleware({
    target: config.url,
    changeOrigin: true,
    timeout: config.timeout,
    on: {
      proxyReq: (proxyReq, req, res) => {
        // Prepend the backend path prefix (Express strips the mount path)
        if (config.pathPrefix) {
          proxyReq.path = config.pathPrefix + proxyReq.path;
        }
        // Inject internal auth headers
        if (req.internalToken) {
          proxyReq.setHeader('Authorization', `Bearer ${req.internalToken}`);
        }
        if (process.env.INTERNAL_API_KEY) {
          proxyReq.setHeader('X-Api-Key', process.env.INTERNAL_API_KEY);
        }
        // Re-attach body consumed by express.json()
        fixRequestBody(proxyReq, req, res);
      },
      error: (err, req, res) => {
        console.error(`[GATEWAY] Proxy error for ${serviceName}:`, err.message);
        if (!res.headersSent) {
          errorResponse(
            res,
            'Service temporarily unavailable',
            'SERVICE_UNAVAILABLE',
            503
          );
        }
      },
    },
  });
}

// Permissions Service proxy (Phase 1 — active)
router.use(
  '/permissions',
  authMiddleware,
  permissionsMiddleware,
  createServiceProxy('permissions', SERVICE_CONFIG.permissions)
);

// Commerce Service proxy — conditionally skips auth for webhook paths
// (Stripe calls webhooks directly without JWT auth)
router.use(
  '/commerce',
  (req, res, next) => {
    if (req.path.startsWith('/webhooks')) {
      return next('route');
    }
    authMiddleware(req, res, next);
  },
  permissionsMiddleware,
  createServiceProxy('commerce', SERVICE_CONFIG.commerce)
);

// Commerce webhook fallback — no auth, uses same proxy
router.use(
  '/commerce',
  createServiceProxy('commerce', SERVICE_CONFIG.commerce)
);

// Image Service proxy (Phase 2 — active)
router.use(
  '/images',
  authMiddleware,
  permissionsMiddleware,
  createServiceProxy('images', SERVICE_CONFIG.images)
);

// LLM Service proxy (Phase 2 — active)
router.use(
  '/llm',
  authMiddleware,
  permissionsMiddleware,
  createServiceProxy('llm', SERVICE_CONFIG.llm)
);

// Chat proxy (→ LLM Service /chat/*)
router.use(
  '/chat',
  authMiddleware,
  permissionsMiddleware,
  createServiceProxy('chat', SERVICE_CONFIG.chat)
);

module.exports = router;
