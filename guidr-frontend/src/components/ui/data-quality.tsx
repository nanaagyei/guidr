'use client';

import { motion } from 'framer-motion';

interface DataQualityBarProps {
  score: number; // 0-100
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
  score: number;
  showTooltip?: boolean;
  className?: string;
}

export function DataQualityDot({ 
  score, 
  showTooltip = false,
  className = '' 
}: DataQualityDotProps) {
  const getColorClass = (score: number) => {
    if (score >= 80) return 'quality-dot-high';
    if (score >= 50) return 'quality-dot-medium';
    return 'quality-dot-low';
  };

  const getLabel = (score: number) => {
    if (score >= 80) return 'High data quality';
    if (score >= 50) return 'Partial data';
    return 'Limited data';
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
  score: number;
  className?: string;
}

export function DataQualityBadge({ score, className = '' }: DataQualityBadgeProps) {
  const getConfig = (score: number) => {
    if (score >= 80) return { label: 'Verified', className: 'badge-success' };
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

