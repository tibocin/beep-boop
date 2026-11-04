/**
 * src/adapters/digi-core/digi-core.adapter.ts - Digi-Core Knowledge Butler Integration
 * 
 * Adapter for integrating with Digi-Core knowledge retrieval system.
 * Implements resilient query patterns with circuit breakers, retries, and streaming.
 * 
 * Related Components:
 * - Circuit breaker for service reliability
 * - Retry handler with exponential backoff
 * - Knowledge query processing and streaming
 * - Health monitoring and metrics collection
 * 
 * Tags: #adapter #digi-core #knowledge #resilience #streaming
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { config } from '@/infrastructure/config';
import { logger, createContextualLogger } from '@/infrastructure/logging';
import { CircuitBreaker } from '@/utils/circuit-breaker';
import { RetryHandler } from '@/utils/retry-handler';
import { CacheConnection } from '@/infrastructure/cache/connection';

/**
 * Knowledge query request structure
 */
export interface KnowledgeQuery {
  query: string;
  context?: {
    userId?: string;
    conversationId?: string;
    responseType?: 'brief' | 'detailed' | 'comprehensive';
    maxResults?: number;
    minConfidence?: number;
  };
  streaming?: boolean;
}

/**
 * Knowledge source information
 */
export interface KnowledgeSource {
  id: string;
  source: string;
  content: string;
  relevanceScore: number;
  metadata?: Record<string, any>;
}

/**
 * Knowledge query result
 */
export interface KnowledgeResult {
  results: KnowledgeSource[];
  confidence: number;
  sources: string[];
  queryStrategy: string;
  processingTime: number;
  cached: boolean;
  metadata?: Record<string, any>;
}

/**
 * Streaming knowledge chunk for real-time updates
 */
export interface KnowledgeChunk {
  type: 'progress' | 'source' | 'complete';
  data: any;
  timestamp: string;
}

/**
 * Digi-Core adapter metrics for monitoring
 */
export interface DigiCoreMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  circuitBreakerState: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
  lastError?: string;
  lastSuccessfulRequest?: string;
}

/**
 * Digi-Core knowledge butler adapter
 * 
 * Provides resilient integration with the Digi-Core knowledge retrieval system
 * including circuit breaker pattern, retry logic, caching, and streaming support.
 */
export class DigiCoreAdapter {
  private httpClient!: AxiosInstance;
  private circuitBreaker!: CircuitBreaker;
  private retryHandler!: RetryHandler;
  private metrics!: DigiCoreMetrics;
  private contextLogger = createContextualLogger({ operation: 'digi-core-adapter' });

  constructor() {
    this.initializeHttpClient();
    this.initializeResilience();
    this.initializeMetrics();
  }

