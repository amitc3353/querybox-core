'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import type { AnswerQualityLevel } from '@/lib/api/types';

interface ChatInputProps {
  onSubmit: (question: string, qualityLevel: AnswerQualityLevel) => void;
  isLoading?: boolean;
  placeholder?: string;
  initialContext?: {
    documentName?: string;
    content?: string;
  };
}

export function ChatInput({
  onSubmit,
  isLoading,
  placeholder = 'Ask a question about your documents...',
  initialContext,
}: ChatInputProps) {
  const [question, setQuestion] = useState('');
  const [qualityLevel, setQualityLevel] = useState<AnswerQualityLevel>('verified');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [question]);

  const handleSubmit = () => {
    const trimmedQuestion = question.trim();
    if (trimmedQuestion && !isLoading) {
      onSubmit(trimmedQuestion, qualityLevel);
      setQuestion('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Quality level descriptions
  const qualityLevelInfo = {
    basic: {
      label: 'Basic',
      description: 'Fast answers using keyword search',
      icon: '⚡',
      color: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400',
    },
    verified: {
      label: 'Verified',
      description: 'Balanced speed and accuracy with cross-checking',
      icon: '✓',
      color: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    },
    enhanced: {
      label: 'Enhanced',
      description: 'Most thorough with multi-source verification',
      icon: '✨',
      color: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
    },
  };

  const currentQualityInfo = qualityLevelInfo[qualityLevel];

  return (
    <div className="space-y-3">
      {/* Initial context banner (if provided from search) */}
      {initialContext && (
        <div className="bg-primary-50 dark:bg-primary-900/10 border border-primary-200 dark:border-primary-800 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-primary-600 dark:text-primary-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-primary-900 dark:text-primary-200 mb-1">
                Context from search result
              </p>
              {initialContext.documentName && (
                <p className="text-xs text-primary-700 dark:text-primary-300 mb-1">
                  Document: {initialContext.documentName}
                </p>
              )}
              {initialContext.content && (
                <p className="text-xs text-primary-600 dark:text-primary-400 line-clamp-2 italic">
                  &quot;{initialContext.content.substring(0, 150)}...&quot;
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Input area */}
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg shadow-sm">
        {/* Quality level selector */}
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 px-3 sm:px-4 py-2 sm:py-3 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center gap-2 sm:gap-3">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Quality:
            </span>
            <Select
              value={qualityLevel}
              onValueChange={(value) => setQualityLevel(value as AnswerQualityLevel)}
              disabled={isLoading}
            >
              <SelectTrigger className="w-[140px] sm:w-[180px] h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="basic" className="text-xs">
                  <div className="flex items-center gap-2">
                    <span>{qualityLevelInfo.basic.icon}</span>
                    <span>{qualityLevelInfo.basic.label}</span>
                  </div>
                </SelectItem>
                <SelectItem value="verified" className="text-xs">
                  <div className="flex items-center gap-2">
                    <span>{qualityLevelInfo.verified.icon}</span>
                    <span>{qualityLevelInfo.verified.label}</span>
                  </div>
                </SelectItem>
                <SelectItem value="enhanced" className="text-xs">
                  <div className="flex items-center gap-2">
                    <span>{qualityLevelInfo.enhanced.icon}</span>
                    <span>{qualityLevelInfo.enhanced.label}</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Badge className={`${currentQualityInfo.color} border-0 text-xs font-normal w-full sm:w-auto justify-center sm:justify-start`}>
            {currentQualityInfo.description}
          </Badge>
        </div>

        {/* Textarea and send button */}
        <div className="flex items-end gap-3 p-4">
          <Textarea
            ref={textareaRef}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isLoading}
            className="min-h-[60px] max-h-[200px] resize-none border-0 focus-visible:ring-0 focus-visible:ring-offset-0 p-0"
            rows={1}
            aria-label="Ask a question about your documents"
            aria-describedby="input-help-text"
          />
          <Button
            onClick={handleSubmit}
            disabled={!question.trim() || isLoading}
            size="icon"
            className="flex-shrink-0"
            aria-label="Send question"
          >
            <Send className="w-4 h-4" aria-hidden="true" />
          </Button>
        </div>

        {/* Character count and hint */}
        <div id="input-help-text" className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 sm:gap-0 px-3 sm:px-4 pb-2 sm:pb-3 text-xs text-gray-500 dark:text-gray-400">
          <span className="hidden sm:inline">
            Press Enter to send, Shift+Enter for new line
          </span>
          <span className="sm:hidden">
            Enter to send, Shift+Enter for new line
          </span>
          <span aria-live="polite">
            {question.length} characters
          </span>
        </div>
      </div>
    </div>
  );
}
