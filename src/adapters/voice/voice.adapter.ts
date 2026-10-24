/**
 * src/adapters/voice/voice.adapter.ts - Voice Processing Integration
 * 
 * Adapter for speech-to-text (STT) and text-to-speech (TTS) capabilities.
 * Integrates with OpenAI Whisper and ElevenLabs for high-quality voice processing.
 * 
 * Related Components:
 * - OpenAI Whisper for speech-to-text
 * - ElevenLabs and OpenAI TTS for text-to-speech
 * - Circuit breaker for service reliability
 * - Audio format handling and validation
 * 
 * Tags: #adapter #voice #stt #tts #audio #streaming
 */

import axios, { AxiosInstance } from 'axios';
import OpenAI from 'openai';
import FormData from 'form-data';
import { config } from '@/infrastructure/config';
import { logger, createContextualLogger } from '@/infrastructure/logging';
import { CircuitBreaker } from '@/utils/circuit-breaker';
import { RetryHandler } from '@/utils/retry-handler';

/**
 * Supported audio formats for voice processing
 */
export enum AudioFormat {
  WAV = 'wav',
  MP3 = 'mp3',
  WEBM = 'webm',
  OGG = 'ogg',
  M4A = 'm4a'
}

/**
 * Voice provider enumeration
 */
export enum VoiceProvider {
  OPENAI_WHISPER = 'openai_whisper',
  OPENAI_TTS = 'openai_tts',
  ELEVENLABS = 'elevenlabs'
}

/**
 * Speech-to-text request
 */
export interface STTRequest {
  audioData: Buffer;
  format: AudioFormat;
  language?: string;
  model?: string;
  temperature?: number;
}

/**
 * Speech-to-text response
 */
export interface STTResponse {
  text: string;
  confidence: number;
  language: string;
  duration: number;
  provider: VoiceProvider;
  metadata: {
    processingTime: number;
    audioSize: number;
    segments?: Array<{
      text: string;
      start: number;
      end: number;
      confidence: number;
    }>;
  };
}

/**
 * Text-to-speech request
 */
export interface TTSRequest {
  text: string;
  voice?: string;
  speed?: number;
  format?: AudioFormat;
  provider?: VoiceProvider;
}

/**
 * Text-to-speech response
 */
export interface TTSResponse {
  audioData: Buffer;
  audioUrl?: string;
  duration: number;
  format: AudioFormat;
  provider: VoiceProvider;
  metadata: {
    processingTime: number;
    textLength: number;
    audioSize: number;
    voice: string;
  };
}

/**
 * Voice adapter metrics
 */
export interface VoiceMetrics {
  stt: {
    totalRequests: number;
    successfulRequests: number;
    averageProcessingTime: number;
    averageConfidence: number;
  };
  tts: {
    totalRequests: number;
    successfulRequests: number;
    averageProcessingTime: number;
    totalAudioGenerated: number; // in seconds
  };
  providers: Record<VoiceProvider, {
    available: boolean;
    lastCheck: string;
    circuitBreakerState: string;
  }>;
}

/**
 * Voice processing adapter
 * 
 * Provides unified interface for speech-to-text and text-to-speech operations
 * with provider fallbacks, resilience patterns, and quality optimization.
 */
export class VoiceAdapter {
  private openaiClient!: OpenAI;
  private elevenlabsClient!: AxiosInstance;
  private circuitBreakers!: Map<VoiceProvider, CircuitBreaker>;
  private retryHandlers!: Map<VoiceProvider, RetryHandler>;
  private metrics!: VoiceMetrics;
  private contextLogger = createContextualLogger({ operation: 'voice-adapter' });

  constructor() {
    this.initializeClients();
    this.initializeResilience();
    this.initializeMetrics();
  }

