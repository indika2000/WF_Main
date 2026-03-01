const rateLimit = require('express-rate-limit');

/**
 * Global rate limiter — 100 requests per minute per IP.
 */
const globalLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    message: 'Too many requests, please try again later',
    error_code: 'RATE_LIMITED',
  },
});

/**
 * Auth endpoint rate limiter — 10 requests per minute per IP.
 */
const authLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    message: 'Too many auth requests, please try again later',
    error_code: 'RATE_LIMITED',
  },
});

/**
 * AI generation rate limiter — 5 requests per minute per IP.
 */
const aiLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 5,
  standardHeaders: true,
  legacyHeaders: false,
  message: {
    success: false,
    message: 'Too many AI generation requests, please try again later',
    error_code: 'RATE_LIMITED',
  },
});

module.exports = { globalLimiter, authLimiter, aiLimiter };
