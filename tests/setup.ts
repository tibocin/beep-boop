/**
 * tests/setup.ts - Test Environment Setup
 * 
 * Global test setup for Jest test environment.
 * Configures test database, mocks, and common utilities.
 */

import { config } from '@/infrastructure/config';

// Increase test timeout for integration tests
jest.setTimeout(30000);

// Mock external services for unit tests
jest.mock('@/adapters/digi-core', () => ({
  DigiCoreAdapter: jest.fn().mockImplementation(() => ({
    queryKnowledge: jest.fn().mockResolvedValue({
      results: [],
      confidence: 0.8,
      sources: []
    }),
    healthCheck: jest.fn().mockResolvedValue(true)
  }))
}));

jest.mock('@/adapters/pcs', () => ({
  PCSAdapter: jest.fn().mockImplementation(() => ({
    generatePrompt: jest.fn().mockResolvedValue('Mock generated prompt'),
    evolvePrompt: jest.fn().mockResolvedValue('Mock evolved prompt'),
    healthCheck: jest.fn().mockResolvedValue(true)
  }))
}));

// Setup test environment variables
process.env.NODE_ENV = 'test';
process.env.JWT_SECRET = 'test_jwt_secret_with_minimum_32_characters';
process.env.SESSION_SECRET = 'test_session_secret_with_minimum_32_chars';
process.env.DATABASE_URL = process.env.TEST_DATABASE_URL || 'postgresql://test:test@localhost:5433/beep_boop_test';