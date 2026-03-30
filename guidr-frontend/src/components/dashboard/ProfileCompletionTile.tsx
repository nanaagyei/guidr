'use client';

import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { Button } from '@/components/ui/button';
import { useProfileCompletion } from '@/contexts/ProfileCompletionContext';
import { motion } from 'framer-motion';
import {
  User,
  BookOpen,
  FileText,
  Settings,
  FlaskConical,
  MapPin,
  GraduationCap,
  Globe,
  Target,
  ArrowRight,
  CheckCircle2,
  Sparkles,
  Lock,
} from 'lucide-react';
import { cn } from '@/lib/utils';

/** Human-readable labels and icons for missing fields. */
const FIELD_META: Record<string, { label: string; icon: React.ReactNode; step?: number }> = {
  intended_degree: { label: 'Intended Degree', icon: <GraduationCap className="h-4 w-4" />, step: 2 },
  primary_field_of_study: { label: 'Field of Study', icon: <BookOpen className="h-4 w-4" />, step: 2 },
  research_areas: { label: 'Research Areas', icon: <FlaskConical className="h-4 w-4" />, step: 5 },
  preferred_countries: { label: 'Preferred Countries', icon: <Globe className="h-4 w-4" />, step: 3 },
  country_of_citizenship: { label: 'Country / Citizenship', icon: <MapPin className="h-4 w-4" />, step: 3 },
  academic_record: { label: 'Academic Record', icon: <FileText className="h-4 w-4" />, step: 4 },
  secondary_fields: { label: 'Secondary Fields', icon: <Target className="h-4 w-4" />, step: 5 },
  career_goals: { label: 'Career Goals', icon: <Target className="h-4 w-4" />, step: 5 },
  funding_priority: { label: 'Funding Priority', icon: <Settings className="h-4 w-4" />, step: 3 },
  program_style_preference: { label: 'Program Style', icon: <Settings className="h-4 w-4" />, step: 3 },
  preferred_start_term: { label: 'Start Term', icon: <Settings className="h-4 w-4" />, step: 2 },
  preferred_start_year: { label: 'Start Year', icon: <Settings className="h-4 w-4" />, step: 2 },
};

const LEVEL_LABELS: Record<number, { label: string; color: string }> = {
  0: { label: 'Getting Started', color: 'text-gray-400' },
  1: { label: 'Level 1 — Basics', color: 'text-warning' },
  2: { label: 'Level 2 — Targeting', color: 'text-info' },
  3: { label: 'Level 3 — Complete', color: 'text-success' },
};

const NEXT_UNLOCK: Record<number, string> = {
  0: 'Complete basics to unlock your dashboard',
  1: 'Add targeting info to unlock Recommendations',
  2: 'Add an academic record to unlock Professor matching',
};

export default function ProfileCompletionTile() {
  const { completion, loading } = useProfileCompletion();

  const percent = completion?.percent ?? 0;
  const level = completion?.level ?? 0;
  const missingFields = completion?.missing_fields ?? [];

  const circumference = 2 * Math.PI * 42;
  const offset = circumference - (percent / 100) * circumference;

  const getProgressColor = () => {
    if (level >= 3) return '#4A9D6E';
    if (level >= 2) return '#5B8DC7';
    if (level >= 1) return '#D4A34E';
    return '#C75B5B';
  };

  const levelInfo = LEVEL_LABELS[level] ?? LEVEL_LABELS[0];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-primary">
              <User className="h-5 w-5" />
            </div>
            <CardTitle className="text-lg">Profile Completion</CardTitle>
          </div>
          <Link
            href="/profile"
            className="text-sm font-medium text-primary hover:text-primaryHover transition-colors flex items-center gap-1"
          >
            Edit
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="flex-1 flex flex-col pt-0">
        {loading ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <Skeleton className="w-28 h-28 rounded-full" />
            <Skeleton variant="text" className="w-32 h-4" />
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            {/* Progress ring */}
            <div className="flex justify-center mb-4">
              <div className="relative w-28 h-28">
                <svg className="transform -rotate-90" width="112" height="112">
                  <circle
                    cx="56"
                    cy="56"
                    r="42"
                    stroke="currentColor"
                    className="text-muted"
                    strokeWidth="10"
                    fill="none"
                  />
                  <motion.circle
                    cx="56"
                    cy="56"
                    r="42"
                    stroke={getProgressColor()}
                    strokeWidth="10"
                    fill="none"
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    initial={{ strokeDashoffset: circumference }}
                    animate={{ strokeDashoffset: offset }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-display font-semibold text-text">
                    {percent}%
                  </span>
                </div>
              </div>
            </div>

            {/* Level badge */}
            <div className="text-center mb-4">
              <span className={cn('text-sm font-semibold', levelInfo.color)}>
                {levelInfo.label}
              </span>

              {level >= 2 ? (
                <div className="flex items-center justify-center gap-2 text-sm text-success mt-1">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="font-medium">Recommendations unlocked</span>
                </div>
              ) : null}

              {level < 3 && NEXT_UNLOCK[level] && (
                <p className="text-xs text-textSecondary mt-1">
                  {NEXT_UNLOCK[level]}
                </p>
              )}
            </div>

            {/* Missing fields checklist */}
            {missingFields.length > 0 && (
              <div className="space-y-2 flex-1">
                <p className="text-xs font-medium text-textMuted uppercase tracking-wide mb-2">
                  Next steps:
                </p>
                {missingFields.map((field, index) => {
                  const meta = FIELD_META[field];
                  return (
                    <motion.div
                      key={field}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.1 }}
                      className="flex items-center gap-2 text-sm text-textSecondary"
                    >
                      <span className="text-textMuted">
                        {meta?.icon ?? <Lock className="h-4 w-4" />}
                      </span>
                      <span>{meta?.label ?? field}</span>
                    </motion.div>
                  );
                })}
              </div>
            )}

            {level >= 3 && missingFields.length === 0 && (
              <div className="flex-1 flex flex-col items-center justify-center gap-2 text-center">
                <Sparkles className="h-6 w-6 text-success" />
                <p className="text-sm font-medium text-success">All features unlocked!</p>
                <p className="text-xs text-textSecondary">
                  Keep your profile updated for the best recommendations.
                </p>
              </div>
            )}

            <Button asChild className="w-full mt-4">
              <Link href={level === 0 ? '/onboarding' : '/profile'}>
                {level === 0 ? 'Start Onboarding' : level < 3 ? 'Complete Profile' : 'Update Profile'}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
