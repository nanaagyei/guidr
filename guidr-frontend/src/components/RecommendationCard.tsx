'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { School, MapPin, Star, ExternalLink, CheckCircle2 } from 'lucide-react';

interface RecommendationCardProps {
  recommendation: {
    program_id: string;
    program_name: string;
    institution_name?: string;
    institution_city?: string;
    institution_country?: string;
    score: number;
    tier: 'dream' | 'reach' | 'target' | 'safety';
    explanation?: string;
    reason_features?: string[];
    rank: number;
  };
  index?: number;
}

export default function RecommendationCard({ recommendation, index = 0 }: RecommendationCardProps) {
  const getTierConfig = (tier: string) => {
    switch (tier) {
      case 'dream':
        return {
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          bg: 'bg-yellow-50/50 border-yellow-200/30',
          label: 'Dream',
        };
      case 'reach':
        return {
          color: 'bg-orange-100 text-orange-800 border-orange-200',
          bg: 'bg-orange-50/50 border-orange-200/30',
          label: 'Reach',
        };
      case 'target':
        return {
          color: 'bg-blue-100 text-blue-700 border-blue-200',
          bg: 'bg-blue-50/50 border-blue-200/30',
          label: 'Target',
        };
      case 'safety':
        return {
          color: 'bg-green-100 text-green-700 border-green-200',
          bg: 'bg-green-50/50 border-green-200/30',
          label: 'Safety',
        };
      default:
        return {
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          bg: 'bg-gray-50/50 border-gray-200/30',
          label: tier,
        };
    }
  };

  const tierConfig = getTierConfig(recommendation.tier);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ scale: 1.02, y: -4 }}
      className={`bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition-all border-2 ${tierConfig.bg}`}
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              <School className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-text mb-1 truncate">
                {recommendation.program_name}
              </h3>
              {recommendation.institution_name && (
                <p className="text-sm text-gray-600 truncate">{recommendation.institution_name}</p>
              )}
            </div>
          </div>

          {/* Location */}
          {(recommendation.institution_city || recommendation.institution_country) && (
            <div className="flex items-center gap-1 text-sm text-gray-600 mb-3">
              <MapPin className="h-4 w-4 text-textSecondary" />
              <span>
                {[recommendation.institution_city, recommendation.institution_country]
                  .filter(Boolean)
                  .join(', ')}
              </span>
            </div>
          )}

          {/* Tier and Score */}
          <div className="flex items-center gap-3 mb-4">
            <span className={`px-3 py-1 rounded-lg text-xs font-semibold border ${tierConfig.color}`}>
              {tierConfig.label}
            </span>
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
              <span className="text-sm font-semibold text-text">{recommendation.score.toFixed(1)}</span>
              <span className="text-xs text-gray-500">/100</span>
            </div>
          </div>

          {/* Explanation */}
          {recommendation.explanation && (
            <div className="mb-4">
              <p className="text-sm text-gray-700 leading-relaxed">{recommendation.explanation}</p>
            </div>
          )}

          {/* Reason Features */}
          {recommendation.reason_features && recommendation.reason_features.length > 0 && (
            <div className="space-y-2">
              {recommendation.reason_features.slice(0, 3).map((reason, i) => (
                <div key={i} className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-gray-700">{reason}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3 pt-4 border-t border-border">
        <Link
          href={`/programs/${recommendation.program_id}`}
          className="flex-1 px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition text-center text-sm"
        >
          View Program
        </Link>
      </div>
    </motion.div>
  );
}

