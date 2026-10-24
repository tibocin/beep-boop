/**
 * src/interfaces/http/api.routes.ts - Main API Routes
 * 
 * Central API router that organizes all API endpoints by feature area.
 * Provides API versioning, documentation, and common middleware.
 * 
 * Related Components:
 * - Chat and conversation endpoints
 * - Memory and relationship management
 * - Learning system integration
 * - Voice and multi-modal features
 * 
 * Tags: #api #routes #versioning #documentation #middleware
 */

import { Router, Request, Response } from 'express';
import { config } from '@/infrastructure/config';
import { logger } from '@/infrastructure/logging';
import { streamRouter } from './stream.routes';

const router = Router();

// Mount streaming routes
router.use('/stream', streamRouter);

/**
 * API documentation endpoint
 * 
 * Serves OpenAPI documentation for the entire API surface.
 */
router.get('/docs', async (req: Request, res: Response) => {
  try {
    // TODO: Implement OpenAPI documentation serving
    const apiDocs = {
      openapi: '3.0.0',
      info: {
        title: 'Beep-Boop v2.0 API',
        version: '2.0.0',
        description: 'Multi-modal conversational AI with dynamic prompts and knowledge integration',
        contact: {
          name: 'Tibo Cintio',
          email: 'tibocin@pm.me'
        }
      },
      servers: [
        {
          url: `http://localhost:${config.port}/api/${config.apiVersion}`,
          description: 'Development server'
        },
        {
          url: `https://chat.tibocin.xyz/api/${config.apiVersion}`,
          description: 'Production server'
        }
      ],
      paths: {
        '/health': {
          get: {
            summary: 'Health check endpoint',
            responses: {
              '200': {
                description: 'Service is healthy'
              }
            }
          }
        },
        '/chat/message': {
          post: {
            summary: 'Process user message',
            requestBody: {
              required: true,
              content: {
                'application/json': {
                  schema: {
                    type: 'object',
                    properties: {
                      message: { type: 'string' },
                      userId: { type: 'string' },
                      conversationId: { type: 'string', format: 'uuid' },
                      voice: { type: 'boolean' }
                    },
                    required: ['message', 'userId']
                  }
                }
              }
            }
          }
        }
      }
    };

    res.status(200).json(apiDocs);

  } catch (error) {
    logger.error('Failed to serve API documentation', error);
    res.status(500).json({
      error: 'Failed to load API documentation'
    });
  }
});

/**
 * API version information
 * 
 * Provides version, build information, and feature flags.
 */
router.get('/version', async (req: Request, res: Response) => {
  try {
    const versionInfo = {
      version: '2.0.0',
      apiVersion: config.apiVersion,
      buildTime: new Date().toISOString(), // TODO: Add actual build time
      environment: config.nodeEnv,
      features: config.features,
      integrations: {
        digiCore: config.digiCore.enabled,
        pcs: config.pcs.enabled,
        ollama: config.ollama.enabled,
        voice: config.features.voice
      }
    };

    res.status(200).json(versionInfo);

  } catch (error) {
    logger.error('Failed to retrieve version information', error);
    res.status(500).json({
      error: 'Failed to retrieve version information'
    });
  }
});

/**
 * Learning system integration endpoints
 * 
 * Provides endpoints for external learning systems like Lernmi to interact
 * with the conversation system and provide feedback.
 */
router.get('/learning/prompts', async (req: Request, res: Response) => {
  try {
    // TODO: Implement prompt retrieval for learning systems
    logger.info('Learning system requesting prompts');

    const mockResponse = {
      prompts: [],
      total: 0,
      page: 1,
      limit: 20
    };

    res.status(200).json({
      success: true,
      data: mockResponse
    });

  } catch (error) {
    logger.error('Failed to retrieve prompts for learning', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve prompts'
    });
  }
});

/**
 * POST /learning/feedback - Receive feedback from learning systems
 * 
 * Allows external learning systems to provide feedback on prompts and responses.
 */
router.post('/learning/feedback', async (req: Request, res: Response) => {
  try {
    // TODO: Implement learning feedback processing
    logger.info('Received learning system feedback', { 
      feedbackData: req.body 
    });

    res.status(200).json({
      success: true,
      message: 'Feedback received and processed'
    });

  } catch (error) {
    logger.error('Failed to process learning feedback', error);
    res.status(500).json({
      success: false,
      error: 'Failed to process feedback'
    });
  }
});

/**
 * Memory and relationship endpoints
 */
router.get('/memory/:userId', async (req: Request, res: Response) => {
  try {
    const userId = req.params.userId;
    const memoryType = req.query.type as string;

    logger.info('Retrieving user memories', { userId, memoryType });

    // TODO: Implement memory retrieval
    const mockResponse = {
      memories: [],
      relationships: [],
      total: 0
    };

    res.status(200).json({
      success: true,
      data: mockResponse
    });

  } catch (error) {
    logger.error('Failed to retrieve memories', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve memories'
    });
  }
});

/**
 * Error handling middleware for API routes
 */
router.use((error: Error, req: Request, res: Response, next: any) => {
  logger.error('API route error', error, {
    method: req.method,
    url: req.url,
    body: req.body
  });

  res.status(500).json({
    success: false,
    error: 'Internal server error',
    requestId: req.headers['x-request-id']
  });
});

export { router as apiRouter };