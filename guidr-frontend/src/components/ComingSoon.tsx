'use client';

import { ReactNode } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ComingSoonProps {
  title: string;
  description?: string;
  /** Optional icon shown in the badge (defaults to Sparkles) */
  icon?: ReactNode;
  /** Where the primary "Back" button points */
  backHref?: string;
  backLabel?: string;
}

/**
 * Full-page "Coming soon" state used to gate features that are built but not
 * yet ready for launch (e.g. essay feedback, document parsing, funding).
 */
export default function ComingSoon({
  title,
  description,
  icon,
  backHref = '/dashboard',
  backLabel = 'Back to dashboard',
}: ComingSoonProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4 py-16">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="max-w-lg text-center"
      >
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-accent/15 text-accent">
          {icon || <Sparkles className="h-7 w-7" />}
        </div>

        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1 text-xs font-medium uppercase tracking-wide text-textSecondary">
          <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
          Coming soon
        </span>

        <h1 className="mt-5 font-display text-3xl font-semibold text-text">
          {title}
        </h1>

        {description && (
          <p className="mt-3 text-base leading-relaxed text-textSecondary">
            {description}
          </p>
        )}

        <div className="mt-8 flex items-center justify-center gap-3">
          <Button asChild className="rounded-full px-6">
            <Link href={backHref}>{backLabel}</Link>
          </Button>
        </div>
      </motion.div>
    </div>
  );
}
