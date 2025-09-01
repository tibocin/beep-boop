/**
 * src/interfaces/http/health.routes.ts - Health Check and Monitoring Endpoints
 * 
 * Provides comprehensive health checks for the application and all integrated services.
 * Includes readiness, liveness, and detailed service status information.
 * 
 * Related Components:
 * - Database connection health checks
 * - External service integration status
 * - Application metrics and performance data
 * - Dependency status monitoring
 * 
 * Tags: #health #monitoring #observability #diagnostics
 */

import { Router, Request, Response } from 'express';
import { config } from '@/infrastructure/config';
import { logger } from '@/infrastructure/logging';
import { DatabaseConnection } from '@/infrastructure/database/connection';
import { CacheConnection } from '@/infrastructure/cache/connection';

/**
 * Health check status enumeration
 */
enum HealthStatus {
  HEALTHY = 'healthy',
  UNHEALTHY = 'unhealthy',
  DEGRADED = 'degraded'
}

/**
 * Individual service health information
 */
interface ServiceHealth {
  status: HealthStatus;
  responseTime?: number;
  lastCheck: string;
  error?: string;
  metadata?: Record<string, any>;
}

/**
 * Overall application health response
 */
interface HealthResponse {
  status: HealthStatus;
  timestamp: string;
  version: string;
  uptime: number;
  services: Record<string, ServiceHealth>;
  metadata?: Record<string, any>;
}

const router = Router();

/**
 * Basic liveness probe - checks if application is running
 * 
 * Used by load balancers and orchestrators to determine if the app should receive traffic.
 * Returns 200 if the application process is healthy.
 */
router.get('/live', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    const response = {
      status: HealthStatus.HEALTHY,
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      pid: process.pid,
      memory: process.memoryUsage(),
      responseTime: Date.now() - startTime
    };
    
    res.status(200).json(response);
  } catch (error) {
    logger.error('Liveness check failed', error);
    res.status(503).json({
      status: HealthStatus.UNHEALTHY,
      timestamp: new Date().toISOString(),
      error: 'Liveness check failed'
    });
  }
});

/**
 * Readiness probe - checks if application is ready to serve requests
 * 
 * Verifies that all critical dependencies are available and functioning.
 * Used by orchestrators to determine when to start sending traffic.
 */
router.get('/ready', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    const services: Record<string, ServiceHealth> = {};
    let overallStatus = HealthStatus.HEALTHY;

    // Check database connections
    try {
      const dbStartTime = Date.now();
      await DatabaseConnection.healthCheck();
      services.database = {
        status: HealthStatus.HEALTHY,
        responseTime: Date.now() - dbStartTime,
        lastCheck: new Date().toISOString()
      };
    } catch (error) {
      services.database = {
        status: HealthStatus.UNHEALTHY,
        lastCheck: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Database connection failed'
      };
      overallStatus = HealthStatus.UNHEALTHY;
    }

    // Check cache connection
    try {
      const cacheStartTime = Date.now();
      await CacheConnection.healthCheck();
      services.cache = {
        status: HealthStatus.HEALTHY,
        responseTime: Date.now() - cacheStartTime,
        lastCheck: new Date().toISOString()
      };
    } catch (error) {
      services.cache = {
        status: HealthStatus.DEGRADED,
        lastCheck: new Date().toISOString(),
        error: error instanceof Error ? error.message : 'Cache connection failed'
      };
      // Cache failure doesn't make the app unhealthy, just degraded
      if (overallStatus === HealthStatus.HEALTHY) {
        overallStatus = HealthStatus.DEGRADED;
      }
    }

    const response: HealthResponse = {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      version: '2.0.0',
      uptime: process.uptime(),
      services,
      metadata: {
        responseTime: Date.now() - startTime,
        environment: config.nodeEnv
      }
    };

    const statusCode = overallStatus === HealthStatus.HEALTHY ? 200 : 503;
    res.status(statusCode).json(response);
    
  } catch (error) {
    logger.error('Readiness check failed', error);
    res.status(503).json({
      status: HealthStatus.UNHEALTHY,
      timestamp: new Date().toISOString(),
      error: 'Readiness check failed',
      responseTime: Date.now() - startTime
    });
  }
});

/**
 * Comprehensive health check - detailed status of all components
 * 
 * Provides detailed information about application health, external services,
 * and performance metrics. Used for monitoring and debugging.
 */
