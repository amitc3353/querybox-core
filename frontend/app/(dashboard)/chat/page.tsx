'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { ChatInput } from '@/components/chat/ChatInput';
import { Button } from '@/components/ui/button';
import { useGenerateAnswer, useAnswerFeedback } from '@/lib/api/hooks';
import type { ConversationMessage, AnswerQualityLevel } from '@/lib/api/types';

export default function ChatPage() {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [initialContext, setInitialContext] = useState<{
    documentName?: string;
    content?: string;
  } | undefined>();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const generateAnswerMutation = useGenerateAnswer();
  const feedbackMutation = useAnswerFeedback();

  // Check for initial context from search page
  useEffect(() => {
    const contextStr = sessionStorage.getItem('chatContext');
    if (contextStr) {
      try {
        const context = JSON.parse(contextStr);
        setInitialContext({
          documentName: context.documentName,
          content: context.content,
        });
        // Clear after reading
        sessionStorage.removeItem('chatContext');
      } catch (e) {
        console.error('Failed to parse chat context:', e);
      }
    }
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmitQuestion = useCallback(
    (question: string, qualityLevel: AnswerQualityLevel) => {
      // Add user message immediately
      const userMessage: ConversationMessage = {
        id: `user-${Date.now()}`,
        conversation_id: conversationId || '',
        role: 'user',
        content: question,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMessage]);

      // Generate answer
      generateAnswerMutation.mutate(
        {
          query: question, // Changed from 'question' to match backend
          include_citations: true,
          top_k: 5, // Number of chunks to retrieve
          temperature: 0.2, // LLM temperature
        },
        {
          onSuccess: (data) => {
            // Update conversation ID if this is the first message
            if (!conversationId) {
              setConversationId(data.conversation_id);
            }

            // Add assistant message
            const assistantMessage: ConversationMessage = {
              id: `assistant-${Date.now()}`,
              conversation_id: data.conversation_id,
              role: 'assistant',
              content: data.answer,
              timestamp: new Date().toISOString(),
              citations: data.citations,
              confidence_score: data.confidence_score,
            };

            setMessages((prev) => [...prev, assistantMessage]);
          },
          onError: (error) => {
            // Add error message
            const errorMessage: ConversationMessage = {
              id: `error-${Date.now()}`,
              conversation_id: conversationId || '',
              role: 'assistant',
              content: `Sorry, I encountered an error: ${error instanceof Error ? error.message : 'Unable to generate answer. Please try again.'}`,
              timestamp: new Date().toISOString(),
              confidence_score: 0,
            };

            setMessages((prev) => [...prev, errorMessage]);
          },
        }
      );
    },
    [conversationId, generateAnswerMutation]
  );

  const handleFeedback = useCallback(
    (messageId: string, rating: 'helpful' | 'not_helpful') => {
      feedbackMutation.mutate({
        answer_id: messageId,
        rating,
      });
    },
    [feedbackMutation]
  );

  const handleClearConversation = () => {
    setMessages([]);
    setConversationId(undefined);
    setInitialContext(undefined);
  };

  return (
    <div className="h-[calc(100vh-7rem)] sm:h-[calc(100vh-8rem)] flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 pb-3 sm:pb-4 border-b border-gray-200 dark:border-gray-800">
        <div className="flex flex-col sm:flex-row items-start sm:justify-between gap-3">
          <div className="flex-1">
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-1 sm:mb-2">
              Chat & Q&A
            </h1>
            <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
              Ask questions about your documents and get AI-powered answers with citations
            </p>
          </div>
          {messages.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearConversation}
              className="w-full sm:w-auto"
            >
              Clear conversation
            </Button>
          )}
        </div>
      </div>

      {/* Messages container */}
      <div className="flex-1 overflow-y-auto py-4 sm:py-6 space-y-4 sm:space-y-6">
        {messages.length === 0 ? (
          // Empty state
          <div className="h-full flex items-center justify-center px-4">
            <div className="text-center max-w-md">
              <div className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-3 sm:mb-4 rounded-full bg-primary-100 dark:bg-primary-900/20 flex items-center justify-center">
                <svg
                  className="w-6 h-6 sm:w-8 sm:h-8 text-primary-600 dark:text-primary-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                  />
                </svg>
              </div>
              <h3 className="text-base sm:text-lg font-medium text-gray-900 dark:text-white mb-2">
                Start a conversation
              </h3>
              <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mb-3 sm:mb-4">
                Ask any question about your uploaded documents. I&apos;ll provide answers with citations and confidence scores.
              </p>
              <div className="text-xs text-gray-400 dark:text-gray-500">
                <p className="mb-2">💡 Tips:</p>
                <ul className="space-y-1 text-left">
                  <li>• Use <strong>Basic</strong> for quick answers</li>
                  <li>• Use <strong>Verified</strong> for balanced accuracy (recommended)</li>
                  <li>• Use <strong>Enhanced</strong> for most thorough analysis</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          // Messages list
          <div className="max-w-4xl mx-auto w-full px-2 sm:px-0">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onFeedback={handleFeedback}
              />
            ))}

            {/* Loading indicator */}
            {generateAnswerMutation.isPending && (
              <div className="flex items-start gap-3 mb-6">
                <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/20 flex-shrink-0">
                  <Loader2 className="w-5 h-5 text-primary-600 dark:text-primary-400 animate-spin" />
                </div>
                <div className="flex-1">
                  <div className="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3">
                    <p className="text-sm text-gray-600 dark:text-gray-400 italic">
                      Analyzing documents and generating answer...
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Error state */}
            {generateAnswerMutation.isError && !messages.some(m => m.content.includes('error')) && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h3 className="text-sm font-medium text-red-900 dark:text-red-200 mb-1">
                      Failed to generate answer
                    </h3>
                    <p className="text-sm text-red-700 dark:text-red-300">
                      {generateAnswerMutation.error instanceof Error
                        ? generateAnswerMutation.error.message
                        : 'Unable to generate answer. Please check if the backend is running and try again.'}
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 pt-4 border-t border-gray-200 dark:border-gray-800">
        <ChatInput
          onSubmit={handleSubmitQuestion}
          isLoading={generateAnswerMutation.isPending}
          initialContext={initialContext}
        />
      </div>
    </div>
  );
}
