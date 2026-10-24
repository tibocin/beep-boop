/**
 * src/infrastructure/config/index.ts - Configuration Management
 * 
 * Centralized configuration management for Beep-Boop v2.0.
 * Validates environment variables and provides typed configuration objects.
 * 
 * Related Components:
 * - Environment variable validation
 * - Service endpoint configuration
 * - Feature flag management
 * - Database connection settings
 * 
 * Tags: #config #environment #validation #settings
 */

import { z } from 'zod';

/**
 * Environment variable schema validation
 * 
 * Ensures all required configuration is present and properly formatted.
 * Provides runtime validation and helpful error messages.
 */
const configSchema = z.object({
  // Application Settings
  nodeEnv: z.enum(['development', 'staging', 'production']).default('development'),
  port: z.coerce.number().int().positive().default(3000),
  apiVersion: z.string().default('v1'),
  logLevel: z.enum(['error', 'warn', 'info', 'debug']).default('info'),
  
  // Security
  corsOrigin: z.string().default('http://localhost:3000'),
  jwtSecret: z.string().min(32, 'JWT secret must be at least 32 characters'),
  sessionSecret: z.string().min(32, 'Session secret must be at least 32 characters'),
  
  // Rate Limiting
  rateLimitRequests: z.coerce.number().int().positive().default(1000),
  rateLimitWindow: z.coerce.number().int().positive().default(900000), // 15 minutes
  
  // Digi-Core Integration
  digiCore: z.object({
    baseUrl: z.string().url(),
    apiKey: z.string().min(1, 'Digi-Core API key is required'),
    enabled: z.coerce.boolean().default(true),
    timeout: z.coerce.number().int().positive().default(30000),
    maxRetries: z.coerce.number().int().positive().default(3)
  }),
  
  // PCS Integration
  pcs: z.object({
    baseUrl: z.string().url(),
    apiKey: z.string().min(1, 'PCS API key is required'),
    appId: z.string().default('beep-boop-v2'),
    enabled: z.coerce.boolean().default(true),
    timeout: z.coerce.number().int().positive().default(15000),
    maxRetries: z.coerce.number().int().positive().default(3)
  }),
  
  // LLM Providers
  ollama: z.object({
    baseUrl: z.string().url().default('http://localhost:11434'),
    model: z.string().default('llama3.1:8b'),
    enabled: z.coerce.boolean().default(true),
    timeout: z.coerce.number().int().positive().default(60000)
  }),
  
  openai: z.object({
    apiKey: z.string().optional(),
    model: z.string().default('gpt-4o-mini'),
    enabled: z.coerce.boolean().default(true),
    timeout: z.coerce.number().int().positive().default(30000)
  }),
  
  // Voice Services
  voice: z.object({
    whisper: z.object({
      apiKey: z.string().optional(),
      model: z.string().default('whisper-1'),
      enabled: z.coerce.boolean().default(true)
    }),
    elevenlabs: z.object({
      apiKey: z.string().optional(),
      voiceId: z.string().optional(),
      enabled: z.coerce.boolean().default(false)
    }),
    openaiTts: z.object({
      enabled: z.coerce.boolean().default(true),
      model: z.string().default('tts-1'),
      voice: z.string().default('alloy')
    })
  }),
  
  // Database Configuration
  database: z.object({
    postgres: z.object({
      host: z.string().default('localhost'),
      port: z.coerce.number().int().positive().default(5432),
      database: z.string().default('beep_boop_v2'),
      username: z.string().default('beep_boop_user'),
      password: z.string().min(1, 'PostgreSQL password is required'),
      ssl: z.coerce.boolean().default(false)
    }),
    neo4j: z.object({
      uri: z.string().default('bolt://localhost:7687'),
      username: z.string().default('neo4j'),
      password: z.string().min(1, 'Neo4j password is required'),
      database: z.string().default('beep_boop_graph')
    }),
    qdrant: z.object({
      url: z.string().url().default('http://localhost:6333'),
      apiKey: z.string().optional(),
      collections: z.object({
        prompts: z.string().default('beep_boop_prompts'),
        memories: z.string().default('beep_boop_memories'),
        contexts: z.string().default('beep_boop_contexts')
      })
    }),
    redis: z.object({
      host: z.string().default('localhost'),
      port: z.coerce.number().int().positive().default(6379),
      password: z.string().optional(),
      db: z.coerce.number().int().min(0).default(0),
      ttl: z.coerce.number().int().positive().default(3600)
    })
  }),
  
  // Feature Flags
  features: z.object({
    voice: z.coerce.boolean().default(true),
    memory: z.coerce.boolean().default(true),
    feedback: z.coerce.boolean().default(true),
    streaming: z.coerce.boolean().default(true),
    promptEvolution: z.coerce.boolean().default(true),
    relationshipMapping: z.coerce.boolean().default(true),
    learningIntegration: z.coerce.boolean().default(false),
    multiModal: z.coerce.boolean().default(false)
  })
});

/**
 * Parse and validate environment variables
 * 
 * Transforms environment variables into typed configuration object.
 * Provides helpful error messages for missing or invalid configuration.
 */
