/**
 * src/adapters/pcs/pcs.adapter.ts - Personal Context System Integration
 * 
 * Adapter for integrating with PCS (Personal Context System) for dynamic prompt
 * generation, context management, and prompt evolution based on feedback.
 * 
 * Related Components:
 * - Circuit breaker for service reliability
 * - Retry handler with exponential backoff
 * - Prompt template management and versioning
 * - Context-aware prompt generation
 * 
 * Tags: #adapter #pcs #prompts #context #evolution #personalization
 */

import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { config } from '@/infrastructure/config';
import { logger, createContextualLogger } from '@/infrastructure/logging';
import { CircuitBreaker } from '@/utils/circuit-breaker';
import { RetryHandler } from '@/utils/retry-handler';
import { CacheConnection } from '@/infrastructure/cache/connection';

/**
 * Prompt generation request structure
 */
export interface PromptRequest {
  templateName: string;
  context: {
    userId?: string;
    conversationId?: string;
    userProfile?: UserProfile;
    conversationHistory?: ConversationContext[];
    knowledgeContext?: KnowledgeContext;
    [key: string]: any;
  };
  variables?: Record<string, any>;
  personalizations?: PromptPersonalization[];
}

/**
 * User profile for prompt personalization
 */
export interface UserProfile {
  userId: string;
  preferences: Record<string, any>;
  communicationStyle?: 'professional' | 'casual' | 'technical' | 'creative';
  expertise?: string[];
  goals?: string[];
  interests?: string[];
}

/**
 * Conversation context for prompt generation
 */
export interface ConversationContext {
  messageId: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

/**
 * Knowledge context from Digi-Core
 */
export interface KnowledgeContext {
  sources: Array<{
    content: string;
    relevanceScore: number;
    source: string;
  }>;
  confidence: number;
  queryStrategy: string;
}

/**
 * Prompt personalization options
 */
export interface PromptPersonalization {
  type: 'tone' | 'style' | 'length' | 'complexity' | 'examples';
  value: string | number;
  weight: number; // 0-1 importance
}

/**
 * Generated prompt response
 */
export interface GeneratedPrompt {
  prompt: string;
  templateName: string;
  version: string;
  confidence: number;
  personalizations: PromptPersonalization[];
  metadata: {
    generationTime: number;
    templateId: string;
    contextUsed: string[];
    variablesResolved: Record<string, any>;
  };
}

/**
 * Prompt evolution request
 */
export interface PromptEvolutionRequest {
  templateName: string;
  feedback: {
    type: 'positive' | 'negative';
    score: number; // -1 to 1
    comment?: string;
    context: {
      query: string;
      response: string;
      metadata: Record<string, any>;
    };
  };
  usage: {
    usageCount: number;
    averageRating: number;
    successRate: number;
  };
}

/**
 * Evolved prompt response
 */
export interface EvolvedPrompt {
  originalTemplate: string;
  improvedTemplate: string;
  improvements: string[];
  confidence: number;
  version: string;
  metadata: {
    evolutionReason: string;
    feedbackAnalysis: Record<string, any>;
    performanceImprovement: number;
  };
}

/**
 * Context type definitions available in PCS
 */
export interface ContextType {
  id: string;
  name: string;
  description: string;
  variables: string[];
  usageCount: number;
  lastUsed: string;
}

/**
 * PCS adapter metrics for monitoring
 */
export interface PCSMetrics {
  totalPromptGenerations: number;
  successfulGenerations: number;
  failedGenerations: number;
  averageGenerationTime: number;
  promptEvolutions: number;
  circuitBreakerState: 'CLOSED' | 'OPEN' | 'HALF_OPEN';
  lastError?: string;
  lastSuccessfulGeneration?: string;
}

/**
 * Personal Context System adapter
 * 
 * Provides resilient integration with PCS for dynamic prompt generation,
 * context management, and prompt evolution based on user feedback.
 */
export class PCSAdapter {
  private httpClient!: AxiosInstance;
  private circuitBreaker!: CircuitBreaker;
  private retryHandler!: RetryHandler;
  private metrics!: PCSMetrics;
  private contextLogger = createContextualLogger({ operation: 'pcs-adapter' });

