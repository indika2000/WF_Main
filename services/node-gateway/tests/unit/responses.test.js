const { successResponse, errorResponse } = require('../../src/utils/responses');

// Mock Express response object
function mockRes() {
  const res = {
    statusCode: null,
    body: null,
    status(code) {
      res.statusCode = code;
      return res;
    },
    json(data) {
      res.body = data;
      return res;
    },
  };
  return res;
}

describe('Response Helpers', () => {
  describe('successResponse', () => {
    test('returns correct format with defaults', () => {
      const res = mockRes();
      successResponse(res, { id: '123' });
      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.message).toBe('Success');
      expect(res.body.data.id).toBe('123');
    });

    test('accepts custom message and status', () => {
      const res = mockRes();
      successResponse(res, null, 'Created', 201);
      expect(res.statusCode).toBe(201);
      expect(res.body.message).toBe('Created');
    });
  });

  describe('errorResponse', () => {
    test('returns correct format', () => {
      const res = mockRes();
      errorResponse(res, 'Not found', 'NOT_FOUND', 404);
      expect(res.statusCode).toBe(404);
      expect(res.body.success).toBe(false);
      expect(res.body.message).toBe('Not found');
      expect(res.body.error_code).toBe('NOT_FOUND');
    });

    test('includes detail when provided', () => {
      const res = mockRes();
      errorResponse(res, 'Error', 'ERR', 400, 'Extra details');
      expect(res.body.detail).toBe('Extra details');
    });

    test('excludes detail when not provided', () => {
      const res = mockRes();
      errorResponse(res, 'Error', 'ERR', 400);
      expect(res.body.detail).toBeUndefined();
    });
  });
});
