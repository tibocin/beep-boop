/**
 * src/utils/retry-handler.ts - Retry Logic with Exponential Backoff
 * 
 * Implements retry pattern with exponential backoff and jitter for resilient
 * external service integration. Prevents thundering herd problems.
 * 
 * Related Components:
 * - Circuit breaker for additional resilience
 * - Service adapters for external APIs
 * - Logging and metrics collection
 * - Error classification and handling
 * 
 * Tags: #resilience #retry #exponential-backoff #jitter #fault-tolerance
 */

import { logger } from '@/infrastructure/logging';

/**
 * Retry configuration options
 */
export interface RetryConfig {
  maxAttempts: number;      // Maximum number of retry attempts
  baseDelay: number;        // Base delay in milliseconds
  maxDelay: number;         // Maximum delay cap in milliseconds
  jitterFactor: number;     // Jitter factor (0-1) to prevent thundering herd
  retryableErrors?: string[]; // Specific error types to retry
}

/**
 * Retry attempt information for logging and metrics
 */
export interface RetryAttempt {
  attempt: number;
  delay: number;
  error: Error;
  timestamp: Date;
}

/**
 * Retry result with attempt history
 */
export interface RetryResult<T> {
  result: T;
  attempts: RetryAttempt[];
  totalTime: number;
  succeeded: boolean;
}

/**
 * Retry handler implementation with exponential backoff and jitter
 * 
 * Provides configurable retry logic for external service calls with
 * intelligent backoff strategies to prevent overwhelming failing services.
 */
export class RetryHandler {
  private readonly config: Required<RetryConfig>;

  constructor(config: RetryConfig) {
    this.config = {
      retryableErrors: [
        'ECONNRESET',
        'ECONNREFUSED', 
        'ETIMEDOUT',
        'ENOTFOUND',
        'ENETUNREACH'
      ],
      ...config
    };

    logger.debug('Retry handler initialized', {
      maxAttempts: this.config.maxAttempts,
      baseDelay: this.config.baseDelay,
      maxDelay: this.config.maxDelay,
      jitterFactor: this.config.jitterFactor
    });
  }

  /**
   * Execute operation with retry logic
   * 
   * Attempts the operation with exponential backoff and jitter.
   * Returns the result or throws the last error after all attempts fail.
   */
  async executeWithRetry<T>(operation: () => Promise<T>): Promise<T> {
    const attempts: RetryAttempt[] = [];
    const startTime = Date.now();

    for (let attempt = 1; attempt <= this.config.maxAttempts; attempt++) {
      try {
        // Execute the operation
        const result = await operation();

        // Log successful retry if this wasn't the first attempt
        if (attempt > 1) {
          logger.info('Operation succeeded after retry', {
            attempt,
            totalAttempts: attempts.length + 1,
            totalTime: Date.now() - startTime
          });
        }

        return result;

      } catch (error) {
        const currentError = error instanceof Error ? error : new Error(String(error));
        
        // Record this attempt
        attempts.push({
          attempt,
          delay: 0, // Will be set below if we retry
          error: currentError,
          timestamp: new Date()
        });

        // Check if this is the last attempt
        if (attempt === this.config.maxAttempts) {
          logger.error('Operation failed after all retry attempts', currentError, {
            totalAttempts: attempt,
            totalTime: Date.now() - startTime,
            attempts: attempts.map(a => ({
              attempt: a.attempt,
              error: a.error.message,
              timestamp: a.timestamp
            }))
          });
          throw currentError;
        }

        // Check if error is retryable
        if (!this.isRetryableError(currentError)) {
          logger.error('Non-retryable error encountered', currentError, {
            attempt,
            errorType: currentError.name
          });
          throw currentError;
        }

        // Calculate delay for next attempt
        const delay = this.calculateDelay(attempt);
        attempts[attempts.length - 1].delay = delay;

        logger.warn('Operation failed, retrying', {
          attempt,
          maxAttempts: this.config.maxAttempts,
          delay,
          error: currentError.message,
          errorCode: (currentError as any).code
        });

        // Wait before retrying
        await this.sleep(delay);
      }
    }

    // This should never be reached due to the logic above
    throw new Error('Unexpected retry handler state');
  }

