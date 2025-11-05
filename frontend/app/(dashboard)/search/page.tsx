'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { AlertCircle } from 'lucide-react';
import { SearchInput } from '@/components/search/SearchInput';
import { SearchResults } from '@/components/search/SearchResults';
import { Button } from '@/components/ui/button';
import { useSearchMutation } from '@/lib/api/hooks';
import type { SearchStrategy, SearchFilters, SearchResultChunk } from '@/lib/api/types';

export default function SearchPage() {
  const router = useRouter();
  const [searchState, setSearchState] = useState<{
    query: string;
    strategy: SearchStrategy;
    filters: SearchFilters;
  } | null>(null);

  const searchMutation = useSearchMutation();

  const handleSearch = useCallback((
    query: string,
    strategy: SearchStrategy,
    filters: SearchFilters
  ) => {
    setSearchState({ query, strategy, filters });

    searchMutation.mutate({
      query,
      strategy,
      filters,
      limit: 20,
    });
  }, [searchMutation]);

  const handleAskAbout = useCallback((chunk: SearchResultChunk) => {
    // Store in session storage for chat page to pick up
    sessionStorage.setItem('chatContext', JSON.stringify({
      documentId: chunk.document_id,
      documentName: chunk.document_filename,
      chunkId: chunk.chunk_id,
      content: chunk.content,
    }));

    router.push('/chat');
  }, [router]);

  return (
    <div className="space-y-4 md:space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Search
        </h1>
        <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
          Search across your documents with keyword, semantic, or hybrid strategies
        </p>
      </div>

      {/* Search input */}
      <SearchInput
        onSearch={handleSearch}
        isLoading={searchMutation.isPending}
      />

      {/* Error state */}
      {searchMutation.isError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-red-900 dark:text-red-200 mb-1">
                Search failed
              </h3>
              <p className="text-sm text-red-700 dark:text-red-300 mb-3">
                {searchMutation.error instanceof Error
                  ? searchMutation.error.message
                  : 'Unable to complete search. Please check if the backend is running.'}
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  if (searchState) {
                    handleSearch(searchState.query, searchState.strategy, searchState.filters);
                  }
                }}
                className="border-red-200 text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-300 dark:hover:bg-red-900/30"
              >
                Try again
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Search results */}
      {searchMutation.data && (
        <SearchResults
          results={searchMutation.data.results}
          isLoading={searchMutation.isPending}
          searchTime={searchMutation.data.search_time_ms}
          onAskAbout={handleAskAbout}
        />
      )}

      {/* Initial state - show when no search has been performed */}
      {!searchMutation.data && !searchMutation.isPending && !searchMutation.isError && (
        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-12 text-center">
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Enter a search query above to find relevant content across your documents
          </p>
          <div className="text-sm text-gray-400 dark:text-gray-500">
            <p>💡 Tips:</p>
            <ul className="mt-2 space-y-1">
              <li>• Use <strong>Keyword</strong> for exact term matching (fastest)</li>
              <li>• Use <strong>Semantic</strong> for meaning-based search (most intelligent)</li>
              <li>• Use <strong>Hybrid</strong> for best of both worlds (recommended)</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
