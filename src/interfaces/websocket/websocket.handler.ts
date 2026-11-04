/**
 * src/interfaces/websocket/websocket.handler.ts - WebSocket Event Management
 * 
 * Handles real-time WebSocket connections for streaming responses,
 * voice interactions, and live processing updates.
 * 
 * Related Components:
 * - Real-time message streaming
 * - Voice input/output streaming
 * - Processing step visibility
 * - Connection lifecycle management
 * 
 * Tags: #websocket #realtime #streaming #voice #events
 */

import { Server as SocketServer, Socket } from 'socket.io';
import { z } from 'zod';
import { logger, createContextualLogger } from '@/infrastructure/logging';
import { CacheConnection } from '@/infrastructure/cache/connection';

/**
 * WebSocket event schemas for type safety and validation
 */
const UserMessageSchema = z.object({
  message: z.string().min(1).max(4000),
  conversationId: z.string().uuid().optional(),
  userId: z.string().min(1),
  voice: z.boolean().default(false),
  context: z.record(z.any()).optional()
});

const VoiceInputSchema = z.object({
  audioData: z.string(), // Base64 encoded audio
  format: z.enum(['wav', 'mp3', 'webm']).default('wav'),
  userId: z.string().min(1),
  conversationId: z.string().uuid().optional()
});

const FeedbackSchema = z.object({
  messageId: z.string().uuid(),
  feedback: z.enum(['up', 'down']),
  comment: z.string().optional(),
  timestamp: z.string().datetime()
});

/**
 * WebSocket event types for client-server communication
 */
interface ClientToServerEvents {
  user_message: (data: z.infer<typeof UserMessageSchema>) => void;
  voice_input: (data: z.infer<typeof VoiceInputSchema>) => void;
  feedback: (data: z.infer<typeof FeedbackSchema>) => void;
  join_conversation: (data: { conversationId: string; userId: string }) => void;
  leave_conversation: (data: { conversationId: string }) => void;
}

interface ServerToClientEvents {
  processing_step: (data: ProcessingStepEvent) => void;
  token_chunk: (data: TokenChunkEvent) => void;
  response_complete: (data: ResponseCompleteEvent) => void;
  voice_output: (data: VoiceOutputEvent) => void;
  error: (data: ErrorEvent) => void;
  connection_status: (data: ConnectionStatusEvent) => void;
}

/**
 * Event data structures for real-time communication
 */
interface ProcessingStepEvent {
  step: 'parsing' | 'knowledge_retrieval' | 'prompt_generation' | 'llm_processing' | 'response_synthesis' | 'memory_storage';
  status: 'started' | 'completed' | 'failed';
  timestamp: string;
  metadata?: Record<string, any>;
}

interface TokenChunkEvent {
  chunk: string;
  messageId: string;
  timestamp: string;
  isComplete: boolean;
}

interface ResponseCompleteEvent {
  messageId: string;
  conversationId: string;
  totalTokens: number;
  processingTime: number;
  confidence: number;
  timestamp: string;
}

interface VoiceOutputEvent {
  audioUrl: string;
  messageId: string;
  duration: number;
  format: 'mp3' | 'wav';
}

interface ErrorEvent {
  error: string;
  code: string;
  timestamp: string;
  requestId?: string;
}

interface ConnectionStatusEvent {
  status: 'connected' | 'disconnected' | 'reconnected';
  timestamp: string;
  userId?: string;
}

/**
 * WebSocket connection and event handler
 * 
 * Manages WebSocket connections, event routing, and real-time communication
 * between the client and server for streaming features.
 */
export class WebSocketHandler {
  private io: SocketServer<ClientToServerEvents, ServerToClientEvents>;
  private connectedUsers = new Map<string, Set<string>>(); // userId -> Set of socketIds

  constructor(io: SocketServer<ClientToServerEvents, ServerToClientEvents>) {
    this.io = io;
  }

