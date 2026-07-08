'use client';

import { motion } from 'framer-motion';
import { Star, CheckCircle2, XCircle, AlertCircle, Sparkles } from 'lucide-react';

interface ReviewDisplayProps {
  review: {
    overall_score?: number;
    content_score?: number;
    structure_score?: number;
    clarity_score?: number;
    grammar_score?: number;
    strengths?: string[];
    weaknesses?: string[];
    suggestions?: Array<{
      section?: string;
      suggestion: string;
      priority: 'high' | 'medium' | 'low';
    }>;
    detailed_feedback?: string;
    created_at: string;
  };
}

export default function ReviewDisplay({ review }: ReviewDisplayProps) {
  const scoreLabels = [
    { key: 'overall_score', label: 'Overall', value: review.overall_score },
    { key: 'content_score', label: 'Content', value: review.content_score },
    { key: 'structure_score', label: 'Structure', value: review.structure_score },
    { key: 'clarity_score', label: 'Clarity', value: review.clarity_score },
    { key: 'grammar_score', label: 'Grammar', value: review.grammar_score },
  ].filter(item => item.value !== undefined && item.value !== null);

  const getScoreColor = (score?: number): string => {
    if (!score) return 'bg-gray-200';
    if (score >= 8) return 'bg-green-500';
    if (score >= 6) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getPriorityColor = (priority: string): string => {
    switch (priority) {
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default:
        return 'bg-blue-100 text-blue-800 border-blue-200';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-card rounded-xl p-6 shadow-sm border border-border"
    >
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Sparkles className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h3 className="text-xl font-semibold text-text">AI Review</h3>
          <p className="text-xs text-gray-500">
            Reviewed {new Date(review.created_at).toLocaleDateString()}
          </p>
        </div>
      </div>

      {/* Overall Score */}
      {review.overall_score !== undefined && (
        <div className="mb-6 p-4 bg-muted rounded-lg border border-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Overall Score</span>
            <div className="flex items-center gap-1">
              <Star className="h-5 w-5 text-yellow-500 fill-yellow-500" />
              <span className="text-2xl font-bold text-text">{review.overall_score.toFixed(1)}</span>
              <span className="text-gray-500">/ 10</span>
            </div>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${(review.overall_score / 10) * 100}%` }}
              transition={{ duration: 1, ease: 'easeOut' }}
              className={`h-full ${getScoreColor(review.overall_score)} rounded-full`}
            />
          </div>
        </div>
      )}

      {/* Score Breakdown */}
      {scoreLabels.length > 1 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text mb-3">Score Breakdown</h4>
          <div className="grid grid-cols-2 gap-3">
            {scoreLabels.filter(item => item.key !== 'overall_score').map((item) => (
              <div key={item.key} className="p-3 bg-muted rounded-lg">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-gray-700">{item.label}</span>
                  <span className="text-sm font-bold text-text">{item.value?.toFixed(1)}</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${((item.value || 0) / 10) * 100}%` }}
                    transition={{ duration: 1, delay: 0.2, ease: 'easeOut' }}
                    className={`h-full ${getScoreColor(item.value)} rounded-full`}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths */}
      {review.strengths && review.strengths.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-600" />
            Strengths
          </h4>
          <ul className="space-y-2">
            {review.strengths.map((strength, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-start gap-2 p-3 bg-green-50 border border-green-200 rounded-lg"
              >
                <CheckCircle2 className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-gray-700">{strength}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Weaknesses */}
      {review.weaknesses && review.weaknesses.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
            <XCircle className="h-4 w-4 text-red-600" />
            Areas for Improvement
          </h4>
          <ul className="space-y-2">
            {review.weaknesses.map((weakness, index) => (
              <motion.li
                key={index}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
                className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-lg"
              >
                <XCircle className="h-4 w-4 text-red-600 flex-shrink-0 mt-0.5" />
                <span className="text-sm text-gray-700">{weakness}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggestions */}
      {review.suggestions && review.suggestions.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-semibold text-text mb-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-yellow-600" />
            Suggestions
          </h4>
          <div className="space-y-3">
            {review.suggestions.map((suggestion, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className={`p-3 rounded-lg border ${getPriorityColor(suggestion.priority)}`}
              >
                {suggestion.section && (
                  <div className="text-xs font-semibold mb-1 uppercase">
                    {suggestion.section}
                  </div>
                )}
                <p className="text-sm">{suggestion.suggestion}</p>
                <span className="text-xs font-medium mt-1 inline-block">
                  Priority: {suggestion.priority}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Feedback */}
      {review.detailed_feedback && (
        <div>
          <h4 className="text-sm font-semibold text-text mb-3">Detailed Feedback</h4>
          <div className="p-4 bg-muted rounded-lg border border-border">
            <p className="text-sm text-gray-700 whitespace-pre-wrap leading-relaxed">
              {review.detailed_feedback}
            </p>
          </div>
        </div>
      )}
    </motion.div>
  );
}