  /**
   * Initialize voice service clients
   */
  private initializeClients(): void {
    // Initialize OpenAI client for Whisper and TTS
    if (config.voice.whisper.apiKey) {
      this.openaiClient = new OpenAI({
        apiKey: config.voice.whisper.apiKey,
        timeout: 30000 // Voice processing needs longer timeout
      });
    }

    // Initialize ElevenLabs client
    if (config.voice.elevenlabs.apiKey) {
      this.elevenlabsClient = axios.create({
        baseURL: 'https://api.elevenlabs.io/v1',
        timeout: 30000,
        headers: {
          'xi-api-key': config.voice.elevenlabs.apiKey,
          'Content-Type': 'application/json'
        }
      });
    }

    this.contextLogger.info('Voice clients initialized', {
      whisper: !!config.voice.whisper.apiKey,
      elevenlabs: !!config.voice.elevenlabs.apiKey,
      openaiTts: config.voice.openaiTts.enabled
    });
  }

  /**
   * Initialize resilience patterns for voice services
   */
  private initializeResilience(): void {
    this.circuitBreakers = new Map();
    this.retryHandlers = new Map();

    // OpenAI Whisper
    this.circuitBreakers.set(VoiceProvider.OPENAI_WHISPER, new CircuitBreaker({
      failureThreshold: 3,
      resetTimeout: 60000,
      monitoringPeriod: 15000
    }));

    this.retryHandlers.set(VoiceProvider.OPENAI_WHISPER, new RetryHandler({
      maxAttempts: 2,
      baseDelay: 2000,
      maxDelay: 10000,
      jitterFactor: 0.15
    }));

    // ElevenLabs TTS
    this.circuitBreakers.set(VoiceProvider.ELEVENLABS, new CircuitBreaker({
      failureThreshold: 3,
      resetTimeout: 45000,
      monitoringPeriod: 15000
    }));

    this.retryHandlers.set(VoiceProvider.ELEVENLABS, new RetryHandler({
      maxAttempts: 2,
      baseDelay: 1500,
      maxDelay: 8000,
      jitterFactor: 0.1
    }));

    // OpenAI TTS
    this.circuitBreakers.set(VoiceProvider.OPENAI_TTS, new CircuitBreaker({
      failureThreshold: 5,
      resetTimeout: 60000,
      monitoringPeriod: 15000
    }));

    this.retryHandlers.set(VoiceProvider.OPENAI_TTS, new RetryHandler({
      maxAttempts: 3,
      baseDelay: 1000,
      maxDelay: 8000,
      jitterFactor: 0.2
    }));
  }

  /**
   * Initialize metrics tracking
   */
  private initializeMetrics(): void {
    this.metrics = {
      stt: {
        totalRequests: 0,
        successfulRequests: 0,
        averageProcessingTime: 0,
        averageConfidence: 0
      },
      tts: {
        totalRequests: 0,
        successfulRequests: 0,
        averageProcessingTime: 0,
        totalAudioGenerated: 0
      },
      providers: {
        [VoiceProvider.OPENAI_WHISPER]: {
          available: !!config.voice.whisper.apiKey,
          lastCheck: new Date().toISOString(),
          circuitBreakerState: 'CLOSED'
        },
        [VoiceProvider.ELEVENLABS]: {
          available: !!config.voice.elevenlabs.apiKey,
          lastCheck: new Date().toISOString(),
          circuitBreakerState: 'CLOSED'
        },
        [VoiceProvider.OPENAI_TTS]: {
          available: config.voice.openaiTts.enabled,
          lastCheck: new Date().toISOString(),
          circuitBreakerState: 'CLOSED'
        }
      }
    };
  }

