/**
 * src/infrastructure/database/neo4j.service.ts - Neo4j Graph Database Service
 * 
 * Service for managing graph relationships in Neo4j including memory storage,
 * relationship mapping, and semantic graph operations for Beep-Boop.
 * 
 * Related Components:
 * - Memory entities and relationship management
 * - Conversation topic clustering and analysis
 * - Query-response relationship tracking
 * - Semantic similarity and graph traversal
 * 
 * Tags: #neo4j #graph #relationships #memory #traversal
 */

import { Session } from 'neo4j-driver';
import { DatabaseConnection } from './connection';
import { MemoryEntity, MemoryType } from '@/domain/entities/memory.entity';
import { logger, createContextualLogger } from '@/infrastructure/logging';

/**
 * Relationship types for graph database
 */
export enum RelationshipType {
  // Memory relationships
  REINFORCES = 'REINFORCES',
  CONTRADICTS = 'CONTRADICTS', 
  EVOLVES_FROM = 'EVOLVES_FROM',
  RELATES_TO = 'RELATES_TO',
  
  // Query-Response relationships
  FOLLOWS_UP = 'FOLLOWS_UP',
  ANSWERS = 'ANSWERS',
  BUILDS_ON = 'BUILDS_ON',
  
  // Topic relationships
  DISCUSSES = 'DISCUSSES',
  CONTAINS = 'CONTAINS',
  TRIGGERS = 'TRIGGERS',
  
  // User relationships
  HAS_MEMORY = 'HAS_MEMORY',
  PARTICIPATES_IN = 'PARTICIPATES_IN',
  
  // Concept relationships
  SIMILAR_TO = 'SIMILAR_TO',
  IMPROVES_ON = 'IMPROVES_ON',
  WORKS_WITH = 'WORKS_WITH'
}

/**
 * Graph node types
 */
export enum NodeType {
  USER = 'User',
  MEMORY = 'Memory',
  CONVERSATION = 'Conversation',
  MESSAGE = 'Message',
  CONCEPT = 'Concept',
  TOPIC = 'Topic',
  PROMPT = 'Prompt'
}

/**
 * Relationship data structure
 */
export interface GraphRelationship {
  sourceId: string;
  targetId: string;
  type: RelationshipType;
  strength: number; // 0.0 - 1.0
  confidence: number; // 0.0 - 1.0
  context: string;
  metadata?: Record<string, any>;
  createdAt: Date;
}

/**
 * Memory graph data for Neo4j storage
 */
export interface MemoryGraphData {
  id: string;
  userId: string;
  type: MemoryType;
  content: string;
  confidence: number;
  importance: number;
  topics: string[];
  relatedConcepts: string[];
  extractedFrom: {
    conversationId: string;
    messageId: string;
  };
  createdAt: Date;
}

/**
 * Graph traversal result
 */
export interface GraphTraversalResult {
  nodes: Array<{
    id: string;
    type: NodeType;
    properties: Record<string, any>;
  }>;
  relationships: Array<{
    id: string;
    type: RelationshipType;
    source: string;
    target: string;
    properties: Record<string, any>;
  }>;
  paths: Array<{
    length: number;
    nodes: string[];
    relationships: string[];
  }>;
}

/**
 * Neo4j graph database service
 * 
 * Provides high-level operations for managing the Beep-Boop knowledge graph
 * including memory storage, relationship discovery, and semantic traversal.
 */
export class Neo4jService {
  private contextLogger = createContextualLogger({ operation: 'neo4j-service' });

  /**
   * Initialize Neo4j schema and constraints
   * 
   * Sets up indexes, constraints, and initial graph structure.
   */
  async initializeSchema(): Promise<void> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      this.contextLogger.info('Initializing Neo4j schema...');

      // Create constraints for unique identifiers
      const constraints = [
        'CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE',
        'CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE',
        'CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE',
        'CREATE CONSTRAINT message_id IF NOT EXISTS FOR (msg:Message) REQUIRE msg.id IS UNIQUE',
        'CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (con:Concept) REQUIRE con.id IS UNIQUE'
      ];

      for (const constraint of constraints) {
        try {
          await session.run(constraint);
        } catch (error) {
          // Constraint might already exist
          this.contextLogger.debug('Constraint creation skipped (might exist)', { constraint });
        }
      }

