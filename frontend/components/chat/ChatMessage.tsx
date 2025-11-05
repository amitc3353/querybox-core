'use client';

import { User, Bot, ThumbsUp, ThumbsDown } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CitationCard } from './CitationCard';
import { formatRelativeTime } from '@/lib/utils/formatters';
import type { ConversationMessage } from '@/lib/api/types';

interface ChatMessageProps {
  message: ConversationMessage;
  onFeedback?: (messageId: string, rating: 'helpful' | 'not_helpful') => void;
  onViewDocument?: (documentId: string) => void;
}

export function ChatMessage({ message, onFeedback, onViewDocument }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const confidenceScore = message.confidence_score || 0;

  // Helper to get confidence color and label
  const getConfidenceInfo = (score: number) => {
    if (score >= 0.75) {
      return {
        color: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
        label: 'High Confidence',
      };
    }
    if (score >= 0.5) {
      return {
        color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
        label: 'Medium Confidence',
      };
    }
    return {
      color: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
      label: 'Low Confidence',
    };
  };

  const confidenceInfo = getConfidenceInfo(confidenceScore);

  // User message - simple bubble
  if (isUser) {
    return (
      <div className="flex items-start gap-3 mb-6" role="article" aria-label="User message">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex-shrink-0" aria-hidden="true">
          <User className="w-5 h-5 text-gray-600 dark:text-gray-300" />
        </div>
        <div className="flex-1 max-w-3xl">
          <div className="bg-gray-100 dark:bg-gray-800 rounded-lg px-4 py-3">
            <p className="text-sm text-gray-900 dark:text-white leading-relaxed">
              {message.content}
            </p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 ml-1">
            <time dateTime={message.timestamp}>{formatRelativeTime(message.timestamp)}</time>
          </p>
        </div>
      </div>
    );
  }

  // Assistant message - answer with citations
  return (
    <div className="mb-8" role="article" aria-label="AI assistant message">
      <div className="flex items-start gap-3">
        <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 dark:bg-primary-900/20 flex-shrink-0" aria-hidden="true">
          <Bot className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        </div>
        <div className="flex-1">
          {/* Header with confidence score */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              QueryBox AI
            </span>
            {message.confidence_score !== undefined && (
              <Badge className={`${confidenceInfo.color} border-0 text-xs font-medium`} role="status" aria-label={`Answer confidence: ${confidenceInfo.label}`}>
                {confidenceInfo.label} ({(confidenceScore * 100).toFixed(0)}%)
              </Badge>
            )}
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
              <time dateTime={message.timestamp}>{formatRelativeTime(message.timestamp)}</time>
            </span>
          </div>

          {/* Answer content */}
          <Card className="mb-4">
            <CardContent className="p-4">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <p className="text-sm text-gray-900 dark:text-white leading-relaxed whitespace-pre-wrap">
                  {message.content}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Citations */}
          {message.citations && message.citations.length > 0 && (
            <div className="space-y-3 mb-4" role="region" aria-label="Answer sources">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Sources ({message.citations.length})
              </h4>
              <div className="space-y-2">
                {message.citations.map((citation, index) => (
                  <CitationCard
                    key={citation.chunk_id}
                    citation={citation}
                    index={index}
                    onViewDocument={onViewDocument}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Feedback buttons */}
          {onFeedback && (
            <div className="flex items-center gap-2" role="group" aria-label="Answer feedback">
              <span className="text-xs text-gray-500 dark:text-gray-400" id={`feedback-label-${message.id}`}>
                Was this answer helpful?
              </span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onFeedback(message.id, 'helpful')}
                className="h-7 px-2 hover:bg-green-50 dark:hover:bg-green-900/20"
                aria-label="Mark answer as helpful"
                aria-describedby={`feedback-label-${message.id}`}
              >
                <ThumbsUp className="w-3.5 h-3.5 mr-1 text-green-600 dark:text-green-400" aria-hidden="true" />
                <span className="text-xs">Yes</span>
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onFeedback(message.id, 'not_helpful')}
                className="h-7 px-2 hover:bg-red-50 dark:hover:bg-red-900/20"
                aria-label="Mark answer as not helpful"
                aria-describedby={`feedback-label-${message.id}`}
              >
                <ThumbsDown className="w-3.5 h-3.5 mr-1 text-red-600 dark:text-red-400" aria-hidden="true" />
                <span className="text-xs">No</span>
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