  /**
   * Convert speech to text using OpenAI Whisper
   * 
   * Transcribes audio input to text with confidence scoring and timing information.
   */
  async speechToText(request: STTRequest): Promise<STTResponse> {
    if (!this.openaiClient) {
      throw new Error('OpenAI client not initialized - API key missing');
    }

    const startTime = Date.now();

    try {
      this.metrics.stt.totalRequests++;

      const result = await this.circuitBreakers.get(VoiceProvider.OPENAI_WHISPER)!.execute(async () => {
        return this.retryHandlers.get(VoiceProvider.OPENAI_WHISPER)!.executeWithRetry(async () => {
          return this.transcribeWithWhisper(request);
        });
      });

      // Update metrics
      const processingTime = Date.now() - startTime;
      this.updateSTTMetrics(true, processingTime, result.confidence);

      this.contextLogger.info('Speech-to-text completed', {
        textLength: result.text.length,
        confidence: result.confidence,
        processingTime,
        audioSize: request.audioData.length
      });

      return result;

    } catch (error) {
      this.updateSTTMetrics(false, Date.now() - startTime, 0);
      this.contextLogger.error('Speech-to-text failed', error);
      throw error;
    }
  }

  /**
   * Convert text to speech with provider selection
   * 
   * Generates audio from text using best available provider (ElevenLabs preferred, OpenAI fallback).
   */
  async textToSpeech(request: TTSRequest): Promise<TTSResponse> {
    const startTime = Date.now();

    try {
      this.metrics.tts.totalRequests++;

      // Try ElevenLabs first if available and enabled
      if (config.voice.elevenlabs.enabled && this.elevenlabsClient) {
        try {
          const result = await this.circuitBreakers.get(VoiceProvider.ELEVENLABS)!.execute(async () => {
            return this.retryHandlers.get(VoiceProvider.ELEVENLABS)!.executeWithRetry(async () => {
              return this.synthesizeWithElevenLabs(request);
            });
          });

          this.updateTTSMetrics(true, Date.now() - startTime, result.duration);
          return result;

        } catch (error) {
          this.contextLogger.warn('ElevenLabs TTS failed, falling back to OpenAI', { error });
        }
      }

      // Fallback to OpenAI TTS
      if (config.voice.openaiTts.enabled && this.openaiClient) {
        const result = await this.circuitBreakers.get(VoiceProvider.OPENAI_TTS)!.execute(async () => {
          return this.retryHandlers.get(VoiceProvider.OPENAI_TTS)!.executeWithRetry(async () => {
            return this.synthesizeWithOpenAI(request);
          });
        });

        this.updateTTSMetrics(true, Date.now() - startTime, result.duration);
        return result;
      }

      throw new Error('No TTS providers available');

    } catch (error) {
      this.updateTTSMetrics(false, Date.now() - startTime, 0);
      this.contextLogger.error('Text-to-speech failed', error);
      throw error;
    }
  }

  /**
   * Transcribe audio using OpenAI Whisper
   */
  private async transcribeWithWhisper(request: STTRequest): Promise<STTResponse> {
    const startTime = Date.now();

    // Create form data for file upload
    const formData = new FormData();
    formData.append('file', request.audioData, {
      filename: `audio.${request.format}`,
      contentType: `audio/${request.format}`
    });
    formData.append('model', request.model || config.voice.whisper.model);
    
    if (request.language) {
      formData.append('language', request.language);
    }
    
    if (request.temperature !== undefined) {
      formData.append('temperature', request.temperature.toString());
    }

    const response = await this.openaiClient.audio.transcriptions.create({
      file: new File([request.audioData], `audio.${request.format}`, { 
        type: `audio/${request.format}` 
      }),
      model: request.model || config.voice.whisper.model,
      language: request.language,
      temperature: request.temperature,
      response_format: 'verbose_json'
    });

    const processingTime = Date.now() - startTime;

    // Estimate confidence from response (Whisper doesn't provide confidence directly)
    const estimatedConfidence = this.estimateTranscriptionConfidence(response.text || '');

    return {
      text: response.text || '',
      confidence: estimatedConfidence,
      language: response.language || request.language || 'en',
      duration: response.duration || 0,
      provider: VoiceProvider.OPENAI_WHISPER,
      metadata: {
        processingTime,
        audioSize: request.audioData.length,
        segments: (response as any).segments?.map((seg: any) => ({
          text: seg.text,
          start: seg.start,
          end: seg.end,
          confidence: seg.confidence || estimatedConfidence
        }))
      }
    };
  }

