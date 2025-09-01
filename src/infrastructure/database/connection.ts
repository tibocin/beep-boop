/**
 * src/infrastructure/database/connection.ts - Database Connection Management
 * 
 * Manages connections to PostgreSQL, Neo4j, and Qdrant databases.
 * Provides health checks, connection pooling, and graceful shutdown.
 * 
 * Related Components:
 * - PostgreSQL via Prisma ORM
 * - Neo4j graph database for relationships
 * - Qdrant vector database for embeddings
 * - Connection health monitoring
 * 
 * Tags: #database #connections #postgresql #neo4j #qdrant #health
 */

import { PrismaClient } from '@prisma/client';
import neo4j, { Driver, Session } from 'neo4j-driver';
import { QdrantClient } from '@qdrant/js-client-rest';
import { config } from '@/infrastructure/config';
import { logger } from '@/infrastructure/logging';

/**
 * Database connection manager for all database services
 * 
 * Provides centralized management of database connections with health checks
 * and graceful shutdown capabilities.
 */
export class DatabaseConnection {
  private static prisma: PrismaClient | null = null;
  private static neo4jDriver: Driver | null = null;
  private static qdrantClient: QdrantClient | null = null;
  private static initialized = false;

  /**
   * Initialize all database connections
   * 
   * Sets up connections to PostgreSQL, Neo4j, and Qdrant with proper error handling.
   * Includes retry logic and connection validation.
   */
  static async initialize(): Promise<void> {
    if (this.initialized) {
      logger.warn('Database connections already initialized');
      return;
    }

    logger.info('🗄️ Initializing database connections...');

    try {
      // Initialize PostgreSQL connection
      await this.initializePostgreSQL();
      
      // Initialize Neo4j connection
      await this.initializeNeo4j();
      
      // Initialize Qdrant connection
      await this.initializeQdrant();
      
      this.initialized = true;
      logger.info('✅ All database connections initialized successfully');
      
    } catch (error) {
      logger.error('❌ Database initialization failed:', error);
      throw error;
    }
  }

