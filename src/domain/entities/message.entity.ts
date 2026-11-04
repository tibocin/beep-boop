/**
 * src/domain/entities/message.entity.ts - Message Domain Entity
 * 
 * Core domain entity representing individual messages within conversations.
 * Handles message content, metadata, feedback, and business validation.
 * 
 * Related Components:
 * - Conversation entities containing messages
 * - Voice processing and transcription
 * - Feedback and scoring systems
 * - Memory extraction from content
 * 
 * Tags: #domain #entity #message #feedback #voice
 */

import { z } from 'zod';

/**
 * Message content types supported by the system
 */
export enum MessageContentType {
  TEXT = 'text',
  VOICE = 'voice',
  IMAGE = 'image',
  VIDEO = 'video',
  DOCUMENT = 'document'
}

/**
 * Message roles in conversation
 */
export enum MessageRole {
  USER = 'user',
  ASSISTANT = 'assistant',
  SYSTEM = 'system'
}

/**
 * Feedback types for message scoring
 */
export enum FeedbackType {
  THUMBS_UP = 'up',
  THUMBS_DOWN = 'down'
}

/**
 * Message metadata schema for validation
 */
export const MessageMetadataSchema = z.object({
  promptTemplate: z.string().optional(),
  knowledgeSources: z.array(z.object({
    id: z.string(),
    source: z.string(),
    relevanceScore: z.number().min(0).max(1),
    content: z.string()
  })).default([]),
  processingTime: z.number().positive().optional(),
  confidenceScore: z.number().min(0).max(1).optional(),
  feedbackScore: z.number().optional(),
  voiceMetadata: z.object({
    originalAudioUrl: z.string().optional(),
    transcriptionConfidence: z.number().min(0).max(1).optional(),
    audioLanguage: z.string().optional(),
    audioDuration: z.number().positive().optional(),
    synthesizedAudioUrl: z.string().optional()
  }).optional(),
  llmMetadata: z.object({
    model: z.string(),
    tokenCount: z.number().positive().optional(),
    temperature: z.number().min(0).max(2).optional(),
    completionReason: z.string().optional()
  }).optional(),
  processingSteps: z.array(z.object({
    step: z.string(),
    duration: z.number().positive(),
    success: z.boolean(),
    metadata: z.record(z.any()).optional()
  })).default([])
});

export type MessageMetadata = z.infer<typeof MessageMetadataSchema>;

/**
 * User feedback data structure
 */
export interface UserFeedback {
  type: FeedbackType;
  comment?: string;
  timestamp: Date;
  metadata?: Record<string, any>;
}

/**
 * Message entity representing individual conversation messages
 * 
 * Core domain entity that manages message content, validation, feedback,
 * and business rules for conversational interactions.
 */
export class MessageEntity {
  public feedback?: UserFeedback;

  constructor(
    public readonly id: string,
    public readonly conversationId: string,
    public readonly role: MessageRole,
    public content: string,
    public readonly contentType: MessageContentType = MessageContentType.TEXT,
    public metadata: MessageMetadata = { knowledgeSources: [], processingSteps: [] },
    public readonly createdAt: Date = new Date(),
    public updatedAt: Date = new Date()
  ) {
    this.validateMessage();
  }