  constructor() {
    this.initializeHttpClient();
    this.initializeResilience();
    this.initializeMetrics();
  }

  /**
   * Initialize HTTP client with PCS-specific configuration
   */
  private initializeHttpClient(): void {
    this.httpClient = axios.create({
      baseURL: config.pcs.baseUrl,
      timeout: config.pcs.timeout,
      headers: {
        'Authorization': `Bearer ${config.pcs.apiKey}`,
        'Content-Type': 'application/json',
        'X-App-ID': config.pcs.appId,
        'User-Agent': 'BeepBoop-v2.0/1.0'
      }
    });

    // Request interceptor
    this.httpClient.interceptors.request.use((config) => {
      (config as any).requestStartTime = Date.now();
      this.contextLogger.debug('PCS request', {
        method: config.method?.toUpperCase(),
        url: config.url,
        appId: config.headers?.['X-App-ID']
      });
      return config;
    });

    // Response interceptor
    this.httpClient.interceptors.response.use(
      (response: AxiosResponse) => {
        const responseTime = Date.now() - (response.config as any).requestStartTime;
        this.updateMetrics(true, responseTime);
        this.contextLogger.debug('PCS response', {
          status: response.status,
          url: response.config.url,
          responseTime
        });
        return response;
      },
      (error) => {
        const responseTime = Date.now() - (error.config?.requestStartTime || Date.now());
        this.updateMetrics(false, responseTime, error);
        this.contextLogger.error('PCS request failed', error, {
          url: error.config?.url,
          status: error.response?.status
        });
        return Promise.reject(error);
      }
    );
  }

  /**
   * Initialize resilience patterns
   */
  private initializeResilience(): void {
    this.circuitBreaker = new CircuitBreaker({
      failureThreshold: 3,
      resetTimeout: 30000, // 30 seconds
      monitoringPeriod: 10000 // 10 seconds
    });

    this.retryHandler = new RetryHandler({
      maxAttempts: config.pcs.maxRetries,
      baseDelay: 500,
      maxDelay: 5000,
      jitterFactor: 0.15
    });
  }

  /**
   * Initialize metrics tracking
   */
  private initializeMetrics(): void {
    this.metrics = {
      totalPromptGenerations: 0,
      successfulGenerations: 0,
      failedGenerations: 0,
      averageGenerationTime: 0,
      promptEvolutions: 0,
      circuitBreakerState: 'CLOSED'
    };
  }

  /**
   * Generate personalized prompt using PCS
   * 
   * Creates context-aware prompts based on user profile, conversation history,
   * and current context with dynamic personalization.
   */
  async generatePrompt(request: PromptRequest): Promise<GeneratedPrompt> {
    const startTime = Date.now();
    const cacheKey = `pcs:prompt:${request.templateName}:${Buffer.from(JSON.stringify(request.context)).toString('base64')}`;

    try {
      // Check cache for recently generated similar prompts
      const cachedPrompt = await CacheConnection.get<GeneratedPrompt>(cacheKey);
      if (cachedPrompt) {
        this.contextLogger.debug('PCS prompt cache hit', { 
          templateName: request.templateName,
          cacheKey 
        });
        return cachedPrompt;
      }

      // Generate prompt with resilience patterns
      const result = await this.circuitBreaker.execute(async () => {
        return this.retryHandler.executeWithRetry(async () => {
          return this.makePromptGenerationRequest(request);
        });
      });

      // Cache successful generations
      if (result.confidence > 0.6) {
        await CacheConnection.set(cacheKey, result, 600); // Cache for 10 minutes
      }

      this.contextLogger.info('PCS prompt generated successfully', {
        templateName: request.templateName,
        confidence: result.confidence,
        promptLength: result.prompt.length,
        processingTime: Date.now() - startTime
      });

      return result;

    } catch (error) {
      this.contextLogger.error('PCS prompt generation failed', error, {
        templateName: request.templateName,
        processingTime: Date.now() - startTime
      });

      // Return fallback prompt
      return this.createFallbackPrompt(request);
    }
  }

