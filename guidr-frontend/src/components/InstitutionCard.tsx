'use client';

import { motion } from 'framer-motion';
import { DataQualityBar } from '@/components/ui/data-quality';

interface InstitutionCardProps {
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
  program_count?: number;
  last_enriched_at?: string | null;
  index?: number;
  onClick?: () => void;
}

function formatEnrichedAge(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86_400_000);
  if (days === 0) return 'Updated today';
  if (days === 1) return 'Updated yesterday';
  if (days < 30) return `Updated ${days}d ago`;
  const months = Math.floor(days / 30);
  return `Updated ${months}mo ago`;
}

export default function InstitutionCard({
  id,
  name,
  city,
  state_or_province,
  country,
  institution_type,
  public_private,
  website_url,
  data_completeness_score = 50,
  in_state_tuition,
  out_of_state_tuition,
  graduation_rate,
  program_count,
  last_enriched_at,
  index = 0,
  onClick,
}: InstitutionCardProps) {
  const location = [city, state_or_province, country].filter(Boolean).join(', ');
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.4 }}
      whileHover={{ y: -3 }}
      onClick={onClick}
      className="card card-hover p-5 cursor-pointer"
    >
      {/* Header */}
      <div className="flex items-start gap-4 mb-4">
        {/* Institution Avatar */}
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/15 to-accent/10 flex items-center justify-center flex-shrink-0 border border-border/50">
          <span className="text-xl font-display font-semibold text-primary">
            {name?.charAt(0) || 'U'}
          </span>
        </div>
        
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-text line-clamp-2 leading-tight mb-1">
            {name}
          </h3>
          <p className="text-sm text-textSecondary truncate">
            {location}
          </p>
        </div>
        
        {/* External Link */}
        {website_url && (
          <a
            href={website_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="p-2 rounded-xl hover:bg-muted transition-colors text-textMuted hover:text-primary"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
          </a>
        )}
      </div>
      
      {/* Tags */}
      <div className="flex flex-wrap gap-2 mb-4">
        {institution_type && (
          <span className="badge badge-primary text-2xs capitalize">
            {institution_type}
          </span>
        )}
        {public_private && (
          <span className="badge bg-muted text-textSecondary text-2xs capitalize">
            {public_private}
          </span>
        )}
        {program_count !== undefined && program_count > 0 && (
          <span className="badge bg-successLight text-success text-2xs">
            {program_count} programs
          </span>
        )}
        {last_enriched_at ? (
          <span className="badge bg-muted text-textSecondary text-2xs" title={new Date(last_enriched_at).toLocaleString()}>
            {formatEnrichedAge(last_enriched_at)}
          </span>
        ) : (
          <span className="badge bg-muted text-textMuted text-2xs">
            Not enriched
          </span>
        )}
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 py-3 border-t border-border/50">
        <div className="text-center">
          <p className="text-2xs text-textMuted mb-0.5">In-State</p>
          <p className="text-sm font-medium text-text">
            {in_state_tuition 
              ? `$${Math.round(in_state_tuition / 1000)}k` 
              : '-'
            }
          </p>
        </div>
        <div className="text-center border-x border-border/50">
          <p className="text-2xs text-textMuted mb-0.5">Out-of-State</p>
          <p className="text-sm font-medium text-text">
            {out_of_state_tuition 
              ? `$${Math.round(out_of_state_tuition / 1000)}k` 
              : '-'
            }
          </p>
        </div>
        <div className="text-center">
          <p className="text-2xs text-textMuted mb-0.5">Grad Rate</p>
          <p className="text-sm font-medium text-text">
            {graduation_rate 
              ? `${Math.round(graduation_rate * 100)}%` 
              : '-'
            }
          </p>
        </div>
      </div>
      
      {/* Data Quality */}
      <div className="mt-3">
        <DataQualityBar score={data_completeness_score} size="sm" />
      </div>
    </motion.div>
  );
}

