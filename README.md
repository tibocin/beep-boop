---
title: beep-boop
app_file: cypherpunk_app.py
sdk: gradio
sdk_version: 5.38.1
---

# beep-boop

A conversational AI chatbot powered by **async OpenAI SDK** with **real-time streaming**, advanced RAG capabilities, and cypherpunk-themed interface.

## 🚀 Features

- **🔄 Async OpenAI SDK Integration**: Full async/await support with optimal performance
- **📡 Real-time Streaming**: Chunk-based response generation for instant feedback
- **🧠 Advanced RAG**: Retrieval-Augmented Generation with multiple backend support
- **🎤 Voice Mode**: Optimized for voice interactions with streaming
- **💾 Memory System**: Conversation memory and context management
- **📝 Resume Generation**: Specialized resume/CV content generation with streaming
- **🎨 Cypherpunk UI**: Themed interface with modern design

## 🛠️ Setup

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd beep-boop
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp env.example .env
# Edit .env and add your OpenAI API key
```

4. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## 🧪 Testing

Run the comprehensive async test suite to verify functionality:

```bash
# Test OpenAI integration
python test_openai_refactor.py

# Test Ollama integration (requires Ollama server)
python test_ollama_integration.py
```

## 🚀 Usage

### Development Mode

```bash
python cypherpunk_app.py
```

### Production Mode

```bash
python app.py
```

### Gradio Spaces

The app is configured for Gradio Spaces deployment with the cypherpunk interface.

## 🏗️ Architecture

### Core Components

- **UnifiedLLMClient** (`modules/core/llm_client.py`): Ollama primary with OpenAI fallback
- **AsyncLLMParser** (`modules/core/parser.py`): Async request parsing with streaming insights
- **AsyncLLMSynthesizer** (`modules/core/synthesizer.py`): Async response generation with streaming
- **AsyncConversationOrchestrator** (`modules/core/orchestrator.py`): Async pipeline coordination
- **RAG System** (`modules/rag/`): Multiple retrieval backends

### Streaming Capabilities

```python
# Regular async processing
response = await orchestrator.process_message("Hello!")

# Streaming response generation
async for chunk in orchestrator.process_message_stream("Hello!"):
    print(chunk, end="", flush=True)
```

### Data Structure

- `data/`: YAML knowledge base files
- `modules/`: Core application modules
- `chroma_db/`: Vector database storage

## 📊 Analytics & Tracking

The system tracks:

- **API Usage**: Token consumption and response times
- **Streaming Performance**: Chunk processing and latency metrics
- **User Interactions**: Conversation patterns and feature usage
- **Error Patterns**: Failed requests and retry success rates

## 🔧 Configuration

### Model Selection

The system uses **Ollama as primary** with **OpenAI as fallback** for cost optimization and reliability.

#### Ollama Setup (Primary)

```bash
# Install Ollama
brew install ollama  # macOS
# or
curl -fsSL https://ollama.ai/install.sh | sh  # Linux

# Pull a model
ollama pull llama3.1:8b

# Start Ollama server
ollama serve
```

#### Configuration

```python
# Initialize with Ollama primary and OpenAI fallback
orchestrator = AsyncConversationOrchestrator(
    model="gpt-4o-mini",  # OpenAI fallback model
    ollama_model="llama3.1:8b",  # Ollama primary model
    rag_backend="auto",
    enable_evaluation=True,
    enable_memory=True
)

# Force OpenAI only (no fallback)
client = UnifiedLLMClient(enable_fallback=False)

# Force OpenAI for specific requests
response = await client.chat_completion(messages, force_openai=True)
```

### RAG Backends

- `auto`: Automatic backend selection
- `simple`: In-memory vector storage
- `chroma`: ChromaDB vector database

### Streaming Options

```python
# Enable streaming for better UX
response = await synthesizer.synthesize_response(
    user_input="Hello!",
    stream=True  # Enable streaming
)

# Or use streaming generator
async for chunk in synthesizer.synthesize_response_stream(user_input="Hello!"):
    yield chunk
```

## ⚡ Performance Benefits

- **Real-time Responses**: Streaming provides instant feedback
- **Reduced Latency**: Async processing eliminates blocking
- **Better UX**: Users see responses as they're generated
- **Resource Efficiency**: Non-blocking I/O operations
- **Scalability**: Handles multiple concurrent requests

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_openai_refactor.py`
5. Submit a pull request

## 📝 License

See LICENSE file for details.

## 🔗 Links

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Gradio Documentation](https://gradio.app/docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
