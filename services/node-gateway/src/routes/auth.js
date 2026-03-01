const express = require('express');
const { auth } = require('../config/firebase');
const { signToken, verifyToken } = require('../utils/jwt');
const { successResponse, errorResponse } = require('../utils/responses');
const { authLimiter } = require('../middleware/rateLimiter');
const { permissionsMiddleware } = require('../middleware/permissions');

const router = express.Router();

/**
 * POST /api/auth/token
 *
 * Exchange a Firebase ID token for an internal JWT with embedded permissions.
 * This is the primary endpoint the mobile app calls after Firebase login.
 */
router.post('/token', authLimiter, async (req, res, next) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return errorResponse(res, 'Firebase token required', 'AUTH_REQUIRED', 401);
  }

  const firebaseToken = authHeader.split('Bearer ')[1];

  try {
    let user;

    // Dev bypass
    if (process.env.NODE_ENV !== 'production' && firebaseToken === 'dev-bypass') {
      user = { uid: 'dev-user', email: 'dev@test.com' };
    } else {
      const decoded = await auth.verifyIdToken(firebaseToken);
      user = { uid: decoded.uid, email: decoded.email || '' };
    }

    // Attach user for permissions middleware
    req.user = user;

    // Fetch permissions and generate internal JWT
    await new Promise((resolve, reject) => {
      permissionsMiddleware(req, res, (err) => {
        if (err) reject(err);
        else resolve();
      });
    });

    // If permissionsMiddleware sent a response (error), don't continue
    if (res.headersSent) return;

    return successResponse(res, {
      token: req.internalToken,
      user: {
        uid: user.uid,
        email: user.email,
        role: req.permissions?.role || 'user',
        is_premium: req.permissions?.is_premium || false,
        permissions: req.permissions?.permissions || {},
        subscription: req.subscription || { tier: 'free', status: 'active' },
      },
    }, 'Authentication successful');
  } catch (error) {
    console.error('[GATEWAY] Auth token exchange error:', error.message);
    return errorResponse(res, 'Authentication failed', 'AUTH_FAILED', 401);
  }
});

/**
 * GET /api/auth/verify
 *
 * Verify an internal JWT is still valid. Returns user info from decoded token.
 */
router.get('/verify', (req, res) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return errorResponse(res, 'Token required', 'AUTH_REQUIRED', 401);
  }

  const token = authHeader.split('Bearer ')[1];

  try {
    const decoded = verifyToken(token);
    return successResponse(res, {
      uid: decoded.uid,
      email: decoded.email,
      role: decoded.role,
      is_premium: decoded.is_premium,
      permissions: decoded.permissions,
      subscription_tier: decoded.subscription_tier,
    }, 'Token is valid');
  } catch (error) {
    return errorResponse(res, 'Invalid or expired token', 'AUTH_INVALID', 401);
  }
});

module.exports = router;
