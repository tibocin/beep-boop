/**
 * src/utils/circuit-breaker.ts - Circuit Breaker Pattern Implementation
 * 
 * Implements circuit breaker pattern for external service resilience.
 * Prevents cascading failures by temporarily failing fast when services are down.
 * 
 * Related Components:
 * - Service adapters for external APIs
 * - Retry mechanisms and error handling
 * - Health monitoring and recovery
 * - Metrics collection and alerting
 * 
 * Tags: #resilience #circuit-breaker #fault-tolerance #monitoring
 */

import { logger } from '@/infrastructure/logging';

/**
 * Circuit breaker states
 */
export enum CircuitBreakerState {
  CLOSED = 'CLOSED',       // Normal operation
  OPEN = 'OPEN',           // Failing fast, not attempting requests
  HALF_OPEN = 'HALF_OPEN'  // Testing if service has recovered
}

/**
 * Circuit breaker configuration
 */
export interface CircuitBreakerConfig {
  failureThreshold: number;    // Number of failures before opening
  resetTimeout: number;        // Time to wait before trying half-open
  monitoringPeriod: number;    // Time window for failure counting
  halfOpenMaxAttempts?: number; // Max attempts in half-open state
}

/**
 * Circuit breaker metrics for monitoring
 */
export interface CircuitBreakerMetrics {
  state: CircuitBreakerState;
  failureCount: number;
  successCount: number;
  totalRequests: number;
  lastFailureTime?: Date;
  lastSuccessTime?: Date;
  openedAt?: Date;
  halfOpenAttempts: number;
}

/**
 * Circuit breaker implementation for service reliability
 * 
 * Provides automatic fault tolerance by failing fast when external services
 * are experiencing issues, preventing cascading failures.
 */
export class CircuitBreaker {
  private state: CircuitBreakerState = CircuitBreakerState.CLOSED;
  private failureCount = 0;
  private successCount = 0;
  private totalRequests = 0;
  private lastFailureTime?: Date;
  private lastSuccessTime?: Date;
  private openedAt?: Date;
  private halfOpenAttempts = 0;
  private readonly config: Required<CircuitBreakerConfig>;

  constructor(config: CircuitBreakerConfig) {
    this.config = {
      halfOpenMaxAttempts: 3,
      ...config
    };

    logger.debug('Circuit breaker initialized', {
      failureThreshold: this.config.failureThreshold,
      resetTimeout: this.config.resetTimeout,
      monitoringPeriod: this.config.monitoringPeriod
    });
  }

  /**
   * Execute operation with circuit breaker protection
   * 
   * Wraps operations to provide automatic failure detection and recovery.
   */
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    this.totalRequests++;

    // Check if circuit should transition to half-open
    this.checkForStateTransition();

    // Handle different circuit states
    switch (this.state) {
      case CircuitBreakerState.OPEN:
        throw new Error('Circuit breaker is OPEN - service unavailable');

      case CircuitBreakerState.HALF_OPEN:
        if (this.halfOpenAttempts >= this.config.halfOpenMaxAttempts) {
          throw new Error('Circuit breaker HALF_OPEN attempt limit exceeded');
        }
        this.halfOpenAttempts++;
        break;

      case CircuitBreakerState.CLOSED:
        // Normal operation
        break;
    }

