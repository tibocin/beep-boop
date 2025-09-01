# ADR-002: Memory and Relationship Architecture

## Status
**ACCEPTED** - 2024-12-19

## Context

Beep-Boop v2.0 requires sophisticated memory and relationship management to create an intelligent personal assistant that:

1. **Learns from conversations** and retains user preferences, facts, skills, goals
2. **Maps relationships** between queries, responses, prompts, context, and conversation topics
3. **Evolves understanding** through reinforcement learning and feedback
4. **Provides context-aware responses** based on historical interactions
5. **Supports prompt evolution** through embedding-based similarity and feedback

The current system has basic conversation memory but lacks:
- Persistent relationship mapping
- Embedding-based similarity search
- Feedback-driven learning
- Complex relationship types
- Multi-dimensional memory organization

## Decision

Implement a **Multi-Database Memory Architecture** using the digi-infrastructure services:

### **Database Allocation Strategy**

#### **PostgreSQL (Structured Data)**
- **Conversations**: Session metadata, timestamps, summaries
- **Messages**: Individual message content, metadata, feedback scores
- **User Profiles**: Preferences, settings, authentication data
- **Feedback**: Thumbs up/down data with detailed metadata
- **API Logs**: Request/response tracking for analytics

#### **Neo4j (Relationship Graph)**
- **Memory Nodes**: User memories (preferences, facts, skills, goals, habits)
- **Concept Nodes**: Abstract concepts, topics, themes
- **Conversation Nodes**: High-level conversation representations
- **Query/Response Nodes**: Individual query-response pairs
- **Relationship Edges**: All types of associations and connections

#### **Qdrant (Vector Embeddings)**
- **Prompt Embeddings**: Vector representations of prompts for similarity search
- **Memory Embeddings**: Vector representations of memories for semantic search
- **Context Embeddings**: Conversation context vectors for matching
- **Topic Embeddings**: Conversation topic vectors for clustering

#### **Redis (Real-time Cache)**
- **Session State**: Active conversation context and user presence
- **Processing Cache**: Temporary data during request processing
- **Rate Limiting**: API request tracking and throttling
- **Real-time Updates**: WebSocket connection management

### **Memory Data Model**

#### **Core Memory Types**
```typescript
enum MemoryType {
  PREFERENCE = 'preference',    // "I prefer dark mode"
  FACT = 'fact',              // "I work at Company X"
  SKILL = 'skill',            // "I know TypeScript"
  GOAL = 'goal',              // "I want to learn React"
  HABIT = 'habit',            // "I usually work mornings"
  INSIGHT = 'insight'         // "User struggles with async code"
}

interface Memory {
  id: string;
  userId: string;
  type: MemoryType;
  content: string;
  confidence: number;        // 0.0 - 1.0
  importance: number;        // 0.0 - 1.0
  extractedFrom: string;     // Conversation ID or source
  createdAt: Date;
  updatedAt: Date;
  embedding?: number[];      // Vector representation
  metadata: MemoryMetadata;
}
```

#### **Relationship Types**
```typescript
enum RelationshipType {
  // Memory Relationships
  REINFORCES = 'reinforces',       // Memory A reinforces Memory B
  CONTRADICTS = 'contradicts',     // Memory A contradicts Memory B
  EVOLVES_FROM = 'evolves_from',   // Memory B evolved from Memory A
  
  // Query-Response Relationships
  FOLLOWS_UP = 'follows_up',       // Query B follows up on Query A
  ANSWERS = 'answers',             // Response A answers Query B
  BUILDS_ON = 'builds_on',         // Response B builds on Response A
  
  // Topic Relationships
  RELATES_TO = 'relates_to',       // Topic A relates to Topic B
  CONTAINS = 'contains',           // Topic A contains Topic B
  TRIGGERS = 'triggers',           // Topic A triggers discussion of Topic B
  
  // Prompt Relationships
  SIMILAR_TO = 'similar_to',       // Prompt A similar to Prompt B
  IMPROVES_ON = 'improves_on',     // Prompt B improves on Prompt A
  WORKS_WITH = 'works_with'        // Prompt A works well with Context B
}

interface Relationship {
  id: string;
  sourceId: string;
  targetId: string;
  type: RelationshipType;
  strength: number;          // 0.0 - 1.0
  confidence: number;        // 0.0 - 1.0
  context: string;           // How relationship was determined
  createdAt: Date;
  metadata: RelationshipMetadata;
}
```

### **Neo4j Graph Schema**

#### **Node Types**
```cypher
// User node
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;

// Memory nodes
CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE;
CREATE INDEX memory_type IF NOT EXISTS FOR (m:Memory) ON (m.type);
CREATE INDEX memory_user IF NOT EXISTS FOR (m:Memory) ON (m.userId);

// Conversation nodes
CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE;

// Query/Response nodes
CREATE CONSTRAINT query_id IF NOT EXISTS FOR (q:Query) REQUIRE q.id IS UNIQUE;
CREATE CONSTRAINT response_id IF NOT EXISTS FOR (r:Response) REQUIRE r.id IS UNIQUE;

// Concept/Topic nodes
CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE;
CREATE INDEX concept_name IF NOT EXISTS FOR (c:Concept) ON (c.name);
```

#### **Relationship Patterns**
```cypher
// User has memories
(User)-[:HAS_MEMORY]->(Memory)

// Memories relate to each other
(Memory)-[:REINFORCES|CONTRADICTS|EVOLVES_FROM]->(Memory)

// Queries and responses
(Query)-[:PART_OF]->(Conversation)
(Response)-[:ANSWERS]->(Query)
(Response)-[:BUILDS_ON]->(Response)

// Topic associations
(Memory)-[:RELATES_TO]->(Concept)
(Conversation)-[:DISCUSSES]->(Concept)
(Concept)-[:CONTAINS|RELATES_TO]->(Concept)
```