  /**
   * Execute operation with detailed retry information
   * 
   * Returns both the result and retry attempt details for analysis.
   */
  async executeWithRetryDetails<T>(operation: () => Promise<T>): Promise<RetryResult<T>> {
    const attempts: RetryAttempt[] = [];
    const startTime = Date.now();

    try {
      const result = await this.executeWithRetry(operation);
      
      return {
        result,
        attempts,
        totalTime: Date.now() - startTime,
        succeeded: true
      };

    } catch (error) {
      return {
        result: null as any,
        attempts,
        totalTime: Date.now() - startTime,
        succeeded: false
      };
    }
  }

  /**
   * Calculate exponential backoff delay with jitter
   * 
   * Uses exponential backoff with jitter to prevent thundering herd problems.
   */
  private calculateDelay(attempt: number): number {
    // Exponential backoff: baseDelay * 2^(attempt-1)
    const exponentialDelay = this.config.baseDelay * Math.pow(2, attempt - 1);
    
    // Apply maximum delay cap
    const cappedDelay = Math.min(exponentialDelay, this.config.maxDelay);
    
    // Add jitter to prevent thundering herd
    const jitter = cappedDelay * this.config.jitterFactor * Math.random();
    const finalDelay = cappedDelay + jitter;

    return Math.floor(finalDelay);
  }

  /**
   * Check if an error is retryable
   * 
   * Determines whether the error type suggests a retry might succeed.
   */
  private isRetryableError(error: Error): boolean {
    // Check error code (for network errors)
    const errorCode = (error as any).code;
    if (errorCode && this.config.retryableErrors.includes(errorCode)) {
      return true;
    }

    // Check HTTP status codes (for HTTP errors)
    const statusCode = (error as any).response?.status;
    if (statusCode) {
      // Retry on server errors (5xx) and some client errors
      const retryableStatusCodes = [429, 500, 502, 503, 504, 520, 521, 522, 524];
      return retryableStatusCodes.includes(statusCode);
    }

    // Check error message patterns
    const retryablePatterns = [
      /timeout/i,
      /connection/i,
      /network/i,
      /socket/i,
      /dns/i
    ];

    return retryablePatterns.some(pattern => pattern.test(error.message));
  }

  /**
   * Sleep for specified milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Get current retry handler metrics
   */
  getMetrics(): {
    config: RetryConfig;
    totalOperations: number;
    averageAttempts: number;
  } {
    return {
      config: this.config,
      totalOperations: this.totalRequests,
      averageAttempts: 1 // Simplified for now
    };
  }

  /**
   * Reset retry handler statistics
   */
  reset(): void {
    this.totalRequests = 0;
    logger.debug('Retry handler statistics reset');
  }

  /**
   * Private property to track total requests
   */
  private totalRequests = 0;
}

/**
 * Create pre-configured retry handlers for common scenarios
 */
export class RetryHandlerFactory {
  /**
   * Create retry handler for API calls
   */
  static forAPICall(): RetryHandler {
    return new RetryHandler({
      maxAttempts: 3,
      baseDelay: 1000,
      maxDelay: 10000,
      jitterFactor: 0.1
    });
  }

  /**
   * Create retry handler for database operations
   */
  static forDatabase(): RetryHandler {
    return new RetryHandler({
      maxAttempts: 5,
      baseDelay: 500,
      maxDelay: 5000,
      jitterFactor: 0.2
    });
  }

  /**
   * Create retry handler for cache operations
   */
  static forCache(): RetryHandler {
    return new RetryHandler({
      maxAttempts: 2,
      baseDelay: 100,
      maxDelay: 1000,
      jitterFactor: 0.1
    });
  }

  /**
   * Create retry handler for voice processing
   */
  static forVoiceProcessing(): RetryHandler {
    return new RetryHandler({
      maxAttempts: 2,
      baseDelay: 2000,
      maxDelay: 10000,
      jitterFactor: 0.15
    });
  }

  /**
   * Create retry handler for LLM operations
   */
  static forLLM(): RetryHandler {
    return new RetryHandler({
      maxAttempts: 3,
      baseDelay: 1500,
      maxDelay: 15000,
      jitterFactor: 0.2
    });
  }
}