/**
 * client/src/App.tsx - Main Beep-Boop React Application
 * 
 * Root component for Beep-Boop v2.0 React frontend.
 * Provides responsive chat interface with real-time streaming and voice support.
 * 
 * Related Components:
 * - Chat interface with WebSocket integration
 * - Voice input/output controls
 * - Real-time processing visibility
 * - Progressive Web App features
 * 
 * Tags: #frontend #react #chat #websocket #pwa
 */

import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { ChatInterface } from './components/ChatInterface';
import { VoiceControls } from './components/VoiceControls';
import { ProcessingIndicator } from './components/ProcessingIndicator';
import { useWebSocket } from './hooks/useWebSocket';
import { useChatStore } from './stores/chatStore';
import './App.css';

/**
 * Main Beep-Boop application component
 * 
 * Provides the root application structure with routing, WebSocket connection,
 * and global state management for the conversational AI interface.
 */
function App(): JSX.Element {
  const [isConnected, setIsConnected] = useState(false);
  const { conversations, addMessage } = useChatStore();

  // Initialize WebSocket connection
  const { socket, isConnected: wsConnected, sendMessage } = useWebSocket({
    url: process.env.REACT_APP_WS_URL || 'ws://localhost:3000',
    onMessage: (event, data) => {
      // Handle different WebSocket events
      switch (event) {
        case 'token_chunk':
          // Update streaming response
          addMessage({
            id: data.messageId,
            content: data.chunk,
            role: 'assistant',
            streaming: !data.isComplete
          });
          break;
        case 'processing_step':
          // Update processing indicator
          console.log('Processing step:', data);
          break;
        case 'response_complete':
          // Mark response as complete
          console.log('Response complete:', data);
          break;
        default:
          console.log('WebSocket event:', event, data);
      }
    }
  });

  useEffect(() => {
    setIsConnected(wsConnected);
  }, [wsConnected]);

  return (
    <Router>
      <div className=\"min-h-screen bg-gray-900 text-white\">
        {/* Header */}
        <header className=\"bg-gray-800 border-b border-gray-700 px-4 py-3\">
          <div className=\"flex items-center justify-between\">
            <div className=\"flex items-center space-x-3\">
              <div className=\"w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center\">
                <span className=\"text-sm font-bold\">BB</span>
              </div>
              <div>
                <h1 className=\"text-lg font-semibold\">Beep-Boop v2.0</h1>
                <p className=\"text-sm text-gray-400\">Your Personal AI Assistant</p>
              </div>
            </div>
            
            <div className=\"flex items-center space-x-4\">
              {/* Connection Status */}
              <div className=\"flex items-center space-x-2\">
                <div 
                  className={`w-2 h-2 rounded-full $\{
                    isConnected ? 'bg-green-500' : 'bg-red-500'
                  }`}
                />
                <span className=\"text-xs text-gray-400\">
                  {isConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {/* Voice Controls */}
              <VoiceControls />
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className=\"flex-1\">
          <Routes>
            <Route path=\"/\" element={
              <div className=\"flex h-[calc(100vh-64px)]\">
                {/* Sidebar - Conversations */}
                <div className=\"w-64 bg-gray-800 border-r border-gray-700 p-4\">
                  <h2 className=\"text-sm font-medium text-gray-300 mb-4\">Conversations</h2>
                  <div className=\"space-y-2\">
                    {conversations.slice(0, 10).map(conversation => (
                      <div 
                        key={conversation.id}
                        className=\"p-2 bg-gray-700 rounded cursor-pointer hover:bg-gray-600 transition-colors\"
                      >
                        <p className=\"text-sm truncate\">{conversation.title}</p>
                        <p className=\"text-xs text-gray-400\">
                          {new Date(conversation.updatedAt).toLocaleDateString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Main Chat Area */}
                <div className=\"flex-1 flex flex-col\">
                  {/* Processing Indicator */}
                  <ProcessingIndicator />
                  
                  {/* Chat Interface */}
                  <ChatInterface 
                    onSendMessage={sendMessage}
                    isConnected={isConnected}
                  />
                </div>
              </div>
            } />
          </Routes>
        </main>

        {/* Toast Notifications */}
        <Toaster 
          position=\"top-right\"
          toastOptions={{
            style: {
              background: '#374151',
              color: '#fff',
            },
          }}
        />
      </div>
    </Router>
  );
}

export default App;