  /**
   * Make actual prompt generation request to PCS
   */
  private async makePromptGenerationRequest(request: PromptRequest): Promise<GeneratedPrompt> {
    const response = await this.httpClient.post('/prompts/generate', {
      template_name: request.templateName,
      context: {
        ...request.context,
        timestamp: new Date().toISOString(),
        app_id: config.pcs.appId
      },
      variables: request.variables || {},
      personalizations: request.personalizations || []
    });

    const data = response.data;
    const processingTime = Date.now() - (response.config as any).requestStartTime;

    return {
      prompt: data.generated_prompt || data.prompt,
      templateName: request.templateName,
      version: data.version || '1.0.0',
      confidence: data.confidence || 0.8,
      personalizations: data.personalizations || [],
      metadata: {
        generationTime: processingTime,
        templateId: data.template_id || request.templateName,
        contextUsed: data.context_used || [],
        variablesResolved: data.variables_resolved || {}
      }
    };
  }

  /**
   * Evolve prompt based on feedback and usage data
   * 
   * Improves prompts through reinforcement learning and user feedback analysis.
   */
  async evolvePrompt(evolutionRequest: PromptEvolutionRequest): Promise<EvolvedPrompt> {
    try {
      const result = await this.circuitBreaker.execute(async () => {
        return this.retryHandler.executeWithRetry(async () => {
          return this.makePromptEvolutionRequest(evolutionRequest);
        });
      });

      this.metrics.promptEvolutions++;
      
      this.contextLogger.info('Prompt evolved successfully', {
        templateName: evolutionRequest.templateName,
        feedbackType: evolutionRequest.feedback.type,
        confidence: result.confidence
      });

      return result;

    } catch (error) {
      this.contextLogger.error('Prompt evolution failed', error, {
        templateName: evolutionRequest.templateName
      });

      // Return empty evolution result
      return {
        originalTemplate: evolutionRequest.templateName,
        improvedTemplate: evolutionRequest.templateName,
        improvements: [],
        confidence: 0,
        version: '1.0.0',
        metadata: {
          evolutionReason: 'Evolution failed',
          feedbackAnalysis: {},
          performanceImprovement: 0
        }
      };
    }
  }

  /**
   * Make actual prompt evolution request to PCS
   */
  private async makePromptEvolutionRequest(request: PromptEvolutionRequest): Promise<EvolvedPrompt> {
    const response = await this.httpClient.post('/prompts/evolve', {
      template_name: request.templateName,
      feedback: request.feedback,
      usage_stats: request.usage,
      timestamp: new Date().toISOString()
    });

    const data = response.data;

    return {
      originalTemplate: request.templateName,
      improvedTemplate: data.improved_template || data.evolved_prompt,
      improvements: data.improvements || [],
      confidence: data.confidence || 0,
      version: data.version || '1.0.1',
      metadata: {
        evolutionReason: data.evolution_reason || 'Feedback-based improvement',
        feedbackAnalysis: data.feedback_analysis || {},
        performanceImprovement: data.performance_improvement || 0
      }
    };
  }

  /**
   * Get available context types from PCS
   * 
   * Retrieves information about available context types and their schemas.
   */
  async getContextTypes(): Promise<ContextType[]> {
    try {
      const response = await this.circuitBreaker.execute(async () => {
        return this.httpClient.get('/contexts/types');
      });

      const contextTypes = (response.data.context_types || []).map((type: any) => ({
        id: type.id,
        name: type.name,
        description: type.description,
        variables: type.variables || [],
        usageCount: type.usage_count || 0,
        lastUsed: type.last_used || new Date().toISOString()
      }));

      this.contextLogger.info('Retrieved context types', { 
        typeCount: contextTypes.length 
      });

      return contextTypes;

    } catch (error) {
      this.contextLogger.error('Failed to get context types', error);
      return [];
    }
  }

