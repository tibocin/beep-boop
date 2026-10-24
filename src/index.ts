/**
 * src/index.ts - Beep-Boop v2.0 Application Entry Point
 * 
 * Main entry point for the Beep-Boop conversational AI application.
 * Initializes the Express server, WebSocket connections, and all integrations.
 * 
 * Related Components:
 * - Express.js HTTP server with API routes
 * - Socket.io WebSocket server for real-time features
 * - Integration adapters for external services
 * - Database connections and health checks
 * 
 * Tags: #entrypoint #server #websocket #health
 */

import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { createServer } from 'http';
import { Server as SocketServer } from 'socket.io';

import { config, configWithHelpers } from '@/infrastructure/config';
import { logger } from '@/infrastructure/logging';
import { healthRouter } from '@/interfaces/http/health.routes';
import { chatRouter } from '@/interfaces/http/chat.routes';
import { apiRouter } from '@/interfaces/http/api.routes';
import { WebSocketHandler } from '@/interfaces/websocket/websocket.handler';
import { DatabaseConnection } from '@/infrastructure/database/connection';
import { CacheConnection } from '@/infrastructure/cache/connection';

/**
 * Main application class that orchestrates the entire Beep-Boop system
 * 
 * Responsibilities:
 * - HTTP and WebSocket server initialization
 * - Database and cache connections
 * - Middleware setup and security
 * - Graceful shutdown handling
 */
class BeepBoopApplication {
  private app: express.Application;
  private server: any;
  private io: SocketServer;
  private wsHandler: WebSocketHandler;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.io = new SocketServer(this.server, {
      cors: {
        origin: configWithHelpers.cors.origin,
        credentials: true
      },
      transports: ['websocket', 'polling']
    });
    
