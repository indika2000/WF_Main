/**
 * Request logging middleware.
 * Logs: method, path, status, duration.
 */
function requestLogger(req, res, next) {
  const start = Date.now();

  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(
      `[GATEWAY] ${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`
    );
  });

  next();
}

module.exports = requestLogger;