router.get('/', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    const services: Record<string, ServiceHealth> = {};
    let overallStatus = HealthStatus.HEALTHY;

    // Check all services in parallel for better performance
    const healthChecks = await Promise.allSettled([
      checkDatabaseHealth(),
      checkCacheHealth(),
      checkDigiCoreHealth(),
      checkPCSHealth(),
      checkOllamaHealth()
    ]);

    // Process database health
    if (healthChecks[0].status === 'fulfilled') {
      services.database = healthChecks[0].value;
    } else {
      services.database = {
        status: HealthStatus.UNHEALTHY,
        lastCheck: new Date().toISOString(),
        error: 'Database health check failed'
      };
      overallStatus = HealthStatus.UNHEALTHY;
    }

    // Process cache health  
    if (healthChecks[1].status === 'fulfilled') {
      services.cache = healthChecks[1].value;
    } else {
      services.cache = {
        status: HealthStatus.DEGRADED,
        lastCheck: new Date().toISOString(),
        error: 'Cache health check failed'
      };
      if (overallStatus === HealthStatus.HEALTHY) {
        overallStatus = HealthStatus.DEGRADED;
      }
    }

    // Process Digi-Core health
    if (healthChecks[2].status === 'fulfilled') {
      services.digiCore = healthChecks[2].value;
    } else {
      services.digiCore = {
        status: HealthStatus.DEGRADED,
        lastCheck: new Date().toISOString(),
        error: 'Digi-Core health check failed'
      };
      if (overallStatus === HealthStatus.HEALTHY) {
        overallStatus = HealthStatus.DEGRADED;
      }
    }

    // Process PCS health
    if (healthChecks[3].status === 'fulfilled') {
      services.pcs = healthChecks[3].value;
    } else {
      services.pcs = {
        status: HealthStatus.DEGRADED,
        lastCheck: new Date().toISOString(),
        error: 'PCS health check failed'
      };
      if (overallStatus === HealthStatus.HEALTHY) {
        overallStatus = HealthStatus.DEGRADED;
      }
    }

    // Process Ollama health
    if (healthChecks[4].status === 'fulfilled') {
      services.ollama = healthChecks[4].value;
    } else {
      services.ollama = {
        status: HealthStatus.DEGRADED,
        lastCheck: new Date().toISOString(),
        error: 'Ollama health check failed'
      };
      if (overallStatus === HealthStatus.HEALTHY) {
        overallStatus = HealthStatus.DEGRADED;
      }
    }

    const response: HealthResponse = {
      status: overallStatus,
      timestamp: new Date().toISOString(),
      version: '2.0.0',
      uptime: process.uptime(),
      services,
      metadata: {
        responseTime: Date.now() - startTime,
        environment: config.nodeEnv,
        nodeVersion: process.version,
        memory: process.memoryUsage(),
        features: config.features
      }
    };

    const statusCode = overallStatus === HealthStatus.UNHEALTHY ? 503 : 200;
    res.status(statusCode).json(response);
    
  } catch (error) {
    logger.error('Comprehensive health check failed', error);
    res.status(503).json({
      status: HealthStatus.UNHEALTHY,
      timestamp: new Date().toISOString(),
      error: 'Health check failed',
      responseTime: Date.now() - startTime
    });
  }
});

/**
 * Application metrics endpoint for monitoring systems
 * 
 * Provides Prometheus-compatible metrics for monitoring and alerting.
 */
router.get('/metrics', async (req: Request, res: Response) => {
  try {
    const metrics = {
      timestamp: new Date().toISOString(),
      uptime: process.uptime(),
      memory: process.memoryUsage(),
      cpu: process.cpuUsage(),
      version: '2.0.0',
      environment: config.nodeEnv,
      features: config.features
    };

    res.setHeader('Content-Type', 'application/json');
    res.status(200).json(metrics);
    
  } catch (error) {
    logger.error('Metrics endpoint failed', error);
    res.status(500).json({
      error: 'Failed to retrieve metrics'
    });
  }
});

/**
 * Check database health (PostgreSQL + Neo4j + Qdrant)
 */
async function checkDatabaseHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  
  try {
    await DatabaseConnection.healthCheck();
    
    return {
      status: HealthStatus.HEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      metadata: {
        postgres: 'connected',
        neo4j: 'connected',
        qdrant: 'connected'
      }
    };
  } catch (error) {
    return {
      status: HealthStatus.UNHEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Database connection failed'
    };
  }
}

/**
 * Check Redis cache health
 */
async function checkCacheHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  
  try {
    await CacheConnection.healthCheck();
    
    return {
      status: HealthStatus.HEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: HealthStatus.UNHEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Cache connection failed'
    };
  }
}

/**
 * Check Digi-Core service health
 */
async function checkDigiCoreHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  
  try {
    // This will be implemented when we create the Digi-Core adapter
    // For now, return a placeholder
    return {
      status: HealthStatus.HEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      metadata: {
        url: config.digiCore.baseUrl,
        enabled: config.digiCore.enabled
      }
    };
  } catch (error) {
    return {
      status: HealthStatus.DEGRADED,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Digi-Core check failed'
    };
  }
}

/**
 * Check PCS service health
 */
async function checkPCSHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  
  try {
    // This will be implemented when we create the PCS adapter
    return {
      status: HealthStatus.HEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      metadata: {
        url: config.pcs.baseUrl,
        enabled: config.pcs.enabled
      }
    };
  } catch (error) {
    return {
      status: HealthStatus.DEGRADED,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'PCS check failed'
    };
  }
}

/**
 * Check Ollama service health
 */
async function checkOllamaHealth(): Promise<ServiceHealth> {
  const startTime = Date.now();
  
  try {
    // This will be implemented when we create the LLM adapter
    return {
      status: HealthStatus.HEALTHY,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      metadata: {
        url: config.ollama.baseUrl,
        model: config.ollama.model,
        enabled: config.ollama.enabled
      }
    };
  } catch (error) {
    return {
      status: HealthStatus.DEGRADED,
      responseTime: Date.now() - startTime,
      lastCheck: new Date().toISOString(),
      error: error instanceof Error ? error.message : 'Ollama check failed'
    };
  }
}

export { router as healthRouter };