  /**
   * Synthesize speech using ElevenLabs
   */
  private async synthesizeWithElevenLabs(request: TTSRequest): Promise<TTSResponse> {
    const startTime = Date.now();
    const voiceId = request.voice || config.voice.elevenlabs.voiceId || 'EXAVITQu4vr4xnSDxMaL';

    const response = await this.elevenlabsClient.post(`/text-to-speech/${voiceId}`, {
      text: request.text,
      model_id: 'eleven_monolingual_v1',
      voice_settings: {
        stability: 0.5,
        similarity_boost: 0.5,
        style: 0.0,
        use_speaker_boost: true
      }
    }, {
      responseType: 'arraybuffer'
    });

    const audioData = Buffer.from(response.data);
    const processingTime = Date.now() - startTime;
    const estimatedDuration = this.estimateAudioDuration(request.text);

    return {
      audioData,
      duration: estimatedDuration,
      format: AudioFormat.MP3,
      provider: VoiceProvider.ELEVENLABS,
      metadata: {
        processingTime,
        textLength: request.text.length,
        audioSize: audioData.length,
        voice: voiceId
      }
    };
  }

  /**
   * Synthesize speech using OpenAI TTS
   */
  private async synthesizeWithOpenAI(request: TTSRequest): Promise<TTSResponse> {
    const startTime = Date.now();

    const response = await this.openaiClient.audio.speech.create({
      model: config.voice.openaiTts.model,
      voice: (request.voice as any) || config.voice.openaiTts.voice,
      input: request.text,
      speed: request.speed || 1.0,
      response_format: 'mp3'
    });

    const audioData = Buffer.from(await response.arrayBuffer());
    const processingTime = Date.now() - startTime;
    const estimatedDuration = this.estimateAudioDuration(request.text);

    return {
      audioData,
      duration: estimatedDuration,
      format: AudioFormat.MP3,
      provider: VoiceProvider.OPENAI_TTS,
      metadata: {
        processingTime,
        textLength: request.text.length,
        audioSize: audioData.length,
        voice: request.voice || config.voice.openaiTts.voice
      }
    };
  }

  /**
   * Estimate transcription confidence based on text characteristics
   * 
   * Since Whisper doesn't provide confidence scores, we estimate based on
   * text quality indicators.
   */
  private estimateTranscriptionConfidence(text: string): number {
    let confidence = 0.8; // Base confidence

    // Penalize very short transcriptions
    if (text.length < 10) {
      confidence -= 0.2;
    }

    // Penalize texts with many special characters (transcription errors)
    const specialCharRatio = (text.match(/[^\w\s]/g) || []).length / text.length;
    if (specialCharRatio > 0.1) {
      confidence -= 0.1;
    }

    // Penalize texts with repeated characters (transcription artifacts)
    if (/(.)\1{3,}/.test(text)) {
      confidence -= 0.2;
    }

    // Boost confidence for texts with proper sentence structure
    if (/[.!?]/.test(text)) {
      confidence += 0.1;
    }

    return Math.max(0.1, Math.min(1.0, confidence));
  }

  /**
   * Estimate audio duration from text length
   * 
   * Rough estimation: ~150 words per minute average speaking rate.
   */
  private estimateAudioDuration(text: string): number {
    const wordCount = text.split(/\s+/).length;
    const wordsPerMinute = 150;
    const durationMinutes = wordCount / wordsPerMinute;
    return durationMinutes * 60; // Convert to seconds
  }

