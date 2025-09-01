# ADR-001: Integration Architecture for Multi-API System

## Status
**ACCEPTED** - 2024-12-19

## Context

Beep-Boop v2.0 must integrate with multiple external services to provide a comprehensive conversational AI experience:

1. **Digi-Core** (port 2000): Knowledge butler with RAG capabilities
2. **PCS** (port 8000): Personal Context System for dynamic prompts  
3. **Digi-Infrastructure**: PostgreSQL + Neo4j + Qdrant + Redis
4. **Lernmi** (future): Learning system for feedback and improvement
5. **LLM Services**: Ollama (primary) + OpenAI/Anthropic/GROK (fallback)
6. **Voice Services**: OpenAI Whisper (STT) + ElevenLabs (TTS)

Each service has different reliability requirements, rate limits, and error patterns. We need a robust integration architecture that provides:
- **Resilience**: Circuit breakers, retries, timeouts
- **Observability**: Tracing, metrics, structured logging
- **Maintainability**: Clear adapter patterns and contracts
- **Performance**: Caching, connection pooling, async processing

## Decision

Implement a **Layered Adapter Architecture** with the following patterns:

### **1. Service Layer Architecture**

```typescript
// Domain Layer (pure business logic)
interface ConversationService {
  processMessage(input: ProcessMessageRequest): Promise<ProcessMessageResponse>;
}

// Application Layer (orchestration)
interface MessageOrchestrator {
  handleUserMessage(message: UserMessage): Promise<AssistantResponse>;
}

// Adapter Layer (external integrations)
interface DigiCoreAdapter {
  queryKnowledge(query: KnowledgeQuery): Promise<KnowledgeResult>;
}
```

### **2. Resilience Patterns**

#### **Circuit Breaker Pattern**
```typescript
class CircuitBreaker {
  private failureCount = 0;
  private lastFailureTime?: Date;
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  
  async execute<T>(operation: () => Promise<T>): Promise<T> {
    // Implementation with exponential backoff
  }
}
```

#### **Retry with Jitter**
```typescript
interface RetryConfig {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  jitterFactor: number;
}

class RetryHandler {
  async executeWithRetry<T>(
    operation: () => Promise<T>,
    config: RetryConfig
  ): Promise<T> {
    // Implementation with exponential backoff + jitter
  }
}
```

### **3. Adapter Pattern Implementation**

#### **Base Adapter Interface**
```typescript
interface BaseAdapter {
  name: string;
  healthCheck(): Promise<boolean>;
  getMetrics(): AdapterMetrics;
}

interface AdapterMetrics {
  successRate: number;
  averageLatency: number;
  circuitBreakerState: string;
  lastError?: Error;
}
```

#### **Specific Adapters**

**Digi-Core Adapter:**
```typescript
class DigiCoreAdapter implements BaseAdapter {
  private circuitBreaker: CircuitBreaker;
  private retryHandler: RetryHandler;
  
  async queryKnowledge(query: KnowledgeQuery): Promise<KnowledgeResult> {
    return this.circuitBreaker.execute(() =>
      this.retryHandler.executeWithRetry(() =>
        this.makeKnowledgeRequest(query)
      )
    );
  }
}
```

**PCS Adapter:**
```typescript
class PCSAdapter implements BaseAdapter {
  async generatePrompt(request: PromptRequest): Promise<GeneratedPrompt> {
    // Dynamic prompt generation with context
  }
  
  async evolvePrompt(feedback: PromptFeedback): Promise<EvolvedPrompt> {
    // Prompt optimization based on user feedback
  }
}
```

### **4. Streaming Architecture**

#### **Multi-Layer Streaming**
```typescript
interface StreamLayer {
  // Layer 1: LLM Token Streaming
  streamLLMTokens(request: LLMRequest): AsyncGenerator<TokenChunk>;
  
  // Layer 2: Agent Processing Streaming  
  streamProcessingSteps(request: ProcessingRequest): AsyncGenerator<ProcessingStep>;
  
  // Layer 3: Knowledge Retrieval Streaming
  streamKnowledgeRetrieval(query: string): AsyncGenerator<KnowledgeChunk>;
}

enum ProcessingStep {
  PARSING = 'parsing',
  KNOWLEDGE_RETRIEVAL = 'knowledge_retrieval',
  PROMPT_GENERATION = 'prompt_generation',
  LLM_PROCESSING = 'llm_processing',
  RESPONSE_SYNTHESIS = 'response_synthesis',
  MEMORY_STORAGE = 'memory_storage'
}
```

#### **WebSocket Event System**
```typescript
interface WebSocketEvents {
  // Client → Server
  'user_message': UserMessageEvent;
  'voice_input': VoiceInputEvent;
  'feedback': FeedbackEvent;
  
  // Server → Client
  'processing_step': ProcessingStepEvent;
  'token_chunk': TokenChunkEvent;
  'response_complete': ResponseCompleteEvent;
  'error': ErrorEvent;
}
```

