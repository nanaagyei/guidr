'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { PenTool, FileText, Eye, Trash2, Loader2, Star } from 'lucide-react';
import { useState } from 'react';

interface EssayCardProps {
  essay: {
    id: string;
    title: string;
    essay_type: string;
    word_count: number;
    created_at: string;
    updated_at: string;
    latest_review?: {
      overall_score?: number;
      created_at: string;
    };
  };
  onDelete?: (id: string) => void;
  index?: number;
}

export default function EssayCard({ essay, onDelete, index = 0 }: EssayCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);

  const getEssayTypeColor = (type: string) => {
    switch (type) {
      case 'personal_statement':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'sop':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'diversity':
        return 'bg-green-100 text-green-700 border-green-200';
      case 'why_school':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  };

  const formatEssayType = (type: string): string => {
    return type
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const handleDelete = async () => {
    if (!onDelete || !confirm('Are you sure you want to delete this essay?')) {
      return;
    }
    setIsDeleting(true);
    try {
      await onDelete(essay.id);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ scale: 1.02, y: -4 }}
      className="bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition-all border border-border hover:border-primary/30 group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2 bg-primary/10 rounded-lg group-hover:bg-primary/20 transition-colors">
              <PenTool className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-text mb-1 truncate">{essay.title}</h3>
              <div className="flex items-center gap-2 flex-wrap">
                <span className={`px-2.5 py-1 rounded-lg text-xs font-semibold border ${getEssayTypeColor(essay.essay_type)}`}>
                  {formatEssayType(essay.essay_type)}
                </span>
                {essay.latest_review?.overall_score !== undefined && (
                  <div className="flex items-center gap-1 px-2.5 py-1 bg-green-50 border border-green-200 rounded-lg">
                    <Star className="h-3 w-3 text-green-600 fill-green-600" />
                    <span className="text-xs font-semibold text-green-700">
                      {essay.latest_review.overall_score.toFixed(1)}/10
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
            <div className="flex items-center gap-1.5">
              <FileText className="h-4 w-4 text-textSecondary" />
              <span>{essay.word_count.toLocaleString()} words</span>
            </div>
            <div className="text-xs text-gray-500">
              Updated {new Date(essay.updated_at).toLocaleDateString()}
            </div>
          </div>

          {/* Latest Review Indicator */}
          {essay.latest_review && (
            <div className="mt-3 pt-3 border-t border-border">
              <p className="text-xs text-gray-500 mb-1">Latest Review</p>
              <p className="text-xs text-gray-600">
                {new Date(essay.latest_review.created_at).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <Link
            href={`/essays/${essay.id}`}
            className="p-2 bg-primary text-white rounded-lg hover:bg-primaryHover transition-colors flex items-center justify-center group"
            title="View essay"
          >
            <Eye className="h-4 w-4 group-hover:scale-110 transition-transform" />
          </Link>
          {onDelete && (
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleDelete}
              disabled={isDeleting}
              className="p-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors disabled:opacity-50 flex items-center justify-center"
              title="Delete essay"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Trash2 className="h-4 w-4" />
              )}
            </motion.button>
          )}
        </div>
      </div>
    </motion.div>
  );
}

