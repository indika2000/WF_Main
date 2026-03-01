/**
 * Global Express error handler.
 * Must be registered LAST in middleware stack (4 parameters required).
 */
function errorHandler(err, req, res, _next) {
  console.error('[GATEWAY] Unhandled error:', err.message);

  if (process.env.NODE_ENV !== 'production') {
    console.error(err.stack);
  }

  const statusCode = err.statusCode || err.status || 500;

  res.status(statusCode).json({
    success: false,
    message: process.env.NODE_ENV === 'production'
      ? 'Internal server error'
      : err.message || 'Internal server error',
    error_code: 'INTERNAL_ERROR',
  });
}

module.exports = errorHandler;
