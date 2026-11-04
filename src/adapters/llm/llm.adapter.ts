/**
 * src/adapters/llm/llm.adapter.ts - LLM Provider Integration
 * 
 * Unified adapter for LLM providers with Ollama as primary and OpenAI/Anthropic
 * as fallbacks. Implements streaming, resilience patterns, and provider selection.
 * 
 * Related Components:
 * - Circuit breaker for provider reliability
 * - Retry handler with exponential backoff
 * - Streaming response handling
 * - Provider fallback logic
 * 
 * Tags: #adapter #llm #ollama #openai #streaming #fallback
 */

import axios, { AxiosInstance } from 'axios';
import OpenAI from 'openai';
import { config } from '@/infrastructure/config';
import { logger, createContextualLogger } from '@/infrastructure/logging';
import { CircuitBreaker } from '@/utils/circuit-breaker';
import { RetryHandler } from '@/utils/retry-handler';

/**
 * LLM provider enumeration
 */
export enum LLMProvider {
  OLLAMA = 'ollama',
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  GROK = 'grok'
}

/**
 * Chat message structure compatible with all providers
 */
export interface ChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
  name?: string;
}

/**
 * LLM request configuration
 */
export interface LLMRequest {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
  provider?: LLMProvider;
  systemPrompt?: string;
  context?: Record<string, any>;
}

/**
 * LLM response structure
 */
export interface LLMResponse {
  content: string;
  provider: LLMProvider;
  model: string;
  usage: {
    promptTokens: number;
    completionTokens: number;
    totalTokens: number;
  };
  metadata: {
    responseTime: number;
    cached: boolean;
    fallback: boolean;
    finishReason: string;
    requestId?: string;
  };
}

/**
 * Streaming token chunk
 */
export interface LLMTokenChunk {
  content: string;
  provider: LLMProvider;
  model: string;
  isComplete: boolean;
  usage?: Partial<LLMResponse['usage']>;
  metadata: {
    chunkIndex: number;
    timestamp: string;
  };
}

/**
 * LLM adapter metrics
 */
export interface LLMMetrics {
  [provider: string]: {
    totalRequests: number;
    successfulRequests: number;
    failedRequests: number;
    averageResponseTime: number;
    totalTokens: number;
    circuitBreakerState: string;
    lastError?: string;
  };
}

/**
 * Unified LLM adapter with provider fallback
 * 
 * Provides a single interface for multiple LLM providers with automatic
 * fallback, streaming support, and resilience patterns.
 */
export class LLMAdapter {
  private ollamaClient!: AxiosInstance;
  private openaiClient!: OpenAI;
  private circuitBreakers!: Map<LLMProvider, CircuitBreaker>;
  private retryHandlers!: Map<LLMProvider, RetryHandler>;
  private metrics!: LLMMetrics;
  private contextLogger = createContextualLogger({ operation: 'llm-adapter' });

  constructor() {
    this.initializeClients();
    this.initializeResilience();
    this.initializeMetrics();
  }

