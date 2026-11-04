# 🤖 Beep-Boop v2.0 - Personal AI Assistant

> **Multi-modal conversational AI with dynamic prompts, knowledge integration, and relationship management**

## 🎯 Overview

Beep-Boop v2.0 is a sophisticated personal AI assistant that serves as your digital twin for professional networking, creative collaboration, and intelligent automation. It integrates multiple AI services to provide context-aware, personalized responses with advanced memory and relationship management.

### **🌟 Key Features**

- **🗣️ Multi-Modal Interaction**: Text, voice, and eventually image/video support
- **🧠 Dynamic Knowledge**: RAG-powered responses using personal knowledge base  
- **🎭 Adaptive Prompts**: Context-aware prompt generation and evolution
- **💾 Smart Memory**: Relationship mapping between conversations, topics, and concepts
- **📱 Progressive Web App**: Mobile-optimized with offline capabilities
- **⚡ Real-Time Streaming**: Live response generation and processing visibility
- **👍 Learning System**: Feedback collection and continuous improvement
- **🔄 API Integration**: Extensible architecture for learning systems

## 🏗️ Architecture

### **System Overview**
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Beep-Boop     │  │   Digi-Core     │  │   PCS Service   │
│   Web App/PWA   │──┤   (Knowledge    │──┤   (Dynamic      │
│   (Port 3000)   │  │    Butler)      │  │    Prompts)     │
└─────────────────┘  │   (Port 2000)   │  │   (Port 8000)   │
          │          └─────────────────┘  └─────────────────┘
          │                      │
          │              ┌─────────────────┐
          │              │ Digi-Infra      │
          │              │ - PostgreSQL    │
          │              │ - Neo4j Graph   │
          │              │ - Qdrant Vector │
          │              │ - Redis Cache   │
          │              └─────────────────┘
          │
    ┌─────────────────┐
    │   Lernmi API    │
    │  (Learning &    │
    │   Feedback)     │
    └─────────────────┘
```

### **Tech Stack**
- **Backend**: TypeScript + Express.js + Socket.io
- **Frontend**: React + Next.js + Tailwind CSS  
- **Database**: PostgreSQL + Neo4j + Qdrant + Redis
- **LLM**: Ollama (primary) + OpenAI/Anthropic (fallback)
- **Voice**: OpenAI Whisper (STT) + ElevenLabs (TTS)
- **Deployment**: Docker + Production ready

## 🚀 Quick Start

### **Prerequisites**
- Node.js 18+
- Docker & Docker Compose
- Digi-Core and PCS services running

### **Development Setup**

1. **Clone and install dependencies:**
   ```bash
   git clone <repository-url>
   cd beep-boop
   make install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and service URLs
   ```

3. **Start development environment:**
   ```bash
   make dev
   ```

4. **Verify services are healthy:**
   ```bash
   make health
   ```

5. **Open the application:**
   - **Web App**: http://localhost:3000
   - **API Docs**: http://localhost:3000/api/v1/docs  
   - **Health Check**: http://localhost:3000/health

### **One-Command Setup**
```bash
make setup  # Complete setup for new development environment
```

## 🛠️ Development

### **Common Commands**

```bash
# Development
make dev              # Start development environment
make test             # Run all tests
make lint             # Lint and format code  
make health           # Check service health

# Database
make db-setup         # Setup databases and migrations
npm run db:migrate    # Run database migrations
npm run db:seed       # Seed development data

# Docker
make docker-dev       # Start Docker development environment
make docker-build     # Build Docker images

# Monitoring
make logs             # View application logs
make metrics          # View monitoring dashboards
```

### **Project Structure**

```
src/
├── domain/           # Business entities and rules
│   ├── entities/     # Core domain entities
│   ├── repositories/ # Data access interfaces
│   └── services/     # Domain services
├── application/      # Use cases and orchestration
│   ├── use-cases/    # Business use cases
│   └── dto/          # Data transfer objects
├── infrastructure/   # External concerns
│   ├── database/     # Database connections and migrations
│   ├── cache/        # Redis cache management
│   ├── logging/      # Structured logging
│   └── config/       # Configuration management
├── interfaces/       # External interfaces
│   ├── http/         # HTTP API routes
│   └── websocket/    # WebSocket handlers
├── adapters/         # External service integrations
│   ├── digi-core/    # Knowledge retrieval adapter
│   ├── pcs/          # Prompt generation adapter
│   ├── llm/          # LLM provider adapters
│   └── voice/        # Voice processing adapters
└── utils/            # Shared utilities
```

## 🔧 Configuration

### **Environment Variables**

Key configuration options (see `.env.example` for complete list):

```bash
# Core Services
DIGI_CORE_BASE_URL=http://localhost:2000
PCS_BASE_URL=http://localhost:8000
OLLAMA_BASE_URL=http://localhost:11434

# API Keys
DIGI_CORE_API_KEY=your_key_here
PCS_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Database
POSTGRES_HOST=localhost
NEO4J_URI=bolt://localhost:7687
QDRANT_URL=http://localhost:6333
REDIS_HOST=localhost

