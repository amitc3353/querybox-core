'use client';

import { usePathname } from 'next/navigation';
import { Menu, Bell, Settings, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

interface TopbarProps {
  onMenuClick?: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const pathname = usePathname();

  // Get page title from pathname
  const getPageTitle = () => {
    if (pathname.startsWith('/documents')) return 'Documents';
    if (pathname.startsWith('/search')) return 'Search';
    if (pathname.startsWith('/chat')) return 'Chat';
    if (pathname.startsWith('/analytics')) return 'Analytics';
    return 'Dashboard';
  };

  return (
    <header className="flex items-center h-16 px-4 bg-white border-b border-gray-200 dark:bg-gray-900 dark:border-gray-800" role="banner">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden mr-2"
        onClick={onMenuClick}
        aria-label="Open navigation menu"
        aria-expanded="false"
      >
        <Menu className="w-5 h-5" aria-hidden="true" />
      </Button>

      {/* Page title / Breadcrumbs */}
      <div className="flex-1">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          {getPageTitle()}
        </h1>
      </div>

      {/* Right side actions */}
      <nav className="flex items-center space-x-2" aria-label="Top navigation">
        {/* Notifications */}
        <Button variant="ghost" size="icon" aria-label="Notifications">
          <Bell className="w-5 h-5" aria-hidden="true" />
        </Button>

        {/* Settings */}
        <Button variant="ghost" size="icon" aria-label="Settings">
          <Settings className="w-5 h-5" aria-hidden="true" />
        </Button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="User menu">
              <div className="w-8 h-8 rounded-full bg-primary-500 flex items-center justify-center">
                <User className="w-5 h-5 text-white" aria-hidden="true" />
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Profile</DropdownMenuItem>
            <DropdownMenuItem>Settings</DropdownMenuItem>
            <DropdownMenuItem>API Keys</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Log out</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </nav>
    </header>
  );
}
