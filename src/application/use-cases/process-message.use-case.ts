/**
 * src/application/use-cases/process-message.use-case.ts - Message Processing Use Case
 * 
 * Core use case that orchestrates the complete message processing pipeline.
 * Integrates knowledge retrieval, prompt generation, LLM processing, and memory storage.
 * 
 * Related Components:
 * - Digi-Core adapter for knowledge retrieval
 * - PCS adapter for dynamic prompt generation
 * - LLM adapter for response generation
 * - Memory extraction and relationship mapping
 * 
 * Tags: #use-case #orchestration #pipeline #streaming #memory
 */

import { v4 as uuidv4 } from 'uuid';
import { digiCoreAdapter, KnowledgeQuery, KnowledgeResult } from '@/adapters/digi-core/digi-core.adapter';
import { pcsAdapter, PromptRequest, GeneratedPrompt } from '@/adapters/pcs/pcs.adapter';
import { llmAdapter, LLMRequest, LLMResponse } from '@/adapters/llm/llm.adapter';
import { ConversationEntity, ConversationStatus } from '@/domain/entities/conversation.entity';
import { MessageEntity, MessageRole, MessageContentType } from '@/domain/entities/message.entity';
import { logger, createContextualLogger } from '@/infrastructure/logging';

/**
 * Input for message processing use case
 */
export interface ProcessMessageInput {
  userId: string;
  message: string;
  conversationId?: string;
  voice?: boolean;
  context?: Record<string, any>;
}

/**
 * Output from message processing use case
 */
export interface ProcessMessageOutput {
  messageId: string;
  conversationId: string;
  response: string;
  confidence: number;
  knowledgeUsed: KnowledgeResult;
  promptUsed: GeneratedPrompt;
  processingSteps: ProcessingStep[];
  metadata: {
    processingTime: number;
    llmProvider: string;
    tokensUsed: number;
    voiceEnabled: boolean;
  };
}

/**
 * Processing step information for streaming
 */
export interface ProcessingStep {
  step: 'parsing' | 'knowledge_retrieval' | 'prompt_generation' | 'llm_processing' | 'response_synthesis' | 'memory_storage';
  status: 'started' | 'completed' | 'failed';
  duration?: number;
  metadata?: Record<string, any>;
  timestamp: string;
}

/**
 * Streaming event types for real-time updates
 */
export interface StreamingEvent {
  type: 'processing_step' | 'token_chunk' | 'knowledge_chunk' | 'complete' | 'error';
  data: any;
  timestamp: string;
}

/**
 * Message processing use case implementation
 * 
 * Orchestrates the complete pipeline from user input to final response,
 * including knowledge retrieval, prompt generation, LLM processing,
 * and memory extraction with real-time streaming support.
 */
export class ProcessMessageUseCase {
  private contextLogger = createContextualLogger({ operation: 'process-message' });