# Features
VOICE_ENABLED=true
MEMORY_ENABLED=true
STREAMING_ENABLED=true
```

## 🧪 Testing

### **Test Types**

- **Unit Tests**: Domain logic and pure functions
- **Integration Tests**: API endpoints and database operations
- **E2E Tests**: Complete user workflows

### **Running Tests**

```bash
# All tests
npm test

# With coverage
npm run test:coverage

# Watch mode
npm run test:watch

# Integration tests only
npm run test:integration
```

## 📊 Monitoring

### **Health Checks**

- **Liveness**: `/health/live` - Basic application health
- **Readiness**: `/health/ready` - Service dependency health  
- **Comprehensive**: `/health` - Detailed system status

### **Observability**

- **Logs**: Structured JSON logging with correlation IDs
- **Metrics**: Prometheus metrics at `/health/metrics`
- **Tracing**: OpenTelemetry integration (planned)
- **Dashboards**: Grafana dashboards for monitoring

## 🔒 Security

### **Security Features**

- **Input Validation**: Zod schema validation on all inputs
- **Rate Limiting**: API endpoint protection
- **CORS Configuration**: Secure cross-origin policies
- **Helmet.js**: Security headers and protection
- **No Secrets in Code**: Environment-based configuration

### **API Security**

- **Authentication**: JWT-based user authentication
- **Authorization**: Role-based access control
- **API Keys**: Service-to-service authentication
- **Request Validation**: Type-safe request handling

## 📚 API Documentation

### **WebSocket Events**

**Client → Server:**
- `user_message` - Send chat message
- `voice_input` - Send voice audio data
- `feedback` - Submit thumbs up/down feedback

**Server → Client:**
- `processing_step` - Real-time processing updates
- `token_chunk` - Streaming response tokens
- `response_complete` - Final response with metadata
- `voice_output` - Synthesized audio response

### **HTTP Endpoints**

**Chat API:**
- `POST /api/v1/chat/message` - Process chat message
- `GET /api/v1/chat/conversations/:userId` - Get conversation history
- `POST /api/v1/chat/feedback` - Submit message feedback

**Learning API:**
- `GET /api/v1/learning/prompts` - Get prompts for learning systems
- `POST /api/v1/learning/feedback` - Receive learning feedback

**Memory API:**
- `GET /api/v1/memory/:userId` - Get user memories
- `POST /api/v1/memory/extract` - Extract memories from conversations

## 🚀 Deployment

### **Production Deployment**

```bash
# Build production image
make docker-build

# Deploy to production
make deploy-prod
```

### **Environment Setup**

The application is designed to deploy to **chat.tibocin.xyz** with:
- SSL/TLS termination
- CDN for static assets
- Database backups and monitoring
- Auto-scaling based on load

## 🤝 Contributing

### **Development Workflow**

1. Create feature branch: `git checkout -b feature/new-feature`
2. Make changes following clean architecture principles
3. Add tests for new functionality
4. Run quality checks: `make lint && make test`
5. Submit pull request with clear description

### **Code Quality Standards**

- **TypeScript**: Strict type checking enabled
- **ESLint**: Code quality and consistency
- **Prettier**: Automated code formatting
- **Jest**: Comprehensive test coverage (>70%)
- **Architecture**: Clean architecture boundaries

## 📈 Roadmap

### **Current Phase: Foundation** ✅
- [x] Project structure and TypeScript setup
- [x] Database schema and connections
- [x] Basic HTTP and WebSocket APIs
- [x] Health checks and monitoring

### **Phase 2: Core Integration** 🔄
- [ ] Digi-Core knowledge retrieval adapter
- [ ] PCS dynamic prompt generation
- [ ] LLM provider integration (Ollama + fallbacks)
- [ ] Basic conversation processing

### **Phase 3: Advanced Features** 📋
- [ ] Voice input/output (STT/TTS)
- [ ] Memory extraction and relationships
- [ ] Real-time streaming implementation
- [ ] Feedback and learning systems

### **Phase 4: Production** 🎯
- [ ] React frontend and PWA features
- [ ] Production deployment pipeline
- [ ] Advanced monitoring and alerting
- [ ] Performance optimization

## 🆘 Support

### **Getting Help**

- **Issues**: [GitHub Issues](link-to-issues)
- **Documentation**: `/docs` directory
- **Health Checks**: Use `make health` for diagnostics
- **Logs**: Use `make logs` to view application logs

### **Common Issues**

1. **Services not starting**: Check `make health` and ensure all dependencies are running
2. **Database connection errors**: Verify database credentials in `.env`
3. **API integration failures**: Check service URLs and API keys
4. **WebSocket connection issues**: Verify CORS configuration

---

**🎉 Ready to transform your conversational AI experience with Beep-Boop v2.0!**

*This application serves as your intelligent digital twin, capable of professional networking, creative collaboration, and personal assistance with advanced memory and learning capabilities.*