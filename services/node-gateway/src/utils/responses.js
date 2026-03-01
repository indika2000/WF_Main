/**
 * Send a standardized success response.
 */
function successResponse(res, data, message = 'Success', statusCode = 200) {
  return res.status(statusCode).json({
    success: true,
    message,
    data,
  });
}

/**
 * Send a standardized error response.
 */
function errorResponse(res, message, errorCode, statusCode = 400, detail = null) {
  const body = {
    success: false,
    message,
    error_code: errorCode,
  };
  if (detail) {
    body.detail = detail;
  }
  return res.status(statusCode).json(body);
}

module.exports = { successResponse, errorResponse };
