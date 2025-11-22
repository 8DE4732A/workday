'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

interface SidebarProps {
  className?: string;
}

const navItems = [
  { icon: '📅', label: 'Timeline', href: '/' },
  { icon: '📊', label: 'Dashboard', href: '/dashboard' },
  { icon: '📖', label: 'Guide', href: '/guide' },
  { icon: '⚙️', label: 'Settings', href: '/settings' },
];

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  return (
    <div className={cn('flex flex-col items-center bg-workday-bg', className)}>
      {/* Logo */}
      <div className="py-8">
        <div className="w-10 h-10 bg-workday-text rounded-lg flex items-center justify-center text-white font-bold text-xl">
          W
        </div>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Navigation */}
      <nav className="flex flex-col items-center gap-4 py-8">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'w-12 h-12 flex items-center justify-center rounded-lg transition-all',
                'hover:bg-white hover:shadow-sm',
                isActive && 'bg-white shadow-sm'
              )}
              title={item.label}
            >
              <span className="text-2xl">{item.icon}</span>
            </Link>
          );
        })}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />
    </div>
  );
}
