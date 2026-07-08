'use client';

import { motion } from 'framer-motion';
import { useState } from 'react';
import { ChevronDown } from 'lucide-react';

interface FitDimensionBarProps {
  label: string;
  score: number;
  explanation?: string;
  icon?: React.ReactNode;
  index?: number;
}

function getScoreColor(score: number): string {
  if (score >= 70) return 'bg-success';
  if (score >= 40) return 'bg-warning';
  return 'bg-error';
}

function getScoreTextColor(score: number): string {
  if (score >= 70) return 'text-success';
  if (score >= 40) return 'text-warning';
  return 'text-error';
}

export default function FitDimensionBar({
  label,
  score,
  explanation,
  icon,
  index = 0,
}: FitDimensionBarProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.15 + index * 0.07, duration: 0.35 }}
      className="group"
    >
      <button
        type="button"
        onClick={() => explanation && setExpanded(!expanded)}
        className={`w-full text-left ${explanation ? 'cursor-pointer' : 'cursor-default'}`}
      >
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-2">
            {icon && <span className="text-textMuted">{icon}</span>}
            <span className="text-sm font-medium text-text">{label}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`text-sm font-semibold tabular-nums ${getScoreTextColor(score)}`}>
              {score}
            </span>
            {explanation && (
              <ChevronDown
                className={`h-3.5 w-3.5 text-textMuted transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
              />
            )}
          </div>
        </div>

        {/* Bar track */}
        <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${score}%` }}
            transition={{ delay: 0.3 + index * 0.07, duration: 0.6, ease: 'easeOut' }}
            className={`h-full rounded-full ${getScoreColor(score)}`}
          />
        </div>
      </button>

      {/* Expandable explanation */}
      {expanded && explanation && (
        <motion.p
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="text-xs text-textSecondary mt-1.5 pl-1 leading-relaxed"
        >
          {explanation}
        </motion.p>
      )}
    </motion.div>
  );
}
