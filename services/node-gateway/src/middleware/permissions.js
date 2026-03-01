const axios = require('axios');
const { signToken } = require('../utils/jwt');
const { errorResponse } = require('../utils/responses');

const PERMISSIONS_URL = process.env.PERMISSIONS_SERVICE_URL || 'http://permissions:5003';
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || '';

/**
 * Permission fetch + JWT generation middleware.
 *
 * After auth middleware sets req.user, this:
 * 1. Fetches user permissions from Permissions Service
 * 2. Auto-creates permissions for new users (404 → POST)
 * 3. Fetches subscription info
 * 4. Generates internal JWT with embedded permissions
 * 5. Attaches req.internalToken and req.permissions
 */
async function permissionsMiddleware(req, res, next) {
  // Skip if no user (public routes)
  if (!req.user) {
    return next();
  }

  const { uid, email } = req.user;
  const headers = { 'X-Api-Key': INTERNAL_API_KEY };

  try {
    // Fetch permissions
    let permissionsData;
    try {
      const permRes = await axios.get(
        `${PERMISSIONS_URL}/permissions/${uid}`,
        { headers, timeout: 10000 }
      );
      permissionsData = permRes.data.data;
    } catch (err) {
      if (err.response && err.response.status === 404) {
        // New user — create default permissions
        const createRes = await axios.post(
          `${PERMISSIONS_URL}/permissions/${uid}`,
          { email },
          { headers, timeout: 10000 }
        );
        permissionsData = createRes.data.data;
      } else {
        throw err;
      }
    }

    // Fetch subscription
    let subscriptionData = { tier: 'free', status: 'active' };
    try {
      const subRes = await axios.get(
        `${PERMISSIONS_URL}/subscriptions/${uid}`,
        { headers, timeout: 10000 }
      );
      subscriptionData = subRes.data.data;
    } catch (err) {
      // Subscription may not exist yet — use defaults
      if (!err.response || err.response.status !== 404) {
        console.warn('[GATEWAY] Subscription fetch warning:', err.message);
      }
    }

    // Generate internal JWT
    const tokenPayload = {
      uid,
      email,
      role: permissionsData.role || 'user',
      is_premium: permissionsData.is_premium || false,
      permissions: permissionsData.permissions || {},
      subscription_tier: subscriptionData.tier || 'free',
    };

    req.internalToken = signToken(tokenPayload);
    req.permissions = permissionsData;
    req.subscription = subscriptionData;

    next();
  } catch (error) {
    console.error('[GATEWAY] Permissions middleware error:', error.message);
    return errorResponse(
      res,
      'Failed to fetch permissions',
      'PERMISSIONS_ERROR',
      503
    );
  }
}

module.exports = { permissionsMiddleware };
