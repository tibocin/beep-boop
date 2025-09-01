# Beep-Boop v2.0 Makefile
# Common development and deployment tasks

.PHONY: help install dev build test lint clean docker-dev docker-prod deploy

# Default target
help: ## Show this help message
	@echo "Beep-Boop v2.0 - Conversational AI Application"
	@echo ""
	@echo "Available commands:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development
install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	npm install
	cd client && npm install
	@echo "✅ Dependencies installed"

dev: ## Start development environment
	@echo "🚀 Starting development environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "⏳ Waiting for services to be ready..."
	sleep 10
	@$(MAKE) health
	npm run dev

build: ## Build the application
	@echo "🔨 Building application..."
	npm run build
	@echo "✅ Build complete"

# Testing
test: ## Run all tests
	@echo "🧪 Running tests..."
	npm run test
	npm run test:integration
	@echo "✅ Tests complete"

test-coverage: ## Run tests with coverage
	@echo "📊 Running tests with coverage..."
	npm run test:coverage
	@echo "✅ Coverage report generated"

# Code Quality
lint: ## Lint and format code
	@echo "🔍 Linting code..."
	npm run lint
	npm run format
	@echo "✅ Code linting complete"

typecheck: ## Type check TypeScript
	@echo "🔍 Type checking..."
	npm run typecheck
	@echo "✅ Type checking complete"

# Database
db-setup: ## Set up databases
	@echo "🗄️ Setting up databases..."
	npm run db:generate
	npm run db:migrate
	npm run db:seed
	@echo "✅ Database setup complete"

# Docker
docker-dev: ## Start development Docker environment
	@echo "🐳 Starting development Docker environment..."
	docker-compose -f docker-compose.dev.yml up -d
	@$(MAKE) health
	@echo "✅ Development environment ready"

docker-prod: ## Start production Docker environment
	@echo "🐳 Starting production Docker environment..."
	docker-compose up -d
	@$(MAKE) health
	@echo "✅ Production environment ready"

docker-build: ## Build Docker images
	@echo "🔨 Building Docker images..."
	docker-compose build
	@echo "✅ Docker images built"

# Health Checks
health: ## Check service health
	@echo "🔍 Checking service health..."
	@echo "  Beep-Boop API..."
	@curl -s http://localhost:3000/health > /dev/null && echo "    ✅ Beep-Boop API: healthy" || echo "    ❌ Beep-Boop API: unhealthy"
	@echo "  Digi-Core..."
	@curl -s http://localhost:2000/health > /dev/null && echo "    ✅ Digi-Core: healthy" || echo "    ❌ Digi-Core: unhealthy"
	@echo "  PCS..."
	@curl -s http://localhost:8000/health > /dev/null && echo "    ✅ PCS: healthy" || echo "    ❌ PCS: unhealthy"
	@echo "  PostgreSQL..."
	@docker exec beep-boop-postgres pg_isready -U beep_boop > /dev/null 2>&1 && echo "    ✅ PostgreSQL: healthy" || echo "    ❌ PostgreSQL: unhealthy"
	@echo "  Redis..."
	@docker exec beep-boop-redis redis-cli ping > /dev/null 2>&1 && echo "    ✅ Redis: healthy" || echo "    ❌ Redis: unhealthy"

# Cleanup
clean: ## Clean build artifacts
	@echo "🧹 Cleaning build artifacts..."
	npm run clean
	rm -rf node_modules/.cache
	docker system prune -f
	@echo "✅ Cleanup complete"

# Deployment
deploy-staging: ## Deploy to staging environment
	@echo "🚀 Deploying to staging..."
	@echo "⚠️  Staging deployment not yet implemented"

deploy-prod: ## Deploy to production (chat.tibocin.xyz)
	@echo "🚀 Deploying to production..."
	@echo "⚠️  Production deployment not yet implemented"

# Security
security-scan: ## Run security scans
	@echo "🔒 Running security scans..."
	npm audit
	@echo "✅ Security scan complete"

# Logs
logs: ## View application logs
	@echo "📋 Viewing application logs..."
	docker-compose logs -f beep-boop

logs-all: ## View all service logs
	@echo "📋 Viewing all service logs..."
	docker-compose logs -f

# Monitoring
metrics: ## View application metrics
	@echo "📊 Application metrics available at:"
	@echo "  Grafana: http://localhost:3001"
	@echo "  Prometheus: http://localhost:9090"

# Development Helpers
setup: install db-setup ## Complete setup for new development environment
	@echo "🎉 Beep-Boop development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and configure"
	@echo "  2. Run 'make dev' to start development"
	@echo "  3. Visit http://localhost:3000 for the app"
	@echo "  4. Visit http://localhost:3000/docs for API documentation"

reset: clean ## Reset entire development environment
	@echo "🔄 Resetting development environment..."
	docker-compose down -v
	rm -rf node_modules
	rm -f .env
	@echo "✅ Environment reset complete"
	@echo "Run 'make setup' to reinitialize"