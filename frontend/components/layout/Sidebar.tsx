'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, Search, MessageSquare, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { APP_NAME } from '@/lib/utils/constants';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  {
    name: 'Documents',
    href: '/documents',
    icon: FileText,
  },
  {
    name: 'Search',
    href: '/search',
    icon: Search,
  },
  {
    name: 'Chat',
    href: '/chat',
    icon: MessageSquare,
  },
  {
    name: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
];

interface SidebarProps {
  mobile?: boolean;
  onNavigate?: () => void;
}

export function Sidebar({ mobile = false, onNavigate }: SidebarProps = {}) {
  const pathname = usePathname();

  return (
    <aside className={cn(
      "flex flex-col w-64 bg-white border-r border-gray-200 dark:bg-gray-900 dark:border-gray-800",
      !mobile && "hidden md:flex"
    )}
    aria-label="Main navigation"
    role="navigation"
    >
      {/* Logo */}
      <div className="flex items-center h-16 px-6 border-b border-gray-200 dark:border-gray-800">
        <Link href="/documents" className="flex items-center space-x-2" aria-label="Go to home page">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center" aria-hidden="true">
            <FileText className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900 dark:text-white">
            {APP_NAME}
          </span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-1" aria-label="Primary navigation">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-label={`${item.name} page`}
              aria-current={isActive ? 'page' : undefined}
              className={cn(
                'flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/20 dark:text-primary-400'
                  : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800'
              )}
            >
              <Icon
                className={cn(
                  'w-5 h-5 mr-3',
                  isActive
                    ? 'text-primary-600 dark:text-primary-400'
                    : 'text-gray-500 dark:text-gray-400'
                )}
                aria-hidden="true"
              />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-800">
        <div className="text-xs text-gray-500 dark:text-gray-400">
          QueryBox v1.0.0
        </div>
      </div>
    </aside>
  );
}
