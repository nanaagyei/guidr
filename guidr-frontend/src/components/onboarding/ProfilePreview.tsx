'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { GraduationCap, MapPin, FlaskConical, BookOpen } from 'lucide-react';
import { OnboardingData } from './validation';
import { cn } from '@/lib/utils';

interface ProfilePreviewProps {
  data: OnboardingData;
}

const fadeIn = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25 },
};

export default function ProfilePreview({ data }: ProfilePreviewProps) {
  const hasAnyData =
    data.intended_degree ||
    data.primary_field_of_study ||
    (data.preferred_countries && data.preferred_countries.length > 0) ||
    (data.research_areas && data.research_areas.length > 0) ||
    data.gpa_value;

  return (
    <div className="hidden lg:block w-80 shrink-0">
      <div className="sticky top-8">
        <div className="rounded-2xl border border-border bg-card p-6 shadow-soft">
          <h3 className="text-sm font-display font-semibold text-textMuted uppercase tracking-wider mb-4">
            Your Profile Preview
          </h3>

          {!hasAnyData ? (
            <p className="text-sm text-textMuted italic">
              Start filling in your details and watch your profile come to life.
            </p>
          ) : (
            <div className="space-y-4">
              <AnimatePresence mode="popLayout">
                {/* Degree badge */}
                {data.intended_degree && (
                  <motion.div key="degree" {...fadeIn} className="flex items-center gap-2">
                    <GraduationCap className="h-4 w-4 text-accent" />
                    <span className="text-sm font-medium text-text capitalize">
                      {data.intended_degree === 'phd' ? 'PhD' : "Master's"} Candidate
                    </span>
                  </motion.div>
                )}

                {/* Field of study */}
                {data.primary_field_of_study && (
                  <motion.div key="field" {...fadeIn}>
                    <p className="text-xs text-textMuted mb-1">Field of Study</p>
                    <p className="text-sm text-text font-medium">{data.primary_field_of_study}</p>
                  </motion.div>
                )}

                {/* Countries */}
                {data.preferred_countries && data.preferred_countries.length > 0 && (
                  <motion.div key="countries" {...fadeIn}>
                    <p className="text-xs text-textMuted mb-1.5 flex items-center gap-1">
                      <MapPin className="h-3 w-3" /> Preferred Locations
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {data.preferred_countries.map((c) => (
                        <span
                          key={c}
                          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-secondary/10 text-secondary border border-secondary/20"
                        >
                          {c}
                        </span>
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* Research areas */}
                {data.research_areas && data.research_areas.length > 0 && (
                  <motion.div key="research" {...fadeIn}>
                    <p className="text-xs text-textMuted mb-1.5 flex items-center gap-1">
                      <FlaskConical className="h-3 w-3" /> Research Interests
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {data.research_areas.map((r) => (
                        <span
                          key={r}
                          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-accent/10 text-accent border border-accent/20"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </motion.div>
                )}

                {/* GPA */}
                {data.gpa_value != null && data.gpa_value > 0 && (
                  <motion.div key="gpa" {...fadeIn}>
                    <p className="text-xs text-textMuted mb-1 flex items-center gap-1">
                      <BookOpen className="h-3 w-3" /> GPA
                    </p>
                    <p className="text-sm text-text font-medium">
                      {data.gpa_value}
                      {data.gpa_scale ? ` / ${data.gpa_scale}` : ''}
                    </p>
                  </motion.div>
                )}

                {/* Funding */}
                {data.funding_priority && (
                  <motion.div key="funding" {...fadeIn}>
                    <p className="text-xs text-textMuted mb-1">Funding Priority</p>
                    <p className="text-sm text-text font-medium capitalize">
                      {data.funding_priority.replace(/_/g, ' ')}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          <div className="mt-6 pt-4 border-t border-border">
            <p className="text-xs text-textMuted">
              This is how Guidr sees your profile. The more you fill in, the better your recommendations.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
