'use client';

import Link from 'next/link';
import { AlertCircle } from 'lucide-react';
import { useProfileCompletion } from '@/contexts/ProfileCompletionContext';

const FIELD_LABELS: Record<string, string> = {
  intended_degree: 'Intended Degree',
  primary_field_of_study: 'Primary Field of Study',
  country_of_citizenship: 'Country of Citizenship',
  current_country: 'Current Country',
  preferred_countries: 'Preferred Countries',
  research_areas: 'Research Areas',
  career_goals: 'Career Goals',
  funding_priority: 'Funding Priority',
  program_style_preference: 'Program Style',
  preferred_start_term: 'Start Term',
  preferred_start_year: 'Start Year',
  secondary_fields: 'Secondary Fields',
  academic_record: 'Academic Record',
};

interface ProfileHealthBannerProps {
  requiredLevel: number;
  featureName?: string;
}

export default function ProfileHealthBanner({ requiredLevel, featureName }: ProfileHealthBannerProps) {
  const { completion, loading } = useProfileCompletion();

  if (loading || !completion || completion.level >= requiredLevel) {
    return null;
  }

  const missingFields = completion.missing_fields || [];
  const hasAcademicMissing = missingFields.includes('academic_record');
  const href = hasAcademicMissing ? '/academic-records' : '/profile';
  const ctaLabel = hasAcademicMissing ? 'Add Academic Records' : 'Complete Profile';

  return (
    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-amber-900 text-sm">
            {featureName
              ? `Complete your profile to unlock ${featureName}`
              : 'Complete your profile to unlock this feature'}
          </h3>
          <p className="text-amber-800 text-xs mt-1">
            You need Level {requiredLevel} (currently Level {completion.level}).
            {missingFields.length > 0 && (
              <> Missing: {missingFields.map((f) => FIELD_LABELS[f] || f).join(', ')}.</>
            )}
          </p>
          <Link
            href={href}
            className="inline-flex mt-3 px-4 py-1.5 bg-amber-600 text-white text-xs font-semibold rounded-lg hover:bg-amber-700 transition"
          >
            {ctaLabel}
          </Link>
        </div>
      </div>
    </div>
  );
}
