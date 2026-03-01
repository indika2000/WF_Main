const nock = require('nock');

const PERMISSIONS_URL = process.env.PERMISSIONS_SERVICE_URL || 'http://permissions:5003';

/**
 * Mock the Permissions Service to return user permissions.
 */
function mockPermissionsGet(userId, permissions = null) {
  const defaultPerms = {
    user_id: userId,
    role: 'user',
    is_premium: false,
    permissions: {
      ad_free: false,
      premium_features: false,
      ai_text_generation: true,
      ai_image_generation: false,
    },
  };

  return nock(PERMISSIONS_URL)
    .get(`/permissions/${userId}`)
    .reply(200, {
      success: true,
      message: 'Success',
      data: permissions || defaultPerms,
    });
}

/**
 * Mock the Permissions Service to return 404 (new user).
 */
function mockPermissionsNotFound(userId) {
  return nock(PERMISSIONS_URL)
    .get(`/permissions/${userId}`)
    .reply(404, {
      success: false,
      message: 'User not found',
      error_code: 'USER_NOT_FOUND',
    });
}

/**
 * Mock the Permissions Service POST to create permissions.
 */
function mockPermissionsCreate(userId) {
  return nock(PERMISSIONS_URL)
    .post(`/permissions/${userId}`)
    .reply(201, {
      success: true,
      message: 'Permissions created',
      data: {
        user_id: userId,
        role: 'user',
        is_premium: false,
        permissions: {
          ad_free: false,
          ai_text_generation: true,
          ai_image_generation: false,
        },
      },
    });
}

/**
 * Mock the subscription GET endpoint.
 */
function mockSubscriptionGet(userId, tier = 'free') {
  return nock(PERMISSIONS_URL)
    .get(`/subscriptions/${userId}`)
    .reply(200, {
      success: true,
      data: { user_id: userId, tier, status: 'active' },
    });
}

/**
 * Mock the subscription 404.
 */
function mockSubscriptionNotFound(userId) {
  return nock(PERMISSIONS_URL)
    .get(`/subscriptions/${userId}`)
    .reply(404, {
      success: false,
      message: 'Not found',
    });
}

/**
 * Clean up all nock interceptors.
 */
function cleanupMocks() {
  nock.cleanAll();
}

module.exports = {
  mockPermissionsGet,
  mockPermissionsNotFound,
  mockPermissionsCreate,
  mockSubscriptionGet,
  mockSubscriptionNotFound,
  cleanupMocks,
};
