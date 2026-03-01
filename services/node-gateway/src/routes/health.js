const express = require('express');
const axios = require('axios');
const { SERVICE_CONFIG } = require('../config/services');
const { successResponse } = require('../utils/responses');

const router = express.Router();

/**
 * GET /health
 * Simple alive check for the gateway itself.
 */
router.get('/', (req, res) => {
  return successResponse(res, {
    status: 'ok',
    service: 'gateway',
    timestamp: new Date().toISOString(),
  });
});

/**
 * GET /health/services
 * Aggregated health check — pings each backend service.
 */
router.get('/services', async (req, res) => {
  const services = {};
  let allOk = true;

  for (const [name, config] of Object.entries(SERVICE_CONFIG)) {
    try {
      const response = await axios.get(`${config.url}/health`, {
        timeout: 5000,
      });
      services[name] = response.data?.data?.status || 'ok';
    } catch (error) {
      services[name] = 'unavailable';
      allOk = false;
    }
  }

  return successResponse(res, {
    status: allOk ? 'ok' : 'degraded',
    service: 'gateway',
    services,
    timestamp: new Date().toISOString(),
  });
});

module.exports = router;
