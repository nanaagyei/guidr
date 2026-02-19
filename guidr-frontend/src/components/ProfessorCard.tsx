'use client';

import { motion } from 'framer-motion';
import { GraduationCap, MapPin, Mail, ExternalLink, Sparkles, Tag } from 'lucide-react';
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
  };
  onGenerateEmail?: (professorId: string) => void;
  index?: number;
}

export default function ProfessorCard({ professor, onGenerateEmail, index = 0 }: ProfessorCardProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateEmail = async () => {
    if (!onGenerateEmail) return;
    setIsGenerating(true);
    try {
      await onGenerateEmail(professor.id);
    } finally {
      setIsGenerating(false);
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
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-start gap-3 mb-3">
            <div className="p-2 bg-purple-100 rounded-lg group-hover:bg-purple-200 transition-colors">
              <GraduationCap className="h-5 w-5 text-purple-700" />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-text mb-1">{professor.full_name}</h3>
              {professor.title && (
                <p className="text-sm text-gray-600">{professor.title}</p>
              )}
            </div>
          </div>

          {/* Institution & Location */}
          {(professor.institution_name || professor.city || professor.country) && (
            <div className="flex items-center gap-2 text-sm text-gray-600 mb-3">
              <MapPin className="h-4 w-4 text-textSecondary" />
              <span className="font-medium">{professor.institution_name}</span>
              {(professor.city || professor.country) && (
                <span className="text-gray-500">
                  • {[professor.city, professor.country].filter(Boolean).join(', ')}
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
          className="flex-1 px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50 flex items-center justify-center gap-2 text-sm"
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
            className="p-2 bg-muted text-text rounded-lg hover:bg-gray-200 transition border border-border"
            title="View profile"
          >
            <ExternalLink className="h-4 w-4" />
          </motion.a>
        )}
      </div>
    </motion.div>
  );
}

