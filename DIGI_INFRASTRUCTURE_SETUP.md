# 🔧 Digi-Infrastructure Integration Setup Guide

This guide will help you connect Beep-Boop to your digi-infrastructure databases and services.

## 📋 Prerequisites

Before starting, ensure you have:
- ✅ Digi-Core RAG engine running
- ✅ PCS (Personal Context System) running  
- ✅ PostgreSQL database with digi-infrastructure schema
- ✅ Neo4j graph database
- ✅ Qdrant vector database
- ✅ Redis cache (optional but recommended)

## 🔑 Environment Configuration

### Step 1: Update Your .env File

Your `.env` file is currently **unlocked** for editing. Update it with your actual credentials:

```bash
# Current status: UNLOCKED (writable)
./scripts/manage-env.sh status
```

### Step 2: Required Environment Variables

Update these critical variables in your `.env` file:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-openai-key-here

# Digi-Core RAG Engine (Primary Knowledge Source)
DIGI_CORE_API_URL=http://localhost:8000  # or your actual URL
DIGI_CORE_API_KEY=your-actual-digi-core-api-key
DIGI_CORE_ENABLED=true
DIGI_CORE_MIN_CONFIDENCE=0.3

# PCS (Personal Context System)
PCS_BASE_URL=http://localhost:8000  # or your actual URL
PCS_API_KEY=your-actual-pcs-api-key
PCS_ENABLED=true

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/beep_boop
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-actual-neo4j-password
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your-actual-qdrant-api-key
```

### Step 3: Test Your Configuration

After updating your credentials, test all connections:

```bash
# Test all service connections
python3 test_connections.py

# Expected output: All services should show ✅ or ⚠️ (not ❌)
```

### Step 4: Re-protect Your .env File

Once configuration is complete, re-protect the file:

```bash
# Re-protect the .env file
./scripts/manage-env.sh lock

# Verify protection
./scripts/manage-env.sh status
```

## 🗄️ Database Setup

### PostgreSQL Setup

1. **Create Database:**
```sql
CREATE DATABASE beep_boop;
CREATE USER beep_boop_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE beep_boop TO beep_boop_user;
```

2. **Run Migrations:**
```bash
# If using Prisma
npx prisma migrate deploy

# Or run the migration SQL directly
psql -d beep_boop -f src/infrastructure/database/migrations/20250901175838_init/migration.sql
```

### Neo4j Setup

1. **Start Neo4j:**
```bash
# Using Docker
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/your_password \
  neo4j:latest

# Or using system service
sudo systemctl start neo4j
```

2. **Verify Connection:**
```bash
# Test connection
cypher-shell -u neo4j -p your_password "RETURN 1 as test;"
```

### Qdrant Setup

1. **Start Qdrant:**
```bash
# Using Docker
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant:latest

# Or using system service
sudo systemctl start qdrant
```

2. **Create Collections:**
```bash
# Create required collections
curl -X PUT "http://localhost:6333/collections/beep_boop_prompts"
curl -X PUT "http://localhost:6333/collections/beep_boop_memories"
curl -X PUT "http://localhost:6333/collections/beep_boop_contexts"
```

## 🧠 Digi-Core Integration

### Health Check

Test your Digi-Core connection:

```bash
# Test health endpoint
curl -H "Authorization: Bearer YOUR_DIGI_CORE_API_KEY" \
     http://localhost:8000/health

# Expected: {"status": "healthy", "version": "..."}
```

### RAG Query Test

Test knowledge retrieval:

```bash
# Test knowledge query
curl -X POST \
  -H "Authorization: Bearer YOUR_DIGI_CORE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "limit": 5}' \
  http://localhost:8000/api/knowledge/query
```

## 🎯 PCS Integration

### Health Check

Test your PCS connection:

```bash
# Test health endpoint
curl -H "Authorization: Bearer YOUR_PCS_API_KEY" \
     -H "X-App-ID: beep-boop-v2" \
     http://localhost:8000/health

# Expected: {"status": "healthy", "version": "..."}
```

### Prompt Generation Test

Test prompt generation:

```bash
# Test prompt generation
curl -X POST \
  -H "Authorization: Bearer YOUR_PCS_API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-App-ID: beep-boop-v2" \
  -d '{"templateName": "conversation", "context": {"userId": "test"}}' \
  http://localhost:8000/api/prompts/generate
```

## 🚀 Application Startup

### Initialize Database Connections

```bash
# Start the application (this will initialize all connections)
npm run dev
# or
python3 app.py
```

### Verify Integration

Check the application logs for successful connections:

```
✅ All database connections initialized successfully
🧠 Digi-Core detected - using as primary RAG backend
🎯 PCS integration active
```

## 🔧 Troubleshooting

### Common Issues

1. **Connection Refused:**
   - Check if services are running
   - Verify ports and URLs
   - Check firewall settings

2. **Authentication Failed:**
   - Verify API keys and passwords
   - Check user permissions
   - Ensure credentials are correctly formatted

3. **Database Schema Issues:**
   - Run migrations
   - Check database permissions
   - Verify schema exists

### Debug Commands

```bash
# Test individual services
python3 test_connections.py

# Check service status
./scripts/manage-env.sh status

# View application logs
tail -f logs/app.log

# Test database connectivity
psql -d beep_boop -c "SELECT 1;"
cypher-shell -u neo4j -p password "RETURN 1;"
curl http://localhost:6333/collections
```

## 📊 Monitoring

### Health Checks

The application includes built-in health checks:

- **Database Health:** `/health/database`
- **Service Health:** `/health/services`
- **Overall Health:** `/health`

### Metrics

Monitor these key metrics:
- Connection pool status
- Query response times
- Error rates
- Memory usage

## 🔄 Next Steps

After successful setup:

1. **Test the full pipeline:**
   - Send a message through the chat interface
   - Verify RAG retrieval works
   - Check prompt generation
   - Confirm database storage

2. **Monitor performance:**
   - Check response times
   - Monitor error rates
   - Verify data persistence

3. **Scale as needed:**
   - Adjust connection pools
   - Configure caching
   - Set up monitoring alerts

## 📞 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review application logs
3. Run the connection test script
4. Verify all services are running and accessible

---

**Remember:** Always re-protect your `.env` file after making changes:
```bash
./scripts/manage-env.sh lock
```
