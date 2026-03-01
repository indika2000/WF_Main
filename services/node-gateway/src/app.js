const express = require('express');
const cors = require('cors');
const helmet = require('helmet');

const requestLogger = require('./middleware/requestLogger');
const { globalLimiter } = require('./middleware/rateLimiter');
const errorHandler = require('./middleware/errorHandler');

const authRoutes = require('./routes/auth');
const healthRoutes = require('./routes/health');
const proxyRoutes = require('./routes/proxy');

const app = express();

// === Middleware Stack (order matters) ===

// 1. Request logging
app.use(requestLogger);

// 2. Security headers
app.use(helmet());

// 3. CORS
const corsOrigins = process.env.CORS_ORIGINS
  ? process.env.CORS_ORIGINS.split(',')
  : ['http://localhost:8081', 'http://localhost:19006'];

app.use(cors({
  origin: corsOrigins,
  credentials: true,
}));

// 4. Global rate limiter
app.use(globalLimiter);

// 5. Body parser (JSON, 1MB limit)
app.use(express.json({ limit: '1mb' }));

// === Routes ===

// Health routes (public, no auth)
app.use('/health', healthRoutes);

// Auth routes (public, own rate limiter)
app.use('/api/auth', authRoutes);

// Service proxy routes (authenticated)
app.use('/api', proxyRoutes);

// === Error Handler (must be last) ===
app.use(errorHandler);

module.exports = app;
