'use client';

import { motion } from 'framer-motion';
import { Skeleton as BaseSkeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
}

export function Skeleton({ className = '', variant = 'rectangular' }: SkeletonProps) {
  const variantClasses = {
    text: 'h-4 rounded',
    circular: 'rounded-full aspect-square',
    rectangular: 'h-full rounded-xl',
  };

  return (
    <BaseSkeleton
      className={cn(variantClasses[variant], className)}
    />
  );
}

export function CardSkeleton() {
  return (
    <div className="card p-6">
      <div className="flex items-start gap-3 mb-4">
        <Skeleton className="w-10 h-10 rounded-xl" />
        <div className="flex-1">
          <Skeleton variant="text" className="w-3/4 h-5 mb-2" />
          <Skeleton variant="text" className="w-1/2 h-4" />
        </div>
      </div>
      <div className="space-y-2">
        <Skeleton variant="text" className="w-full h-3" />
        <Skeleton variant="text" className="w-2/3 h-3" />
      </div>
      <div className="flex gap-2 mt-4">
        <Skeleton className="w-16 h-6 rounded-full" />
        <Skeleton className="w-20 h-6 rounded-full" />
      </div>
    </div>
  );
}

export function ProgramCardSkeleton() {
  return (
    <div className="card p-6">
      <div className="flex items-start gap-3 mb-4">
        <Skeleton className="w-11 h-11 rounded-xl" />
        <div className="flex-1 min-w-0">
          <Skeleton variant="text" className="w-4/5 h-6 mb-2" />
          <Skeleton variant="text" className="w-1/2 h-4" />
        </div>
      </div>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded" />
          <Skeleton variant="text" className="w-32 h-4" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded" />
          <Skeleton variant="text" className="w-40 h-4" />
        </div>
        <div className="flex items-center gap-2">
          <Skeleton className="w-4 h-4 rounded" />
          <Skeleton variant="text" className="w-24 h-4" />
        </div>
      </div>
      <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
        <Skeleton className="w-20 h-6 rounded-full" />
        <Skeleton className="w-16 h-5 rounded" />
      </div>
    </div>
  );
}

export function InstitutionCardSkeleton() {
  return (
    <div className="card p-5">
      <div className="flex items-center gap-4">
        <Skeleton className="w-14 h-14 rounded-2xl" />
        <div className="flex-1">
          <Skeleton variant="text" className="w-3/4 h-5 mb-2" />
          <Skeleton variant="text" className="w-1/2 h-4" />
        </div>
        <Skeleton className="w-8 h-8 rounded-full" />
      </div>
      <div className="mt-4 grid grid-cols-3 gap-4">
        <div>
          <Skeleton variant="text" className="w-full h-3 mb-1" />
          <Skeleton variant="text" className="w-2/3 h-4" />
        </div>
        <div>
          <Skeleton variant="text" className="w-full h-3 mb-1" />
          <Skeleton variant="text" className="w-2/3 h-4" />
        </div>
        <div>
          <Skeleton variant="text" className="w-full h-3 mb-1" />
          <Skeleton variant="text" className="w-2/3 h-4" />
        </div>
      </div>
    </div>
  );
}

export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <tr className="border-b border-border">
      {Array.from({ length: columns }).map((_, i) => (
        <td key={i} className="py-4 px-4">
          <Skeleton variant="text" className="h-4 w-full max-w-[120px]" />
        </td>
      ))}
    </tr>
  );
}

export function FilterSidebarSkeleton() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i}>
          <Skeleton variant="text" className="w-24 h-4 mb-3" />
          <Skeleton className="w-full h-10 rounded-xl" />
        </div>
      ))}
    </div>
  );
}

export function LoadingSpinner({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'h-5 w-5 border-2',
    md: 'h-8 w-8 border-[3px]',
    lg: 'h-12 w-12 border-4',
  };

  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: 'linear' }}
      className={`${sizeClasses[size]} border-primary border-t-transparent rounded-full`}
    />
  );
}

export function PageLoadingState({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <LoadingSpinner size="lg" />
      <p className="text-textSecondary text-sm animate-pulse">{message}</p>
    </div>
  );
}

export function InlineLoadingState() {
  return (
    <div className="flex items-center gap-2 text-textSecondary">
      <LoadingSpinner size="sm" />
      <span className="text-sm">Loading...</span>
    </div>
  );
}
