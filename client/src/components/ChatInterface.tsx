/**
 * client/src/components/ChatInterface.tsx - Main Chat Interface Component
 * 
 * Core chat interface with message display, input handling, and real-time streaming.
 * Supports text and voice input with responsive design for mobile and desktop.
 */

import React, { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon, MicrophoneIcon, HandThumbUpIcon, HandThumbDownIcon } from '@heroicons/react/24/outline';
import { useChatStore } from '../stores/chatStore';
import { Message } from '../types/chat';

interface ChatInterfaceProps {
  onSendMessage: (message: string, voice?: boolean) => void;
  isConnected: boolean;
}

export function ChatInterface({ onSendMessage, isConnected }: ChatInterfaceProps): JSX.Element {
  const [inputMessage, setInputMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  const { currentConversation, addFeedback } = useChatStore();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);

  // Focus input on component mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendMessage = () => {
    if (!inputMessage.trim() || !isConnected) return;
    
    onSendMessage(inputMessage.trim());
    setInputMessage('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleVoiceToggle = () => {
    setIsRecording(!isRecording);
    // TODO: Implement voice recording
  };

  const handleFeedback = (messageId: string, feedback: 'up' | 'down') => {
    addFeedback(messageId, feedback);
  };

  const renderMessage = (message: Message) => {
    const isUser = message.role === 'user';
    
    return (
      <div 
        key={message.id}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div className={`max-w-[70%] ${
          isUser 
            ? 'bg-blue-600 text-white' 
            : 'bg-gray-700 text-gray-100'
        } rounded-lg px-4 py-2 relative group`}>
          
          {/* Message Content */}
          <div className=\"whitespace-pre-wrap break-words\">
            {message.content}
            {message.streaming && (
              <span className=\"inline-block w-2 h-4 bg-current ml-1 animate-pulse\" />
            )}
          </div>
          
          {/* Message Metadata */}
          {message.metadata && (
            <div className=\"text-xs opacity-70 mt-1\">
              {message.metadata.confidence && (
                <span>Confidence: {Math.round(message.metadata.confidence * 100)}%</span>
              )}
              {message.metadata.processingTime && (
                <span className=\"ml-2\">
                  {Math.round(message.metadata.processingTime)}ms
                </span>
              )}
            </div>
          )}
          
          {/* Feedback Buttons (for assistant messages) */}
          {!isUser && !message.streaming && (
            <div className=\"absolute top-0 right-0 transform translate-x-full opacity-0 group-hover:opacity-100 transition-opacity flex space-x-1 ml-2\">
              <button
                onClick={() => handleFeedback(message.id, 'up')}
                className=\"p-1 bg-green-600 hover:bg-green-700 rounded text-white transition-colors\"
                title=\"Good response\"
              >
                <HandThumbUpIcon className=\"w-3 h-3\" />
              </button>
              <button
                onClick={() => handleFeedback(message.id, 'down')}
                className=\"p-1 bg-red-600 hover:bg-red-700 rounded text-white transition-colors\"
                title=\"Poor response\"
              >
                <HandThumbDownIcon className=\"w-3 h-3\" />
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className=\"flex flex-col h-full\">
      {/* Messages Area */}
      <div className=\"flex-1 overflow-y-auto p-4 space-y-4\">
        {currentConversation?.messages.length === 0 ? (
          <div className=\"text-center text-gray-400 mt-8\">
            <div className=\"w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4\">
              <span className=\"text-2xl\">🤖</span>
            </div>
            <h3 className=\"text-lg font-medium mb-2\">Welcome to Beep-Boop v2.0</h3>
            <p className=\"text-sm max-w-md mx-auto\">
              I'm your personal AI assistant powered by dynamic prompts and knowledge integration. 
              Ask me anything, and I'll provide context-aware responses using your personal knowledge base.
            </p>
          </div>
        ) : (
          currentConversation?.messages.map(renderMessage)
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className=\"border-t border-gray-700 p-4\">
        <div className=\"flex items-end space-x-3\">
          {/* Text Input */}
          <div className=\"flex-1\">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isConnected ? \"Type your message...\" : \"Connecting...\"}
              disabled={!isConnected}
              rows={1}
              className=\"w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none\"
              style={{
                minHeight: '40px',
                maxHeight: '120px'
              }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement;
                target.style.height = 'auto';
                target.style.height = `${target.scrollHeight}px`;
              }}
            />
          </div>

          {/* Voice Button */}
          <button
            onClick={handleVoiceToggle}
            disabled={!isConnected}
            className={`p-2 rounded-lg transition-colors ${
              isRecording
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-gray-600 hover:bg-gray-500'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title={isRecording ? 'Stop recording' : 'Start voice input'}
          >
            <MicrophoneIcon className={`w-5 h-5 ${isRecording ? 'animate-pulse' : ''}`} />
          </button>

          {/* Send Button */}
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || !isConnected}
            className=\"p-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors\"
            title=\"Send message\"
          >
            <PaperAirplaneIcon className=\"w-5 h-5\" />
          </button>
        </div>

        {/* Connection Status */}
        {!isConnected && (
          <div className=\"mt-2 text-center\">
            <span className=\"text-xs text-red-400\">
              ⚠️ Disconnected - Attempting to reconnect...
            </span>
          </div>
        )}
      </div>
    </div>
  );
}