/**
 * src/interfaces/http/stream.routes.ts - Streaming Chat API Routes
 * 
 * HTTP endpoints for streaming chat functionality using Server-Sent Events (SSE).
 * Provides real-time message processing updates for web clients.
 * 
 * Related Components:
 * - Message processing use case with streaming
 * - Server-Sent Events for HTTP streaming
 * - Real-time processing visibility
 * - Error handling for stream connections
 * 
 * Tags: #streaming #sse #realtime #chat #api
 */

import { Router, Request, Response } from 'express';
import { z } from 'zod';
import { logger } from '@/infrastructure/logging';
import { processMessageUseCase, ProcessMessageInput } from '@/application/use-cases/process-message.use-case';

const router = Router();

/**
 * Request validation schema for streaming
 */
const StreamMessageSchema = z.object({
  message: z.string().min(1).max(4000),
  conversationId: z.string().uuid().optional(),
  userId: z.string().min(1),
  voice: z.boolean().default(false),
  context: z.record(z.any()).optional()
});

/**
 * POST /stream/message - Process message with Server-Sent Events streaming
 * 
 * Provides real-time streaming of message processing pipeline for web clients
 * that prefer HTTP-based streaming over WebSockets.
 */
router.post('/message', async (req: Request, res: Response) => {
  try {
    // Validate request
    const validatedData = StreamMessageSchema.parse(req.body);
    
    // Set up Server-Sent Events
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Cache-Control'
    });

    logger.info('Starting streaming message processing', {
      userId: validatedData.userId,
      messageLength: validatedData.message.length,
      hasConversationId: !!validatedData.conversationId,
      isVoice: validatedData.voice
    });

    // Helper function to send SSE events
    const sendEvent = (eventType: string, data: any) => {
      res.write(`event: ${eventType}\n`);
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    };

    try {
      // Process message with streaming
      const processInput: ProcessMessageInput = {
        userId: validatedData.userId,
        message: validatedData.message,
        conversationId: validatedData.conversationId,
        voice: validatedData.voice,
        context: validatedData.context
      };

      // Send initial event
      sendEvent('stream_started', {
        messageId: 'pending',
        timestamp: new Date().toISOString()
      });

      // Process with streaming
      for await (const event of processMessageUseCase.executeWithStreaming(processInput)) {
        sendEvent(event.type, event.data);
        
        // End stream on completion or error
        if (event.type === 'complete' || event.type === 'error') {
          break;
        }
      }

      // Send final event and close
      sendEvent('stream_ended', {
        timestamp: new Date().toISOString()
      });

    } catch (error) {
      logger.error('Streaming message processing failed', error);
      
      sendEvent('error', {
        error: error instanceof Error ? error.message : 'Processing failed',
        timestamp: new Date().toISOString()
      });
    }

    res.end();

  } catch (error) {
    logger.error('Streaming setup failed', error);
    
    if (error instanceof z.ZodError) {
      res.status(400).json({
        success: false,
        error: 'Invalid request data',
        details: error.errors
      });
    } else {
      res.status(500).json({
        success: false,
        error: 'Streaming setup failed'
      });
    }
  }
});

/**
 * GET /stream/health - Health check for streaming endpoints
 * 
 * Simple endpoint to verify streaming capabilities are working.
 */
router.get('/health', (req: Request, res: Response) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive'
  });

  let counter = 0;
  const interval = setInterval(() => {
    res.write(`event: heartbeat\n`);
    res.write(`data: ${JSON.stringify({ 
      count: ++counter, 
      timestamp: new Date().toISOString() 
    })}\n\n`);

    if (counter >= 5) {
      clearInterval(interval);
      res.write(`event: complete\n`);
      res.write(`data: ${JSON.stringify({ 
        message: 'Health check complete',
        timestamp: new Date().toISOString() 
      })}\n\n`);
      res.end();
    }
  }, 1000);

  // Clean up on client disconnect
  req.on('close', () => {
    clearInterval(interval);
    logger.debug('Streaming health check client disconnected');
  });
});

export { router as streamRouter };