### **5. Data Flow Architecture**

#### **Request Processing Pipeline**
```
User Input
    ↓
[1] Input Parsing & Validation
    ↓
[2] Context Retrieval (PCS)
    ↓
[3] Knowledge Query (Digi-Core)
    ↓
[4] Prompt Generation (PCS)
    ↓
[5] LLM Processing (Ollama/OpenAI)
    ↓
[6] Response Synthesis
    ↓
[7] Memory Extraction & Storage (Neo4j)
    ↓
[8] Feedback Collection
    ↓
Final Response
```

#### **Streaming Events**
Each step emits streaming events to provide real-time visibility:
- Processing step updates
- Knowledge retrieval progress
- LLM token generation
- Memory relationship creation

## Rationale

### **Why Layered Adapter Architecture?**

1. **Separation of Concerns**: Clear boundaries between business logic and external services
2. **Testability**: Each adapter can be mocked and tested independently
3. **Resilience**: Circuit breakers and retries contained within adapters
4. **Observability**: Centralized metrics and logging per adapter
5. **Maintainability**: Changes to external APIs isolated to specific adapters

### **Why Multi-Layer Streaming?**

1. **User Experience**: Users see progress throughout the entire pipeline
2. **Debugging**: Real-time visibility into system behavior
3. **Performance**: Non-blocking processing with immediate feedback
4. **Scalability**: Efficient resource utilization with async streams

### **Why WebSocket-First Design?**

1. **Real-time Requirements**: Voice and streaming need low-latency communication
2. **Bi-directional**: Support for real-time feedback and corrections
3. **Connection Efficiency**: Single persistent connection vs multiple HTTP requests
4. **Event-Driven**: Natural fit for streaming and state updates

## Implementation Plan

### **Phase 1: Core Infrastructure**
1. Express.js server with TypeScript setup
2. Socket.io WebSocket infrastructure
3. Basic health endpoints and observability
4. Docker development environment

### **Phase 2: Adapter Layer**
1. Base adapter interfaces and implementations
2. Digi-Core adapter with circuit breaker and retry
3. PCS adapter for dynamic prompt generation
4. Database adapters for PostgreSQL and Neo4j

### **Phase 3: Streaming Pipeline**
1. Processing step streaming implementation
2. LLM token streaming integration
3. Knowledge retrieval streaming
4. WebSocket event system

### **Phase 4: Frontend Integration**
1. React components for real-time chat
2. WebSocket client integration
3. Voice input/output components
4. PWA service worker implementation

## Consequences

### **Positive**
- ✅ **Modern Web Standards**: Full support for PWA, WebSockets, Service Workers
- ✅ **Real-time Capabilities**: Native streaming and event-driven architecture
- ✅ **Mobile Experience**: Responsive design and PWA features
- ✅ **Developer Experience**: Excellent tooling and debugging capabilities
- ✅ **Scalability**: Better handling of concurrent users and real-time features
- ✅ **Maintainability**: Clear architectural boundaries and type safety

### **Negative**
- ❌ **Migration Complexity**: Significant effort to rewrite core components
- ❌ **Learning Curve**: Team needs TypeScript/Node.js expertise
- ❌ **Initial Setup**: More complex infrastructure vs simple Python script

### **Risk Mitigation**
- **Incremental Migration**: Build new system in parallel, migrate gradually
- **Comprehensive Testing**: Unit, integration, and E2E tests throughout
- **Documentation**: Detailed docs for each component and integration
- **Monitoring**: Observability from day one to catch issues early

## Alternatives Considered

### **Option 1: Enhance Python/Gradio** ❌
- **Pros**: Minimal changes, preserve existing code
- **Cons**: Limited web capabilities, poor streaming, no PWA support
- **Verdict**: Rejected - doesn't meet requirements

### **Option 2: Python Backend + React Frontend** ⚠️
- **Pros**: Preserve backend logic, modern frontend
- **Cons**: Complex API boundaries, dual language maintenance, limited real-time capabilities
- **Verdict**: Considered but rejected - prefer unified stack

### **Option 3: Full TypeScript/Node.js** ✅
- **Pros**: Unified stack, excellent web support, native streaming
- **Cons**: Migration effort, new technology adoption
- **Verdict**: **SELECTED** - best alignment with requirements

## References

- [Integration Guide Documentation](../integration-guide.md)
- [Beep-Boop Integration Specifications](../digi-core/INTEGRATIONS/BEEP_BOOP_INTEGRATION_GUIDE.md)
- [Express.js Best Practices](https://expressjs.com/en/advanced/best-practice-performance.html)
- [Socket.io Documentation](https://socket.io/docs/v4/)
- [Next.js PWA Guide](https://nextjs.org/docs/app/building-your-application/configuring/progressive-web-apps)

---

**This architecture provides the foundation for a production-ready, scalable conversational AI system with modern web capabilities and robust external service integration.**