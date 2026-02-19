'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { useEffect, useCallback } from 'react';
import { DataQualityBar } from '@/components/ui/data-quality';
import { EnrichmentBadge } from '@/components/ui/enrichment-badge';

interface InstitutionModalProps {
  institution: {
    id: string;
    name: string;
    city?: string;
    state_or_province?: string;
    country: string;
    institution_type?: string;
    public_private?: string;
    website_url?: string;
    data_completeness_score?: number;
    in_state_tuition?: number;
    out_of_state_tuition?: number;
    graduation_rate?: number;
    average_cost?: number;
    median_earnings?: number;
  } | null;
  isOpen: boolean;
  onClose: () => void;
  onViewPrograms: (institutionId: string, institutionName: string) => void;
}

export default function InstitutionModal({
  institution,
  isOpen,
  onClose,
  onViewPrograms,
}: InstitutionModalProps) {
  // Handle escape key
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, handleEscape]);

  if (!institution) return null;

  const location = [institution.city, institution.state_or_province, institution.country]
    .filter(Boolean)
    .join(', ');

  return (
    <AnimatePresence mode="wait">
      {isOpen && (
        <>
          {/* Backdrop + Centering Container */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
          >
            {/* Modal */}
            <motion.div
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-2xl bg-card rounded-2xl shadow-soft-lg overflow-hidden flex flex-col max-h-[85vh]"
            >
            {/* Header */}
            <div className="p-6 border-b border-border bg-gradient-to-br from-primaryLight/30 to-transparent">
              <div className="flex items-start gap-4">
                {/* Avatar */}
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center flex-shrink-0 border border-border/50">
                  <span className="text-2xl font-display font-semibold text-primary">
                    {institution.name?.charAt(0) || 'U'}
                  </span>
                </div>
                
                <div className="flex-1 min-w-0">
                  <h2 className="text-xl font-display font-semibold text-text mb-1">
                    {institution.name}
                  </h2>
                  <p className="text-textSecondary flex items-center gap-1.5">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                    </svg>
                    {location}
                  </p>
                  
                  {/* Tags */}
                  <div className="flex flex-wrap items-center gap-2 mt-3">
                    {institution.institution_type && (
                      <span className="badge badge-primary capitalize">
                        {institution.institution_type}
                      </span>
                    )}
                    {institution.public_private && (
                      <span className="badge bg-muted text-textSecondary capitalize">
                        {institution.public_private}
                      </span>
                    )}
                    <EnrichmentBadge
                      entityKind="school"
                      entityId={institution.id}
                    />
                  </div>
                </div>
                
                {/* Close button */}
                <button
                  onClick={onClose}
                  className="p-2 rounded-xl hover:bg-muted transition-colors text-textMuted hover:text-text"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            
            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="card p-4 text-center">
                  <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">In-State Tuition</p>
                  <p className="text-lg font-semibold text-text">
                    {institution.in_state_tuition 
                      ? `$${Math.round(institution.in_state_tuition).toLocaleString()}`
                      : '-'
                    }
                  </p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Out-of-State</p>
                  <p className="text-lg font-semibold text-text">
                    {institution.out_of_state_tuition 
                      ? `$${Math.round(institution.out_of_state_tuition).toLocaleString()}`
                      : '-'
                    }
                  </p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Graduation Rate</p>
                  <p className="text-lg font-semibold text-text">
                    {institution.graduation_rate 
                      ? `${Math.round(institution.graduation_rate * 100)}%`
                      : '-'
                    }
                  </p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Avg Cost</p>
                  <p className="text-lg font-semibold text-text">
                    {institution.average_cost 
                      ? `$${Math.round(institution.average_cost).toLocaleString()}`
                      : '-'
                    }
                  </p>
                </div>
              </div>
              
              {/* Median Earnings */}
              {institution.median_earnings && (
                <div className="card p-4 mb-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-textSecondary">Median Earnings After Graduation</p>
                      <p className="text-2xl font-semibold text-success">
                        ${Math.round(institution.median_earnings).toLocaleString()}
                        <span className="text-sm font-normal text-textMuted">/year</span>
                      </p>
                    </div>
                    <div className="p-3 bg-successLight rounded-xl">
                      <svg className="w-6 h-6 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />
                      </svg>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Data Quality */}
              <div className="card p-4 mb-6">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-text">Data Completeness</p>
                  <span className="text-sm text-textSecondary">
                    {institution.data_completeness_score || 0}%
                  </span>
                </div>
                <DataQualityBar 
                  score={institution.data_completeness_score || 0} 
                  showLabel={false} 
                  size="lg" 
                />
                <p className="text-xs text-textMuted mt-2">
                  Data sourced from IPEDS and College Scorecard
                </p>
              </div>
              
              {/* Info Message */}
              <div className="bg-muted rounded-xl p-4 text-center">
                <p className="text-sm text-textSecondary">
                  View available graduate programs at this institution to learn more about specific degree offerings, requirements, and deadlines.
                </p>
              </div>
            </div>
            
            {/* Footer Actions */}
            <div className="p-6 border-t border-border bg-card flex flex-col sm:flex-row gap-3">
              {institution.website_url && (
                <a
                  href={institution.website_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary flex-1 justify-center"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                  </svg>
                  Visit Website
                </a>
              )}
              <button
                onClick={() => onViewPrograms(institution.id, institution.name)}
                className="btn-primary flex-1 justify-center"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
                </svg>
                View Programs
              </button>
            </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

