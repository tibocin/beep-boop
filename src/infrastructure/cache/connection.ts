/**
 * src/infrastructure/cache/connection.ts - Redis Cache Connection Management
 * 
 * Manages Redis connection for caching, sessions, and real-time data.
 * Provides connection pooling, health checks, and operational utilities.
 * 
 * Related Components:
 * - Session management and storage
 * - API response caching
 * - Real-time data synchronization
 * - Rate limiting token storage
 * 
 * Tags: #redis #cache #sessions #realtime #health
 */

import Redis from 'ioredis';
import { config, getRedisConfig } from '@/infrastructure/config';
import { logger } from '@/infrastructure/logging';

/**
 * Cache connection manager for Redis operations
 * 
 * Provides centralized Redis connection management with health monitoring,
 * automatic reconnection, and graceful shutdown capabilities.
 */
export class CacheConnection {
  private static client: Redis | null = null;
  private static subscriber: Redis | null = null;
  private static publisher: Redis | null = null;
  private static initialized = false;

  /**
   * Initialize Redis connections for different use cases
   * 
   * Creates separate connections for general cache operations, pub/sub subscriber,
   * and pub/sub publisher to optimize performance and avoid blocking operations.
   */
  static async initialize(): Promise<void> {
    if (this.initialized) {
      logger.warn('Redis connections already initialized');
      return;
    }

    logger.info('💾 Initializing Redis connections...');

    try {
      const redisConfig = getRedisConfig();

      // Main Redis client for caching and general operations
      this.client = new Redis({
        ...redisConfig,
        enableReadyCheck: true,
        lazyConnect: true,
        maxRetriesPerRequest: 3
      });

      // Subscriber client for pub/sub operations
      this.subscriber = new Redis({
        ...redisConfig,
        lazyConnect: true,
        enableReadyCheck: true
      });

      // Publisher client for pub/sub operations  
      this.publisher = new Redis({
        ...redisConfig,
        lazyConnect: true,
        enableReadyCheck: true
      });

      // Setup event handlers
      this.setupEventHandlers();

      // Connect all clients
      await Promise.all([
        this.client.connect(),
        this.subscriber.connect(),
        this.publisher.connect()
      ]);

      // Test connections
      await this.healthCheck();

      this.initialized = true;
      logger.info('✅ Redis connections initialized successfully');

    } catch (error) {
      logger.error('❌ Redis initialization failed:', error);
      throw error;
    }
  }

  /**
   * Setup event handlers for Redis connections
   * 
   * Handles connection events, errors, and reconnection logic.
   */
  private static setupEventHandlers(): void {
    if (!this.client || !this.subscriber || !this.publisher) return;

    // Main client events
    this.client.on('connect', () => logger.info('Redis client connected'));
    this.client.on('ready', () => logger.info('Redis client ready'));
    this.client.on('error', (err) => logger.error('Redis client error:', err));
    this.client.on('close', () => logger.warn('Redis client connection closed'));
    this.client.on('reconnecting', () => logger.info('Redis client reconnecting...'));

    // Subscriber events
    this.subscriber.on('connect', () => logger.debug('Redis subscriber connected'));
    this.subscriber.on('error', (err) => logger.error('Redis subscriber error:', err));

    // Publisher events
    this.publisher.on('connect', () => logger.debug('Redis publisher connected'));
    this.publisher.on('error', (err) => logger.error('Redis publisher error:', err));
  }

  /**
   * Perform health check on Redis connections
   * 
   * Verifies that Redis is responsive and functioning properly.
   */
  static async healthCheck(): Promise<void> {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }

