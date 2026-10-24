/**
 * src/domain/entities/conversation.entity.ts - Conversation Domain Entity
 * 
 * Core domain entity representing a conversation session between user and AI.
 * Encapsulates conversation state, metadata, and business rules.
 * 
 * Related Components:
 * - Message entities within conversations
 * - User context and preferences
 * - Conversation persistence and retrieval
 * - Topic clustering and analysis
 * 
 * Tags: #domain #entity #conversation #business-rules
 */

import { z } from 'zod';

/**
 * Conversation metadata schema for type safety and validation
 */
export const ConversationMetadataSchema = z.object({
  title: z.string().optional(),
  summary: z.string().optional(),
  topics: z.array(z.string()).default([]),
  mood: z.enum(['professional', 'casual', 'technical', 'creative']).optional(),
  context: z.record(z.any()).default({}),
  performance: z.object({
    averageResponseTime: z.number().optional(),
    totalTokens: z.number().default(0),
    totalMessages: z.number().default(0)
  }).optional()
});

export type ConversationMetadata = z.infer<typeof ConversationMetadataSchema>;

/**
 * Conversation status enumeration
 */
export enum ConversationStatus {
  ACTIVE = 'active',
  PAUSED = 'paused', 
  COMPLETED = 'completed',
  ARCHIVED = 'archived'
}

/**
 * Conversation entity representing a chat session
 * 
 * Core domain entity that manages conversation state, validation,
 * and business rules for user-AI interactions.
 */
export class ConversationEntity {
  constructor(
    public readonly id: string,
    public readonly userId: string,
    public title: string,
    public status: ConversationStatus = ConversationStatus.ACTIVE,
    public metadata: ConversationMetadata = { topics: [], context: {} },
    public readonly createdAt: Date = new Date(),
    public updatedAt: Date = new Date()
  ) {
    this.validateConversation();
  }

  /**
   * Validate conversation entity business rules
   * 
   * Ensures conversation data meets domain requirements and constraints.
   */
  private validateConversation(): void {
    if (!this.id || this.id.trim().length === 0) {
      throw new Error('Conversation ID cannot be empty');
    }

    if (!this.userId || this.userId.trim().length === 0) {
      throw new Error('User ID cannot be empty');
    }

    if (!this.title || this.title.trim().length === 0) {
      throw new Error('Conversation title cannot be empty');
    }

    if (this.title.length > 200) {
      throw new Error('Conversation title cannot exceed 200 characters');
    }

    // Validate metadata
    try {
      ConversationMetadataSchema.parse(this.metadata);
    } catch (error) {
      throw new Error(`Invalid conversation metadata: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update conversation title with validation
   */
  updateTitle(newTitle: string): void {
    if (!newTitle || newTitle.trim().length === 0) {
      throw new Error('Title cannot be empty');
    }

    if (newTitle.length > 200) {
      throw new Error('Title cannot exceed 200 characters');
    }

    this.title = newTitle.trim();
    this.updatedAt = new Date();
  }

  /**
   * Update conversation status with business rules
   */
  updateStatus(newStatus: ConversationStatus): void {
    // Validate status transitions
    const validTransitions: Record<ConversationStatus, ConversationStatus[]> = {
      [ConversationStatus.ACTIVE]: [ConversationStatus.PAUSED, ConversationStatus.COMPLETED],
      [ConversationStatus.PAUSED]: [ConversationStatus.ACTIVE, ConversationStatus.COMPLETED],
      [ConversationStatus.COMPLETED]: [ConversationStatus.ARCHIVED],
      [ConversationStatus.ARCHIVED]: [] // No transitions from archived
    };

    const allowedTransitions = validTransitions[this.status];
    if (!allowedTransitions.includes(newStatus)) {
      throw new Error(`Invalid status transition from ${this.status} to ${newStatus}`);
    }

    this.status = newStatus;
    this.updatedAt = new Date();
  }

  /**
   * Add a topic to the conversation metadata
   */
  addTopic(topic: string): void {
    if (!topic || topic.trim().length === 0) {
      throw new Error('Topic cannot be empty');
    }

    const normalizedTopic = topic.trim().toLowerCase();
    
    if (!this.metadata.topics) {
      this.metadata.topics = [];
    }

    if (!this.metadata.topics.includes(normalizedTopic)) {
      this.metadata.topics.push(normalizedTopic);
      this.updatedAt = new Date();
    }
  }

  /**
   * Update conversation summary
   */
  updateSummary(summary: string): void {
    if (summary && summary.length > 1000) {
      throw new Error('Summary cannot exceed 1000 characters');
    }

    this.metadata.summary = summary?.trim();
    this.updatedAt = new Date();
  }

  /**
   * Update performance metrics
   */
  updatePerformanceMetrics(metrics: Partial<ConversationMetadata['performance']>): void {
    if (!this.metadata.performance) {
      this.metadata.performance = {
        totalTokens: 0,
        totalMessages: 0
      };
    }

    this.metadata.performance = {
      ...this.metadata.performance,
      ...metrics
    };
    
    this.updatedAt = new Date();
  }

  /**
   * Check if conversation is active and can receive new messages
   */
  canReceiveMessages(): boolean {
    return this.status === ConversationStatus.ACTIVE;
  }

  /**
   * Calculate conversation duration in minutes
   */
  getDurationMinutes(): number {
    return Math.floor((this.updatedAt.getTime() - this.createdAt.getTime()) / (1000 * 60));
  }

  /**
   * Convert entity to plain object for serialization
   */
  toJSON(): Record<string, any> {
    return {
      id: this.id,
      userId: this.userId,
      title: this.title,
      status: this.status,
      metadata: this.metadata,
      createdAt: this.createdAt.toISOString(),
      updatedAt: this.updatedAt.toISOString(),
      durationMinutes: this.getDurationMinutes(),
      canReceiveMessages: this.canReceiveMessages()
    };
  }

  /**
   * Create conversation entity from database record
   */
  static fromDatabaseRecord(record: any): ConversationEntity {
    return new ConversationEntity(
      record.id,
      record.userId || record.user_id,
      record.title,
      record.status as ConversationStatus,
      record.metadata || {},
      new Date(record.createdAt || record.created_at),
      new Date(record.updatedAt || record.updated_at)
    );
  }

  /**
   * Generate conversation title from first message
   */
  static generateTitleFromMessage(message: string): string {
    const maxLength = 50;
    const cleaned = message.trim().replace(/\s+/g, ' ');
    
    if (cleaned.length <= maxLength) {
      return cleaned;
    }
    
    // Try to break at word boundary
    const truncated = cleaned.substring(0, maxLength);
    const lastSpaceIndex = truncated.lastIndexOf(' ');
    
    if (lastSpaceIndex > maxLength * 0.7) {
      return truncated.substring(0, lastSpaceIndex) + '...';
    }
    
    return truncated + '...';
  }
}