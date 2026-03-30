'use client';

import { ReactNode } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { ChevronRight } from 'lucide-react';

interface TileHeaderProps {
  title: string;
  actionLabel?: string;
  actionHref?: string;
  onActionClick?: () => void;
  icon?: ReactNode;
  className?: string;
}

export function TileHeader({ 
  title, 
  actionLabel, 
  actionHref, 
  onActionClick,
  icon,
  className 
}: TileHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)}>
      <div className="flex items-center gap-3">
        {icon && (
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
            {icon}
          </div>
        )}
        <h2 className="text-lg font-semibold text-text">{title}</h2>
      </div>
      {(actionLabel || actionHref) && (
        actionHref ? (
          <Link
            href={actionHref}
            className={cn(
              'text-sm font-medium text-primary hover:text-primaryHover transition-colors',
              'flex items-center gap-1'
            )}
          >
            {actionLabel || 'View All'}
            <ChevronRight className="h-4 w-4" />
          </Link>
        ) : (
          <button
            type="button"
            onClick={onActionClick}
            className={cn(
              'text-sm font-medium text-primary hover:text-primaryHover transition-colors',
              'flex items-center gap-1',
              'cursor-pointer'
            )}
          >
            {actionLabel || 'View All'}
            <ChevronRight className="h-4 w-4" />
          </button>
        )
      )}
    </div>
  );
}

