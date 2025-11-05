'use client';

import { FileText, MessageSquare, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatDate } from '@/lib/utils/formatters';
import { FILE_TYPE_LABELS } from '@/lib/utils/constants';
import type { SearchResultChunk } from '@/lib/api/types';

interface SearchResultsProps {
  results: SearchResultChunk[];
  isLoading?: boolean;
  searchTime?: number;
  onAskAbout?: (chunk: SearchResultChunk) => void;
}

export function SearchResults({
  results,
  isLoading,
  searchTime,
  onAskAbout,
}: SearchResultsProps) {
  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="space-y-2">
              <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-3/4" />
              <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-1/2" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded" />
                <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded" />
                <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-5/6" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  // Empty state
  if (results.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <FileText className="w-12 h-12 text-gray-400 mb-4" />
          <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            No results found
          </p>
          <p className="text-sm text-gray-500 text-center max-w-sm">
            Try adjusting your search query or filters, or use a different search strategy
          </p>
        </CardContent>
      </Card>
    );
  }

  // Helper function to get relevance color
  const getRelevanceColor = (score: number) => {
    if (score >= 0.7) return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20';
    if (score >= 0.4) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20';
    return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20';
  };

  // Helper function to get relevance label
  const getRelevanceLabel = (score: number) => {
    if (score >= 0.7) return 'High';
    if (score >= 0.4) return 'Medium';
    return 'Low';
  };

  return (
    <div className="space-y-4">
      {/* Results header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-1 sm:gap-0 text-xs sm:text-sm text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
        <span>
          Found {results.length} result{results.length !== 1 ? 's' : ''}
        </span>
        {searchTime !== undefined && (
          <span>Search completed in {searchTime}ms</span>
        )}
      </div>

      {/* Results list */}
      <div className="space-y-4" role="region" aria-label="Search results">
        {results.map((result, index) => {
          const relevanceScore = result.relevance_score || result.score;
          const normalizedScore = relevanceScore > 1 ? relevanceScore / 100 : relevanceScore;

          return (
            <Card key={result.chunk_id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex flex-col sm:flex-row items-start sm:justify-between gap-3">
                  <div className="flex-1 min-w-0 w-full">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                      <h3 className="font-medium text-sm sm:text-base text-gray-900 dark:text-white truncate">
                        {result.document_filename}
                      </h3>
                    </div>

                    <div className="flex items-center gap-2 flex-wrap text-sm text-gray-500">
                      <Badge variant="outline" className="text-xs">
                        {FILE_TYPE_LABELS[`.${result.metadata.file_type}`] ||
                         result.metadata.file_type.toUpperCase()}
                      </Badge>

                      {result.page_number && (
                        <span className="text-xs">Page {result.page_number}</span>
                      )}

                      <span className="text-xs">Chunk {result.chunk_index + 1}</span>

                      {result.metadata.upload_date && (
                        <span className="text-xs hidden sm:inline">
                          {formatDate(result.metadata.upload_date, 'MMM d, yyyy')}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-start">
                    <Badge
                      className={`${getRelevanceColor(normalizedScore)} border-0 font-medium text-xs whitespace-nowrap`}
                    >
                      {getRelevanceLabel(normalizedScore)} ({(normalizedScore * 100).toFixed(0)}%)
                    </Badge>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="space-y-3">
                {/* Content snippet */}
                <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  {result.highlights && result.highlights.length > 0 ? (
                    // Show highlights if available
                    <div className="space-y-2">
                      {result.highlights.map((highlight, i) => (
                        <p key={i}>
                          <span
                            dangerouslySetInnerHTML={{ __html: highlight }}
                            className="[&_mark]:bg-yellow-200 [&_mark]:text-gray-900 [&_mark]:font-medium [&_mark]:px-1 [&_mark]:rounded dark:[&_mark]:bg-yellow-900/30 dark:[&_mark]:text-yellow-200"
                          />
                        </p>
                      ))}
                    </div>
                  ) : (
                    // Fallback to regular content
                    <p className="line-clamp-3">{result.content}</p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2 pt-2">
                  {onAskAbout && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onAskAbout(result)}
                      className="w-full sm:w-auto text-primary-600 border-primary-200 hover:bg-primary-50 hover:text-primary-700 dark:text-primary-400 dark:border-primary-800 dark:hover:bg-primary-900/20"
                    >
                      <MessageSquare className="w-4 h-4 mr-1.5" />
                      Ask about this
                    </Button>
                  )}

                  <Button
                    size="sm"
                    variant="ghost"
                    className="w-full sm:w-auto sm:ml-auto"
                  >
                    <ExternalLink className="w-4 h-4 mr-1.5" />
                    View document
                  </Button>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
