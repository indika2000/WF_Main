// Set env before imports
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-for-testing';

// Mock firebase
jest.mock('../../src/config/firebase', () => ({
  auth: { verifyIdToken: jest.fn() },
}));

const request = require('supertest');
const app = require('../../src/app');

describe('Rate Limiting', () => {
  test('allows requests within global limit', async () => {
    const res = await request(app)
      .get('/health')
      .expect(200);

    expect(res.body.success).toBe(true);
  });

  test('returns 429 after exceeding auth rate limit', async () => {
    // Auth limiter is 10 per minute
    const promises = [];
    for (let i = 0; i < 12; i++) {
      promises.push(
        request(app)
          .post('/api/auth/token')
          .set('Authorization', 'Bearer dev-bypass')
      );
    }

    const results = await Promise.all(promises);
    const tooManyRequests = results.filter(r => r.status === 429);

    // At least some should be rate-limited
    expect(tooManyRequests.length).toBeGreaterThan(0);
    expect(tooManyRequests[0].body.error_code).toBe('RATE_LIMITED');
  });
});
