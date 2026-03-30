'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Recommendation {
  institution_name?: string;
  program_name?: string;
  tier?: string;
  score?: number;
  explanation?: string;
  reason_features?: string[];
}

interface RecommendationExplainModalProps {
  recommendation: Recommendation | null;
  open: boolean;
  onClose: () => void;
}

const TIER_COLORS: Record<string, string> = {
  dream: 'bg-purple-100 text-purple-700 border-purple-200',
  reach: 'bg-blue-100 text-blue-700 border-blue-200',
  target: 'bg-green-100 text-green-700 border-green-200',
  safety: 'bg-amber-100 text-amber-700 border-amber-200',
};

export default function RecommendationExplainModal({
  recommendation,
  open,
  onClose,
}: RecommendationExplainModalProps) {
  if (!recommendation) return null;

  const tier = recommendation.tier || 'target';
  const tierColor = TIER_COLORS[tier] || TIER_COLORS.target;

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/40 z-50"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bg-card rounded-2xl border border-border shadow-xl max-w-lg w-full max-h-[80vh] overflow-y-auto">
              {/* Header */}
              <div className="flex items-center justify-between p-6 pb-4 border-b border-border">
                <div className="flex items-center gap-3">
                  <Sparkles className="h-5 w-5 text-accent" />
                  <h2 className="text-lg font-display font-semibold text-text">
                    Why This Recommendation?
                  </h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg hover:bg-sidebarHover transition-colors"
                  aria-label="Close"
                >
                  <X className="h-5 w-5 text-textSecondary" />
                </button>
              </div>

              {/* Content */}
              <div className="p-6 space-y-5">
                {/* Program name + tier */}
                <div>
                  <h3 className="text-base font-semibold text-text">
                    {recommendation.program_name || recommendation.institution_name || 'Program'}
                  </h3>
                  {recommendation.institution_name && recommendation.program_name && (
                    <p className="text-sm text-textSecondary mt-0.5">
                      {recommendation.institution_name}
                    </p>
                  )}
                  <div className="flex items-center gap-3 mt-2">
                    <span className={cn('px-3 py-1 rounded-lg text-xs font-semibold border capitalize', tierColor)}>
                      {tier}
                    </span>
                    {recommendation.score != null && (
                      <span className="text-sm text-textSecondary">
                        Match score: <strong className="text-text">{recommendation.score}%</strong>
                      </span>
                    )}
                  </div>
                </div>

                {/* Explanation */}
                {recommendation.explanation && (
                  <div>
                    <h4 className="text-sm font-semibold text-textMuted uppercase tracking-wide mb-2">
                      Analysis
                    </h4>
                    <p className="text-sm text-textSecondary leading-relaxed">
                      {recommendation.explanation}
                    </p>
                  </div>
                )}

                {/* Reason features */}
                {recommendation.reason_features && recommendation.reason_features.length > 0 && (
                  <div>
                    <h4 className="text-sm font-semibold text-textMuted uppercase tracking-wide mb-2">
                      Key Factors
                    </h4>
                    <ul className="space-y-2">
                      {recommendation.reason_features.map((reason, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-textSecondary">
                          <CheckCircle2 className="h-4 w-4 text-success flex-shrink-0 mt-0.5" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {!recommendation.explanation && (!recommendation.reason_features || recommendation.reason_features.length === 0) && (
                  <p className="text-sm text-textMuted italic">
                    Detailed explanation is not yet available for this recommendation.
                  </p>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
