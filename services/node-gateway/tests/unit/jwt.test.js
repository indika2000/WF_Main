// Set env before imports
process.env.JWT_SECRET = 'test-jwt-secret-for-testing';

const { signToken, verifyToken } = require('../../src/utils/jwt');

describe('JWT Utils', () => {
  const payload = { uid: 'user123', email: 'test@example.com', role: 'user' };

  test('signs and verifies a valid token', () => {
    const token = signToken(payload);
    const decoded = verifyToken(token);
    expect(decoded.uid).toBe('user123');
    expect(decoded.email).toBe('test@example.com');
    expect(decoded.role).toBe('user');
  });

  test('token includes iat and exp', () => {
    const token = signToken(payload);
    const decoded = verifyToken(token);
    expect(decoded.iat).toBeDefined();
    expect(decoded.exp).toBeDefined();
    expect(decoded.exp).toBeGreaterThan(decoded.iat);
  });

  test('respects custom expiry', () => {
    const token = signToken(payload, '2h');
    const decoded = verifyToken(token);
    // 2 hours = 7200 seconds
    expect(decoded.exp - decoded.iat).toBe(7200);
  });

  test('rejects expired token', () => {
    const token = signToken(payload, '0s');
    expect(() => verifyToken(token)).toThrow();
  });

  test('rejects tampered token', () => {
    const token = signToken(payload) + 'tampered';
    expect(() => verifyToken(token)).toThrow();
  });

  test('includes permissions in payload', () => {
    const fullPayload = {
      ...payload,
      permissions: { ad_free: true, ai_text_generation: true },
      is_premium: true,
    };
    const token = signToken(fullPayload);
    const decoded = verifyToken(token);
    expect(decoded.permissions.ad_free).toBe(true);
    expect(decoded.is_premium).toBe(true);
  });
});
