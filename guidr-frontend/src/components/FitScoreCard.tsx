'use client';

import { motion, useReducedMotion } from 'framer-motion';
import { BookOpen, Activity, UserCheck, DollarSign, FlaskConical, AlertCircle } from 'lucide-react';
import FitDimensionBar from './FitDimensionBar';

interface Dimension {
  score: number;
  explanation: string;
}

interface FitScoreData {
  overall_score: number;
  dimensions: {
    topic_overlap: Dimension;
    research_activity: Dimension;
    availability: Dimension;
    funding: Dimension;
    methods_alignment: Dimension;
  };
  enrichment_match_score?: number | null;
  funding_count?: number;
}

interface FitScoreCardProps {
  data: FitScoreData | null;
  loading?: boolean;
}

function getOverallColor(score: number): string {
  if (score >= 70) return '#4A9D6E'; // success
  if (score >= 40) return '#D4A34E'; // warning
  return '#C75B5B'; // error
}

function getOverallLabel(score: number): string {
  if (score >= 80) return 'Excellent Fit';
  if (score >= 60) return 'Good Fit';
  if (score >= 40) return 'Moderate Fit';
  return 'Low Fit';
}

function ScoreRing({ score, size = 120 }: { score: number; size?: number }) {
  const prefersReducedMotion = useReducedMotion();
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = getOverallColor(score);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="transform -rotate-90">
        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          className="text-muted"
          strokeWidth={strokeWidth}
          fill="none"
        />
        {/* Progress */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: prefersReducedMotion ? offset : circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: prefersReducedMotion ? 0 : 1.2, ease: 'easeOut', delay: 0.2 }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold tabular-nums text-text">{score}</span>
        <span className="text-2xs font-medium text-textMuted uppercase tracking-wider">/100</span>
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="bg-card rounded-2xl border border-border p-6 animate-pulse">
      <div className="flex flex-col items-center mb-6">
        <div className="w-[120px] h-[120px] rounded-full bg-muted" />
        <div className="h-4 w-24 bg-muted rounded mt-3" />
      </div>
      <div className="space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i}>
            <div className="flex justify-between mb-1.5">
              <div className="h-3.5 w-28 bg-muted rounded" />
              <div className="h-3.5 w-8 bg-muted rounded" />
            </div>
            <div className="h-2 w-full bg-muted rounded-full" />
          </div>
        ))}
      </div>
    </div>
  );
}

const DIMENSION_CONFIG = [
  { key: 'topic_overlap', label: 'Topic Overlap', icon: <BookOpen className="h-4 w-4" /> },
  { key: 'research_activity', label: 'Research Activity', icon: <Activity className="h-4 w-4" /> },
  { key: 'availability', label: 'Availability', icon: <UserCheck className="h-4 w-4" /> },
  { key: 'funding', label: 'Funding', icon: <DollarSign className="h-4 w-4" /> },
  { key: 'methods_alignment', label: 'Methods Alignment', icon: <FlaskConical className="h-4 w-4" /> },
] as const;

export default function FitScoreCard({ data, loading = false }: FitScoreCardProps) {
  if (loading) return <SkeletonCard />;

  if (!data) {
    return (
      <div className="bg-card rounded-2xl border border-border p-6">
        <div className="flex flex-col items-center text-center py-4">
          <AlertCircle className="h-10 w-10 text-textMuted mb-3" />
          <p className="text-sm font-medium text-text mb-1">Fit Score Unavailable</p>
          <p className="text-xs text-textSecondary leading-relaxed max-w-[220px]">
            Complete your profile and save this school to generate a fit score.
          </p>
        </div>
      </div>
    );
  }

  const allZero = DIMENSION_CONFIG.every(
    (d) => data.dimensions[d.key]?.score === 0
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="bg-card rounded-2xl border border-border p-6"
    >
      {/* Score ring */}
      <div className="flex flex-col items-center mb-6">
        <ScoreRing score={data.overall_score} />
        <p
          className="text-sm font-semibold mt-2"
          style={{ color: getOverallColor(data.overall_score) }}
        >
          {getOverallLabel(data.overall_score)}
        </p>
        {data.enrichment_match_score != null && (
          <p className="text-2xs text-textMuted mt-0.5">
            AI match: {Math.round(data.enrichment_match_score * 100)}%
          </p>
        )}
      </div>

      {/* Sparse data warning */}
      {allZero && (
        <div className="flex items-start gap-2 mb-5 p-3 rounded-xl bg-warningLight border border-warning/20">
          <AlertCircle className="h-4 w-4 text-warning flex-shrink-0 mt-0.5" />
          <p className="text-xs text-text leading-relaxed">
            Limited data available. Save this school and complete your profile for a more accurate fit score.
          </p>
        </div>
      )}

      {/* Dimensions */}
      <div className="space-y-4">
        {DIMENSION_CONFIG.map((dim, i) => {
          const d = data.dimensions[dim.key];
          return (
            <FitDimensionBar
              key={dim.key}
              label={dim.label}
              score={d?.score ?? 0}
              explanation={d?.explanation}
              icon={dim.icon}
              index={i}
            />
          );
        })}
      </div>

      {/* Funding quick stat */}
      {data.funding_count != null && data.funding_count > 0 && (
        <div className="mt-5 pt-4 border-t border-border flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-success" />
          <span className="text-xs font-medium text-text">
            {data.funding_count} funding opportunit{data.funding_count === 1 ? 'y' : 'ies'} available
          </span>
        </div>
      )}
    </motion.div>
  );
}
