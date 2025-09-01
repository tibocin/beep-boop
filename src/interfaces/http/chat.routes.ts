/**
 * src/interfaces/http/chat.routes.ts - Chat API Routes
 * 
 * HTTP endpoints for chat functionality including message processing,
 * conversation management, and voice interactions.
 * 
 * Related Components:
 * - Message processing orchestration
 * - Conversation history management
 * - Voice input/output handling
 * - Feedback collection
 * 
 * Tags: #chat #api #conversations #voice #feedback
 */

import { Router, Request, Response } from 'express';
import { z } from 'zod';
import { logger } from '@/infrastructure/logging';
import { processMessageUseCase, ProcessMessageInput } from '@/application/use-cases/process-message.use-case';

const router = Router();

/**
 * Request validation schemas
 */
const SendMessageSchema = z.object({
  message: z.string().min(1).max(4000),
  conversationId: z.string().uuid().optional(),
  userId: z.string().min(1),
  voice: z.boolean().default(false),
  context: z.record(z.any()).optional()
});

const FeedbackSchema = z.object({
  messageId: z.string().uuid(),
  feedback: z.enum(['up', 'down']),
  comment: z.string().optional(),
  metadata: z.record(z.any()).optional()
});

/**
 * POST /chat/message - Process user message
 * 
 * Main endpoint for processing user messages through the complete pipeline.
 * Supports both text and voice input with real-time streaming.
 */
router.post('/message', async (req: Request, res: Response) => {
  const startTime = Date.now();
  
  try {
    // Validate request
    const validatedData = SendMessageSchema.parse(req.body);
    
    logger.info('Processing chat message', {
      userId: validatedData.userId,
      messageLength: validatedData.message.length,
      hasConversationId: !!validatedData.conversationId,
      isVoice: validatedData.voice
    });

    // Process message through the complete pipeline
    const processInput: ProcessMessageInput = {
      userId: validatedData.userId,
      message: validatedData.message,
      conversationId: validatedData.conversationId,
      voice: validatedData.voice,
      context: validatedData.context
    };

    const result = await processMessageUseCase.execute(processInput);

    res.status(200).json({
      success: true,
      data: {
        id: result.messageId,
        conversationId: result.conversationId,
        content: result.response,
        timestamp: new Date().toISOString(),
        metadata: {
          processingTime: result.metadata.processingTime,
          model: result.metadata.llmProvider,
          confidence: result.confidence,
          knowledgeSources: result.knowledgeUsed.results.length,
          promptTemplate: result.promptUsed.templateName
        }
      }
    });

  } catch (error) {
    logger.error('Chat message processing failed', error);
    
    if (error instanceof z.ZodError) {
      res.status(400).json({
        success: false,
        error: 'Invalid request data',
        details: error.errors
      });
    } else {
      res.status(500).json({
        success: false,
        error: 'Message processing failed'
      });
    }
  }
});

/**
 * GET /chat/conversations/:userId - Get conversation history
 * 
 * Retrieves conversation history for a specific user with pagination support.
 */
router.get('/conversations/:userId', async (req: Request, res: Response) => {
  try {
    const userId = req.params.userId;
    const page = parseInt(req.query.page as string) || 1;
    const limit = Math.min(parseInt(req.query.limit as string) || 20, 100);

    logger.info('Retrieving conversations', { userId, page, limit });

    // TODO: Implement conversation retrieval from database
    const mockConversations = {
      conversations: [],
      pagination: {
        page,
        limit,
        total: 0,
        totalPages: 0
      }
    };

    res.status(200).json({
      success: true,
      data: mockConversations
    });

  } catch (error) {
    logger.error('Failed to retrieve conversations', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve conversations'
    });
  }
});

/**
 * GET /chat/conversation/:conversationId - Get specific conversation
 * 
 * Retrieves a specific conversation with all messages and metadata.
 */
router.get('/conversation/:conversationId', async (req: Request, res: Response) => {
  try {
    const conversationId = req.params.conversationId;

    logger.info('Retrieving conversation', { conversationId });

    // TODO: Implement specific conversation retrieval
    const mockConversation = {
      id: conversationId,
      title: 'Mock Conversation',
      createdAt: new Date().toISOString(),
      messages: []
    };

    res.status(200).json({
      success: true,
      data: mockConversation
    });

  } catch (error) {
    logger.error('Failed to retrieve conversation', error);
    res.status(500).json({
      success: false,
      error: 'Failed to retrieve conversation'
    });
  }
});

/**
 * POST /chat/feedback - Submit user feedback
 * 
 * Collects user feedback (thumbs up/down) for responses to improve the system.
 */
router.post('/feedback', async (req: Request, res: Response) => {
  try {
    const validatedData = FeedbackSchema.parse(req.body);

    logger.info('Processing user feedback', {
      messageId: validatedData.messageId,
      feedback: validatedData.feedback,
      hasComment: !!validatedData.comment
    });

    // TODO: Implement feedback processing and storage
    const mockResponse = {
      id: `feedback_${Date.now()}`,
      messageId: validatedData.messageId,
      feedback: validatedData.feedback,
      processed: true,
      timestamp: new Date().toISOString()
    };

    res.status(200).json({
      success: true,
      data: mockResponse
    });

  } catch (error) {
    logger.error('Feedback processing failed', error);
    
    if (error instanceof z.ZodError) {
      res.status(400).json({
        success: false,
        error: 'Invalid feedback data',
        details: error.errors
      });
    } else {
      res.status(500).json({
        success: false,
        error: 'Feedback processing failed'
      });
    }
  }
});

/**
 * POST /chat/voice/transcribe - Transcribe voice input
 * 
 * Converts voice audio to text using speech-to-text services.
 */
router.post('/voice/transcribe', async (req: Request, res: Response) => {
  try {
    // TODO: Implement voice transcription
    logger.info('Voice transcription requested');

    const mockResponse = {
      text: 'Mock transcription result',
      confidence: 0.95,
      duration: 2.5,
      language: 'en'
    };

    res.status(200).json({
      success: true,
      data: mockResponse
    });

  } catch (error) {
    logger.error('Voice transcription failed', error);
    res.status(500).json({
      success: false,
      error: 'Voice transcription failed'
    });
  }
});

/**
 * POST /chat/voice/synthesize - Synthesize text to speech
 * 
 * Converts text responses to audio using text-to-speech services.
 */
router.post('/voice/synthesize', async (req: Request, res: Response) => {
  try {
    const { text, voice, speed } = req.body;

    if (!text || typeof text !== 'string') {
      return res.status(400).json({
        success: false,
        error: 'Text is required for synthesis'
      });
    }

    logger.info('Voice synthesis requested', { 
      textLength: text.length,
      voice: voice || 'default',
      speed: speed || 1.0
    });

    // TODO: Implement voice synthesis
    const mockResponse = {
      audioUrl: '/api/audio/mock.mp3',
      duration: 3.2,
      voice: voice || 'alloy',
      format: 'mp3'
    };

    res.status(200).json({
      success: true,
      data: mockResponse
    });

  } catch (error) {
    logger.error('Voice synthesis failed', error);
    res.status(500).json({
      success: false,
      error: 'Voice synthesis failed'
    });
  }
});

export { router as chatRouter };