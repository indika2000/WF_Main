/**
 * Mock Firebase Admin SDK for testing.
 * Call before requiring app modules.
 */
function mockFirebaseVerify(decodedToken = { uid: 'test-user', email: 'test@example.com' }) {
  jest.mock('../../src/config/firebase', () => ({
    auth: {
      verifyIdToken: jest.fn().mockResolvedValue(decodedToken),
    },
  }));
}

/**
 * Mock Firebase to reject tokens.
 */
function mockFirebaseReject(error = new Error('Invalid token')) {
  jest.mock('../../src/config/firebase', () => ({
    auth: {
      verifyIdToken: jest.fn().mockRejectedValue(error),
    },
  }));
}

module.exports = { mockFirebaseVerify, mockFirebaseReject };
