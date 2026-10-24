/**
 * src/domain/entities/memory.entity.ts - Memory Domain Entity
 * 
 * Core domain entity representing user memories extracted from conversations.
 * Manages memory types, confidence scoring, and relationship associations.
 * 
 * Related Components:
 * - Conversation and message entities
 * - Neo4j relationship storage
 * - Vector embedding generation
 * - Memory extraction algorithms
 * 
 * Tags: #domain #entity #memory #relationships #learning
 */

import { z } from 'zod';

/**
 * Memory types that can be extracted from conversations
 */
export enum MemoryType {
  PREFERENCE = 'preference',    // "I prefer dark mode"
  FACT = 'fact',              // "I work at Company X"  
  SKILL = 'skill',            // "I know TypeScript"
  GOAL = 'goal',              // "I want to learn React"
  HABIT = 'habit',            // "I usually work mornings"
  INSIGHT = 'insight',        // "User struggles with async code"
  RELATIONSHIP = 'relationship', // "John is my colleague"
  INTEREST = 'interest'       // "I enjoy hiking"
}

/**
 * Memory metadata schema for validation
 */
export const MemoryMetadataSchema = z.object({
  extractedFrom: z.object({
    conversationId: z.string(),
    messageId: z.string(),
    extractionMethod: z.enum(['llm', 'pattern', 'explicit']),
    extractionConfidence: z.number().min(0).max(1)
  }),
  topics: z.array(z.string()).default([]),
  relatedConcepts: z.array(z.string()).default([]),
  reinforcementCount: z.number().int().min(0).default(1),
  lastReinforced: z.date().optional(),
  contradictionFlags: z.array(z.string()).default([]),
  embedding: z.array(z.number()).optional(),
  validationStatus: z.enum(['pending', 'validated', 'rejected']).default('pending')
});

export type MemoryMetadata = z.infer<typeof MemoryMetadataSchema>;

/**
 * Memory entity representing extracted user information
 * 
 * Core domain entity that manages user memories with validation,
 * confidence tracking, and relationship management capabilities.
 */
export class MemoryEntity {
  constructor(
    public readonly id: string,
    public readonly userId: string,
    public type: MemoryType,
    public content: string,
    public confidence: number = 0.5,
    public importance: number = 0.5,
    public metadata: MemoryMetadata,
    public readonly createdAt: Date = new Date(),
    public updatedAt: Date = new Date()
  ) {
    this.validateMemory();
  }