    try {
      // Test basic connectivity
      const pong = await this.client.ping();
      if (pong !== 'PONG') {
        throw new Error('Redis ping failed');
      }

      // Test read/write operations
      const testKey = `health_check_${Date.now()}`;
      await this.client.set(testKey, 'test', 'EX', 10);
      const result = await this.client.get(testKey);
      if (result !== 'test') {
        throw new Error('Redis read/write test failed');
      }
      await this.client.del(testKey);

      logger.debug('Redis health check passed');

    } catch (error) {
      logger.error('Redis health check failed:', error);
      throw error;
    }
  }

  /**
   * Get the main Redis client for cache operations
   */
  static getClient(): Redis {
    if (!this.client) {
      throw new Error('Redis client not initialized');
    }
    return this.client;
  }

  /**
   * Get Redis subscriber client for pub/sub
   */
  static getSubscriber(): Redis {
    if (!this.subscriber) {
      throw new Error('Redis subscriber not initialized');
    }
    return this.subscriber;
  }

  /**
   * Get Redis publisher client for pub/sub
   */
  static getPublisher(): Redis {
    if (!this.publisher) {
      throw new Error('Redis publisher not initialized');
    }
    return this.publisher;
  }

  /**
   * Cache operations helper methods
   */

  /**
   * Set a value in cache with optional TTL
   */
  static async set(key: string, value: any, ttlSeconds?: number): Promise<void> {
    const client = this.getClient();
    const serializedValue = JSON.stringify(value);
    
    if (ttlSeconds) {
      await client.setex(key, ttlSeconds, serializedValue);
    } else {
      await client.set(key, serializedValue);
    }
  }

  /**
   * Get a value from cache with automatic deserialization
   */
  static async get<T>(key: string): Promise<T | null> {
    const client = this.getClient();
    const value = await client.get(key);
    
    if (value === null) {
      return null;
    }

    try {
      return JSON.parse(value) as T;
    } catch (error) {
      logger.warn('Failed to parse cached value, returning as string:', { key, error });
      return value as unknown as T;
    }
  }

  /**
   * Delete a key from cache
   */
  static async delete(key: string): Promise<void> {
    const client = this.getClient();
    await client.del(key);
  }

  /**
   * Check if a key exists in cache
   */
  static async exists(key: string): Promise<boolean> {
    const client = this.getClient();
    const result = await client.exists(key);
    return result === 1;
  }

  /**
   * Increment a counter in cache (useful for rate limiting)
   */
  static async increment(key: string, ttlSeconds?: number): Promise<number> {
    const client = this.getClient();
    const value = await client.incr(key);
    
    if (ttlSeconds && value === 1) {
      await client.expire(key, ttlSeconds);
    }
    
    return value;
  }

  /**
   * Publish a message to a Redis channel
   */
  static async publish(channel: string, message: any): Promise<void> {
    const publisher = this.getPublisher();
    const serializedMessage = JSON.stringify(message);
    await publisher.publish(channel, serializedMessage);
  }

  /**
   * Subscribe to a Redis channel with message handler
   */
  static async subscribe(channel: string, handler: (message: any) => void): Promise<void> {
    const subscriber = this.getSubscriber();
    
    subscriber.on('message', (receivedChannel, message) => {
      if (receivedChannel === channel) {
        try {
          const parsedMessage = JSON.parse(message);
          handler(parsedMessage);
        } catch (error) {
          logger.error('Failed to parse pub/sub message:', { channel, message, error });
        }
      }
    });

    await subscriber.subscribe(channel);
    logger.info(`Subscribed to Redis channel: ${channel}`);
  }

  /**
   * Close all Redis connections gracefully
   * 
   * Should be called during application shutdown.
   */
  static async close(): Promise<void> {
    logger.info('💾 Closing Redis connections...');

    const closePromises = [];

    if (this.client) {
      closePromises.push(
        this.client.quit()
          .then(() => logger.info('✅ Redis client connection closed'))
          .catch((err: any) => logger.error('❌ Error closing Redis client:', err))
      );
    }

    if (this.subscriber) {
      closePromises.push(
        this.subscriber.quit()
          .then(() => logger.info('✅ Redis subscriber connection closed'))
          .catch((err: any) => logger.error('❌ Error closing Redis subscriber:', err))
      );
    }

    if (this.publisher) {
      closePromises.push(
        this.publisher.quit()
          .then(() => logger.info('✅ Redis publisher connection closed'))
          .catch((err: any) => logger.error('❌ Error closing Redis publisher:', err))
      );
    }

    await Promise.all(closePromises);

    this.client = null;
    this.subscriber = null;
    this.publisher = null;
    this.initialized = false;

    logger.info('✅ All Redis connections closed');
  }
}