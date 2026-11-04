/**
 * src/infrastructure/logging/index.ts - Structured Logging System
 * 
 * Centralized logging configuration using Pino for high-performance structured logging.
 * Provides correlation IDs, proper log levels, and production-ready log formatting.
 * 
 * Related Components:
 * - Request correlation tracking
 * - Error logging and stack traces
 * - Performance metrics logging
 * - Development vs production log formats
 * 
 * Tags: #logging #observability #correlation #performance
 */

import pino from 'pino';
import { config } from '@/infrastructure/config';

/**
 * Log correlation context for tracking requests across services
 * 
 * Provides request IDs and user context for distributed tracing.
 */
interface LogContext {
  requestId?: string;
  userId?: string;
  conversationId?: string;
  sessionId?: string;
  operation?: string;
}

/**
 * Performance metrics for operation timing and monitoring
 */
interface PerformanceMetrics {
  operation: string;
  duration: number;
  success: boolean;
  metadata?: Record<string, any>;
}

/**
 * Create Pino logger instance with appropriate configuration
 * 
 * Uses different formatters for development (pretty) vs production (JSON).
 * Includes correlation ID injection and performance timing helpers.
 */
function createLogger() {
  const isDevelopment = config.nodeEnv === 'development';
  
  const baseConfig: pino.LoggerOptions = {
    level: config.logLevel,
    name: 'beep-boop-v2',
    timestamp: () => `,"timestamp":"${new Date().toISOString()}"`,
    formatters: {
      level: (label) => ({ level: label }),
      bindings: (bindings) => ({
        pid: bindings.pid,
        hostname: bindings.hostname,
        name: bindings.name
      })
    }
  };

  if (isDevelopment) {
    return pino({
      ...baseConfig,
      transport: {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'HH:MM:ss.l',
          ignore: 'pid,hostname'
        }
      }
    });
  }

  return pino(baseConfig);
}

/**
 * Main logger instance for application-wide use
 */
const logger = createLogger();

/**
 * Enhanced logger with correlation context support
 * 
 * Provides methods for logging with request correlation and performance tracking.
 */
class ContextualLogger {
  private context: LogContext = {};

  /**
   * Set correlation context for all subsequent log messages
   */
  setContext(context: Partial<LogContext>): void {
    this.context = { ...this.context, ...context };
  }

  /**
   * Clear correlation context
   */
  clearContext(): void {
    this.context = {};
  }

  /**
   * Log with current context
   */
  private logWithContext(level: string, message: string, meta?: any): void {
    const logData = {
      ...this.context,
      ...meta
    };
    
    (logger as any)[level](logData, message);
  }

  /**
   * Debug level logging
   */
  debug(message: string, meta?: any): void {
    this.logWithContext('debug', message, meta);
  }

  /**
   * Info level logging
   */
  info(message: string, meta?: any): void {
    this.logWithContext('info', message, meta);
  }

  /**
   * Warning level logging
   */
  warn(message: string, meta?: any): void {
    this.logWithContext('warn', message, meta);
  }

  /**
   * Error level logging with stack trace support
   */
  error(message: string, error?: Error | any, meta?: any): void {
    const errorData = {
      ...meta,
      error: error instanceof Error ? {
        name: error.name,
        message: error.message,
        stack: error.stack
      } : error
    };
    
    this.logWithContext('error', message, errorData);
  }

  /**
   * Log performance metrics for operations
   */
  performance(metrics: PerformanceMetrics): void {
    this.info('Performance Metric', {
      type: 'performance',
      operation: metrics.operation,
      duration: metrics.duration,
      success: metrics.success,
      ...metrics.metadata
    });
  }

  /**
   * Create a performance timer for operation measurement
   */
  startTimer(operation: string): () => void {
    const startTime = Date.now();
    
    return (success: boolean = true, metadata?: Record<string, any>) => {
      const duration = Date.now() - startTime;
      this.performance({
        operation,
        duration,
        success,
        metadata
      });
    };
  }

  /**
   * Log API request/response for debugging and monitoring
   */
  apiCall(
    method: string,
    url: string,
    statusCode: number,
    duration: number,
    meta?: any
  ): void {
    const level = statusCode >= 400 ? 'warn' : 'info';
    this.logWithContext(level, `API Call: ${method} ${url}`, {
      type: 'api_call',
      method,
      url,
      statusCode,
      duration,
      ...meta
    });
  }

  /**
   * Log WebSocket events for real-time monitoring
   */
  websocket(event: string, data?: any): void {
    this.info(`WebSocket: ${event}`, {
      type: 'websocket',
      event,
      data
    });
  }

  /**
   * Log memory operations for relationship tracking
   */
  memory(operation: string, data?: any): void {
    this.info(`Memory: ${operation}`, {
      type: 'memory',
      operation,
      data
    });
  }

  /**
   * Log integration events for external service monitoring
   */
  integration(service: string, operation: string, success: boolean, meta?: any): void {
    const level = success ? 'info' : 'warn';
    this.logWithContext(level, `Integration: ${service} ${operation}`, {
      type: 'integration',
      service,
      operation,
      success,
      ...meta
    });
  }
}

/**
 * Create contextual logger instance for request-scoped logging
 */
export function createContextualLogger(initialContext?: LogContext): ContextualLogger {
  const contextLogger = new ContextualLogger();
  if (initialContext) {
    contextLogger.setContext(initialContext);
  }
  return contextLogger;
}

/**
 * Express middleware for request correlation and logging
 */
export function requestLoggingMiddleware(
  req: any,
  res: any,
  next: any
): void {
  // Generate request ID if not present
  const requestId = req.headers['x-request-id'] || `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  
  // Add request ID to headers
  req.requestId = requestId;
  res.setHeader('X-Request-ID', requestId);
  
  // Create contextual logger for this request
  req.logger = createContextualLogger({
    requestId,
    operation: `${req.method} ${req.path}`
  });
  
  // Log request start
  req.logger.info('Request started', {
    method: req.method,
    url: req.url,
    userAgent: req.get('User-Agent'),
    ip: req.ip
  });
  
  next();
}

/**
 * Default logger instance for general application logging
 */
export { logger };

/**
 * Export logger types for type safety
 */
export type { LogContext, PerformanceMetrics };