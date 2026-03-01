const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'change-me';

/**
 * Sign a JWT with HS256.
 * @param {Object} payload - Token payload
 * @param {string} expiresIn - Expiration (default from env or '1h')
 * @returns {string} Signed JWT
 */
function signToken(payload, expiresIn) {
  return jwt.sign(payload, JWT_SECRET, {
    algorithm: 'HS256',
    expiresIn: expiresIn || process.env.JWT_EXPIRY || '1h',
  });
}

/**
 * Verify and decode a JWT.
 * @param {string} token - JWT to verify
 * @returns {Object} Decoded payload
 * @throws {Error} If token is invalid or expired
 */
function verifyToken(token) {
  return jwt.verify(token, JWT_SECRET, { algorithms: ['HS256'] });
}

module.exports = { signToken, verifyToken };
