const SERVICE_CONFIG = {
  permissions: {
    url: process.env.PERMISSIONS_SERVICE_URL || 'http://permissions:5003',
    timeout: 10000,
    pathPrefix: '/permissions',
  },
  commerce: {
    url: process.env.COMMERCE_SERVICE_URL || 'http://commerce:3004',
    timeout: 30000,
    pathPrefix: '',  // Commerce routes are /cart/*, /checkout/*, etc. — no common prefix
  },
  images: {
    url: process.env.IMAGE_SERVICE_URL || 'http://image-service:5001',
    timeout: 60000,
    pathPrefix: '/images',
  },
  llm: {
    url: process.env.LLM_SERVICE_URL || 'http://llm-service:5000',
    timeout: 120000,
    pathPrefix: '',  // LLM routes are /generate/*, /providers/* — no common prefix
  },
  chat: {
    url: process.env.LLM_SERVICE_URL || 'http://llm-service:5000',
    timeout: 120000,
    pathPrefix: '/chat',  // Chat routes are /chat/* on the LLM service
  },
  characters: {
    url: process.env.CHARACTER_SERVICE_URL || 'http://character:5002',
    timeout: 30000,
    pathPrefix: '',  // Character routes are /generate, /creatures/*, /collection/*, /supply
  },
};

module.exports = { SERVICE_CONFIG };