  /**
   * Initialize WebSocket event handlers and middleware
   * 
   * Sets up all event handlers, authentication, and connection management.
   */
  initialize(): void {
    logger.info('🔌 Initializing WebSocket handlers...');

    // Connection middleware for authentication and setup
    this.io.use(async (socket, next) => {
      try {
        const userId = socket.handshake.auth.userId as string;
        const sessionId = socket.handshake.auth.sessionId as string;

        if (!userId) {
          throw new Error('User ID is required for WebSocket connection');
        }

        // Create contextual logger for this socket
        const socketLogger = createContextualLogger({
          requestId: socket.id,
          userId,
          sessionId,
          operation: 'websocket_connection'
        });

        socket.data = {
          userId,
          sessionId,
          logger: socketLogger,
          connectedAt: new Date()
        };

        socketLogger.websocket('Authentication successful', { userId });
        next();

      } catch (error) {
        logger.error('WebSocket authentication failed', error);
        next(new Error('Authentication failed'));
      }
    });

    // Handle new connections
    this.io.on('connection', (socket) => {
      this.handleConnection(socket);
    });

    logger.info('✅ WebSocket handlers initialized');
  }

  /**
   * Handle new WebSocket connection
   * 
   * Sets up event handlers for the individual socket connection.
   */
  private handleConnection(socket: Socket): void {
    const { userId, logger: socketLogger } = socket.data;

    socketLogger.websocket('Client connected', { 
      socketId: socket.id,
      userId 
    });

    // Track user connection
    this.trackUserConnection(userId, socket.id);

    // Send connection confirmation
    socket.emit('connection_status', {
      status: 'connected',
      timestamp: new Date().toISOString(),
      userId
    });

    // Handle user messages
    socket.on('user_message', async (data) => {
      await this.handleUserMessage(socket, data);
    });

    // Handle voice input
    socket.on('voice_input', async (data) => {
      await this.handleVoiceInput(socket, data);
    });

    // Handle feedback
    socket.on('feedback', async (data) => {
      await this.handleFeedback(socket, data);
    });

    // Handle conversation room management
    socket.on('join_conversation', (data) => {
      this.handleJoinConversation(socket, data);
    });

    socket.on('leave_conversation', (data) => {
      this.handleLeaveConversation(socket, data);
    });

    // Handle disconnection
    socket.on('disconnect', (reason) => {
      this.handleDisconnection(socket, reason);
    });
  }

  /**
   * Handle user message processing with streaming
   */
  private async handleUserMessage(socket: Socket, data: any): Promise<void> {
    const { userId, logger: socketLogger } = socket.data;

    try {
      // Validate message data
      const validatedData = UserMessageSchema.parse(data);

      socketLogger.info('Processing user message via WebSocket', {
        messageLength: validatedData.message.length,
        hasConversationId: !!validatedData.conversationId,
        isVoice: validatedData.voice
      });

      // TODO: Implement message processing with streaming
      // For now, emit mock processing steps
      await this.simulateProcessing(socket, validatedData);

    } catch (error) {
      socketLogger.error('WebSocket message processing failed', error);
      
      socket.emit('error', {
        error: error instanceof Error ? error.message : 'Message processing failed',
        code: 'MESSAGE_PROCESSING_ERROR',
        timestamp: new Date().toISOString()
      });
    }
  }

  /**
   * Handle voice input processing
   */
  private async handleVoiceInput(socket: Socket, data: any): Promise<void> {
    const { logger: socketLogger } = socket.data;

    try {
      const validatedData = VoiceInputSchema.parse(data);

      socketLogger.info('Processing voice input', {
        audioFormat: validatedData.format,
        userId: validatedData.userId
      });

      // TODO: Implement voice processing
      // For now, emit mock transcription
      socket.emit('processing_step', {
        step: 'parsing',
        status: 'started',
        timestamp: new Date().toISOString()
      });

      // Simulate voice processing delay
      setTimeout(() => {
        socket.emit('token_chunk', {
          chunk: 'Mock transcription result',
          messageId: `msg_${Date.now()}`,
          timestamp: new Date().toISOString(),
          isComplete: true
        });
      }, 1000);

    } catch (error) {
      socketLogger.error('Voice input processing failed', error);
      
      socket.emit('error', {
        error: 'Voice processing failed',
        code: 'VOICE_PROCESSING_ERROR',
        timestamp: new Date().toISOString()
      });
    }
  }

