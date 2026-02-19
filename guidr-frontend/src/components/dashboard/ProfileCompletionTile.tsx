'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { Button } from '@/components/ui/button';
import { getProfile } from '@/utils/api';
import { motion } from 'framer-motion';
import { User, BookOpen, FileText, Settings, FlaskConical, ArrowRight } from 'lucide-react';

const SECTION_ICONS: Record<string, React.ReactNode> = {
  'Academic Records': <BookOpen className="h-4 w-4 text-textSecondary" />,
  'Test Scores': <FileText className="h-4 w-4 text-textSecondary" />,
  'Preferences': <Settings className="h-4 w-4 text-textSecondary" />,
  'Research Interests': <FlaskConical className="h-4 w-4 text-textSecondary" />,
};

export default function ProfileCompletionTile() {
  const [completionScore, setCompletionScore] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      setLoading(true);
      try {
        const profile = await getProfile();
        setCompletionScore(profile?.profile_completion_score || 0);
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, []);

  const missingSections = [
    { name: 'Academic Records', complete: completionScore >= 40 },
    { name: 'Test Scores', complete: completionScore >= 50 },
    { name: 'Preferences', complete: completionScore >= 60 },
    { name: 'Research Interests', complete: completionScore >= 70 },
  ].filter((section) => !section.complete);

  const circumference = 2 * Math.PI * 42;
  const offset = circumference - (completionScore / 100) * circumference;

  const getProgressColor = () => {
    if (completionScore >= 80) return '#4A9D6E';
    if (completionScore >= 50) return '#D4A34E';
    return '#C75B5B';
  };

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
                    {completionScore}%
                  </span>
                </div>
              </div>
            </div>

            <div className="text-center mb-4">
              {completionScore >= 60 ? (
                <div className="flex items-center justify-center gap-2 text-sm text-success">
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span className="font-medium">Ready for recommendations</span>
                </div>
              ) : (
                <p className="text-sm text-textSecondary">
                  Complete your profile to unlock recommendations
                </p>
              )}
            </div>

            {missingSections.length > 0 && (
              <div className="space-y-2 flex-1">
                <p className="text-xs font-medium text-textMuted uppercase tracking-wide mb-2">
                  To complete:
                </p>
                {missingSections.slice(0, 3).map((section, index) => (
                  <motion.div
                    key={section.name}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className="flex items-center gap-2 text-sm text-textSecondary"
                  >
                    {SECTION_ICONS[section.name]}
                    <span>{section.name}</span>
                  </motion.div>
                ))}
              </div>
            )}

            <Button asChild className="w-full mt-4">
              <Link href="/profile">
                {completionScore < 60 ? 'Complete Profile' : 'Update Profile'}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