  /**
   * Validate message entity business rules
   * 
   * Ensures message data meets domain requirements and constraints.
   */
  private validateMessage(): void {
    if (!this.id || this.id.trim().length === 0) {
      throw new Error('Message ID cannot be empty');
    }

    if (!this.conversationId || this.conversationId.trim().length === 0) {
      throw new Error('Conversation ID cannot be empty');
    }

    if (!this.content || this.content.trim().length === 0) {
      throw new Error('Message content cannot be empty');
    }

    if (this.content.length > 10000) {
      throw new Error('Message content cannot exceed 10,000 characters');
    }

    // Validate metadata
    try {
      MessageMetadataSchema.parse(this.metadata);
    } catch (error) {
      throw new Error(`Invalid message metadata: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update message content with validation
   */
  updateContent(newContent: string): void {
    if (!newContent || newContent.trim().length === 0) {
      throw new Error('Content cannot be empty');
    }

    if (newContent.length > 10000) {
      throw new Error('Content cannot exceed 10,000 characters');
    }

    this.content = newContent.trim();
    this.updatedAt = new Date();
  }

  /**
   * Add user feedback to the message
   * 
   * Records user feedback (thumbs up/down) with optional comments and metadata.
   */
  addFeedback(feedback: UserFeedback): void {
    // Validate feedback
    if (!Object.values(FeedbackType).includes(feedback.type)) {
      throw new Error('Invalid feedback type');
    }

    if (feedback.comment && feedback.comment.length > 500) {
      throw new Error('Feedback comment cannot exceed 500 characters');
    }

    this.feedback = {
      ...feedback,
      timestamp: new Date()
    };

    // Update metadata with feedback score
    this.metadata.feedbackScore = feedback.type === FeedbackType.THUMBS_UP ? 1 : -1;
    this.updatedAt = new Date();
  }

  /**
   * Add knowledge source reference
   * 
   * Records which knowledge sources were used to generate this message.
   */
  addKnowledgeSource(source: MessageMetadata['knowledgeSources'][0]): void {
    if (!this.metadata.knowledgeSources) {
      this.metadata.knowledgeSources = [];
    }

    // Avoid duplicate sources
    const existingSource = this.metadata.knowledgeSources.find(s => s.id === source.id);
    if (!existingSource) {
      this.metadata.knowledgeSources.push(source);
      this.updatedAt = new Date();
    }
  }

  /**
   * Add processing step information
   * 
   * Records the steps taken to process and generate this message.
   */
  addProcessingStep(step: MessageMetadata['processingSteps'][0]): void {
    if (!this.metadata.processingSteps) {
      this.metadata.processingSteps = [];
    }

    this.metadata.processingSteps.push(step);
    this.updatedAt = new Date();
  }

  /**
   * Update LLM metadata after generation
   */
  updateLLMMetadata(llmData: MessageMetadata['llmMetadata']): void {
    this.metadata.llmMetadata = llmData;
    this.updatedAt = new Date();
  }

  /**
   * Update voice metadata for voice messages
   */
  updateVoiceMetadata(voiceData: MessageMetadata['voiceMetadata']): void {
    if (this.contentType !== MessageContentType.VOICE) {
      throw new Error('Cannot add voice metadata to non-voice message');
    }

    this.metadata.voiceMetadata = voiceData;
    this.updatedAt = new Date();
  }

  /**
   * Calculate total processing time from steps
   */
  getTotalProcessingTime(): number {
    if (!this.metadata.processingSteps) {
      return this.metadata.processingTime || 0;
    }

    return this.metadata.processingSteps.reduce((total, step) => total + step.duration, 0);
  }

  /**
   * Get confidence score with fallback calculation
   */
  getConfidenceScore(): number {
    if (this.metadata.confidenceScore !== undefined) {
      return this.metadata.confidenceScore;
    }

    // Calculate from knowledge sources if available
    if (this.metadata.knowledgeSources && this.metadata.knowledgeSources.length > 0) {
      const avgScore = this.metadata.knowledgeSources.reduce((sum, source) => 
        sum + source.relevanceScore, 0) / this.metadata.knowledgeSources.length;
      return avgScore;
    }

    return 0.5; // Default confidence
  }

  /**
   * Check if message has positive feedback
   */
  hasPositiveFeedback(): boolean {
    return this.feedback?.type === FeedbackType.THUMBS_UP;
  }

  /**
   * Check if message has negative feedback
   */
  hasNegativeFeedback(): boolean {
    return this.feedback?.type === FeedbackType.THUMBS_DOWN;
  }

  /**
   * Check if message is voice-based
   */
  isVoiceMessage(): boolean {
    return this.contentType === MessageContentType.VOICE;
  }

  /**
   * Check if message was generated by AI assistant
   */
  isAssistantMessage(): boolean {
    return this.role === MessageRole.ASSISTANT;
  }

  /**
   * Get word count for analytics
   */
  getWordCount(): number {
    return this.content.trim().split(/\s+/).length;
  }

  /**
   * Convert entity to plain object for serialization
   */
  toJSON(): Record<string, any> {
    return {
      id: this.id,
      conversationId: this.conversationId,
      role: this.role,
      content: this.content,
      contentType: this.contentType,
      metadata: this.metadata,
      feedback: this.feedback,
      createdAt: this.createdAt.toISOString(),
      updatedAt: this.updatedAt.toISOString(),
      wordCount: this.getWordCount(),
      processingTime: this.getTotalProcessingTime(),
      confidenceScore: this.getConfidenceScore()
    };
  }

  /**
   * Create message entity from database record
   */
  static fromDatabaseRecord(record: any): MessageEntity {
    const message = new MessageEntity(
      record.id,
      record.conversationId || record.conversation_id,
      record.role as MessageRole,
      record.content,
      record.contentType || record.content_type as MessageContentType,
      record.metadata || { knowledgeSources: [], processingSteps: [] },
      new Date(record.createdAt || record.created_at),
      new Date(record.updatedAt || record.updated_at)
    );

    // Add feedback if present
    if (record.feedback) {
      message.feedback = {
        type: record.feedback.type as FeedbackType,
        comment: record.feedback.comment,
        timestamp: new Date(record.feedback.timestamp),
        metadata: record.feedback.metadata
      };
    }

    return message;
  }

  /**
   * Create user message entity
   */
  static createUserMessage(
    id: string,
    conversationId: string,
    content: string,
    contentType: MessageContentType = MessageContentType.TEXT
  ): MessageEntity {
    return new MessageEntity(
      id,
      conversationId,
      MessageRole.USER,
      content,
      contentType
    );
  }

  /**
   * Create assistant message entity
   */
  static createAssistantMessage(
    id: string,
    conversationId: string,
    content: string,
    metadata: MessageMetadata = { knowledgeSources: [], processingSteps: [] }
  ): MessageEntity {
    return new MessageEntity(
      id,
      conversationId,
      MessageRole.ASSISTANT,
      content,
      MessageContentType.TEXT,
      metadata
    );
  }
}