  /**
   * Initialize LLM provider clients
   */
  private initializeClients(): void {
    // Initialize Ollama client
    this.ollamaClient = axios.create({
      baseURL: config.ollama.baseUrl,
      timeout: config.ollama.timeout,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Initialize OpenAI client
    if (config.openai.apiKey) {
      this.openaiClient = new OpenAI({
        apiKey: config.openai.apiKey,
        timeout: config.openai.timeout
      });
    }

    this.contextLogger.info('LLM clients initialized', {
      ollama: config.ollama.enabled,
      openai: !!config.openai.apiKey,
      primary: 'ollama'
    });
  }

  /**
   * Initialize resilience patterns for each provider
   */
  private initializeResilience(): void {
    this.circuitBreakers = new Map();
    this.retryHandlers = new Map();

    // Ollama resilience
    this.circuitBreakers.set(LLMProvider.OLLAMA, new CircuitBreaker({
      failureThreshold: 3,
      resetTimeout: 30000,
      monitoringPeriod: 10000
    }));

    this.retryHandlers.set(LLMProvider.OLLAMA, new RetryHandler({
      maxAttempts: 2,
      baseDelay: 1000,
      maxDelay: 5000,
      jitterFactor: 0.1
    }));

    // OpenAI resilience
    this.circuitBreakers.set(LLMProvider.OPENAI, new CircuitBreaker({
      failureThreshold: 5,
      resetTimeout: 60000,
      monitoringPeriod: 15000
    }));

    this.retryHandlers.set(LLMProvider.OPENAI, new RetryHandler({
      maxAttempts: 3,
      baseDelay: 1500,
      maxDelay: 15000,
      jitterFactor: 0.2
    }));
  }

  /**
   * Initialize metrics tracking for all providers
   */
  private initializeMetrics(): void {
    this.metrics = {};
    
    for (const provider of Object.values(LLMProvider)) {
      this.metrics[provider] = {
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        averageResponseTime: 0,
        totalTokens: 0,
        circuitBreakerState: 'CLOSED'
      };
    }
  }

  /**
   * Generate chat completion with automatic provider fallback
   * 
   * Attempts Ollama first, falls back to OpenAI if Ollama fails.
   * Includes streaming support for real-time responses.
   */
  async generateCompletion(request: LLMRequest): Promise<LLMResponse> {
    const providers = this.getProviderOrder(request.provider);
    
    for (const provider of providers) {
      try {
        const startTime = Date.now();
        
        this.contextLogger.info('Attempting LLM completion', {
          provider,
          model: this.getModelForProvider(provider, request.model),
          messageCount: request.messages.length,
          streaming: request.stream || false
        });

        const result = await this.executeWithProvider(provider, request);
        
        this.updateMetrics(provider, true, Date.now() - startTime, result.usage.totalTokens);
        
        return {
          ...result,
          metadata: {
            ...result.metadata,
            fallback: provider !== LLMProvider.OLLAMA
          }
        };

      } catch (error) {
        this.updateMetrics(provider, false, 0, 0, error);
        
        this.contextLogger.warn('LLM provider failed, trying next', {
          provider,
          error: error instanceof Error ? error.message : 'Unknown error',
          hasNextProvider: providers.indexOf(provider) < providers.length - 1
        });

        // If this is the last provider, throw the error
        if (provider === providers[providers.length - 1]) {
          throw error;
        }
      }
    }

    throw new Error('All LLM providers failed');
  }

  /**
   * Stream chat completion with real-time token generation
   * 
   * Provides streaming responses for better user experience.
   */
  async* streamCompletion(request: LLMRequest): AsyncGenerator<LLMTokenChunk> {
    const providers = this.getProviderOrder(request.provider);
    let chunkIndex = 0;

    for (const provider of providers) {
      try {
        this.contextLogger.info('Starting streaming completion', {
          provider,
          model: this.getModelForProvider(provider, request.model)
        });

        // Stream from the specific provider
        const stream = this.streamFromProvider(provider, { ...request, stream: true });
        
        for await (const chunk of stream) {
          yield {
            ...chunk,
            metadata: {
              ...chunk.metadata,
              chunkIndex: chunkIndex++
            }
          };
        }

        // If we get here, streaming was successful
        this.updateMetrics(provider, true, 0, 0);
        return;

      } catch (error) {
        this.updateMetrics(provider, false, 0, 0, error);
        
        this.contextLogger.warn('Streaming provider failed, trying next', {
          provider,
          error: error instanceof Error ? error.message : 'Unknown error'
        });

        // If this is the last provider, throw the error
        if (provider === providers[providers.length - 1]) {
          throw error;
        }
      }
    }
  }

  /**
   * Execute completion with specific provider
   */
  private async executeWithProvider(provider: LLMProvider, request: LLMRequest): Promise<LLMResponse> {
    const circuitBreaker = this.circuitBreakers.get(provider)!;
    const retryHandler = this.retryHandlers.get(provider)!;

    return circuitBreaker.execute(async () => {
      return retryHandler.executeWithRetry(async () => {
        switch (provider) {
          case LLMProvider.OLLAMA:
            return this.executeOllama(request);
          case LLMProvider.OPENAI:
            return this.executeOpenAI(request);
          default:
            throw new Error(`Provider ${provider} not implemented`);
        }
      });
    });
  }

  /**
   * Execute completion with Ollama
   */
  private async executeOllama(request: LLMRequest): Promise<LLMResponse> {
    const startTime = Date.now();
    const model = this.getModelForProvider(LLMProvider.OLLAMA, request.model);

    // Format messages for Ollama
    const prompt = this.formatMessagesForOllama(request.messages);

    const response = await this.ollamaClient.post('/api/generate', {
      model,
      prompt,
      stream: false,
      options: {
        temperature: request.temperature || 0.7,
        num_predict: request.maxTokens || 2000
      }
    });

    const data = response.data;
    const responseTime = Date.now() - startTime;

    return {
      content: data.response || '',
      provider: LLMProvider.OLLAMA,
      model,
      usage: {
        promptTokens: data.prompt_eval_count || 0,
        completionTokens: data.eval_count || 0,
        totalTokens: (data.prompt_eval_count || 0) + (data.eval_count || 0)
      },
      metadata: {
        responseTime,
        cached: false,
        fallback: false,
        finishReason: data.done ? 'stop' : 'length',
        requestId: data.request_id
      }
    };
  }

  /**
   * Execute completion with OpenAI
   */
  private async executeOpenAI(request: LLMRequest): Promise<LLMResponse> {
    if (!this.openaiClient) {
      throw new Error('OpenAI client not initialized - API key missing');
    }

    const startTime = Date.now();
    const model = this.getModelForProvider(LLMProvider.OPENAI, request.model);

    const completion = await this.openaiClient.chat.completions.create({
      model,
      messages: request.messages,
      temperature: request.temperature || 0.7,
      max_tokens: request.maxTokens || 2000,
      stream: false
    });

    const responseTime = Date.now() - startTime;
    const choice = completion.choices[0];

    return {
      content: choice.message.content || '',
      provider: LLMProvider.OPENAI,
      model,
      usage: {
        promptTokens: completion.usage?.prompt_tokens || 0,
        completionTokens: completion.usage?.completion_tokens || 0,
        totalTokens: completion.usage?.total_tokens || 0
      },
      metadata: {
        responseTime,
        cached: false,
        fallback: true,
        finishReason: choice.finish_reason || 'stop',
        requestId: completion.id
      }
    };
  }

  /**
   * Stream from specific provider
   */
  private async* streamFromProvider(provider: LLMProvider, request: LLMRequest): AsyncGenerator<LLMTokenChunk> {
    switch (provider) {
      case LLMProvider.OLLAMA:
        yield* this.streamOllama(request);
        break;
      case LLMProvider.OPENAI:
        yield* this.streamOpenAI(request);
        break;
      default:
        throw new Error(`Streaming not implemented for provider: ${provider}`);
    }
  }

  /**
   * Stream completion from Ollama
   */
  private async* streamOllama(request: LLMRequest): AsyncGenerator<LLMTokenChunk> {
    const model = this.getModelForProvider(LLMProvider.OLLAMA, request.model);
    const prompt = this.formatMessagesForOllama(request.messages);

    const response = await this.ollamaClient.post('/api/generate', {
      model,
      prompt,
      stream: true,
      options: {
        temperature: request.temperature || 0.7,
        num_predict: request.maxTokens || 2000
      }
    }, {
      responseType: 'stream'
    });

    let chunkIndex = 0;
    let accumulatedContent = '';

    for await (const chunk of response.data) {
      try {
        const data = JSON.parse(chunk.toString());
        
        if (data.response) {
          accumulatedContent += data.response;
          
          yield {
            content: data.response,
            provider: LLMProvider.OLLAMA,
            model,
            isComplete: data.done || false,
            usage: data.done ? {
              promptTokens: data.prompt_eval_count || 0,
              completionTokens: data.eval_count || 0,
              totalTokens: (data.prompt_eval_count || 0) + (data.eval_count || 0)
            } : undefined,
            metadata: {
              chunkIndex: chunkIndex++,
              timestamp: new Date().toISOString()
            }
          };
        }

        if (data.done) {
          break;
        }
      } catch (parseError) {
        this.contextLogger.warn('Failed to parse Ollama stream chunk', { chunk });
      }
    }
  }

  /**
   * Stream completion from OpenAI
   */
  private async* streamOpenAI(request: LLMRequest): AsyncGenerator<LLMTokenChunk> {
    if (!this.openaiClient) {
      throw new Error('OpenAI client not initialized');
    }

    const model = this.getModelForProvider(LLMProvider.OPENAI, request.model);
    let chunkIndex = 0;

    const stream = await this.openaiClient.chat.completions.create({
      model,
      messages: request.messages,
      temperature: request.temperature || 0.7,
      max_tokens: request.maxTokens || 2000,
      stream: true
    });

    for await (const chunk of stream) {
      const delta = chunk.choices[0]?.delta;
      
      if (delta?.content) {
        yield {
          content: delta.content,
          provider: LLMProvider.OPENAI,
          model,
          isComplete: chunk.choices[0]?.finish_reason !== null,
          usage: chunk.usage ? {
            promptTokens: chunk.usage.prompt_tokens,
            completionTokens: chunk.usage.completion_tokens,
            totalTokens: chunk.usage.total_tokens
          } : undefined,
          metadata: {
            chunkIndex: chunkIndex++,
            timestamp: new Date().toISOString()
          }
        };
      }

      if (chunk.choices[0]?.finish_reason) {
        break;
      }
    }
  }

  /**
   * Get provider order for fallback logic
   */
  private getProviderOrder(preferredProvider?: LLMProvider): LLMProvider[] {
    const enabledProviders: LLMProvider[] = [];

    // Add preferred provider first if specified and enabled
    if (preferredProvider) {
      enabledProviders.push(preferredProvider);
    }

    // Add Ollama if enabled and not already added
    if (config.ollama.enabled && !enabledProviders.includes(LLMProvider.OLLAMA)) {
      enabledProviders.push(LLMProvider.OLLAMA);
    }

    // Add OpenAI if enabled and not already added
    if (config.openai.enabled && config.openai.apiKey && !enabledProviders.includes(LLMProvider.OPENAI)) {
      enabledProviders.push(LLMProvider.OPENAI);
    }

    if (enabledProviders.length === 0) {
      throw new Error('No LLM providers are enabled and configured');
    }

    return enabledProviders;
  }

  /**
   * Get model name for specific provider
   */
  private getModelForProvider(provider: LLMProvider, requestedModel?: string): string {
    if (requestedModel) {
      return requestedModel;
    }

    switch (provider) {
      case LLMProvider.OLLAMA:
        return config.ollama.model;
      case LLMProvider.OPENAI:
        return config.openai.model;
      default:
        throw new Error(`Model configuration not found for provider: ${provider}`);
    }
  }

  /**
   * Format chat messages for Ollama's expected format
   */
  private formatMessagesForOllama(messages: ChatMessage[]): string {
    return messages.map(msg => {
      const rolePrefix = msg.role === 'user' ? 'Human: ' : 
                        msg.role === 'assistant' ? 'Assistant: ' : 
                        msg.role === 'system' ? 'System: ' : '';
      return `${rolePrefix}${msg.content}`;
    }).join('\n\n') + '\n\nAssistant: ';
  }

  /**
   * Check health of all LLM providers
   */
  async healthCheck(): Promise<Record<LLMProvider, boolean>> {
    const healthResults: Record<string, boolean> = {};

    // Check Ollama health
    if (config.ollama.enabled) {
      try {
        const response = await this.ollamaClient.get('/api/tags', { timeout: 5000 });
        healthResults[LLMProvider.OLLAMA] = response.status === 200;
      } catch (error) {
        healthResults[LLMProvider.OLLAMA] = false;
        this.contextLogger.warn('Ollama health check failed', { error });
      }
    }

    // Check OpenAI health (simple API call)
    if (config.openai.enabled && this.openaiClient) {
      try {
        await this.openaiClient.models.list();
        healthResults[LLMProvider.OPENAI] = true;
      } catch (error) {
        healthResults[LLMProvider.OPENAI] = false;
        this.contextLogger.warn('OpenAI health check failed', { error });
      }
    }

    return healthResults as Record<LLMProvider, boolean>;
  }

  /**
   * Get available models from each provider
   */
  async getAvailableModels(): Promise<Record<LLMProvider, string[]>> {
    const models: Record<string, string[]> = {};

    // Get Ollama models
    if (config.ollama.enabled) {
      try {
        const response = await this.ollamaClient.get('/api/tags');
        models[LLMProvider.OLLAMA] = response.data.models?.map((m: any) => m.name) || [];
      } catch (error) {
        models[LLMProvider.OLLAMA] = [];
      }
    }

    // Get OpenAI models
    if (config.openai.enabled && this.openaiClient) {
      try {
        const response = await this.openaiClient.models.list();
        models[LLMProvider.OPENAI] = response.data
          .filter(model => model.id.includes('gpt'))
          .map(model => model.id);
      } catch (error) {
        models[LLMProvider.OPENAI] = [];
      }
    }

    return models as Record<LLMProvider, string[]>;
  }

  /**
   * Get adapter metrics for monitoring
   */
  getMetrics(): LLMMetrics {
    // Update circuit breaker states
    for (const [provider, circuitBreaker] of this.circuitBreakers.entries()) {
      this.metrics[provider].circuitBreakerState = circuitBreaker.getState();
    }

    return this.metrics;
  }

  /**
   * Update provider metrics
   */
  private updateMetrics(
    provider: LLMProvider, 
    success: boolean, 
    responseTime: number, 
    tokens: number,
    error?: any
  ): void {
    const providerMetrics = this.metrics[provider];
    
    providerMetrics.totalRequests++;
    
    if (success) {
      providerMetrics.successfulRequests++;
      providerMetrics.totalTokens += tokens;
      
      // Update rolling average response time
      const totalSuccessTime = providerMetrics.averageResponseTime * (providerMetrics.successfulRequests - 1);
      providerMetrics.averageResponseTime = (totalSuccessTime + responseTime) / providerMetrics.successfulRequests;
      
    } else {
      providerMetrics.failedRequests++;
      providerMetrics.lastError = error instanceof Error ? error.message : 'Unknown error';
    }
  }

  /**
   * Force switch to specific provider (for testing)
   */
  async forceSwitchProvider(provider: LLMProvider): Promise<void> {
    this.contextLogger.info('Forcing provider switch', { provider });
    
    // Open circuit breakers for other providers
    for (const [p, cb] of this.circuitBreakers.entries()) {
      if (p !== provider) {
        cb.forceOpen();
      } else {
        cb.forceClose();
      }
    }
  }

  /**
   * Reset all provider circuit breakers
   */
  resetCircuitBreakers(): void {
    for (const circuitBreaker of this.circuitBreakers.values()) {
      circuitBreaker.reset();
    }
    this.contextLogger.info('All LLM circuit breakers reset');
  }
}

/**
 * Singleton instance for application-wide use
 */
export const llmAdapter = new LLMAdapter();