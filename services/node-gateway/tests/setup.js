// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test-jwt-secret-for-testing';
process.env.INTERNAL_API_KEY = 'test-api-key';
process.env.FIREBASE_PROJECT_ID = 'test-project';
process.env.FIREBASE_CLIENT_EMAIL = 'test@test.iam.gserviceaccount.com';
process.env.FIREBASE_PRIVATE_KEY = 'test-key';
process.env.PERMISSIONS_SERVICE_URL = 'http://permissions:5003';
process.env.REDIS_URL = 'redis://localhost:6379';