  /**
   * Handle user feedback submission
   */
  private async handleFeedback(socket: Socket, data: any): Promise<void> {
    const { logger: socketLogger } = socket.data;

    try {
      const validatedData = FeedbackSchema.parse(data);

      socketLogger.info('Processing user feedback', {
        messageId: validatedData.messageId,
        feedback: validatedData.feedback
      });

      // TODO: Implement feedback processing
      // Store feedback and trigger learning updates

    } catch (error) {
      socketLogger.error('Feedback processing failed', error);
      
      socket.emit('error', {
        error: 'Feedback processing failed',
        code: 'FEEDBACK_ERROR',
        timestamp: new Date().toISOString()
      });
    }
  }

  /**
   * Handle joining a conversation room
   */
  private handleJoinConversation(socket: Socket, data: { conversationId: string; userId: string }): void {
    const { logger: socketLogger } = socket.data;

    socketLogger.info('Joining conversation', { 
      conversationId: data.conversationId 
    });

    socket.join(data.conversationId);
  }

  /**
   * Handle leaving a conversation room
   */
  private handleLeaveConversation(socket: Socket, data: { conversationId: string }): void {
    const { logger: socketLogger } = socket.data;

    socketLogger.info('Leaving conversation', { 
      conversationId: data.conversationId 
    });

    socket.leave(data.conversationId);
  }

  /**
   * Handle client disconnection
   */
  private handleDisconnection(socket: Socket, reason: string): void {
    const { userId, logger: socketLogger } = socket.data;

    socketLogger.websocket('Client disconnected', { 
      reason,
      socketId: socket.id
    });

    // Remove from user tracking
    this.removeUserConnection(userId, socket.id);
  }

  /**
   * Track user connections for presence and broadcasting
   */
  private trackUserConnection(userId: string, socketId: string): void {
    if (!this.connectedUsers.has(userId)) {
      this.connectedUsers.set(userId, new Set());
    }
    this.connectedUsers.get(userId)!.add(socketId);

    logger.debug('User connection tracked', { 
      userId, 
      socketId,
      totalConnections: this.connectedUsers.get(userId)!.size
    });
  }

  /**
   * Remove user connection tracking
   */
  private removeUserConnection(userId: string, socketId: string): void {
    const userSockets = this.connectedUsers.get(userId);
    if (userSockets) {
      userSockets.delete(socketId);
      if (userSockets.size === 0) {
        this.connectedUsers.delete(userId);
      }
    }
  }

  /**
   * Simulate processing steps for development
   * 
   * TODO: Replace with actual processing pipeline integration
   */
  private async simulateProcessing(socket: Socket, data: z.infer<typeof UserMessageSchema>): Promise<void> {
    const messageId = `msg_${Date.now()}`;
    const steps: ProcessingStepEvent['step'][] = [
      'parsing',
      'knowledge_retrieval', 
      'prompt_generation',
      'llm_processing',
      'response_synthesis',
      'memory_storage'
    ];

    for (const step of steps) {
      // Emit step start
      socket.emit('processing_step', {
        step,
        status: 'started',
        timestamp: new Date().toISOString()
      });

      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 300));

      // Emit step completion
      socket.emit('processing_step', {
        step,
        status: 'completed',
        timestamp: new Date().toISOString()
      });
    }

    // Simulate token streaming
    const responseTokens = `Hello! I received your message: "${data.message}". This is a mock response for testing.`.split(' ');
    
    for (const token of responseTokens) {
      socket.emit('token_chunk', {
        chunk: token + ' ',
        messageId,
        timestamp: new Date().toISOString(),
        isComplete: false
      });
      
      await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 100));
    }

    // Emit completion
    socket.emit('response_complete', {
      messageId,
      conversationId: data.conversationId || `conv_${Date.now()}`,
      totalTokens: responseTokens.length,
      processingTime: 2000,
      confidence: 0.95,
      timestamp: new Date().toISOString()
    });
  }

  /**
   * Broadcast message to all connections for a user
   */
  broadcastToUser(userId: string, event: string, data: any): void {
    const userSockets = this.connectedUsers.get(userId);
    if (userSockets) {
      userSockets.forEach(socketId => {
        this.io.to(socketId).emit(event as any, data);
      });
    }
  }

  /**
   * Get connection statistics
   */
  getConnectionStats(): { totalConnections: number; uniqueUsers: number } {
    const totalConnections = Array.from(this.connectedUsers.values())
      .reduce((sum, sockets) => sum + sockets.size, 0);
    
    return {
      totalConnections,
      uniqueUsers: this.connectedUsers.size
    };
  }
}