/**
 * src/application/services/memory.service.ts - Memory Management Service
 * 
 * Application service that coordinates memory extraction, storage, and relationship
 * management across PostgreSQL and Neo4j databases.
 * 
 * Related Components:
 * - Memory entities and domain logic
 * - Neo4j service for relationship storage
 * - PCS adapter for memory extraction prompts
 * - LLM adapter for content analysis
 * 
 * Tags: #service #memory #relationships #extraction #analysis
 */

import { v4 as uuidv4 } from 'uuid';
import { MemoryEntity, MemoryType } from '@/domain/entities/memory.entity';
import { MessageEntity } from '@/domain/entities/message.entity';
import { ConversationEntity } from '@/domain/entities/conversation.entity';
import { neo4jService, GraphRelationship } from '@/infrastructure/database/neo4j.service';
import { pcsAdapter, PromptRequest } from '@/adapters/pcs/pcs.adapter';
import { llmAdapter, LLMRequest } from '@/adapters/llm/llm.adapter';
import { DatabaseConnection } from '@/infrastructure/database/connection';
import { logger, createContextualLogger } from '@/infrastructure/logging';

/**
 * Memory extraction request
 */
export interface MemoryExtractionRequest {
  userId: string;
  conversationId: string;
  userMessage: string;
  assistantResponse: string;
  existingMemories?: MemoryEntity[];
  context?: Record<string, any>;
}

/**
 * Memory extraction result
 */
export interface MemoryExtractionResult {
  extractedMemories: MemoryEntity[];
  discoveredRelationships: GraphRelationship[];
  metadata: {
    extractionTime: number;
    extractionMethod: 'llm' | 'pattern' | 'explicit';
    extractionConfidence: number;
    llmProvider: string;
  };
}

/**
 * Memory search request
 */
export interface MemorySearchRequest {
  userId: string;
  query?: string;
  topics?: string[];
  memoryTypes?: MemoryType[];
  minConfidence?: number;
  limit?: number;
  includeRelationships?: boolean;
}

/**
 * Memory search result
 */
export interface MemorySearchResult {
  memories: MemoryEntity[];
  relationships: GraphRelationship[];
  totalFound: number;
  confidence: number;
  metadata: {
    searchTime: number;
    searchMethod: string;
    filters: Record<string, any>;
  };
}

/**
 * Memory management service
 * 
 * Coordinates memory extraction, storage, relationship discovery, and retrieval
 * across multiple databases and AI services.
 */
export class MemoryService {
  private contextLogger = createContextualLogger({ operation: 'memory-service' });

  /**
   * Extract memories from conversation
   * 
   * Analyzes user-assistant conversation to extract new memories and relationships.
   */
  async extractMemoriesFromConversation(
    request: MemoryExtractionRequest
  ): Promise<MemoryExtractionResult> {
    const startTime = Date.now();

    try {
      this.contextLogger.info('Starting memory extraction', {
        userId: request.userId,
        conversationId: request.conversationId,
        userMessageLength: request.userMessage.length,
        assistantResponseLength: request.assistantResponse.length
      });

      // Get existing user memories for context
      const existingMemories = request.existingMemories || 
        await this.getUserMemories(request.userId, { limit: 20 });

      // Generate memory extraction prompt
      const extractionPrompt = await this.generateExtractionPrompt(request, existingMemories);

      // Use LLM to extract structured memory data
      const extractionResult = await this.executeMemoryExtraction(extractionPrompt);

      // Parse extracted memories
      const newMemories = await this.parseAndValidateMemories(
        extractionResult,
        request.userId,
        request.conversationId
      );

      // Discover relationships between memories
      const relationships = await this.discoverMemoryRelationships(newMemories, existingMemories);

      // Store memories and relationships
      await this.storeMemoriesAndRelationships(newMemories, relationships);

      const extractionTime = Date.now() - startTime;

      this.contextLogger.info('Memory extraction completed', {
        extractedCount: newMemories.length,
        relationshipCount: relationships.length,
        extractionTime
      });

      return {
        extractedMemories: newMemories,
        discoveredRelationships: relationships,
        metadata: {
          extractionTime,
          extractionMethod: 'llm',
          extractionConfidence: this.calculateExtractionConfidence(newMemories),
          llmProvider: 'ollama' // TODO: Get from actual LLM response
        }
      };

    } catch (error) {
      this.contextLogger.error('Memory extraction failed', error, {
        userId: request.userId,
        conversationId: request.conversationId
      });
      throw error;
    }
  }

  /**
   * Search user memories with various filters
   * 
   * Provides flexible memory search across content, topics, and relationships.
   */
  async searchMemories(request: MemorySearchRequest): Promise<MemorySearchResult> {
    const startTime = Date.now();

    try {
      this.contextLogger.info('Searching memories', {
        userId: request.userId,
        hasQuery: !!request.query,
        topicCount: request.topics?.length || 0,
        typeFilters: request.memoryTypes?.length || 0
      });

      const memories = await this.getUserMemories(request.userId, {
        query: request.query,
        topics: request.topics,
        types: request.memoryTypes,
        minConfidence: request.minConfidence,
        limit: request.limit
      });

      let relationships: GraphRelationship[] = [];
      if (request.includeRelationships && memories.length > 0) {
        // Get relationships for found memories
        relationships = await this.getMemoryRelationships(memories.map(m => m.id));
      }

      const searchTime = Date.now() - startTime;

      return {
        memories,
        relationships,
        totalFound: memories.length,
        confidence: this.calculateSearchConfidence(memories, request),
        metadata: {
          searchTime,
          searchMethod: 'graph_traversal',
          filters: {
            query: request.query,
            topics: request.topics,
            types: request.memoryTypes,
            minConfidence: request.minConfidence
          }
        }
      };

    } catch (error) {
      this.contextLogger.error('Memory search failed', error, { userId: request.userId });
      throw error;
    }
  }

