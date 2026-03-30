'use client';

import { motion } from 'framer-motion';
import { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
  variant?: 'default' | 'search' | 'error' | 'success';
  className?: string;
  /** Custom illustration element */
  illustration?: ReactNode;
}

export function EmptyState({
  title,
  description,
  action,
  variant = 'default',
  className = '',
  illustration,
}: EmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`empty-state ${className}`}
    >
      {/* Illustration */}
      <div className="flex items-center justify-center w-32 h-32 mb-2">
        {illustration || <EmptyStateIllustration variant={variant} />}
      </div>
      
      <h3 className="empty-state-title">{title}</h3>
      
      {description && (
        <p className="empty-state-description">{description}</p>
      )}
      
      {action && (
        <div className="mt-6">
          {action}
        </div>
      )}
    </motion.div>
  );
}

// Default SVG illustrations when no Lottie is provided
function EmptyStateIllustration({ variant }: { variant: string }) {
  const baseClasses = "w-24 h-24";
  
  switch (variant) {
    case 'search':
      return (
        <svg className={baseClasses} viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="40" cy="40" r="24" stroke="currentColor" className="text-border" strokeWidth="4" />
          <path d="M56 56L72 72" stroke="currentColor" className="text-primary" strokeWidth="4" strokeLinecap="round" />
          <circle cx="40" cy="40" r="12" stroke="currentColor" className="text-muted" strokeWidth="2" strokeDasharray="4 4" />
          <circle cx="40" cy="40" r="4" fill="currentColor" className="text-primaryMuted" />
        </svg>
      );
    
    case 'error':
      return (
        <svg className={baseClasses} viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="48" cy="48" r="32" stroke="currentColor" className="text-errorLight" strokeWidth="4" />
          <path d="M36 36L60 60M60 36L36 60" stroke="currentColor" className="text-error" strokeWidth="4" strokeLinecap="round" />
        </svg>
      );
    
    case 'success':
      return (
        <svg className={baseClasses} viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="48" cy="48" r="32" stroke="currentColor" className="text-successLight" strokeWidth="4" />
          <path d="M32 48L44 60L64 36" stroke="currentColor" className="text-success" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    
    default:
      return (
        <svg className={baseClasses} viewBox="0 0 96 96" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="16" y="24" width="64" height="48" rx="8" stroke="currentColor" className="text-border" strokeWidth="3" />
          <rect x="24" y="32" width="24" height="4" rx="2" fill="currentColor" className="text-muted" />
          <rect x="24" y="40" width="48" height="4" rx="2" fill="currentColor" className="text-mutedAlt" />
          <rect x="24" y="48" width="40" height="4" rx="2" fill="currentColor" className="text-muted" />
          <rect x="24" y="56" width="32" height="4" rx="2" fill="currentColor" className="text-mutedAlt" />
          <circle cx="72" cy="64" r="16" fill="currentColor" className="text-primaryLight" />
          <path d="M72 56V64L78 70" stroke="currentColor" className="text-primary" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
  }
}

// Specific empty states for common scenarios
export function NoResultsState({ 
  query,
  onClearFilters 
}: { 
  query?: string;
  onClearFilters?: () => void;
}) {
  return (
    <EmptyState
      variant="search"
      title={query ? `No results for "${query}"` : "No results found"}
      description="Try adjusting your search terms or filters to find what you're looking for."
      action={
        onClearFilters && (
          <button onClick={onClearFilters} className="btn-secondary">
            Clear all filters
          </button>
        )
      }
    />
  );
}

export function NoDataState({ 
  entityName = 'items',
  actionLabel,
  onAction 
}: { 
  entityName?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <EmptyState
      title={`No ${entityName} yet`}
      description={`When you add ${entityName}, they will appear here.`}
      action={
        actionLabel && onAction && (
          <button onClick={onAction} className="btn-primary">
            {actionLabel}
          </button>
        )
      }
    />
  );
}

export function ErrorState({ 
  title = 'Something went wrong',
  description = "We couldn't load this content. Please try again.",
  onRetry 
}: { 
  title?: string;
  description?: string;
  onRetry?: () => void;
}) {
  return (
    <EmptyState
      variant="error"
      title={title}
      description={description}
      action={
        onRetry && (
          <button onClick={onRetry} className="btn-primary">
            Try again
          </button>
        )
      }
    />
  );
}

export function SuccessState({ 
  title,
  description,
  action 
}: { 
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <EmptyState
      variant="success"
      title={title}
      description={description}
      action={action}
    />
  );
}