      // Create indexes for performance
      const indexes = [
        'CREATE INDEX memory_type IF NOT EXISTS FOR (m:Memory) ON (m.type)',
        'CREATE INDEX memory_user IF NOT EXISTS FOR (m:Memory) ON (m.userId)',
        'CREATE INDEX memory_confidence IF NOT EXISTS FOR (m:Memory) ON (m.confidence)',
        'CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name)',
        'CREATE INDEX conversation_user IF NOT EXISTS FOR (c:Conversation) ON (c.userId)'
      ];

      for (const index of indexes) {
        try {
          await session.run(index);
        } catch (error) {
          // Index might already exist
          this.contextLogger.debug('Index creation skipped (might exist)', { index });
        }
      }

      this.contextLogger.info('✅ Neo4j schema initialization complete');

    } catch (error) {
      this.contextLogger.error('Neo4j schema initialization failed', error);
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Store memory in Neo4j graph
   * 
   * Creates memory node and establishes relationships with user and concepts.
   */
  async storeMemory(memory: MemoryEntity): Promise<void> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      const memoryData: MemoryGraphData = {
        id: memory.id,
        userId: memory.userId,
        type: memory.type,
        content: memory.content,
        confidence: memory.confidence,
        importance: memory.importance,
        topics: memory.metadata.topics || [],
        relatedConcepts: memory.metadata.relatedConcepts || [],
        extractedFrom: memory.metadata.extractedFrom,
        createdAt: memory.createdAt
      };

      // Create memory node and relationship with user
      await session.run(`
        MERGE (u:User {id: $userId})
        MERGE (m:Memory {id: $memoryId})
        SET m.type = $type,
            m.content = $content,
            m.confidence = $confidence,
            m.importance = $importance,
            m.topics = $topics,
            m.relatedConcepts = $relatedConcepts,
            m.extractedFrom = $extractedFrom,
            m.createdAt = $createdAt,
            m.updatedAt = datetime()
        MERGE (u)-[:HAS_MEMORY]->(m)
      `, {
        userId: memoryData.userId,
        memoryId: memoryData.id,
        type: memoryData.type,
        content: memoryData.content,
        confidence: memoryData.confidence,
        importance: memoryData.importance,
        topics: memoryData.topics,
        relatedConcepts: memoryData.relatedConcepts,
        extractedFrom: memoryData.extractedFrom,
        createdAt: memoryData.createdAt.toISOString()
      });

      // Create concept nodes and relationships
      for (const concept of memoryData.relatedConcepts) {
        await session.run(`
          MATCH (m:Memory {id: $memoryId})
          MERGE (c:Concept {name: $conceptName})
          SET c.updatedAt = datetime()
          MERGE (m)-[:RELATES_TO]->(c)
        `, {
          memoryId: memoryData.id,
          conceptName: concept
        });
      }

      this.contextLogger.info('Memory stored in Neo4j', {
        memoryId: memory.id,
        type: memory.type,
        conceptCount: memoryData.relatedConcepts.length
      });

    } catch (error) {
      this.contextLogger.error('Failed to store memory in Neo4j', error, {
        memoryId: memory.id
      });
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Create relationship between two entities
   * 
   * Establishes typed relationships between graph nodes with metadata.
   */
  async createRelationship(relationship: GraphRelationship): Promise<void> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      await session.run(`
        MATCH (source {id: $sourceId})
        MATCH (target {id: $targetId})
        MERGE (source)-[r:${relationship.type}]->(target)
        SET r.strength = $strength,
            r.confidence = $confidence,
            r.context = $context,
            r.metadata = $metadata,
            r.createdAt = $createdAt,
            r.updatedAt = datetime()
      `, {
        sourceId: relationship.sourceId,
        targetId: relationship.targetId,
        strength: relationship.strength,
        confidence: relationship.confidence,
        context: relationship.context,
        metadata: relationship.metadata || {},
        createdAt: relationship.createdAt.toISOString()
      });

      this.contextLogger.info('Relationship created', {
        type: relationship.type,
        sourceId: relationship.sourceId,
        targetId: relationship.targetId,
        strength: relationship.strength
      });

    } catch (error) {
      this.contextLogger.error('Failed to create relationship', error, {
        type: relationship.type,
        sourceId: relationship.sourceId,
        targetId: relationship.targetId
      });
      throw error;
    } finally {
      await session.close();
    }
  }

  /**
   * Find related memories using graph traversal
   * 
   * Discovers memories related to a given memory through various relationship types.
   */
  async findRelatedMemories(
    memoryId: string, 
    maxDepth: number = 2, 
    minStrength: number = 0.3
  ): Promise<MemoryEntity[]> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      const result = await session.run(`
        MATCH (m:Memory {id: $memoryId})
        MATCH (m)-[r*1..${maxDepth}]-(related:Memory)
        WHERE ALL(rel IN r WHERE rel.strength >= $minStrength)
        RETURN DISTINCT related
        ORDER BY related.importance DESC, related.confidence DESC
        LIMIT 20
      `, {
        memoryId,
        minStrength
      });

      const memories = result.records.map(record => {
        const memoryNode = record.get('related');
        return this.nodeToMemoryEntity(memoryNode);
      });

      this.contextLogger.info('Found related memories', {
        memoryId,
        relatedCount: memories.length,
        maxDepth,
        minStrength
      });

      return memories;

    } catch (error) {
      this.contextLogger.error('Failed to find related memories', error, { memoryId });
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * Find memories by topic or concept
   * 
   * Searches for memories related to specific topics or concepts.
   */
  async findMemoriesByTopic(
    userId: string, 
    topic: string, 
    limit: number = 10
  ): Promise<MemoryEntity[]> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      const result = await session.run(`
        MATCH (u:User {id: $userId})-[:HAS_MEMORY]->(m:Memory)
        WHERE $topic IN m.topics OR $topic IN m.relatedConcepts
           OR m.content CONTAINS $topic
        RETURN m
        ORDER BY m.importance DESC, m.confidence DESC
        LIMIT $limit
      `, {
        userId,
        topic: topic.toLowerCase(),
        limit
      });

      const memories = result.records.map(record => {
        const memoryNode = record.get('m');
        return this.nodeToMemoryEntity(memoryNode);
      });

      this.contextLogger.info('Found memories by topic', {
        userId,
        topic,
        memoryCount: memories.length
      });

      return memories;

    } catch (error) {
      this.contextLogger.error('Failed to find memories by topic', error, { userId, topic });
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * Discover new relationships between memories
   * 
   * Analyzes memory content and metadata to automatically discover relationships.
   */
  async discoverRelationships(
    newMemory: MemoryEntity,
    existingMemories: MemoryEntity[]
  ): Promise<GraphRelationship[]> {
    const relationships: GraphRelationship[] = [];

    try {
      // Find concept overlaps (RELATES_TO relationships)
      for (const existing of existingMemories) {
        const sharedConcepts = this.findSharedConcepts(newMemory, existing);
        
        if (sharedConcepts.length > 0) {
          const strength = Math.min(sharedConcepts.length * 0.2, 1.0);
          
          relationships.push({
            sourceId: newMemory.id,
            targetId: existing.id,
            type: RelationshipType.RELATES_TO,
            strength,
            confidence: 0.8,
            context: `Shared concepts: ${sharedConcepts.join(', ')}`,
            metadata: { sharedConcepts },
            createdAt: new Date()
          });
        }
      }

      // Find contradictions (CONTRADICTS relationships)
      const contradictions = this.findContradictions(newMemory, existingMemories);
      relationships.push(...contradictions);

      // Find reinforcements (REINFORCES relationships) 
      const reinforcements = this.findReinforcements(newMemory, existingMemories);
      relationships.push(...reinforcements);

      this.contextLogger.info('Discovered relationships', {
        memoryId: newMemory.id,
        relationshipCount: relationships.length
      });

      return relationships;

    } catch (error) {
      this.contextLogger.error('Relationship discovery failed', error, {
        memoryId: newMemory.id
      });
      return [];
    }
  }

  /**
   * Get conversation topic clusters
   * 
   * Analyzes conversation content to identify and cluster related topics.
   */
  async getConversationTopics(
    userId: string,
    timeRange?: { start: Date; end: Date }
  ): Promise<Array<{
    topic: string;
    memoryCount: number;
    strength: number;
    relatedTopics: string[];
  }>> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      let timeFilter = '';
      const params: any = { userId };

      if (timeRange) {
        timeFilter = 'AND m.createdAt >= $startDate AND m.createdAt <= $endDate';
        params.startDate = timeRange.start.toISOString();
        params.endDate = timeRange.end.toISOString();
      }

      const result = await session.run(`
        MATCH (u:User {id: $userId})-[:HAS_MEMORY]->(m:Memory)
        ${timeFilter}
        UNWIND m.topics as topic
        WITH topic, collect(m) as memories
        RETURN topic,
               size(memories) as memoryCount,
               avg([memory IN memories | memory.importance]) as avgImportance,
               collect(DISTINCT [concept IN memories[0].relatedConcepts | concept][0..3]) as relatedConcepts
        ORDER BY memoryCount DESC, avgImportance DESC
        LIMIT 20
      `, params);

      const topics = result.records.map(record => ({
        topic: record.get('topic'),
        memoryCount: record.get('memoryCount').toNumber(),
        strength: record.get('avgImportance'),
        relatedTopics: record.get('relatedConcepts').flat().filter((c: string) => c)
      }));

      this.contextLogger.info('Retrieved conversation topics', {
        userId,
        topicCount: topics.length,
        hasTimeRange: !!timeRange
      });

      return topics;

    } catch (error) {
      this.contextLogger.error('Failed to get conversation topics', error, { userId });
      return [];
    } finally {
      await session.close();
    }
  }

  /**
   * Find memory evolution chains
   * 
   * Traces how memories evolve and change over time through conversation.
   */
  async findMemoryEvolution(memoryId: string): Promise<{
    evolutionChain: MemoryEntity[];
    branchPoints: Array<{ memoryId: string; branches: string[] }>;
  }> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      // Find evolution chain
      const evolutionResult = await session.run(`
        MATCH path = (start:Memory {id: $memoryId})<-[:EVOLVES_FROM*]-(evolved:Memory)
        RETURN nodes(path) as evolutionNodes
        ORDER BY length(path) DESC
        LIMIT 1
      `, { memoryId });

      let evolutionChain: MemoryEntity[] = [];
      if (evolutionResult.records.length > 0) {
        const nodes = evolutionResult.records[0].get('evolutionNodes');
        evolutionChain = nodes.map((node: any) => this.nodeToMemoryEntity(node));
      }

      // Find branch points
      const branchResult = await session.run(`
        MATCH (m:Memory {id: $memoryId})
        MATCH (m)<-[:EVOLVES_FROM]-(branches:Memory)
        RETURN m.id as memoryId, collect(branches.id) as branchIds
      `, { memoryId });

      const branchPoints = branchResult.records.map(record => ({
        memoryId: record.get('memoryId'),
        branches: record.get('branchIds')
      }));

      return { evolutionChain, branchPoints };

    } catch (error) {
      this.contextLogger.error('Failed to find memory evolution', error, { memoryId });
      return { evolutionChain: [], branchPoints: [] };
    } finally {
      await session.close();
    }
  }

  /**
   * Get user memory statistics
   * 
   * Provides insights into user's memory patterns and relationship density.
   */
  async getUserMemoryStats(userId: string): Promise<{
    totalMemories: number;
    memoriesByType: Record<MemoryType, number>;
    totalRelationships: number;
    averageConfidence: number;
    topConcepts: Array<{ concept: string; count: number }>;
  }> {
    const session = DatabaseConnection.createNeo4jSession();
    
    try {
      const result = await session.run(`
        MATCH (u:User {id: $userId})-[:HAS_MEMORY]->(m:Memory)
        OPTIONAL MATCH (m)-[r]-()
        RETURN 
          count(DISTINCT m) as totalMemories,
          collect(DISTINCT m.type) as types,
          count(DISTINCT r) as totalRelationships,
          avg(m.confidence) as avgConfidence,
          apoc.map.groupByMulti(
            [memory IN collect(m) | memory.relatedConcepts], 
            null
          ) as concepts
      `, { userId });

      if (result.records.length === 0) {
        return {
          totalMemories: 0,
          memoriesByType: {} as Record<MemoryType, number>,
          totalRelationships: 0,
          averageConfidence: 0,
          topConcepts: []
        };
      }

      const record = result.records[0];
      
      // Count memories by type
      const typeCountResult = await session.run(`
        MATCH (u:User {id: $userId})-[:HAS_MEMORY]->(m:Memory)
        RETURN m.type as type, count(m) as count
      `, { userId });

      const memoriesByType: Record<string, number> = {};
      typeCountResult.records.forEach(r => {
        memoriesByType[r.get('type')] = r.get('count').toNumber();
      });

      return {
        totalMemories: record.get('totalMemories').toNumber(),
        memoriesByType: memoriesByType as Record<MemoryType, number>,
        totalRelationships: record.get('totalRelationships').toNumber(),
        averageConfidence: record.get('avgConfidence') || 0,
        topConcepts: [] // TODO: Implement concept counting
      };

    } catch (error) {
      this.contextLogger.error('Failed to get user memory stats', error, { userId });
      return {
        totalMemories: 0,
        memoriesByType: {} as Record<MemoryType, number>,
        totalRelationships: 0,
        averageConfidence: 0,
        topConcepts: []
      };
    } finally {
      await session.close();
    }
  }

  /**
   * Helper methods for relationship discovery
   */

  private findSharedConcepts(memory1: MemoryEntity, memory2: MemoryEntity): string[] {
    const concepts1 = new Set(memory1.metadata.relatedConcepts || []);
    const concepts2 = new Set(memory2.metadata.relatedConcepts || []);
    
    return Array.from(concepts1).filter(concept => concepts2.has(concept));
  }

  private findContradictions(
    newMemory: MemoryEntity, 
    existingMemories: MemoryEntity[]
  ): GraphRelationship[] {
    const contradictions: GraphRelationship[] = [];

    for (const existing of existingMemories) {
      // Simple contradiction detection based on opposing keywords
      const contradictionSignals = this.detectContradiction(newMemory.content, existing.content);
      
      if (contradictionSignals.isContradiction) {
        contradictions.push({
          sourceId: newMemory.id,
          targetId: existing.id,
          type: RelationshipType.CONTRADICTS,
          strength: contradictionSignals.strength,
          confidence: contradictionSignals.confidence,
          context: contradictionSignals.reason,
          createdAt: new Date()
        });
      }
    }

    return contradictions;
  }

  private findReinforcements(
    newMemory: MemoryEntity,
    existingMemories: MemoryEntity[]
  ): GraphRelationship[] {
    const reinforcements: GraphRelationship[] = [];

    for (const existing of existingMemories) {
      // Simple reinforcement detection based on similar content
      const reinforcementSignals = this.detectReinforcement(newMemory.content, existing.content);
      
      if (reinforcementSignals.isReinforcement) {
        reinforcements.push({
          sourceId: newMemory.id,
          targetId: existing.id,
          type: RelationshipType.REINFORCES,
          strength: reinforcementSignals.strength,
          confidence: reinforcementSignals.confidence,
          context: reinforcementSignals.reason,
          createdAt: new Date()
        });
      }
    }

    return reinforcements;
  }

  private detectContradiction(content1: string, content2: string): {
    isContradiction: boolean;
    strength: number;
    confidence: number;
    reason: string;
  } {
    // Simple keyword-based contradiction detection
    const oppositeWords = [
      ['like', 'dislike'], ['love', 'hate'], ['prefer', 'avoid'],
      ['good', 'bad'], ['yes', 'no'], ['true', 'false']
    ];

    for (const [word1, word2] of oppositeWords) {
      if ((content1.toLowerCase().includes(word1) && content2.toLowerCase().includes(word2)) ||
          (content1.toLowerCase().includes(word2) && content2.toLowerCase().includes(word1))) {
        return {
          isContradiction: true,
          strength: 0.7,
          confidence: 0.6,
          reason: `Opposite expressions: ${word1} vs ${word2}`
        };
      }
    }

    return { isContradiction: false, strength: 0, confidence: 0, reason: '' };
  }

  private detectReinforcement(content1: string, content2: string): {
    isReinforcement: boolean;
    strength: number;
    confidence: number;
    reason: string;
  } {
    // Simple similarity-based reinforcement detection
    const words1 = new Set(content1.toLowerCase().split(/\s+/));
    const words2 = new Set(content2.toLowerCase().split(/\s+/));
    
    const intersection = new Set([...words1].filter(word => words2.has(word)));
    const union = new Set([...words1, ...words2]);
    
    const similarity = intersection.size / union.size;
    
    if (similarity > 0.3) {
      return {
        isReinforcement: true,
        strength: similarity,
        confidence: 0.7,
        reason: `Content similarity: ${(similarity * 100).toFixed(1)}%`
      };
    }

    return { isReinforcement: false, strength: 0, confidence: 0, reason: '' };
  }

  /**
   * Convert Neo4j node to MemoryEntity
   */
  private nodeToMemoryEntity(node: any): MemoryEntity {
    const props = node.properties;
    
    return MemoryEntity.fromDatabaseRecord({
      id: props.id,
      userId: props.userId,
      type: props.type,
      content: props.content,
      confidence: props.confidence,
      importance: props.importance,
      metadata: {
        extractedFrom: props.extractedFrom,
        topics: props.topics || [],
        relatedConcepts: props.relatedConcepts || [],
        reinforcementCount: 1,
        contradictionFlags: [],
        validationStatus: 'pending'
      },
      createdAt: props.createdAt,
      updatedAt: props.updatedAt
    });
  }
}

/**
 * Singleton instance for application-wide use
 */
export const neo4jService = new Neo4jService();