  /**
   * Get user memories with filters
   */
  private async getUserMemories(
    userId: string,
    filters: {
      query?: string;
      topics?: string[];
      types?: MemoryType[];
      minConfidence?: number;
      limit?: number;
    } = {}
  ): Promise<MemoryEntity[]> {
    // TODO: Implement memory retrieval from PostgreSQL with filters
    // For now, return empty array as placeholder
    this.contextLogger.debug('Retrieving user memories', { userId, filters });
    return [];
  }

  /**
   * Generate memory extraction prompt using PCS
   */
  private async generateExtractionPrompt(
    request: MemoryExtractionRequest,
    existingMemories: MemoryEntity[]
  ): Promise<string> {
    const promptRequest: PromptRequest = {
      templateName: 'beep_boop_memory_extraction',
      context: {
        user_message: request.userMessage,
        assistant_response: request.assistantResponse,
        existing_knowledge: JSON.stringify(existingMemories.map(m => ({
          type: m.type,
          content: m.content,
          confidence: m.confidence
        })))
      }
    };

    const generatedPrompt = await pcsAdapter.generatePrompt(promptRequest);
    return generatedPrompt.prompt;
  }

  /**
   * Execute memory extraction using LLM
   */
  private async executeMemoryExtraction(prompt: string): Promise<string> {
    const llmRequest: LLMRequest = {
      messages: [
        {
          role: 'system',
          content: prompt
        }
      ],
      temperature: 0.3, // Lower temperature for structured extraction
      maxTokens: 1500
    };

    const response = await llmAdapter.generateCompletion(llmRequest);
    return response.content;
  }

  /**
   * Parse and validate extracted memory data
   */
  private async parseAndValidateMemories(
    extractionResult: string,
    userId: string,
    conversationId: string
  ): Promise<MemoryEntity[]> {
    try {
      const parsedData = JSON.parse(extractionResult);
      const memories: MemoryEntity[] = [];

      for (const memoryData of parsedData.new_memories || []) {
        try {
          const memory = MemoryEntity.createFromExtraction(
            uuidv4(),
            userId,
            memoryData.type as MemoryType,
            memoryData.content,
            {
              conversationId,
              messageId: `extraction_${Date.now()}`,
              extractionMethod: 'llm',
              extractionConfidence: memoryData.confidence || 0.7
            },
            memoryData.confidence || 0.7,
            memoryData.importance || 0.5
          );

          memories.push(memory);

        } catch (error) {
          this.contextLogger.warn('Failed to create memory from extraction', {
            memoryData,
            error: error instanceof Error ? error.message : 'Unknown error'
          });
        }
      }

      return memories;

    } catch (error) {
      this.contextLogger.error('Failed to parse memory extraction result', error, {
        extractionResult: extractionResult.substring(0, 200)
      });
      return [];
    }
  }

  /**
   * Discover relationships between new and existing memories
   */
  private async discoverMemoryRelationships(
    newMemories: MemoryEntity[],
    existingMemories: MemoryEntity[]
  ): Promise<GraphRelationship[]> {
    const allRelationships: GraphRelationship[] = [];

    for (const newMemory of newMemories) {
      const relationships = await neo4jService.discoverRelationships(newMemory, existingMemories);
      allRelationships.push(...relationships);
    }

    return allRelationships;
  }

  /**
   * Store memories and relationships in databases
   */
  private async storeMemoriesAndRelationships(
    memories: MemoryEntity[],
    relationships: GraphRelationship[]
  ): Promise<void> {
    // Store memories in both PostgreSQL and Neo4j
    for (const memory of memories) {
      // TODO: Store in PostgreSQL via Prisma
      
      // Store in Neo4j for graph relationships
      await neo4jService.storeMemory(memory);
    }

    // Create relationships in Neo4j
    for (const relationship of relationships) {
      await neo4jService.createRelationship(relationship);
    }
  }

  /**
   * Get memory relationships
   */
  private async getMemoryRelationships(memoryIds: string[]): Promise<GraphRelationship[]> {
    // TODO: Implement relationship retrieval from Neo4j
    this.contextLogger.debug('Retrieving memory relationships', { memoryIds });
    return [];
  }

  /**
   * Calculate extraction confidence based on memory quality
   */
  private calculateExtractionConfidence(memories: MemoryEntity[]): number {
    if (memories.length === 0) return 0;

    const avgConfidence = memories.reduce((sum, m) => sum + m.confidence, 0) / memories.length;
    return avgConfidence;
  }

  /**
   * Calculate search confidence based on results
   */
  private calculateSearchConfidence(memories: MemoryEntity[], request: MemorySearchRequest): number {
    if (memories.length === 0) return 0;

    let baseConfidence = 0.8;

    // Boost confidence if specific filters were used
    if (request.query) baseConfidence += 0.1;
    if (request.topics && request.topics.length > 0) baseConfidence += 0.05;
    if (request.memoryTypes && request.memoryTypes.length > 0) baseConfidence += 0.05;

    return Math.min(1.0, baseConfidence);
  }
}

/**
 * Singleton instance for application-wide use
 */
export const memoryService = new MemoryService();