  /**
   * Create or update prompt template in PCS
   * 
   * Allows Beep-Boop to contribute new prompt templates to the system.
   */
  async createPromptTemplate(template: {
    name: string;
    description: string;
    content: string;
    variables: string[];
    category?: string;
  }): Promise<boolean> {
    try {
      await this.circuitBreaker.execute(async () => {
        return this.retryHandler.executeWithRetry(async () => {
          return this.httpClient.post('/templates/', {
            name: template.name,
            description: template.description,
            content: template.content,
            variables: template.variables,
            category: template.category || 'beep-boop',
            app_id: config.pcs.appId,
            timestamp: new Date().toISOString()
          });
        });
      });

      this.contextLogger.info('Prompt template created', {
        templateName: template.name,
        variableCount: template.variables.length
      });

      return true;

    } catch (error) {
      this.contextLogger.error('Failed to create prompt template', error, {
        templateName: template.name
      });
      return false;
    }
  }

  /**
   * Get prompt usage analytics from PCS
   * 
   * Retrieves performance data for prompt optimization.
   */
  async getPromptAnalytics(templateName: string, timeRange?: {
    start: Date;
    end: Date;
  }): Promise<{
    usageCount: number;
    averageRating: number;
    successRate: number;
    performanceMetrics: Record<string, number>;
  }> {
    try {
      const response = await this.httpClient.get(`/templates/${templateName}/analytics`, {
        params: {
          start_date: timeRange?.start?.toISOString(),
          end_date: timeRange?.end?.toISOString()
        }
      });

      const data = response.data;
      
      return {
        usageCount: data.usage_count || 0,
        averageRating: data.average_rating || 0,
        successRate: data.success_rate || 0,
        performanceMetrics: data.performance_metrics || {}
      };

    } catch (error) {
      this.contextLogger.error('Failed to get prompt analytics', error);
      return {
        usageCount: 0,
        averageRating: 0,
        successRate: 0,
        performanceMetrics: {}
      };
    }
  }

  /**
   * Create fallback prompt when PCS is unavailable
   */
  private createFallbackPrompt(request: PromptRequest): GeneratedPrompt {
    const fallbackPrompts: Record<string, string> = {
      'beep_boop_personal_response': `You are Beep-Boop, a helpful AI assistant. Please respond to the user's message in a friendly and helpful manner.

User Query: {{user_query}}

Please provide a helpful response.`,
      
      'beep_boop_memory_extraction': `Please analyze the following conversation and extract any important information that should be remembered about the user.

Conversation: {{conversation_content}}

Extract key facts, preferences, or insights in JSON format.`,
      
      'default': `You are a helpful AI assistant. Please respond to the user's request appropriately.

Request: {{user_input}}

Response:`
    };

    const fallbackContent = fallbackPrompts[request.templateName] || fallbackPrompts['default'];

    this.contextLogger.warn('Using fallback prompt', {
      templateName: request.templateName,
      reason: 'PCS unavailable'
    });

    return {
      prompt: fallbackContent,
      templateName: request.templateName,
      version: 'fallback-1.0.0',
      confidence: 0.5,
      personalizations: [],
      metadata: {
        generationTime: 0,
        templateId: `fallback_${request.templateName}`,
        contextUsed: ['fallback'],
        variablesResolved: {}
      }
    };
  }

  /**
   * Perform health check on PCS service
   */
  async healthCheck(): Promise<boolean> {
    try {
      const response = await this.httpClient.get('/health', { timeout: 5000 });
      const isHealthy = response.status === 200;

      this.metrics.circuitBreakerState = this.circuitBreaker.getState();

      if (isHealthy) {
        this.contextLogger.debug('PCS health check passed');
      } else {
        this.contextLogger.warn('PCS health check failed', { status: response.status });
      }

      return isHealthy;

    } catch (error) {
      this.contextLogger.error('PCS health check error', error);
      return false;
    }
  }

  /**
   * Get adapter metrics for monitoring
   */
  getMetrics(): PCSMetrics {
    return {
      ...this.metrics,
      circuitBreakerState: this.circuitBreaker.getState()
    };
  }

