'use client';

import { motion } from 'framer-motion';

// These components describe how many fields a record has filled
// (`data_completeness_score`), not whether a person checked it. Never label them
// "verified": that word is reserved for human verification (VERIFICATION_POLICY.md).

/** A score of null, undefined or 0 means the record has not been assessed. */
function isAssessed(score: number | null | undefined): score is number {
  return typeof score === 'number' && score > 0;
}

function NotAssessed({ className = '' }: { className?: string }) {
  return (
    <span className={`text-2xs font-medium text-textMuted ${className}`}>Not assessed</span>
  );
}

interface DataQualityBarProps {
  score: number | null | undefined; // 0-100
  showLabel?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function DataQualityBar({
  score,
  showLabel = true,
  size = 'md',
  className = ''
}: DataQualityBarProps) {
  if (!isAssessed(score)) {
    return <NotAssessed className={className} />;
  }

  const getColor = (score: number) => {
    if (score >= 80) return 'bg-success';
    if (score >= 50) return 'bg-warning';
    return 'bg-error';
  };

  const getLabel = (score: number) => {
    if (score >= 80) return 'Complete';
    if (score >= 50) return 'Partial';
    return 'Limited';
  };

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-1.5',
    lg: 'h-2',
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`completeness-bar flex-1 ${sizeClasses[size]}`}>
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(score, 100)}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className={`completeness-fill ${getColor(score)}`}
        />
      </div>
      {showLabel && (
        <span className="text-2xs font-medium text-textSecondary min-w-[50px] text-right">
          {getLabel(score)}
        </span>
      )}
    </div>
  );
}

interface DataQualityDotProps {
  score: number | null | undefined;
  showTooltip?: boolean;
  className?: string;
}

export function DataQualityDot({
  score,
  showTooltip = false,
  className = ''
}: DataQualityDotProps) {
  if (!isAssessed(score)) {
    return <NotAssessed className={className} />;
  }

  const getColorClass = (score: number) => {
    if (score >= 80) return 'quality-dot-high';
    if (score >= 50) return 'quality-dot-medium';
    return 'quality-dot-low';
  };

  const getLabel = (score: number) => {
    if (score >= 80) return 'Most fields filled';
    if (score >= 50) return 'Some fields filled';
    return 'Few fields filled';
  };

  return (
    <div className={`relative group ${className}`}>
      <div className={`quality-dot ${getColorClass(score)}`} />
      {showTooltip && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-sidebar text-text text-2xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
          {getLabel(score)} ({score}%)
        </div>
      )}
    </div>
  );
}

interface DataQualityBadgeProps {
  score: number | null | undefined;
  className?: string;
}

export function DataQualityBadge({ score, className = '' }: DataQualityBadgeProps) {
  if (!isAssessed(score)) {
    return <span className={`badge text-textMuted ${className}`}>Not assessed</span>;
  }

  const getConfig = (score: number) => {
    if (score >= 80) return { label: 'Complete', className: 'badge-success' };
    if (score >= 50) return { label: 'Partial', className: 'badge-warning' };
    return { label: 'Limited', className: 'badge-error' };
  };

  const config = getConfig(score);

  return (
    <span className={`badge ${config.className} ${className}`}>
      <DataQualityDot score={score} />
      {config.label}
    </span>
  );
}

interface StatsCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export function StatsCard({
  label,
  value,
  subValue,
  trend,
  className = ''
}: StatsCardProps) {
  const trendColors = {
    up: 'text-success',
    down: 'text-error',
    neutral: 'text-textSecondary',
  };

  return (
    <div className={`text-center ${className}`}>
      <p className="text-2xs text-textMuted uppercase tracking-wide mb-1">{label}</p>
      <p className="text-xl font-semibold text-text">{value}</p>
      {subValue && (
        <p className={`text-2xs mt-0.5 ${trend ? trendColors[trend] : 'text-textSecondary'}`}>
          {subValue}
        </p>
      )}
    </div>
  );
}