  /**
   * Initialize PostgreSQL connection via Prisma
   */
  private static async initializePostgreSQL(): Promise<void> {
    logger.info('📊 Connecting to PostgreSQL...');
    
    try {
      this.prisma = new PrismaClient({
        log: config.nodeEnv === 'development' ? ['query', 'info', 'warn', 'error'] : ['error'],
        errorFormat: 'pretty',
      });

      // Test the connection
      await this.prisma.$connect();
      
      // Run a simple query to verify connectivity
      await this.prisma.$queryRaw`SELECT 1 as test`;
      
      logger.info('✅ PostgreSQL connection established');
      
    } catch (error) {
      logger.error('❌ PostgreSQL connection failed:', error);
      throw new Error(`PostgreSQL connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Initialize Neo4j graph database connection
   */
  private static async initializeNeo4j(): Promise<void> {
    logger.info('🕸️ Connecting to Neo4j...');
    
    try {
      const { neo4j: neo4jConfig } = config.database;
      
      this.neo4jDriver = neo4j.driver(
        neo4jConfig.uri,
        neo4j.auth.basic(neo4jConfig.username, neo4jConfig.password),
        {
          maxConnectionPoolSize: 50,
          maxTransactionRetryTime: 30000,
          logging: {
            level: config.nodeEnv === 'development' ? 'info' : 'warn',
            logger: (level, message) => logger.info(`Neo4j ${level}: ${message}`)
          }
        }
      );

      // Verify connectivity
      const session = this.neo4jDriver.session();
      try {
        await session.run('RETURN 1 as test');
        logger.info('✅ Neo4j connection established');
      } finally {
        await session.close();
      }
      
    } catch (error) {
      logger.error('❌ Neo4j connection failed:', error);
      throw new Error(`Neo4j connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Initialize Qdrant vector database connection
   */
  private static async initializeQdrant(): Promise<void> {
    logger.info('🔍 Connecting to Qdrant...');
    
    try {
      const { qdrant: qdrantConfig } = config.database;
      
      this.qdrantClient = new QdrantClient({
        url: qdrantConfig.url,
        apiKey: qdrantConfig.apiKey,
      });

      // Test the connection by getting cluster info
      await this.qdrantClient.getCollections();
      
      logger.info('✅ Qdrant connection established');
      
    } catch (error) {
      logger.error('❌ Qdrant connection failed:', error);
      throw new Error(`Qdrant connection failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Perform health checks on all database connections
   * 
   * Verifies that all database services are responsive and functioning properly.
   */
  static async healthCheck(): Promise<void> {
    if (!this.initialized) {
      throw new Error('Database connections not initialized');
    }

    const healthChecks = [];

    // PostgreSQL health check
    if (this.prisma) {
      healthChecks.push(
        this.prisma.$queryRaw`SELECT 1 as health_check`
          .then(() => logger.debug('PostgreSQL health check passed'))
          .catch(err => {
            logger.error('PostgreSQL health check failed:', err);
            throw new Error('PostgreSQL health check failed');
          })
      );
    }

    // Neo4j health check
    if (this.neo4jDriver) {
      const session = this.neo4jDriver.session();
      healthChecks.push(
        session.run('RETURN 1 as health_check')
          .then(() => {
            logger.debug('Neo4j health check passed');
            return session.close();
          })
          .catch(err => {
            session.close();
            logger.error('Neo4j health check failed:', err);
            throw new Error('Neo4j health check failed');
          })
      );
    }

    // Qdrant health check
    if (this.qdrantClient) {
      healthChecks.push(
        this.qdrantClient.getCollections()
          .then(() => logger.debug('Qdrant health check passed'))
          .catch(err => {
            logger.error('Qdrant health check failed:', err);
            throw new Error('Qdrant health check failed');
          })
      );
    }

    // Wait for all health checks to complete
    await Promise.all(healthChecks);
  }

  /**
   * Get PostgreSQL client instance
   */
  static getPostgreSQL(): PrismaClient {
    if (!this.prisma) {
      throw new Error('PostgreSQL not initialized');
    }
    return this.prisma;
  }

  /**
   * Get Neo4j driver instance
   */
  static getNeo4j(): Driver {
    if (!this.neo4jDriver) {
      throw new Error('Neo4j not initialized');
    }
    return this.neo4jDriver;
  }

  /**
   * Get Qdrant client instance
   */
  static getQdrant(): QdrantClient {
    if (!this.qdrantClient) {
      throw new Error('Qdrant not initialized');
    }
    return this.qdrantClient;
  }

  /**
   * Create a new Neo4j session for graph operations
   * 
   * Returns a new session that should be closed after use.
   */
  static createNeo4jSession(): Session {
    if (!this.neo4jDriver) {
      throw new Error('Neo4j not initialized');
    }
    return this.neo4jDriver.session({ database: config.database.neo4j.database });
  }

  /**
   * Close all database connections gracefully
   * 
   * Should be called during application shutdown to ensure clean closure.
   */
  static async close(): Promise<void> {
    logger.info('🗄️ Closing database connections...');

    const closePromises = [];

    if (this.prisma) {
      closePromises.push(
        this.prisma.$disconnect()
          .then(() => logger.info('✅ PostgreSQL connection closed'))
          .catch(err => logger.error('❌ Error closing PostgreSQL:', err))
      );
    }

    if (this.neo4jDriver) {
      closePromises.push(
        this.neo4jDriver.close()
          .then(() => logger.info('✅ Neo4j connection closed'))
          .catch(err => logger.error('❌ Error closing Neo4j:', err))
      );
    }

    // Qdrant client doesn't need explicit closing
    if (this.qdrantClient) {
      logger.info('✅ Qdrant connection closed');
    }

    await Promise.all(closePromises);
    
    this.prisma = null;
    this.neo4jDriver = null;
    this.qdrantClient = null;
    this.initialized = false;
    
    logger.info('✅ All database connections closed');
  }
}