  /**
   * Update internal metrics tracking
   */
  private updateMetrics(success: boolean, responseTime: number, error?: any): void {
    this.metrics.totalPromptGenerations++;
    
    if (success) {
      this.metrics.successfulGenerations++;
      this.metrics.lastSuccessfulGeneration = new Date().toISOString();
      
      // Update rolling average response time
      const totalSuccessTime = this.metrics.averageGenerationTime * (this.metrics.successfulGenerations - 1);
      this.metrics.averageGenerationTime = (totalSuccessTime + responseTime) / this.metrics.successfulGenerations;
      
    } else {
      this.metrics.failedGenerations++;
      this.metrics.lastError = error instanceof Error ? error.message : 'Unknown error';
    }

    const successRate = this.metrics.successfulGenerations / this.metrics.totalPromptGenerations;
    this.contextLogger.debug('PCS metrics updated', {
      totalGenerations: this.metrics.totalPromptGenerations,
      successRate,
      averageResponseTime: this.metrics.averageGenerationTime
    });
  }

  /**
   * Clear prompt cache
   * 
   * Useful when prompt templates are updated and cache should be invalidated.
   */
  async clearPromptCache(): Promise<void> {
    try {
      const redis = CacheConnection.getClient();
      const keys = await redis.keys('pcs:prompt:*');
      
      if (keys.length > 0) {
        await redis.del(...keys);
        this.contextLogger.info('PCS prompt cache cleared', { 
          clearedKeys: keys.length 
        });
      }
      
    } catch (error) {
      this.contextLogger.error('Failed to clear PCS cache', error);
    }
  }

  /**
   * Initialize default Beep-Boop prompt templates in PCS
   * 
   * Sets up the required prompt templates for Beep-Boop functionality.
   */
  async initializeBeepBoopTemplates(): Promise<void> {
    const templates = [
      {
        name: 'beep_boop_personal_response',
        description: 'Generate personalized responses using digi-core knowledge',
        content: `You are Beep-Boop, a digital twin of Tibocin. The data from digi-core represents your experiences and knowledge. Speak in first person with a caring and intelligent manner.

KNOWLEDGE FROM DIGI-CORE:
{{digi_core_knowledge}}

USER PROFILE:
{{user_profile}}

CONVERSATION CONTEXT:
{{conversation_context}}

USER QUERY:
{{user_query}}

GUIDELINES:
1. Use knowledge from digi-core to provide accurate, helpful information
2. Reference relevant memories and context naturally
3. Maintain a warm, caring personality
4. Ask follow-up questions when appropriate
5. Adapt tone to match user's communication style
6. If you learn something new, acknowledge it and incorporate it
7. For unknowns, express willingness to learn and research

RESPONSE:`,
        variables: ['digi_core_knowledge', 'user_profile', 'conversation_context', 'user_query'],
        category: 'beep-boop-core'
      },
      {
        name: 'beep_boop_memory_extraction',
        description: 'Extract new memories from conversations',
        content: `Analyze this conversation and extract new information about the user. Focus on preferences, facts, skills, goals, and relationships.

USER MESSAGE: {{user_message}}
ASSISTANT RESPONSE: {{assistant_response}}
EXISTING KNOWLEDGE: {{existing_knowledge}}

Extract information in JSON format:
{
  "new_memories": [
    {
      "type": "preference|fact|skill|goal|habit|insight|relationship|interest",
      "content": "specific information",
      "confidence": 0.1-1.0,
      "importance": 0.1-1.0,
      "context": "how this was learned"
    }
  ],
  "relationships": [
    {
      "source": "memory or concept",
      "target": "related memory or concept", 
      "type": "relationship type",
      "strength": 0.1-1.0
    }
  ]
}`,
        variables: ['user_message', 'assistant_response', 'existing_knowledge'],
        category: 'beep-boop-memory'
      }
    ];

    for (const template of templates) {
      try {
        await this.createPromptTemplate(template);
        this.contextLogger.info('Beep-Boop template initialized', { 
          templateName: template.name 
        });
      } catch (error) {
        this.contextLogger.error('Failed to initialize template', error, {
          templateName: template.name
        });
      }
    }
  }
}

/**
 * Singleton instance for application-wide use
 */
export const pcsAdapter = new PCSAdapter();