### **Vector Embedding Strategy**

#### **Qdrant Collections**
```typescript
const QdrantCollections = {
  PROMPTS: 'beep_boop_prompts',
  MEMORIES: 'beep_boop_memories', 
  CONTEXTS: 'beep_boop_contexts',
  TOPICS: 'beep_boop_topics'
} as const;

interface VectorPayload {
  id: string;
  type: string;
  content: string;
  metadata: Record<string, any>;
  timestamp: string;
}
```

#### **Similarity Search**
```typescript
class EmbeddingService {
  async findSimilarPrompts(query: string, limit = 5): Promise<SimilarPrompt[]> {
    // Search prompt embeddings for similar templates
  }
  
  async findRelatedMemories(memory: Memory, limit = 10): Promise<RelatedMemory[]> {
    // Find semantically similar memories
  }
  
  async clusterConversationTopics(conversationId: string): Promise<TopicCluster[]> {
    // Group conversation content by semantic similarity
  }
}
```

## Rationale

### **Why Multi-Database Approach?**

1. **Optimal Data Models**: Each database optimized for specific data patterns
   - **PostgreSQL**: ACID compliance for critical data (conversations, users)
   - **Neo4j**: Graph traversal for complex relationships
   - **Qdrant**: High-performance vector similarity search
   - **Redis**: Sub-millisecond access for real-time features

2. **Scalability**: Each database can be scaled independently based on usage patterns
3. **Performance**: Specialized indexes and query optimization per data type
4. **Consistency**: Strong consistency where needed, eventual consistency where appropriate

### **Why Graph-Based Memory Model?**

1. **Natural Relationships**: Human memory is inherently graph-based
2. **Traversal Queries**: Find related memories through relationship paths
3. **Contextual Understanding**: Understand how concepts connect and influence each other
4. **Learning Opportunities**: Identify knowledge gaps and reinforcement patterns

### **Why Vector Embeddings for Prompts?**

1. **Semantic Similarity**: Find prompts that work for similar contexts
2. **Evolution Tracking**: Measure how prompts improve over time
3. **Automatic Optimization**: Suggest better prompts based on similarity and feedback
4. **Context Matching**: Match prompts to conversation context automatically

## Implementation Details

### **Memory Extraction Pipeline**
```typescript
class MemoryExtractor {
  async extractFromConversation(
    conversation: Conversation
  ): Promise<ExtractedMemory[]> {
    // 1. Use PCS to generate memory extraction prompt
    // 2. Process conversation with LLM to identify new information
    // 3. Create memory nodes in Neo4j
    // 4. Generate embeddings and store in Qdrant
    // 5. Create relationships based on context
  }
}
```

### **Relationship Discovery**
```typescript
class RelationshipMapper {
  async discoverRelationships(
    newMemory: Memory,
    existingMemories: Memory[]
  ): Promise<Relationship[]> {
    // 1. Semantic similarity via embeddings
    // 2. Logical analysis via LLM reasoning
    // 3. Temporal analysis (conversation flow)
    // 4. Reinforcement/contradiction detection
  }
}
```

### **Feedback Integration**
```typescript
class FeedbackProcessor {
  async processFeedback(feedback: UserFeedback): Promise<void> {
    // 1. Store feedback in PostgreSQL
    // 2. Update relationship strengths in Neo4j
    // 3. Trigger prompt evolution in PCS
    // 4. Update confidence scores for related memories
  }
}
```

## Performance Considerations

### **Query Optimization**
- **Neo4j**: Index on userId, memory type, and relationship types
- **Qdrant**: Optimize vector dimensions and search parameters
- **PostgreSQL**: Proper indexing on conversation and message lookups
- **Redis**: TTL policies for temporary data and cache invalidation

### **Caching Strategy**
- **Hot Memories**: Frequently accessed memories cached in Redis
- **Prompt Templates**: Cache generated prompts with TTL
- **Relationship Paths**: Cache common relationship traversals
- **Embeddings**: Cache vector search results for similar queries

### **Consistency Patterns**
- **Eventual Consistency**: Memory relationships can be updated asynchronously
- **Strong Consistency**: Critical user data (conversations, feedback) uses transactions
- **Event Sourcing**: Track memory evolution through event logs
- **Compensation**: Rollback patterns for failed multi-database transactions

## Testing Strategy

### **Unit Tests**
- Individual adapter functionality
- Memory extraction logic
- Relationship discovery algorithms
- Vector similarity calculations

### **Integration Tests**
- Multi-database consistency
- Cross-service communication
- End-to-end memory creation and retrieval
- Feedback processing workflows

### **Performance Tests**
- Vector search performance under load
- Graph traversal query optimization
- Concurrent user memory access
- Real-time streaming throughput

## Monitoring & Observability

### **Key Metrics**
- **Memory Creation Rate**: New memories per conversation
- **Relationship Discovery**: New relationships discovered per session
- **Feedback Processing**: User feedback processing time and accuracy
- **Query Performance**: Response time for memory/relationship queries
- **Data Consistency**: Cross-database synchronization success rate

### **Alerts**
- **Memory Extraction Failures**: When conversation analysis fails
- **Relationship Inconsistencies**: When graph data becomes inconsistent
- **Embedding Performance**: When vector searches become slow
- **Cache Miss Rate**: When Redis cache performance degrades

---

**This architecture creates a sophisticated memory system that enables Beep-Boop to truly learn and evolve as a personal AI assistant, building rich contextual understanding through multi-dimensional relationship mapping.**