    this.wsHandler = new WebSocketHandler(this.io);
  }

  /**
   * Initialize all application components and connections
   * 
   * Sets up middleware, routes, database connections, and health checks.
   * Ensures all external services are reachable before starting.
   */
  async initialize(): Promise<void> {
    logger.info('🚀 Initializing Beep-Boop v2.0...');
    
    try {
      // Setup middleware
      await this.setupMiddleware();
      
      // Setup routes
      await this.setupRoutes();
      
      // Initialize database connections
      await this.initializeDatabase();
      
      // Initialize cache connection
      await this.initializeCache();
      
      // Setup WebSocket handlers
      await this.setupWebSocket();
      
      logger.info('✅ Beep-Boop initialization complete');
    } catch (error) {
      logger.error('❌ Failed to initialize Beep-Boop:', error);
      throw error;
    }
  }

  /**
   * Setup Express.js middleware for security, performance, and functionality
   * 
   * Includes CORS, security headers, compression, rate limiting, and logging.
   */
  private async setupMiddleware(): Promise<void> {
    logger.info('🔧 Setting up middleware...');
    
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'", "'unsafe-inline'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          connectSrc: ["'self'", "ws:", "wss:"],
        },
      },
    }));
    
    // CORS configuration
    this.app.use(cors({
      origin: configWithHelpers.cors.origin,
      credentials: true,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
    }));
    
    // Performance middleware
    this.app.use(compression());
    
    // Rate limiting
    const limiter = rateLimit({
      windowMs: configWithHelpers.rateLimiting.windowMs,
      max: configWithHelpers.rateLimiting.max,
      message: {
        error: 'Too many requests, please try again later',
        retryAfter: '15 minutes'
      },
      standardHeaders: true,
      legacyHeaders: false,
    });
    this.app.use('/api/', limiter);
    
    // Body parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));
    
    // Request logging middleware
    this.app.use((req, res, next) => {
      const startTime = Date.now();
      res.on('finish', () => {
        const duration = Date.now() - startTime;
        logger.info('HTTP Request', {
          method: req.method,
          url: req.url,
          statusCode: res.statusCode,
          duration,
          userAgent: req.get('User-Agent'),
          ip: req.ip
        });
      });
      next();
    });
    
    logger.info('✅ Middleware setup complete');
  }

  /**
   * Setup HTTP routes for API endpoints
   * 
   * Organizes routes by feature area: health, chat, API endpoints.
   */
  private async setupRoutes(): Promise<void> {
    logger.info('🛣️ Setting up routes...');
    
    // Health and monitoring routes
    this.app.use('/health', healthRouter);
    
    // Main API routes
    this.app.use('/api/v1', apiRouter);
    this.app.use('/api/v1/chat', chatRouter);
    
    // Serve static files in production
    if (config.nodeEnv === 'production') {
      this.app.use(express.static('client/dist'));
      
      // Catch-all handler for SPA routing
      this.app.get('*', (req, res) => {
        res.sendFile('index.html', { root: 'client/dist' });
      });
    }
    
    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Route not found',
        method: req.method,
        url: req.originalUrl
      });
    });
    
    // Error handler
    this.app.use((err: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
      logger.error('Unhandled HTTP error:', err);
      res.status(500).json({
        error: 'Internal server error',
        requestId: req.headers['x-request-id'] || 'unknown'
      });
    });
    
    logger.info('✅ Routes setup complete');
  }

  /**
   * Initialize database connections with health checks
   * 
   * Connects to PostgreSQL, Neo4j, and Qdrant with retry logic.
   */
  private async initializeDatabase(): Promise<void> {
    logger.info('🗄️ Initializing database connections...');
    
    try {
      await DatabaseConnection.initialize();
      logger.info('✅ Database connections established');
    } catch (error) {
      logger.error('❌ Database initialization failed:', error);
      throw error;
    }
  }

  /**
   * Initialize Redis cache connection
   * 
   * Sets up Redis connection for sessions, caching, and real-time data.
   */
  private async initializeCache(): Promise<void> {
    logger.info('💾 Initializing cache connection...');
    
    try {
      await CacheConnection.initialize();
      logger.info('✅ Cache connection established');
    } catch (error) {
      logger.error('❌ Cache initialization failed:', error);
      throw error;
    }
  }

  /**
   * Setup WebSocket event handlers for real-time features
   * 
   * Configures Socket.io for streaming, voice, and real-time updates.
   */
  private async setupWebSocket(): Promise<void> {
    logger.info('🔌 Setting up WebSocket handlers...');
    
    this.wsHandler.initialize();
    
    logger.info('✅ WebSocket handlers ready');
  }

  /**
   * Start the HTTP and WebSocket servers
   * 
   * Begins listening on configured port and sets up graceful shutdown.
   */
  async start(): Promise<void> {
    const port = config.port;
    
    return new Promise((resolve, reject) => {
      this.server.listen(port, (err?: Error) => {
        if (err) {
          logger.error('❌ Failed to start server:', err);
          reject(err);
          return;
        }
        
        logger.info(`🎯 Beep-Boop v2.0 running on port ${port}`);
        logger.info(`📚 Environment: ${config.nodeEnv}`);
        logger.info(`🔗 WebSocket enabled on ws://localhost:${port}`);
        logger.info(`📖 API Documentation: http://localhost:${port}/docs`);
        logger.info(`💖 Health Check: http://localhost:${port}/health`);
        
        resolve();
      });
    });
  }

  /**
   * Graceful shutdown handler
   * 
   * Closes all connections cleanly when the application is terminated.
   */
  async shutdown(): Promise<void> {
    logger.info('🛑 Shutting down Beep-Boop...');
    
    try {
      // Close WebSocket connections
      this.io.close();
      
      // Close database connections  
      await DatabaseConnection.close();
      
      // Close cache connections
      await CacheConnection.close();
      
      // Close HTTP server
      this.server.close();
      
      logger.info('✅ Beep-Boop shutdown complete');
    } catch (error) {
      logger.error('❌ Error during shutdown:', error);
      throw error;
    }
  }
}

/**
 * Application startup and graceful shutdown handling
 * 
 * Creates application instance, handles initialization, and manages process signals.
 */
async function main(): Promise<void> {
  const app = new BeepBoopApplication();
  
  try {
    await app.initialize();
    await app.start();
    
    // Graceful shutdown handlers
    process.on('SIGTERM', async () => {
      logger.info('📡 Received SIGTERM, starting graceful shutdown...');
      await app.shutdown();
      process.exit(0);
    });
    
    process.on('SIGINT', async () => {
      logger.info('📡 Received SIGINT, starting graceful shutdown...');
      await app.shutdown();
      process.exit(0);
    });
    
    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      logger.error('💥 Uncaught Exception:', error);
      process.exit(1);
    });
    
    process.on('unhandledRejection', (reason, promise) => {
      logger.error('💥 Unhandled Rejection at:', promise, 'reason:', reason);
      process.exit(1);
    });
    
  } catch (error) {
    logger.error('💥 Failed to start Beep-Boop:', error);
    process.exit(1);
  }
}

// Start the application
if (require.main === module) {
  main().catch((error) => {
    console.error('Fatal error starting application:', error);
    process.exit(1);
  });
}

export { BeepBoopApplication };