    try {
      // Execute the operation
      const result = await operation();
      
      // Record success
      this.onSuccess();
      
      return result;

    } catch (error) {
      // Record failure
      this.onFailure(error);
      throw error;
    }
  }

  /**
   * Handle successful operation
   */
  private onSuccess(): void {
    this.successCount++;
    this.lastSuccessTime = new Date();

    // Reset failure count in closed state
    if (this.state === CircuitBreakerState.CLOSED) {
      this.failureCount = 0;
    }

    // Transition from half-open to closed after successful attempts
    if (this.state === CircuitBreakerState.HALF_OPEN) {
      this.transitionToClosed();
    }

    logger.debug('Circuit breaker success recorded', {
      state: this.state,
      successCount: this.successCount,
      failureCount: this.failureCount
    });
  }

  /**
   * Handle failed operation
   */
  private onFailure(error: any): void {
    this.failureCount++;
    this.lastFailureTime = new Date();

    logger.warn('Circuit breaker failure recorded', {
      state: this.state,
      failureCount: this.failureCount,
      error: error instanceof Error ? error.message : 'Unknown error'
    });

    // Check if we should open the circuit
    if (this.state === CircuitBreakerState.CLOSED && 
        this.failureCount >= this.config.failureThreshold) {
      this.transitionToOpen();
    }

    // Transition back to open from half-open on failure
    if (this.state === CircuitBreakerState.HALF_OPEN) {
      this.transitionToOpen();
    }
  }

  /**
   * Check if circuit breaker should transition states
   */
  private checkForStateTransition(): void {
    if (this.state === CircuitBreakerState.OPEN && this.shouldAttemptReset()) {
      this.transitionToHalfOpen();
    }
  }

  /**
   * Check if enough time has passed to attempt reset
   */
  private shouldAttemptReset(): boolean {
    if (!this.openedAt) {
      return false;
    }

    const timeSinceOpened = Date.now() - this.openedAt.getTime();
    return timeSinceOpened >= this.config.resetTimeout;
  }

  /**
   * Transition circuit breaker to OPEN state
   */
  private transitionToOpen(): void {
    this.state = CircuitBreakerState.OPEN;
    this.openedAt = new Date();
    this.halfOpenAttempts = 0;

    logger.warn('Circuit breaker opened', {
      failureCount: this.failureCount,
      threshold: this.config.failureThreshold,
      resetTimeout: this.config.resetTimeout
    });
  }

  /**
   * Transition circuit breaker to HALF_OPEN state
   */
  private transitionToHalfOpen(): void {
    this.state = CircuitBreakerState.HALF_OPEN;
    this.halfOpenAttempts = 0;

    logger.info('Circuit breaker transitioned to HALF_OPEN', {
      timeSinceOpened: this.openedAt ? Date.now() - this.openedAt.getTime() : 0
    });
  }

  /**
   * Transition circuit breaker to CLOSED state
   */
  private transitionToClosed(): void {
    this.state = CircuitBreakerState.CLOSED;
    this.failureCount = 0;
    this.openedAt = undefined;
    this.halfOpenAttempts = 0;

    logger.info('Circuit breaker closed - service recovered', {
      successCount: this.successCount
    });
  }

  /**
   * Get current circuit breaker state
   */
  getState(): CircuitBreakerState {
    return this.state;
  }

  /**
   * Get circuit breaker metrics for monitoring
   */
  getMetrics(): CircuitBreakerMetrics {
    return {
      state: this.state,
      failureCount: this.failureCount,
      successCount: this.successCount,
      totalRequests: this.totalRequests,
      lastFailureTime: this.lastFailureTime,
      lastSuccessTime: this.lastSuccessTime,
      openedAt: this.openedAt,
      halfOpenAttempts: this.halfOpenAttempts
    };
  }

  /**
   * Manually open the circuit breaker
   * 
   * For testing or emergency situations where the circuit needs to be opened manually.
   */
  forceOpen(): void {
    this.transitionToOpen();
    logger.warn('Circuit breaker manually opened');
  }

  /**
   * Manually close the circuit breaker
   * 
   * For testing or recovery situations where the circuit needs to be closed manually.
   */
  forceClose(): void {
    this.transitionToClosed();
    logger.info('Circuit breaker manually closed');
  }

  /**
   * Reset circuit breaker statistics
   * 
   * Clears all metrics and resets to initial state.
   */
  reset(): void {
    this.state = CircuitBreakerState.CLOSED;
    this.failureCount = 0;
    this.successCount = 0;
    this.totalRequests = 0;
    this.lastFailureTime = undefined;
    this.lastSuccessTime = undefined;
    this.openedAt = undefined;
    this.halfOpenAttempts = 0;

    logger.info('Circuit breaker reset to initial state');
  }
}