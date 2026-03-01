// Set env before imports
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-for-testing';

// Mock firebase
jest.mock('../../src/config/firebase', () => ({
  auth: { verifyIdToken: jest.fn() },
}));

const request = require('supertest');
const nock = require('nock');
const app = require('../../src/app');

afterEach(() => {
  nock.cleanAll();
});

describe('GET /health', () => {
  test('returns ok status', async () => {
    const res = await request(app)
      .get('/health')
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.data.status).toBe('ok');
    expect(res.body.data.service).toBe('gateway');
  });
});

describe('GET /health/services', () => {
  test('reports all services healthy', async () => {
    // Mock all service health endpoints
    nock('http://permissions:5003')
      .get('/health')
      .reply(200, { data: { status: 'ok' } });

    nock('http://commerce:3004')
      .get('/health')
      .reply(200, { data: { status: 'ok' } });

    nock('http://image-service:5001')
      .get('/health')
      .reply(200, { data: { status: 'ok' } });

    nock('http://llm-service:5000')
      .get('/health')
      .reply(200, { data: { status: 'ok' } });

    const res = await request(app)
      .get('/health/services')
      .expect(200);

    expect(res.body.data.status).toBe('ok');
    expect(res.body.data.services.permissions).toBe('ok');
  });

  test('reports degraded when service is unavailable', async () => {
    nock('http://permissions:5003')
      .get('/health')
      .reply(200, { data: { status: 'ok' } });

    // Other services are down
    nock('http://commerce:3004')
      .get('/health')
      .replyWithError('Connection refused');

    nock('http://image-service:5001')
      .get('/health')
      .replyWithError('Connection refused');

    nock('http://llm-service:5000')
      .get('/health')
      .replyWithError('Connection refused');

    const res = await request(app)
      .get('/health/services')
      .expect(200);

    expect(res.body.data.status).toBe('degraded');
    expect(res.body.data.services.permissions).toBe('ok');
    expect(res.body.data.services.commerce).toBe('unavailable');
  });
});
