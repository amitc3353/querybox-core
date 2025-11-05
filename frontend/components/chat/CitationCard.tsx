'use client';

import { FileText, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getCitationQualityColor } from '@/lib/utils/formatters';
import { FILE_TYPE_LABELS } from '@/lib/utils/constants';
import type { Citation } from '@/lib/api/types';

interface CitationCardProps {
  citation: Citation;
  index: number;
  onViewDocument?: (documentId: string) => void;
}

export function CitationCard({ citation, index, onViewDocument }: CitationCardProps) {
  const qualityColor = getCitationQualityColor(citation.quality);

  return (
    <Card className={`border-l-4 ${qualityColor}`}>
      <CardContent className="p-4 space-y-3">
        {/* Header with citation number and quality */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 dark:bg-gray-800 text-xs font-medium">
              {index + 1}
            </div>
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-gray-400" />
              <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                {citation.document_filename}
              </span>
            </div>
          </div>

          <Badge variant="outline" className={`${qualityColor} border-0 text-xs font-medium`}>
            {citation.quality}
          </Badge>
        </div>

        {/* Metadata */}
        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <Badge variant="outline" className="text-xs">
            {FILE_TYPE_LABELS[`.${citation.metadata.file_type}`] ||
             citation.metadata.file_type.toUpperCase()}
          </Badge>

          {citation.page_number && (
            <span>Page {citation.page_number}</span>
          )}

          <span>Chunk {citation.chunk_index + 1}</span>

          <span className="ml-auto">
            Relevance: {(citation.relevance_score * 100).toFixed(0)}%
          </span>
        </div>

        {/* Content excerpt */}
        <div className="text-sm text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-900 rounded p-3">
          <p className="line-clamp-3 italic">
            &quot;{citation.content}&quot;
          </p>
        </div>

        {/* Actions */}
        {onViewDocument && (
          <div className="flex justify-end pt-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onViewDocument(citation.document_id)}
              className="text-xs"
            >
              <ExternalLink className="w-3 h-3 mr-1" />
              View full document
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
