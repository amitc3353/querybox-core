'use client';

import { useState, useMemo } from 'react';
import {
  FileText,
  HardDrive,
  CheckCircle2,
  AlertCircle,
  RefreshCcw,
} from 'lucide-react';
import { StatsCard } from '@/components/analytics/StatsCard';
import { UploadTrendChart } from '@/components/analytics/UploadTrendChart';
import { DocumentTypeChart } from '@/components/analytics/DocumentTypeChart';
import { SystemHealthCard } from '@/components/analytics/SystemHealthCard';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useDocumentStats } from '@/lib/api/hooks';
import { formatFileSize } from '@/lib/utils/formatters';
import { subDays } from 'date-fns';

type TimeRange = '7d' | '30d' | '90d' | 'all';

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const { data: stats, isLoading: statsLoading, refetch } = useDocumentStats();

  // Generate mock upload trend data based on time range
  const uploadTrendData = useMemo(() => {
    const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 365;
    const data = [];
    const today = new Date();

    for (let i = days - 1; i >= 0; i--) {
      const date = subDays(today, i);
      const uploads = Math.floor(Math.random() * 10) + 1; // Random 1-10 uploads per day
      data.push({
        date: date.toISOString(),
        uploads,
      });
    }

    return data;
  }, [timeRange]);

  // Generate mock document type data from stats
  const documentTypeData = useMemo(() => {
    if (!stats) {
      return [
        { fileType: 'pdf', count: 45 },
        { fileType: 'docx', count: 23 },
        { fileType: 'xlsx', count: 12 },
        { fileType: 'pptx', count: 8 },
        { fileType: 'txt', count: 5 },
      ];
    }

    // In a real implementation, this would come from the API
    // For now, using mock data based on total documents
    const total = stats.total_documents || 0;
    return [
      { fileType: 'pdf', count: Math.floor(total * 0.48) },
      { fileType: 'docx', count: Math.floor(total * 0.25) },
      { fileType: 'xlsx', count: Math.floor(total * 0.13) },
      { fileType: 'pptx', count: Math.floor(total * 0.09) },
      { fileType: 'txt', count: Math.floor(total * 0.05) },
    ].filter((item) => item.count > 0);
  }, [stats]);

  // System health data (mock - would come from API)
  const systemHealthData = {
    services: [
      {
        name: 'Database',
        status: 'healthy' as const,
        message: 'PostgreSQL running',
        icon: 'database' as const,
      },
      {
        name: 'Redis Cache',
        status: 'healthy' as const,
        message: 'Connected and responsive',
        icon: 'server' as const,
      },
      {
        name: 'Storage',
        status: 'healthy' as const,
        message: 'Filesystem accessible',
        icon: 'storage' as const,
      },
      {
        name: 'Ollama (LLM)',
        status: 'healthy' as const,
        message: 'qwen2:7b model loaded',
        icon: 'cpu' as const,
      },
    ],
    diskUsage: {
      used: 50 * 1024 * 1024 * 1024, // 50 GB
      total: 500 * 1024 * 1024 * 1024, // 500 GB
      percentage: 10,
    },
    lastChecked: new Date().toISOString(),
  };

  const handleRefresh = () => {
    refetch();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-2">
            Analytics
          </h1>
          <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400">
            Monitor your document library and system performance
          </p>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <Select value={timeRange} onValueChange={(v) => setTimeRange(v as TimeRange)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
              <SelectItem value="all">All time</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="icon" onClick={handleRefresh}>
            <RefreshCcw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6">
        <StatsCard
          title="Total Documents"
          value={stats?.total_documents || 0}
          icon={FileText}
          description="Uploaded documents"
          iconColor="text-primary-600 dark:text-primary-400"
          iconBgColor="bg-primary-100 dark:bg-primary-900/20"
        />
        <StatsCard
          title="Total Storage"
          value={stats?.total_size ? formatFileSize(stats.total_size) : '0 B'}
          icon={HardDrive}
          description="Space used"
          iconColor="text-blue-600 dark:text-blue-400"
          iconBgColor="bg-blue-100 dark:bg-blue-900/20"
        />
        <StatsCard
          title="Completed"
          value={stats?.by_status?.completed || 0}
          icon={CheckCircle2}
          description="Ready for search"
          iconColor="text-green-600 dark:text-green-400"
          iconBgColor="bg-green-100 dark:bg-green-900/20"
        />
        <StatsCard
          title="Failed"
          value={stats?.by_status?.failed || 0}
          icon={AlertCircle}
          description="Needs attention"
          iconColor="text-red-600 dark:text-red-400"
          iconBgColor="bg-red-100 dark:bg-red-900/20"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        <UploadTrendChart data={uploadTrendData} isLoading={statsLoading} />
        <DocumentTypeChart data={documentTypeData} isLoading={statsLoading} />
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 md:gap-6">
        <div className="lg:col-span-2">
          <SystemHealthCard data={systemHealthData} />
        </div>
        <div className="bg-gradient-to-br from-primary-50 to-primary-100 dark:from-primary-900/10 dark:to-primary-800/10 rounded-lg p-6 border border-primary-200 dark:border-primary-800">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            System Status
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
            All systems operational
          </p>
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Uptime</span>
              <span className="font-medium text-gray-900 dark:text-white">99.9%</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Avg Response Time</span>
              <span className="font-medium text-gray-900 dark:text-white">245ms</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">API Calls (24h)</span>
              <span className="font-medium text-gray-900 dark:text-white">1,234</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Error Rate</span>
              <span className="font-medium text-gray-900 dark:text-white">0.1%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
