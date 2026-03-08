// Set env before imports
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-for-testing';
process.env.INTERNAL_API_KEY = 'test-api-key';
process.env.PERMISSIONS_SERVICE_URL = 'http://permissions:5003';

// Mock firebase before requiring app
jest.mock('../../src/config/firebase', () => ({
  auth: {
    verifyIdToken: jest.fn(),
  },
}));

const request = require('supertest');
const nock = require('nock');
const app = require('../../src/app');
const { verifyToken } = require('../../src/utils/jwt');
const firebase = require('../../src/config/firebase');

const PERMISSIONS_URL = 'http://permissions:5003';

beforeEach(() => {
  // Restore mock after resetMocks clears it each test
  firebase.auth.verifyIdToken.mockResolvedValue({
    uid: 'test-user-123',
    email: 'test@example.com',
  });
});

afterEach(() => {
  nock.cleanAll();
});

describe('POST /api/auth/token', () => {
  test('exchanges Firebase token for internal JWT', async () => {
    // Mock permissions service
    nock(PERMISSIONS_URL)
      .get('/permissions/test-user-123')
      .reply(200, {
        success: true,
        data: {
          user_id: 'test-user-123',
          role: 'user',
          is_premium: false,
          permissions: { ad_free: false, ai_text_generation: true },
        },
      });

    nock(PERMISSIONS_URL)
      .get('/subscriptions/test-user-123')
      .reply(200, {
        success: true,
        data: { tier: 'free', status: 'active' },
      });

    const res = await request(app)
      .post('/api/auth/token')
      .set('Authorization', 'Bearer valid-firebase-token')
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data.token).toBeDefined();
    expect(res.body.data.user.uid).toBe('test-user-123');
    expect(res.body.data.user.email).toBe('test@example.com');

    // Verify the returned JWT is valid
    const decoded = verifyToken(res.body.data.token);
    expect(decoded.uid).toBe('test-user-123');
    expect(decoded.permissions.ai_text_generation).toBe(true);
  });

  test('creates new user on first auth (404 from permissions)', async () => {
    // First call returns 404
    nock(PERMISSIONS_URL)
      .get('/permissions/test-user-123')
      .reply(404, { success: false });

    // Then creates the user
    nock(PERMISSIONS_URL)
      .post('/permissions/test-user-123')
      .reply(201, {
        success: true,
        data: {
          user_id: 'test-user-123',
          role: 'user',
          is_premium: false,
          permissions: { ad_free: false, ai_text_generation: true },
        },
      });

    nock(PERMISSIONS_URL)
      .get('/subscriptions/test-user-123')
      .reply(404, { success: false });

    const res = await request(app)
      .post('/api/auth/token')
      .set('Authorization', 'Bearer valid-firebase-token')
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data.token).toBeDefined();
  });

  test('rejects missing auth header', async () => {
    const res = await request(app)
      .post('/api/auth/token')
      .expect(401);

    expect(res.body.success).toBe(false);
    expect(res.body.error_code).toBe('AUTH_REQUIRED');
  });

  test('dev-bypass works in test env', async () => {
    nock(PERMISSIONS_URL)
      .get('/permissions/dev-user')
      .reply(200, {
        success: true,
        data: {
          user_id: 'dev-user',
          role: 'user',
          is_premium: false,
          permissions: { ai_text_generation: true },
        },
      });

    nock(PERMISSIONS_URL)
      .get('/subscriptions/dev-user')
      .reply(200, {
        success: true,
        data: { tier: 'free', status: 'active' },
      });

    const res = await request(app)
      .post('/api/auth/token')
      .set('Authorization', 'Bearer dev-bypass')
      .expect(200);

    expect(res.body.data.user.uid).toBe('dev-user');
  });
});

describe('GET /api/auth/verify', () => {
  test('verifies a valid internal JWT', async () => {
    // First get a token
    nock(PERMISSIONS_URL)
      .get('/permissions/test-user-123')
      .reply(200, {
        success: true,
        data: {
          user_id: 'test-user-123',
          role: 'user',
          is_premium: false,
          permissions: {},
        },
      });

    nock(PERMISSIONS_URL)
      .get('/subscriptions/test-user-123')
      .reply(200, {
        success: true,
        data: { tier: 'free', status: 'active' },
      });

    const authRes = await request(app)
      .post('/api/auth/token')
      .set('Authorization', 'Bearer valid-firebase-token');

    const token = authRes.body.data.token;

    // Verify it
    const res = await request(app)
      .get('/api/auth/verify')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data.uid).toBe('test-user-123');
  });

  test('rejects invalid token', async () => {
    const res = await request(app)
      .get('/api/auth/verify')
      .set('Authorization', 'Bearer invalid-token')
      .expect(401);

    expect(res.body.success).toBe(false);
  });
});