  /**
   * Initialize HTTP client with timeout and interceptors
   */
  private initializeHttpClient(): void {
    this.httpClient = axios.create({
      baseURL: config.digiCore.baseUrl,
      timeout: config.digiCore.timeout,
      headers: {
        'Authorization': `Bearer ${config.digiCore.apiKey}`,
        'Content-Type': 'application/json',
        'User-Agent': 'BeepBoop-v2.0/1.0'
      }
    });

    // Request interceptor for logging
    this.httpClient.interceptors.request.use((config) => {
      this.contextLogger.debug('Digi-Core request', {
        method: config.method?.toUpperCase(),
        url: config.url,
        timeout: config.timeout
      });
      return config;
    });

    // Response interceptor for metrics and logging
    this.httpClient.interceptors.response.use(
      (response: AxiosResponse) => {
        this.updateMetrics(true, response.config.url || 'unknown');
        this.contextLogger.debug('Digi-Core response', {
          status: response.status,
          url: response.config.url,
          responseTime: Date.now() - (response.config as any).requestStartTime
        });
        return response;
      },
      (error) => {
        this.updateMetrics(false, error.config?.url || 'unknown', error);
        this.contextLogger.error('Digi-Core request failed', error, {
          url: error.config?.url,
          status: error.response?.status
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Initialize circuit breaker and retry handler
   */
  private initializeResilience(): void {
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: 5,
      resetTimeout: 60000, // 1 minute
      monitoringPeriod: 10000 // 10 seconds
    });

    this.retryHandler = new RetryHandler({
      maxAttempts: config.digiCore.maxRetries,
      baseDelay: 1000,
      maxDelay: 30000,
      jitterFactor: 0.1
    });
  }

  /**
   * Initialize metrics tracking
   */
  private initializeMetrics(): void {
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
      circuitBreakerState: 'CLOSED'
    };
  }

  /**
   * Query knowledge from Digi-Core with resilience patterns
   * 
   * Retrieves relevant knowledge for user queries with automatic retries,
   * circuit breaker protection, and caching for performance.
   */
  async queryKnowledge(query: KnowledgeQuery): Promise<KnowledgeResult> {
    const startTime = Date.now();
    const cacheKey = `digi-core:query:${Buffer.from(JSON.stringify(query)).toString('base64')}`;

    try {
      // Check cache first
      const cachedResult = await CacheConnection.get<KnowledgeResult>(cacheKey);
      if (cachedResult) {
        this.contextLogger.debug('Digi-Core cache hit', { cacheKey });
        return {
          ...cachedResult,
          cached: true,
          processingTime: Date.now() - startTime
        };
      }

      // Execute query with resilience patterns
      const result = await this.circuitBreaker.execute(async () => {
        return this.retryHandler.executeWithRetry(async () => {
          return this.makeKnowledgeRequest(query);
        });
      });

      // Cache successful results
      if (result.confidence > 0.5) {
        await CacheConnection.set(cacheKey, result, 300); // Cache for 5 minutes
      }

      const finalResult: KnowledgeResult = {
        ...result,
        cached: false,
        processingTime: Date.now() - startTime
      };

      this.contextLogger.info('Digi-Core query successful', {
        query: query.query.substring(0, 100),
        confidence: result.confidence,
        sourceCount: result.sources.length,
        processingTime: finalResult.processingTime
      });

      return finalResult;

    } catch (error) {
      this.contextLogger.error('Digi-Core query failed after all retries', error, {
        query: query.query.substring(0, 100),
        processingTime: Date.now() - startTime
      });

      // Return empty result with error context
      return {
        results: [],
        confidence: 0,
        sources: [],
        queryStrategy: 'failed',
        processingTime: Date.now() - startTime,
        cached: false,
        metadata: {
          error: error instanceof Error ? error.message : 'Unknown error',
          fallback: true
        }
      };
    }
  }

  /**
   * Stream knowledge query for real-time updates
   * 
   * Provides streaming knowledge retrieval with progress updates.
   */
  async* streamKnowledgeQuery(query: KnowledgeQuery): AsyncGenerator<KnowledgeChunk> {
    const startTime = Date.now();

    try {
      // Emit progress start
      yield {
        type: 'progress',
        data: { step: 'started', message: 'Initiating knowledge query' },
        timestamp: new Date().toISOString()
      };

      // Execute query (this could be enhanced with actual streaming from Digi-Core)
      const result = await this.queryKnowledge(query);

      // Emit sources as they're processed
      for (const source of result.results) {
        yield {
          type: 'source',
          data: source,
          timestamp: new Date().toISOString()
        };
        
        // Small delay to simulate streaming
        await new Promise(resolve => setTimeout(resolve, 100));
      }

      // Emit completion
      yield {
        type: 'complete',
        data: {
          confidence: result.confidence,
          totalSources: result.results.length,
          processingTime: Date.now() - startTime
        },
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      this.contextLogger.error('Streaming knowledge query failed', error);
      
      yield {
        type: 'complete',
        data: {
          error: error instanceof Error ? error.message : 'Streaming failed',
          processingTime: Date.now() - startTime
        },
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Make actual HTTP request to Digi-Core API
   */
  private async makeKnowledgeRequest(query: KnowledgeQuery): Promise<KnowledgeResult> {
    const requestStartTime = Date.now();

    const response = await this.httpClient.post('/query/', {
      query: query.query,
      response_type: query.context?.responseType || 'detailed',
      context: {
        user_context: query.context || {},
        conversation_type: 'personal_assistant',
        response_format: 'structured',
        max_results: query.context?.maxResults || 5,
        min_confidence: query.context?.minConfidence || 0.3
      }
    });

    const processingTime = Date.now() - requestStartTime;

    // Transform Digi-Core response to our format
    return {
      results: this.transformKnowledgeSources(response.data.results || []),
      confidence: response.data.confidence || 0,
      sources: response.data.sources || [],
      queryStrategy: response.data.strategy_used || 'default',
      processingTime,
      cached: false,
      metadata: {
        digiCoreVersion: response.data.version,
        queryId: response.data.query_id
      }
    };
  }

  /**
   * Transform Digi-Core knowledge sources to our format
   */
  private transformKnowledgeSources(sources: any[]): KnowledgeSource[] {
    return sources.map((source, index) => ({
      id: source.id || `source_${index}`,
      source: source.source || 'unknown',
      content: source.content || '',
      relevanceScore: source.relevance_score || source.score || 0,
      metadata: {
        originalData: source,
        reasoning: source.relevance_reasoning
      }
    }));
  }

  /**
   * Store new knowledge or learning in Digi-Core
   * 
   * Allows Beep-Boop to contribute knowledge back to the system.
   */
  async storeKnowledge(knowledge: {
    content: string;
    source: string;
    context?: Record<string, any>;
  }): Promise<boolean> {
    try {
      await this.circuitBreaker.execute(async () => {
        return this.retryHandler.executeWithRetry(async () => {
          return this.httpClient.post('/learning/', {
            content: knowledge.content,
            source: knowledge.source,
            context: knowledge.context || {},
            timestamp: new Date().toISOString()
          });
        });
      });

      this.contextLogger.info('Knowledge stored in Digi-Core', {
        contentLength: knowledge.content.length,
        source: knowledge.source
      });

      return true;

    } catch (error) {
      this.contextLogger.error('Failed to store knowledge in Digi-Core', error);
      return false;
    }
  }

  /**
   * Perform health check on Digi-Core service
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.httpClient.get('/health', { timeout: 5000 });
      const isHealthy = response.status === 200;
      
      this.metrics.circuitBreakerState = this.circuitBreaker.getState();
      
      if (isHealthy) {
        this.contextLogger.debug('Digi-Core health check passed');
      } else {
        this.contextLogger.warn('Digi-Core health check failed', { status: response.status });
      }
      
      return isHealthy;
      
    } catch (error) {
      this.contextLogger.error('Digi-Core health check error', error);
      return false;
    }
  }

  /**
   * Get adapter metrics for monitoring
   */
  getMetrics(): DigiCoreMetrics {
    return {
      ...this.metrics,
      circuitBreakerState: this.circuitBreaker.getState()
    };
  }

  /**
   * Update internal metrics tracking
   */
  private updateMetrics(success: boolean, endpoint: string, error?: any): void {
    this.metrics.totalRequests++;
    
    if (success) {
      this.metrics.successfulRequests++;
      this.metrics.lastSuccessfulRequest = new Date().toISOString();
    } else {
      this.metrics.failedRequests++;
      this.metrics.lastError = error instanceof Error ? error.message : 'Unknown error';
    }

    // Update success rate and average response time
    const successRate = this.metrics.successfulRequests / this.metrics.totalRequests;
    this.contextLogger.debug('Digi-Core metrics updated', {
      totalRequests: this.metrics.totalRequests,
      successRate,
      endpoint
    });
  }

  /**
   * Clear cache for knowledge queries
   * 
   * Useful when knowledge base is updated and cache should be invalidated.
   */
  async clearKnowledgeCache(): Promise<void> {
    try {
      // Get all cache keys that match our pattern
      const redis = CacheConnection.getClient();
      const keys = await redis.keys('digi-core:query:*');
      
      if (keys.length > 0) {
        await redis.del(...keys);
        this.contextLogger.info('Digi-Core cache cleared', { 
          clearedKeys: keys.length 
        });
      }
      
    } catch (error) {
      this.contextLogger.error('Failed to clear Digi-Core cache', error);
    }
  }

  /**
   * Get query suggestions based on user context
   * 
   * Provides intelligent query suggestions for improved user experience.
   */
  async getQuerySuggestions(context: {
    userId?: string;
    conversationHistory?: string[];
    currentTopic?: string;
  }): Promise<string[]> {
    try {
      const response = await this.circuitBreaker.execute(async () => {
        return this.httpClient.post('/suggestions/', {
          context,
          max_suggestions: 5
        });
      });

      const suggestions = response.data.suggestions || [];
      
      this.contextLogger.info('Query suggestions retrieved', {
        suggestionCount: suggestions.length,
        userId: context.userId
      });

      return suggestions;

    } catch (error) {
      this.contextLogger.error('Failed to get query suggestions', error);
      return [];
    }
  }

  /**
   * Analyze query for learning opportunities
   * 
   * Identifies gaps in knowledge base and opportunities for improvement.
   */
  async analyzeQuery(query: string, result: KnowledgeResult): Promise<{
    knowledgeGaps: string[];
    improvementSuggestions: string[];
    confidence: number;
  }> {
    try {
      const response = await this.httpClient.post('/analysis/', {
        query,
        result,
        timestamp: new Date().toISOString()
      });

      return {
        knowledgeGaps: response.data.knowledge_gaps || [],
        improvementSuggestions: response.data.improvement_suggestions || [],
        confidence: response.data.confidence || 0
      };

    } catch (error) {
      this.contextLogger.error('Query analysis failed', error);
      return {
        knowledgeGaps: [],
        improvementSuggestions: [],
        confidence: 0
      };
    }
  }

  /**
   * Get knowledge base statistics
   * 
   * Provides information about the current state of the knowledge base.
   */
  async getKnowledgeBaseStats(): Promise<{
    totalDocuments: number;
    totalEmbeddings: number;
    lastUpdated: string;
    categories: Record<string, number>;
  }> {
    try {
      const response = await this.httpClient.get('/stats/');
      
      return {
        totalDocuments: response.data.total_documents || 0,
        totalEmbeddings: response.data.total_embeddings || 0,
        lastUpdated: response.data.last_updated || new Date().toISOString(),
        categories: response.data.categories || {}
      };

    } catch (error) {
      this.contextLogger.error('Failed to get knowledge base stats', error);
      return {
        totalDocuments: 0,
        totalEmbeddings: 0,
        lastUpdated: new Date().toISOString(),
        categories: {}
      };
    }
  }

  /**
   * Process incremental data update
   * 
   * Triggers processing of new data in the knowledge base.
   */
  async processDataUpdate(incremental: boolean = true): Promise<boolean> {
    try {
      const response = await this.httpClient.post('/apps/process-data', {
        incremental,
        timestamp: new Date().toISOString()
      });

      const success = response.status === 200;
      
      this.contextLogger.info('Data processing triggered', {
        incremental,
        success,
        processingId: response.data.processing_id
      });

      return success;

    } catch (error) {
      this.contextLogger.error('Data processing trigger failed', error);
      return false;
    }
  }
}

/**
 * Singleton instance for application-wide use
 */
export const digiCoreAdapter = new DigiCoreAdapter();