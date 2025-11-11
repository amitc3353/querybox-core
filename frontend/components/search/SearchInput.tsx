'use client';

import { useState, useEffect } from 'react';
import { Search, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import {
  SEARCH_STRATEGIES,
  SEARCH_STRATEGY_LABELS,
  MIN_QUERY_LENGTH,
} from '@/lib/utils/constants';
import type { SearchStrategy, SearchFilters } from '@/lib/api/types';

interface SearchInputProps {
  onSearch: (query: string, strategy: SearchStrategy, filters: SearchFilters) => void;
  isLoading?: boolean;
}

export function SearchInput({ onSearch, isLoading }: SearchInputProps) {
  const [query, setQuery] = useState('');
  const [strategy, setStrategy] = useState<SearchStrategy>('hybrid');
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({});

  // Auto-search disabled - user must click Search button or press Enter
  // If you want to re-enable auto-search on typing, uncomment this useEffect:
  // useEffect(() => {
  //   if (query.length < MIN_QUERY_LENGTH) return;
  //   const timer = setTimeout(() => {
  //     onSearch(query, strategy, filters);
  //   }, 500);
  //   return () => clearTimeout(timer);
  // }, [query, strategy, filters]);

  const handleSearch = () => {
    if (query.length >= MIN_QUERY_LENGTH) {
      onSearch(query, strategy, filters);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const activeFilterCount = Object.keys(filters).filter(
    (key) => filters[key as keyof SearchFilters] !== undefined
  ).length;

  const clearFilters = () => {
    setFilters({});
  };

  return (
    <div className="space-y-4">
      {/* Main search bar */}
      <div className="flex items-center gap-3" role="search" aria-label="Document search">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" aria-hidden="true" />
          <Input
            type="search"
            placeholder="Search across your documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-10 pr-4"
            disabled={isLoading}
            aria-label="Search query"
            aria-describedby="search-help-text"
          />
        </div>

        <Select
          value={strategy}
          onValueChange={(value) => setStrategy(value as SearchStrategy)}
          disabled={isLoading}
        >
          <SelectTrigger className="w-[200px]" aria-label="Search strategy">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={SEARCH_STRATEGIES.KEYWORD}>
              {SEARCH_STRATEGY_LABELS.keyword}
            </SelectItem>
            <SelectItem value={SEARCH_STRATEGIES.SEMANTIC}>
              {SEARCH_STRATEGY_LABELS.semantic}
            </SelectItem>
            <SelectItem value={SEARCH_STRATEGIES.HYBRID}>
              {SEARCH_STRATEGY_LABELS.hybrid}
            </SelectItem>
          </SelectContent>
        </Select>

        <Button
          variant="outline"
          size="icon"
          onClick={() => setShowFilters(!showFilters)}
          className={activeFilterCount > 0 ? 'border-primary-500' : ''}
          aria-label={`${showFilters ? 'Hide' : 'Show'} advanced filters${activeFilterCount > 0 ? ` (${activeFilterCount} active)` : ''}`}
          aria-expanded={showFilters}
        >
          <Filter className="w-5 h-5" aria-hidden="true" />
          {activeFilterCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-primary-500 text-white text-xs flex items-center justify-center" aria-hidden="true">
              {activeFilterCount}
            </span>
          )}
        </Button>

        <Button onClick={handleSearch} disabled={isLoading || query.length < MIN_QUERY_LENGTH} aria-label="Execute search">
          <Search className="w-4 h-4 mr-2" aria-hidden="true" />
          Search
        </Button>
      </div>

      {/* Advanced filters */}
      {showFilters && (
        <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
              Advanced Filters
            </h3>
            {activeFilterCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                aria-label="Clear all filters"
              >
                <X className="w-4 h-4 mr-1" aria-hidden="true" />
                Clear Filters
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* File type filter */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                File Type
              </label>
              <Select
                value={filters.file_types?.[0] || 'all'}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    file_types: value === 'all' ? undefined : [value],
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="All types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All types</SelectItem>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="docx">Word</SelectItem>
                  <SelectItem value="xlsx">Excel</SelectItem>
                  <SelectItem value="pptx">PowerPoint</SelectItem>
                  <SelectItem value="txt">Text</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Min score filter */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                Minimum Relevance
              </label>
              <Select
                value={filters.min_score?.toString() || 'none'}
                onValueChange={(value) =>
                  setFilters({
                    ...filters,
                    min_score: value === 'none' ? undefined : parseFloat(value),
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Any relevance" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Any relevance</SelectItem>
                  <SelectItem value="0.3">30% or higher</SelectItem>
                  <SelectItem value="0.5">50% or higher</SelectItem>
                  <SelectItem value="0.7">70% or higher</SelectItem>
                  <SelectItem value="0.9">90% or higher</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Date range filter */}
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 block">
                Uploaded Within
              </label>
              <Select
                value={filters.date_from ? 'custom' : 'all'}
                onValueChange={(value) => {
                  if (value === 'all') {
                    setFilters({
                      ...filters,
                      date_from: undefined,
                      date_to: undefined,
                    });
                  } else {
                    const date = new Date();
                    const daysAgo = parseInt(value);
                    date.setDate(date.getDate() - daysAgo);
                    setFilters({
                      ...filters,
                      date_from: date.toISOString().split('T')[0],
                      date_to: undefined,
                    });
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Any time" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Any time</SelectItem>
                  <SelectItem value="7">Last 7 days</SelectItem>
                  <SelectItem value="30">Last 30 days</SelectItem>
                  <SelectItem value="90">Last 90 days</SelectItem>
                  <SelectItem value="365">Last year</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Active filters display */}
          {activeFilterCount > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-500">Active filters:</span>
              {filters.file_types && (
                <Badge variant="secondary">
                  Type: {filters.file_types[0].toUpperCase()}
                </Badge>
              )}
              {filters.min_score && (
                <Badge variant="secondary">
                  Min score: {(filters.min_score * 100).toFixed(0)}%
                </Badge>
              )}
              {filters.date_from && (
                <Badge variant="secondary">
                  After: {filters.date_from}
                </Badge>
              )}
            </div>
          )}
        </div>
      )}

      {/* Helper text */}
      {query.length > 0 && query.length < MIN_QUERY_LENGTH && (
        <p id="search-help-text" className="text-sm text-gray-500" role="status" aria-live="polite">
          Enter at least {MIN_QUERY_LENGTH} characters to search
        </p>
      )}
    </div>
  );
}
