const { auth } = require('../config/firebase');
const { errorResponse } = require('../utils/responses');

/**
 * Paths that skip authentication.
 */
const PUBLIC_PATHS = [
  '/health',
  '/health/services',
];

/**
 * Firebase token verification middleware.
 *
 * - Extracts Bearer token from Authorization header
 * - Verifies via Firebase Admin SDK
 * - Attaches user info to req.user
 * - Supports dev-bypass in non-production environments
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
