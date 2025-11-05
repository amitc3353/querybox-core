'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import {
  Database,
  Server,
  HardDrive,
  Cpu,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils/formatters';

interface ServiceStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'degraded';
  message?: string;
  icon: 'database' | 'server' | 'storage' | 'cpu';
}

interface SystemHealthData {
  services: ServiceStatus[];
  diskUsage?: {
    used: number;
    total: number;
    percentage: number;
  };
  lastChecked: string;
}

interface SystemHealthCardProps {
  data?: SystemHealthData;
  isLoading?: boolean;
}

const iconMap = {
  database: Database,
  server: Server,
  storage: HardDrive,
  cpu: Cpu,
};

const statusConfig = {
  healthy: {
    icon: CheckCircle2,
    color: 'text-green-600 dark:text-green-400',
    badge: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    label: 'Healthy',
  },
  degraded: {
    icon: AlertCircle,
    color: 'text-yellow-600 dark:text-yellow-400',
    badge: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    label: 'Degraded',
  },
  unhealthy: {
    icon: XCircle,
    color: 'text-red-600 dark:text-red-400',
    badge: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
    label: 'Unhealthy',
  },
};

export function SystemHealthCard({ data, isLoading }: SystemHealthCardProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="animate-pulse flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-800 rounded-lg" />
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-24 mb-2" />
                  <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-32" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>System Health</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-gray-400 py-8">
            Unable to load system health data
          </div>
        </CardContent>
      </Card>
    );
  }

  const overallHealthy = data.services.every((s) => s.status === 'healthy');
  const overallStatus = overallHealthy
    ? 'healthy'
    : data.services.some((s) => s.status === 'unhealthy')
    ? 'unhealthy'
    : 'degraded';

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>System Health</CardTitle>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Last checked {formatRelativeTime(data.lastChecked)}
            </p>
          </div>
          <Badge className={statusConfig[overallStatus].badge}>
            {statusConfig[overallStatus].label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Service statuses */}
        {data.services.map((service) => {
          const ServiceIcon = iconMap[service.icon];
          const StatusIcon = statusConfig[service.status].icon;
          const statusColor = statusConfig[service.status].color;

          return (
            <div key={service.name} className="flex items-start gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800">
                <ServiceIcon className="w-5 h-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">
                    {service.name}
                  </span>
                  <StatusIcon className={`w-4 h-4 ${statusColor}`} />
                </div>
                {service.message && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {service.message}
                  </p>
                )}
              </div>
            </div>
          );
        })}

        {/* Disk usage */}
        {data.diskUsage && (
          <div className="pt-4 border-t border-gray-200 dark:border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-900 dark:text-white">
                Disk Usage
              </span>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {data.diskUsage.percentage.toFixed(1)}%
              </span>
            </div>
            <Progress value={data.diskUsage.percentage} className="h-2" />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {(data.diskUsage.used / 1024 / 1024 / 1024).toFixed(2)} GB /{' '}
              {(data.diskUsage.total / 1024 / 1024 / 1024).toFixed(2)} GB used
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
