import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PaperAirplaneIcon, UserIcon, ChatBubbleLeftIcon } from '@heroicons/react/24/outline';
import { useAnalysis } from '../context/AnalysisContext';
import { apiService } from '../services/api';
import { ChatMessage } from '../types';
import toast from 'react-hot-toast';

interface ChatInterfaceProps {
  documentId: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ documentId }) => {
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { chatMessages, addChatMessage } = useAnalysis();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      question: message,
      answer: '',
      timestamp: new Date().toISOString(),
      document_id: documentId,
    };

    // Add user message to chat
    setMessage('');
    setIsLoading(true);

    try {
      const response = await apiService.chatWithDocument(documentId, message);
      
      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        question: message,
        answer: response.answer,
        timestamp: new Date().toISOString(),
        document_id: documentId,
      };

      addChatMessage(aiMessage);
    } catch (error: any) {
      console.error('Chat error:', error);
      toast.error(error.response?.data?.detail || 'Failed to get response');
    } finally {
      setIsLoading(false);
    }
  };

  const suggestedQuestions = [
    "What are the top 5 largest transactions?",
    "Are there any suspicious patterns?",
    "How much was spent on travel last quarter?",
    "What's the total amount of all transactions?",
    "Are there any duplicate payments?",
    "What are the high-risk transactions?",
  ];

  const documentMessages = chatMessages.filter(msg => msg.document_id === documentId);

  return (
    <div className="bg-white rounded-lg border border-gray-200 h-[600px] flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center space-x-2">
          <ChatBubbleLeftIcon className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold text-gray-900">Ask AI about your document</h3>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          Get insights and answers about your financial data
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {documentMessages.length === 0 ? (
          <div className="text-center py-8">
            <ChatBubbleLeftIcon className="w-12 h-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500 mb-6">Ask questions about your document to get started!</p>
            
            {/* Suggested Questions */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-gray-700 mb-3">Try asking:</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {suggestedQuestions.map((question, index) => (
                  <button
                    key={index}
                    onClick={() => setMessage(question)}
                    className="text-left p-3 text-sm bg-gray-50 hover:bg-gray-100 rounded-lg border border-gray-200 transition-colors"
                  >
                    "{question}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <AnimatePresence>
            {documentMessages.map((msg, index) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="space-y-4"
              >
                {/* User Question */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center">
                      <UserIcon className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="bg-primary-50 border border-primary-200 rounded-lg p-3">
                      <p className="text-gray-900">{msg.question}</p>
                    </div>
                  </div>
                </div>

                {/* AI Answer */}
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                      <ChatBubbleLeftIcon className="w-4 h-4 text-white" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                      <p className="text-gray-900 whitespace-pre-wrap">{msg.answer}</p>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start space-x-3"
          >
            <div className="flex-shrink-0">
              <div className="w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                <ChatBubbleLeftIcon className="w-4 h-4 text-white" />
              </div>
            </div>
            <div className="flex-1">
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                <div className="flex items-center space-x-2">
                  <div className="loading-spinner w-4 h-4 text-gray-600"></div>
                  <span className="text-gray-600">AI is thinking...</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-gray-200">
        <div className="flex space-x-3">
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Ask a question about your document..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!message.trim() || isLoading}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <PaperAirplaneIcon className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Ask about transactions, patterns, anomalies, or any insights from your document
        </p>
      </form>
    </div>
  );
};

export default ChatInterface;