function parseEnvironment(): z.infer<typeof configSchema> {
  const env = {
    // Application Settings
    nodeEnv: process.env.NODE_ENV,
    port: process.env.PORT,
    apiVersion: process.env.API_VERSION,
    logLevel: process.env.LOG_LEVEL,
    
    // Security
    corsOrigin: process.env.CORS_ORIGIN,
    jwtSecret: process.env.JWT_SECRET,
    sessionSecret: process.env.SESSION_SECRET,
    
    // Rate Limiting
    rateLimitRequests: process.env.RATE_LIMIT_REQUESTS,
    rateLimitWindow: process.env.RATE_LIMIT_WINDOW,
    
    // Digi-Core Integration
    digiCore: {
      baseUrl: process.env.DIGI_CORE_BASE_URL,
      apiKey: process.env.DIGI_CORE_API_KEY,
      enabled: process.env.DIGI_CORE_ENABLED,
      timeout: process.env.DIGI_CORE_TIMEOUT,
      maxRetries: process.env.DIGI_CORE_MAX_RETRIES
    },
    
    // PCS Integration
    pcs: {
      baseUrl: process.env.PCS_BASE_URL,
      apiKey: process.env.PCS_API_KEY,
      appId: process.env.PCS_APP_ID,
      enabled: process.env.PCS_ENABLED,
      timeout: process.env.PCS_TIMEOUT,
      maxRetries: process.env.PCS_MAX_RETRIES
    },
    
    // LLM Providers
    ollama: {
      baseUrl: process.env.OLLAMA_BASE_URL,
      model: process.env.OLLAMA_MODEL,
      enabled: process.env.OLLAMA_ENABLED,
      timeout: process.env.OLLAMA_TIMEOUT
    },
    
    openai: {
      apiKey: process.env.OPENAI_API_KEY,
      model: process.env.OPENAI_MODEL,
      enabled: process.env.OPENAI_ENABLED,
      timeout: process.env.OPENAI_TIMEOUT
    },
    
    // Voice Services
    voice: {
      whisper: {
        apiKey: process.env.WHISPER_API_KEY || process.env.OPENAI_API_KEY,
        model: process.env.WHISPER_MODEL,
        enabled: process.env.WHISPER_ENABLED
      },
      elevenlabs: {
        apiKey: process.env.ELEVENLABS_API_KEY,
        voiceId: process.env.ELEVENLABS_VOICE_ID,
        enabled: process.env.ELEVENLABS_ENABLED
      },
      openaiTts: {
        enabled: process.env.OPENAI_TTS_ENABLED,
        model: process.env.OPENAI_TTS_MODEL,
        voice: process.env.OPENAI_TTS_VOICE
      }
    },
    
    // Database Configuration
    database: {
      postgres: {
        host: process.env.POSTGRES_HOST,
        port: process.env.POSTGRES_PORT,
        database: process.env.POSTGRES_DB,
        username: process.env.POSTGRES_USER,
        password: process.env.POSTGRES_PASSWORD,
        ssl: process.env.POSTGRES_SSL
      },
      neo4j: {
        uri: process.env.NEO4J_URI,
        username: process.env.NEO4J_USERNAME,
        password: process.env.NEO4J_PASSWORD,
        database: process.env.NEO4J_DATABASE
      },
      qdrant: {
        url: process.env.QDRANT_URL,
        apiKey: process.env.QDRANT_API_KEY,
        collections: {
          prompts: process.env.QDRANT_COLLECTION_PROMPTS,
          memories: process.env.QDRANT_COLLECTION_MEMORIES,
          contexts: process.env.QDRANT_COLLECTION_CONTEXTS
        }
      },
      redis: {
        host: process.env.REDIS_HOST,
        port: process.env.REDIS_PORT,
        password: process.env.REDIS_PASSWORD,
        db: process.env.REDIS_DB,
        ttl: process.env.REDIS_TTL
      }
    },
    
    // Feature Flags
    features: {
      voice: process.env.VOICE_ENABLED,
      memory: process.env.MEMORY_ENABLED,
      feedback: process.env.FEEDBACK_ENABLED,
      streaming: process.env.STREAMING_ENABLED,
      promptEvolution: process.env.PROMPT_EVOLUTION_ENABLED,
      relationshipMapping: process.env.RELATIONSHIP_MAPPING_ENABLED,
      learningIntegration: process.env.LEARNING_INTEGRATION_ENABLED,
      multiModal: process.env.MULTI_MODAL_ENABLED
    }
  };

  try {
    return configSchema.parse(env);
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('❌ Configuration validation failed:');
      error.errors.forEach(err => {
        console.error(`  - ${err.path.join('.')}: ${err.message}`);
      });
      console.error('\n💡 Please check your .env file against .env.example');
    }
    throw error;
  }
}

/**
 * Validated configuration object
 * 
 * Exported configuration with TypeScript type safety and runtime validation.
 */
export const config = parseEnvironment();

// Add helper properties for easier access
export const configWithHelpers = {
  ...config,
  cors: {
    origin: config.corsOrigin
  },
  rateLimiting: {
    windowMs: config.rateLimitWindow,
    max: config.rateLimitRequests
  }
};

/**
 * Configuration type for TypeScript consumers
 */
export type Config = typeof config;

/**
 * Helper function to get database connection string
 */
export function getDatabaseUrl(): string {
  const { postgres } = config.database;
  const sslQuery = postgres.ssl ? '?sslmode=require' : '';
  return `postgresql://${postgres.username}:${postgres.password}@${postgres.host}:${postgres.port}/${postgres.database}${sslQuery}`;
}

/**
 * Helper function to get Redis connection configuration
 */
export function getRedisConfig() {
  return {
    host: config.database.redis.host,
    port: config.database.redis.port,
    password: config.database.redis.password,
    db: config.database.redis.db,
    retryDelayOnFailover: 100,
    enableReadyCheck: true,
    lazyConnect: true
  };
}