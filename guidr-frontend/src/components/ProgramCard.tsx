'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { DataQualityDot } from '@/components/ui/data-quality';

interface ProgramCardProps {
  id: string;
  program_name: string;
  institution_name: string;
  city: string;
  country: string;
  degree_level: string;
  field_of_study: string | null;
  tuition: number | null;
  deadline: string | null;
  data_completeness_score?: number;
  last_enriched_at?: string | null;
  index?: number;
}

function formatEnrichedAge(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86_400_000);
  if (days === 0) return 'Updated today';
  if (days === 1) return 'Updated yesterday';
  if (days < 30) return `Updated ${days}d ago`;
  return `Updated ${Math.floor(days / 30)}mo ago`;
}

export default function ProgramCard({
  id,
  program_name,
  institution_name,
  city,
  country,
  degree_level,
  field_of_study,
  tuition,
  deadline,
  data_completeness_score = 50,
  last_enriched_at,
  index = 0,
}: ProgramCardProps) {
  const isDeadlineSoon = deadline && new Date(deadline) <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.4 }}
      whileHover={{ y: -4 }}
      className="h-full"
    >
      <Link href={`/programs/${id}`} className="block h-full">
        <div className="card card-hover h-full p-5 flex flex-col">
          {/* Header */}
          <div className="flex items-start gap-3 mb-4">
            {/* Institution Initial Avatar */}
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-primary/10 to-accent/10 flex items-center justify-center flex-shrink-0 border border-border/50">
              <span className="text-lg font-semibold text-primary">
                {institution_name?.charAt(0) || 'U'}
              </span>
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-text line-clamp-2 leading-tight mb-1">
                {program_name}
              </h3>
              <p className="text-sm text-textSecondary truncate">
                {institution_name}
              </p>
            </div>
          </div>

          {/* Details */}
          <div className="space-y-2.5 flex-1">
            <div className="flex items-center gap-2 text-sm text-textSecondary">
              <svg className="w-4 h-4 text-textMuted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
              </svg>
              <span className="truncate">{city}, {country}</span>
            </div>

            <div className="flex items-center gap-2 text-sm text-textSecondary">
              <svg className="w-4 h-4 text-textMuted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
              <span className="capitalize">{degree_level}</span>
              {field_of_study && (
                <span className="text-textMuted">in {field_of_study}</span>
              )}
            </div>

            {tuition && (
              <div className="flex items-center gap-2 text-sm text-textSecondary">
                <svg className="w-4 h-4 text-textMuted flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>${tuition.toLocaleString()}/year</span>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/50">
            {deadline ? (
              <div className={`flex items-center gap-1.5 text-xs font-medium ${
                isDeadlineSoon ? 'text-warning' : 'text-textSecondary'
              }`}>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                </svg>
                <span>{new Date(deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
              </div>
            ) : (
              <span className="text-xs text-textMuted">No deadline set</span>
            )}

            <div className="flex items-center gap-1.5">
              <DataQualityDot score={data_completeness_score} showTooltip />
              {last_enriched_at && (
                <span
                  className="text-xs text-textMuted"
                  title={new Date(last_enriched_at).toLocaleString()}
                >
                  {formatEnrichedAge(last_enriched_at)}
                </span>
              )}
              {!last_enriched_at && (
                <span className="text-xs text-textMuted">View details</span>
              )}
              <svg className="w-3.5 h-3.5 text-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </div>
        </div>
      </Link>
    </motion.div>
  );
}