  /**
   * Validate audio format and size
   */
  validateAudioInput(audioData: Buffer, format: AudioFormat): { valid: boolean; error?: string } {
    // Check file size (max 25MB for Whisper)
    if (audioData.length > 25 * 1024 * 1024) {
      return { valid: false, error: 'Audio file too large (max 25MB)' };
    }

    // Check minimum size
    if (audioData.length < 1024) {
      return { valid: false, error: 'Audio file too small' };
    }

    // Validate format
    if (!Object.values(AudioFormat).includes(format)) {
      return { valid: false, error: 'Unsupported audio format' };
    }

    return { valid: true };
  }

  /**
   * Validate TTS input text
   */
  validateTTSInput(text: string): { valid: boolean; error?: string } {
    // Check text length
    if (text.length === 0) {
      return { valid: false, error: 'Text cannot be empty' };
    }

    if (text.length > 4096) {
      return { valid: false, error: 'Text too long (max 4096 characters)' };
    }

    // Check for potentially problematic content
    if (text.includes('<') && text.includes('>')) {
      return { valid: false, error: 'HTML tags not allowed in TTS text' };
    }

    return { valid: true };
  }

  /**
   * Perform health checks on voice services
   */
  async healthCheck(): Promise<Record<VoiceProvider, boolean>> {
    const results: Record<string, boolean> = {};

    // Check OpenAI Whisper/TTS
    if (this.openaiClient) {
      try {
        await this.openaiClient.models.list();
        results[VoiceProvider.OPENAI_WHISPER] = true;
        results[VoiceProvider.OPENAI_TTS] = true;
      } catch (error) {
        results[VoiceProvider.OPENAI_WHISPER] = false;
        results[VoiceProvider.OPENAI_TTS] = false;
      }
    }

    // Check ElevenLabs
    if (this.elevenlabsClient) {
      try {
        await this.elevenlabsClient.get('/voices');
        results[VoiceProvider.ELEVENLABS] = true;
      } catch (error) {
        results[VoiceProvider.ELEVENLABS] = false;
      }
    }

    // Update provider availability in metrics
    for (const [provider, available] of Object.entries(results)) {
      this.metrics.providers[provider as VoiceProvider] = {
        available,
        lastCheck: new Date().toISOString(),
        circuitBreakerState: this.circuitBreakers.get(provider as VoiceProvider)?.getState() || 'UNKNOWN'
      };
    }

    return results as Record<VoiceProvider, boolean>;
  }

  /**
   * Get voice adapter metrics
   */
  getMetrics(): VoiceMetrics {
    // Update circuit breaker states
    for (const [provider, circuitBreaker] of this.circuitBreakers.entries()) {
      this.metrics.providers[provider].circuitBreakerState = circuitBreaker.getState();
    }

    return this.metrics;
  }

  /**
   * Update STT metrics
   */
  private updateSTTMetrics(success: boolean, processingTime: number, confidence: number): void {
    if (success) {
      this.metrics.stt.successfulRequests++;
      
      // Update rolling averages
      const totalSuccessfulTime = this.metrics.stt.averageProcessingTime * (this.metrics.stt.successfulRequests - 1);
      this.metrics.stt.averageProcessingTime = (totalSuccessfulTime + processingTime) / this.metrics.stt.successfulRequests;
      
      const totalConfidence = this.metrics.stt.averageConfidence * (this.metrics.stt.successfulRequests - 1);
      this.metrics.stt.averageConfidence = (totalConfidence + confidence) / this.metrics.stt.successfulRequests;
    }
  }

  /**
   * Update TTS metrics
   */
  private updateTTSMetrics(success: boolean, processingTime: number, audioDuration: number): void {
    if (success) {
      this.metrics.tts.successfulRequests++;
      this.metrics.tts.totalAudioGenerated += audioDuration;
      
      // Update rolling average
      const totalSuccessfulTime = this.metrics.tts.averageProcessingTime * (this.metrics.tts.successfulRequests - 1);
      this.metrics.tts.averageProcessingTime = (totalSuccessfulTime + processingTime) / this.metrics.tts.successfulRequests;
    }
  }
}

/**
 * Singleton instance for application-wide use
 */
export const voiceAdapter = new VoiceAdapter();