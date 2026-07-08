'use client';

import { motion } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { GraduationCap, MapPin, ExternalLink, Sparkles, CheckCircle2, DollarSign } from 'lucide-react';
import { useState } from 'react';

interface ProfessorCardProps {
  professor: {
    id: string;
    full_name: string;
    title?: string;
    institution_name?: string;
    country?: string;
    city?: string;
    research_summary?: string;
    tags?: string[];
    email?: string;
    personal_page_url?: string;
    scholar_profile_url?: string;
    is_accepting_students?: boolean;
    match_score?: number;
    funding_available?: boolean;
    funding_count?: number;
  };
  onGenerateEmail?: (professorId: string) => void;
  index?: number;
}

export default function ProfessorCard({ professor, onGenerateEmail, index = 0 }: ProfessorCardProps) {
  const router = useRouter();
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateEmail = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!onGenerateEmail) return;
    setIsGenerating(true);
    try {
      await onGenerateEmail(professor.id);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCardClick = () => {
    router.push(`/professors/${professor.id}`);
  };

  const hasFunding = professor.funding_available || (professor.funding_count != null && professor.funding_count > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ scale: 1.02, y: -4 }}
      onClick={handleCardClick}
      className="bg-card rounded-xl p-6 shadow-sm hover:shadow-md transition-all border border-border hover:border-primary/30 group cursor-pointer relative"
    >
      {/* Match score badge */}
      {professor.match_score != null && professor.match_score > 0 && (
        <div className="absolute top-4 right-4">
          <span className="inline-flex items-center px-2 py-0.5 bg-secondary/10 text-secondary text-xs font-semibold rounded-lg border border-secondary/20 tabular-nums">
            {Math.round(professor.match_score * 100)}% match
          </span>
        </div>
      )}

      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors flex-shrink-0">
              <GraduationCap className="h-5 w-5 text-purple-700" />
            </div>
            <div className="flex-1 min-w-0 pr-16">
              <h3 className="text-lg font-semibold text-text mb-1">{professor.full_name}</h3>
              {professor.title && (
                <p className="text-sm text-gray-600">{professor.title}</p>
              )}
            </div>
          </div>

          {/* Institution & Location */}
          {(professor.institution_name || professor.city || professor.country) && (
            <div className="flex items-center gap-2 text-sm text-gray-600 mb-2">
              <MapPin className="h-4 w-4 text-textSecondary flex-shrink-0" />
              <span className="font-medium">{professor.institution_name}</span>
              {(professor.city || professor.country) && (
                <span className="text-gray-500">
                  · {[professor.city, professor.country].filter(Boolean).join(', ')}
                </span>
              )}
            </div>
          )}

          {/* Status badges */}
          {(professor.is_accepting_students === true || hasFunding) && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {professor.is_accepting_students === true && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-successLight text-success text-2xs font-medium rounded-md border border-success/20">
                  <CheckCircle2 className="h-3 w-3" />
                  Accepting Students
                </span>
              )}
              {hasFunding && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-successLight text-success text-2xs font-medium rounded-md border border-success/20">
                  <DollarSign className="h-3 w-3" />
                  Funding Available
                </span>
              )}
            </div>
          )}

          {/* Research Summary */}
          {professor.research_summary && (
            <p className="text-sm text-gray-700 mb-3 line-clamp-2">
              {professor.research_summary}
            </p>
          )}

          {/* Tags */}
          {professor.tags && professor.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-4">
              {professor.tags.slice(0, 5).map((tag, i) => (
                <span
                  key={i}
                  className="px-2.5 py-1 bg-primary/10 text-primary text-xs font-medium rounded-lg border border-primary/20"
                >
                  {tag}
                </span>
              ))}
              {professor.tags.length > 5 && (
                <span className="px-2.5 py-1 bg-gray-100 text-gray-600 text-xs font-medium rounded-lg">
                  +{professor.tags.length - 5}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-4 border-t border-border">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGenerateEmail}
          disabled={isGenerating}
          className="flex-1 px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50 flex items-center justify-center gap-2 text-sm cursor-pointer"
        >
          {isGenerating ? (
            <>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="h-4 w-4 border-2 border-white border-t-transparent rounded-full"
              />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-4 w-4" />
              Generate Email
            </>
          )}
        </motion.button>
        {professor.personal_page_url && (
          <motion.a
            whileHover={{ scale: 1.05 }}
            href={professor.personal_page_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-2 bg-muted text-text rounded-lg hover:bg-gray-200 transition border border-border cursor-pointer"
            title="View profile"
          >
            <ExternalLink className="h-4 w-4" />
          </motion.a>
        )}
      </div>
    </motion.div>
  );
}
