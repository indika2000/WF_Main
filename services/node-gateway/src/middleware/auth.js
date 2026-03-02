const { auth } = require('../config/firebase');
const { verifyToken } = require('../utils/jwt');
const { errorResponse } = require('../utils/responses');

/**
 * Paths that skip authentication.
 */
const PUBLIC_PATHS = [
  '/health',
  '/health/services',
];

/**
 * Authentication middleware.
 *
 * Accepts either:
 * 1. Internal JWT (from /api/auth/token exchange) — verified locally via HS256
 * 2. Firebase ID token — verified via Firebase Admin SDK
 * 3. "dev-bypass" token — in non-production environments
 *
 * Internal JWTs are tried first since they're the common path for SDK
 * requests after the initial token exchange.
 */
async function authMiddleware(req, res, next) {
  // Skip auth for public paths
  if (PUBLIC_PATHS.includes(req.path)) {
    return next();
  }

  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return errorResponse(res, 'Authentication required', 'AUTH_REQUIRED', 401);
  }

  const token = authHeader.split('Bearer ')[1];

  // Dev bypass for non-production environments
  if (process.env.NODE_ENV !== 'production' && token === 'dev-bypass') {
    req.user = {
      uid: 'dev-user',
      email: 'dev@test.com',
    };
    return next();
  }

  // Try internal JWT first (most common path for SDK requests)
  try {
    const decoded = verifyToken(token);
    req.user = {
      uid: decoded.uid,
      email: decoded.email || '',
    };
    // Pass through the already-valid internal token — skip permissions refetch
    req.internalToken = token;
    req.permissions = decoded.permissions || {};
    req.subscription = { tier: decoded.subscription_tier || 'free' };
    return next();
  } catch (_) {
    // Not an internal JWT — fall through to Firebase verification
  }

  // Fall back to Firebase ID token verification
  try {
    const decodedToken = await auth.verifyIdToken(token);
    req.user = {
      uid: decodedToken.uid,
      email: decodedToken.email || '',
    };
    next();
  } catch (error) {
    console.error('[GATEWAY] Firebase auth error:', error.message);
    return errorResponse(res, 'Invalid or expired token', 'AUTH_INVALID', 401);
  }
}

module.exports = { authMiddleware, PUBLIC_PATHS };