  /**
   * Validate memory entity business rules
   * 
   * Ensures memory data meets domain requirements and constraints.
   */
  private validateMemory(): void {
    if (!this.id || this.id.trim().length === 0) {
      throw new Error('Memory ID cannot be empty');
    }

    if (!this.userId || this.userId.trim().length === 0) {
      throw new Error('User ID cannot be empty');
    }

    if (!this.content || this.content.trim().length === 0) {
      throw new Error('Memory content cannot be empty');
    }

    if (this.content.length > 2000) {
      throw new Error('Memory content cannot exceed 2,000 characters');
    }

    if (this.confidence < 0 || this.confidence > 1) {
      throw new Error('Confidence must be between 0 and 1');
    }

    if (this.importance < 0 || this.importance > 1) {
      throw new Error('Importance must be between 0 and 1');
    }

    // Validate metadata
    try {
      MemoryMetadataSchema.parse(this.metadata);
    } catch (error) {
      throw new Error(`Invalid memory metadata: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Update memory content with validation
   */
  updateContent(newContent: string): void {
    if (!newContent || newContent.trim().length === 0) {
      throw new Error('Content cannot be empty');
    }

    if (newContent.length > 2000) {
      throw new Error('Content cannot exceed 2,000 characters');
    }

    this.content = newContent.trim();
    this.updatedAt = new Date();
  }

  /**
   * Update confidence score with validation and reinforcement tracking
   */
  updateConfidence(newConfidence: number, reinforced: boolean = false): void {
    if (newConfidence < 0 || newConfidence > 1) {
      throw new Error('Confidence must be between 0 and 1');
    }

    this.confidence = newConfidence;
    
    if (reinforced) {
      this.metadata.reinforcementCount += 1;
      this.metadata.lastReinforced = new Date();
    }
    
    this.updatedAt = new Date();
  }

  /**
   * Update importance score based on usage and feedback
   */
  updateImportance(newImportance: number): void {
    if (newImportance < 0 || newImportance > 1) {
      throw new Error('Importance must be between 0 and 1');
    }

    this.importance = newImportance;
    this.updatedAt = new Date();
  }

  /**
   * Add a topic association to the memory
   */
  addTopic(topic: string): void {
    if (!topic || topic.trim().length === 0) {
      throw new Error('Topic cannot be empty');
    }

    const normalizedTopic = topic.trim().toLowerCase();
    
    if (!this.metadata.topics.includes(normalizedTopic)) {
      this.metadata.topics.push(normalizedTopic);
      this.updatedAt = new Date();
    }
  }

  /**
   * Add a related concept to enhance memory context
   */
  addRelatedConcept(concept: string): void {
    if (!concept || concept.trim().length === 0) {
      throw new Error('Concept cannot be empty');
    }

    const normalizedConcept = concept.trim().toLowerCase();
    
    if (!this.metadata.relatedConcepts.includes(normalizedConcept)) {
      this.metadata.relatedConcepts.push(normalizedConcept);
      this.updatedAt = new Date();
    }
  }

  /**
   * Flag a contradiction with another memory
   */
  flagContradiction(contradictionDescription: string): void {
    if (!contradictionDescription || contradictionDescription.trim().length === 0) {
      throw new Error('Contradiction description cannot be empty');
    }

    this.metadata.contradictionFlags.push(contradictionDescription.trim());
    this.updatedAt = new Date();
  }

  /**
   * Update vector embedding for similarity search
   */
  updateEmbedding(embedding: number[]): void {
    if (!embedding || embedding.length === 0) {
      throw new Error('Embedding cannot be empty');
    }

    this.metadata.embedding = embedding;
    this.updatedAt = new Date();
  }

  /**
   * Validate the memory (mark as validated by human or system)
   */
  validate(): void {
    this.metadata.validationStatus = 'validated';
    this.updatedAt = new Date();
  }

  /**
   * Reject the memory (mark as incorrect or irrelevant)
   */
  reject(): void {
    this.metadata.validationStatus = 'rejected';
    this.confidence = 0;
    this.updatedAt = new Date();
  }

  /**
   * Calculate memory score based on confidence, importance, and reinforcement
   */
  getMemoryScore(): number {
    const baseScore = (this.confidence + this.importance) / 2;
    const reinforcementBonus = Math.min(this.metadata.reinforcementCount * 0.1, 0.3);
    const contradictionPenalty = this.metadata.contradictionFlags.length * 0.1;
    
    return Math.max(0, Math.min(1, baseScore + reinforcementBonus - contradictionPenalty));
  }

  /**
   * Check if memory should be included in responses
   */
  isActiveMemory(): boolean {
    return this.metadata.validationStatus !== 'rejected' && 
           this.confidence > 0.3 && 
           this.getMemoryScore() > 0.4;
  }

  /**
   * Check if memory needs validation
   */
  needsValidation(): boolean {
    return this.metadata.validationStatus === 'pending' && 
           this.confidence < 0.7;
  }

  /**
   * Get age of memory in days
   */
  getAgeInDays(): number {
    return Math.floor((Date.now() - this.createdAt.getTime()) / (1000 * 60 * 60 * 24));
  }

  /**
   * Convert entity to plain object for serialization
   */
  toJSON(): Record<string, any> {
    return {
      id: this.id,
      userId: this.userId,
      type: this.type,
      content: this.content,
      confidence: this.confidence,
      importance: this.importance,
      metadata: this.metadata,
      // feedback: this.feedback, // Not part of memory entity
      createdAt: this.createdAt.toISOString(),
      updatedAt: this.updatedAt.toISOString(),
      memoryScore: this.getMemoryScore(),
      ageInDays: this.getAgeInDays(),
      isActive: this.isActiveMemory(),
      needsValidation: this.needsValidation()
    };
  }

  /**
   * Create memory entity from database record
   */
  static fromDatabaseRecord(record: any): MemoryEntity {
    const memory = new MemoryEntity(
      record.id,
      record.userId || record.user_id,
      record.type as MemoryType,
      record.content,
      record.confidence,
      record.importance,
      record.metadata || { extractedFrom: {}, topics: [], relatedConcepts: [], reinforcementCount: 1, contradictionFlags: [] },
      new Date(record.createdAt || record.created_at),
      new Date(record.updatedAt || record.updated_at)
    );

    return memory;
  }

  /**
   * Create memory from conversation extraction
   */
  static createFromExtraction(
    id: string,
    userId: string,
    type: MemoryType,
    content: string,
    extractionContext: {
      conversationId: string;
      messageId: string;
      extractionMethod: 'llm' | 'pattern' | 'explicit';
      extractionConfidence: number;
    },
    confidence: number = 0.7,
    importance: number = 0.5
  ): MemoryEntity {
    const metadata: MemoryMetadata = {
      extractedFrom: extractionContext,
      topics: [],
      relatedConcepts: [],
      reinforcementCount: 1,
      contradictionFlags: [],
      validationStatus: 'pending'
    };

    return new MemoryEntity(
      id,
      userId,
      type,
      content,
      confidence,
      importance,
      metadata
    );
  }
}