  /**
   * Process user message through complete pipeline
   * 
   * Executes the full conversation pipeline with knowledge integration,
   * dynamic prompt generation, and response synthesis.
   */
  async execute(input: ProcessMessageInput): Promise<ProcessMessageOutput> {
    const startTime = Date.now();
    const messageId = uuidv4();
    const processingSteps: ProcessingStep[] = [];

    // Set up contextual logging
    this.contextLogger.setContext({
      userId: input.userId,
      conversationId: input.conversationId,
      requestId: messageId
    });

    try {
      this.contextLogger.info('Starting message processing', {
        messageLength: input.message.length,
        hasConversationId: !!input.conversationId,
        isVoice: input.voice || false
      });

      // Step 1: Parse and validate input
      const parseStep = this.startProcessingStep('parsing');
      const parsedInput = await this.parseUserInput(input);
      this.completeProcessingStep(parseStep, processingSteps);

      // Step 2: Retrieve relevant knowledge from Digi-Core
      const knowledgeStep = this.startProcessingStep('knowledge_retrieval');
      const knowledgeResult = await this.retrieveKnowledge(parsedInput);
      this.completeProcessingStep(knowledgeStep, processingSteps, { 
        sourceCount: knowledgeResult.results.length,
        confidence: knowledgeResult.confidence 
      });

      // Step 3: Generate dynamic prompt using PCS
      const promptStep = this.startProcessingStep('prompt_generation');
      const generatedPrompt = await this.generatePrompt(parsedInput, knowledgeResult);
      this.completeProcessingStep(promptStep, processingSteps, {
        templateName: generatedPrompt.templateName,
        promptLength: generatedPrompt.prompt.length
      });

      // Step 4: Generate LLM response
      const llmStep = this.startProcessingStep('llm_processing');
      const llmResponse = await this.generateLLMResponse(generatedPrompt, parsedInput);
      this.completeProcessingStep(llmStep, processingSteps, {
        provider: llmResponse.provider,
        tokens: llmResponse.usage.totalTokens
      });

      // Step 5: Synthesize final response
      const synthesisStep = this.startProcessingStep('response_synthesis');
      const finalResponse = await this.synthesizeResponse(llmResponse, parsedInput);
      this.completeProcessingStep(synthesisStep, processingSteps);

      // Step 6: Extract and store memories (async)
      const memoryStep = this.startProcessingStep('memory_storage');
      // Note: Memory storage happens asynchronously to not block response
      this.extractAndStoreMemories(parsedInput, finalResponse, generatedPrompt, knowledgeResult)
        .then(() => this.completeProcessingStep(memoryStep, processingSteps))
        .catch(error => this.failProcessingStep(memoryStep, processingSteps, error));

      const processingTime = Date.now() - startTime;

      this.contextLogger.info('Message processing completed', {
        messageId,
        processingTime,
        confidence: knowledgeResult.confidence,
        responseLength: finalResponse.length
      });

      return {
        messageId,
        conversationId: parsedInput.conversationId,
        response: finalResponse,
        confidence: knowledgeResult.confidence,
        knowledgeUsed: knowledgeResult,
        promptUsed: generatedPrompt,
        processingSteps,
        metadata: {
          processingTime,
          llmProvider: llmResponse.provider,
          tokensUsed: llmResponse.usage.totalTokens,
          voiceEnabled: input.voice || false
        }
      };

    } catch (error) {
      this.contextLogger.error('Message processing failed', error, {
        messageId,
        processingTime: Date.now() - startTime
      });

      throw new Error(`Message processing failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Process message with streaming for real-time updates
   * 
   * Provides real-time streaming of processing steps and response generation.
   */
  async* executeWithStreaming(input: ProcessMessageInput): AsyncGenerator<StreamingEvent> {
    const startTime = Date.now();
    const messageId = uuidv4();

    try {
      // Emit processing start
      yield {
        type: 'processing_step',
        data: {
          step: 'parsing',
          status: 'started',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      // Step 1: Parse input
      const parsedInput = await this.parseUserInput(input);
      yield {
        type: 'processing_step',
        data: {
          step: 'parsing',
          status: 'completed',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      // Step 2: Stream knowledge retrieval
      yield {
        type: 'processing_step',
        data: {
          step: 'knowledge_retrieval',
          status: 'started',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      const knowledgeResult = await this.retrieveKnowledge(parsedInput);
      
      // Emit knowledge chunks
      for (const source of knowledgeResult.results) {
        yield {
          type: 'knowledge_chunk',
          data: source,
          timestamp: new Date().toISOString()
        };
      }

      yield {
        type: 'processing_step',
        data: {
          step: 'knowledge_retrieval',
          status: 'completed',
          metadata: { sourceCount: knowledgeResult.results.length },
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      // Step 3: Generate prompt
      yield {
        type: 'processing_step',
        data: {
          step: 'prompt_generation',
          status: 'started',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      const generatedPrompt = await this.generatePrompt(parsedInput, knowledgeResult);
      
      yield {
        type: 'processing_step',
        data: {
          step: 'prompt_generation',
          status: 'completed',
          metadata: { templateName: generatedPrompt.templateName },
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      // Step 4: Stream LLM response
      yield {
        type: 'processing_step',
        data: {
          step: 'llm_processing',
          status: 'started',
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      // Stream LLM tokens
      const llmRequest = this.createLLMRequest(generatedPrompt, parsedInput);
      let fullResponse = '';
      let tokenCount = 0;

      for await (const chunk of llmAdapter.streamCompletion(llmRequest)) {
        fullResponse += chunk.content;
        tokenCount++;
        
        yield {
          type: 'token_chunk',
          data: {
            chunk: chunk.content,
            messageId,
            isComplete: chunk.isComplete,
            provider: chunk.provider
          },
          timestamp: new Date().toISOString()
        };

        if (chunk.isComplete) {
          break;
        }
      }

      yield {
        type: 'processing_step',
        data: {
          step: 'llm_processing',
          status: 'completed',
          metadata: { tokenCount },
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      // Step 5: Complete processing
      const processingTime = Date.now() - startTime;

      yield {
        type: 'complete',
        data: {
          messageId,
          conversationId: parsedInput.conversationId,
          response: fullResponse,
          processingTime,
          confidence: knowledgeResult.confidence
        },
        timestamp: new Date().toISOString()
      };

    } catch (error) {
      this.contextLogger.error('Streaming message processing failed', error);
      
      yield {
        type: 'error',
        data: {
          error: error instanceof Error ? error.message : 'Processing failed',
          messageId,
          timestamp: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * Parse and validate user input
   */
  private async parseUserInput(input: ProcessMessageInput): Promise<{
    userId: string;
    message: string;
    conversationId: string;
    voice: boolean;
    context: Record<string, any>;
  }> {
    return {
      userId: input.userId,
      message: input.message.trim(),
      conversationId: input.conversationId || uuidv4(),
      voice: input.voice || false,
      context: input.context || {}
    };
  }

  /**
   * Retrieve relevant knowledge from Digi-Core
   */
  private async retrieveKnowledge(input: any): Promise<KnowledgeResult> {
    const query: KnowledgeQuery = {
      query: input.message,
      context: {
        userId: input.userId,
        conversationId: input.conversationId,
        responseType: 'detailed',
        maxResults: 5,
        minConfidence: 0.3
      }
    };

    return digiCoreAdapter.queryKnowledge(query);
  }

  /**
   * Generate dynamic prompt using PCS
   */
  private async generatePrompt(input: any, knowledgeResult: KnowledgeResult): Promise<GeneratedPrompt> {
    const promptRequest: PromptRequest = {
      templateName: 'beep_boop_personal_response',
      context: {
        userId: input.userId,
        conversationId: input.conversationId,
        digi_core_knowledge: JSON.stringify(knowledgeResult.results),
        user_query: input.message,
        conversation_context: JSON.stringify(input.context),
        user_profile: {} // TODO: Get from user profile service
      }
    };

    return pcsAdapter.generatePrompt(promptRequest);
  }

  /**
   * Generate LLM response
   */
  private async generateLLMResponse(prompt: GeneratedPrompt, input: any): Promise<LLMResponse> {
    const llmRequest: LLMRequest = this.createLLMRequest(prompt, input);
    return llmAdapter.generateCompletion(llmRequest);
  }

  /**
   * Create LLM request from prompt and input
   */
  private createLLMRequest(prompt: GeneratedPrompt, input: any): LLMRequest {
    return {
      messages: [
        {
          role: 'system',
          content: prompt.prompt
        },
        {
          role: 'user', 
          content: input.message
        }
      ],
      temperature: 0.7,
      maxTokens: 2000,
      context: {
        userId: input.userId,
        conversationId: input.conversationId,
        templateName: prompt.templateName
      }
    };
  }

  /**
   * Synthesize final response with post-processing
   */
  private async synthesizeResponse(llmResponse: LLMResponse, input: any): Promise<string> {
    let response = llmResponse.content.trim();

    // Post-processing for Beep-Boop personality
    if (input.voice) {
      // Adapt response for voice interaction
      response = this.adaptForVoice(response);
    }

    return response;
  }

  /**
   * Adapt response for voice interaction
   */
  private adaptForVoice(response: string): string {
    // Remove markdown formatting for voice
    let adapted = response
      .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold
      .replace(/\*(.*?)\*/g, '$1')     // Remove italics
      .replace(/`(.*?)`/g, '$1')       // Remove code formatting
      .replace(/#{1,6}\s/g, '')        // Remove headers
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1'); // Remove links

    // Add natural pauses
    adapted = adapted
      .replace(/\. /g, '. ... ')       // Pause after sentences
      .replace(/\? /g, '? ... ')       // Pause after questions
      .replace(/! /g, '! ... ');       // Pause after exclamations

    return adapted;
  }

  /**
   * Extract and store memories from conversation (async)
   */
  private async extractAndStoreMemories(
    input: any,
    response: string,
    prompt: GeneratedPrompt,
    knowledgeResult: KnowledgeResult
  ): Promise<void> {
    try {
      // Use PCS to extract memories
      const memoryPrompt = await pcsAdapter.generatePrompt({
        templateName: 'beep_boop_memory_extraction',
        context: {
          user_message: input.message,
          assistant_response: response,
          existing_knowledge: JSON.stringify(knowledgeResult.results)
        }
      });

      // Process memory extraction with LLM
      const memoryExtractionRequest: LLMRequest = {
        messages: [
          {
            role: 'system',
            content: memoryPrompt.prompt
          }
        ],
        temperature: 0.3, // Lower temperature for structured extraction
        maxTokens: 1000
      };

      const memoryResponse = await llmAdapter.generateCompletion(memoryExtractionRequest);
      
      // Parse extracted memories
      try {
        const extractedData = JSON.parse(memoryResponse.content);
        
        this.contextLogger.info('Memories extracted', {
          memoryCount: extractedData.new_memories?.length || 0,
          relationshipCount: extractedData.relationships?.length || 0
        });

        // TODO: Store memories in Neo4j and update relationships
        
      } catch (parseError) {
        this.contextLogger.warn('Failed to parse memory extraction result', {
          response: memoryResponse.content.substring(0, 200)
        });
      }

    } catch (error) {
      this.contextLogger.error('Memory extraction failed', error);
      // Don't throw - memory extraction failure shouldn't break response
    }
  }

  /**
   * Helper methods for processing step tracking
   */
  private startProcessingStep(step: ProcessingStep['step']): { step: string; startTime: number } {
    return {
      step,
      startTime: Date.now()
    };
  }

  private completeProcessingStep(
    stepInfo: { step: string; startTime: number },
    steps: ProcessingStep[],
    metadata?: Record<string, any>
  ): void {
    steps.push({
      step: stepInfo.step as ProcessingStep['step'],
      status: 'completed',
      duration: Date.now() - stepInfo.startTime,
      metadata,
      timestamp: new Date().toISOString()
    });

    this.contextLogger.debug('Processing step completed', {
      step: stepInfo.step,
      duration: Date.now() - stepInfo.startTime,
      metadata
    });
  }

  private failProcessingStep(
    stepInfo: { step: string; startTime: number },
    steps: ProcessingStep[],
    error: any
  ): void {
    steps.push({
      step: stepInfo.step as ProcessingStep['step'],
      status: 'failed',
      duration: Date.now() - stepInfo.startTime,
      metadata: {
        error: error instanceof Error ? error.message : 'Unknown error'
      },
      timestamp: new Date().toISOString()
    });

    this.contextLogger.error('Processing step failed', error, {
      step: stepInfo.step,
      duration: Date.now() - stepInfo.startTime
    });
  }
}

/**
 * Singleton instance for application-wide use
 */
export const processMessageUseCase = new ProcessMessageUseCase();