'use client';

import { ReactNode } from 'react';
import { LandingHeader } from '@/components/landing/LandingHeader';
import { LandingFooter } from '@/components/landing/LandingFooter';

interface MarketingPageShellProps {
  title: string;
  subtitle?: string;
  /** Optional eyebrow label above the title (e.g. "Legal") */
  eyebrow?: string;
  children: ReactNode;
}

/**
 * Shared shell for public marketing/legal pages (about, contact, terms,
 * privacy). Renders the landing header + footer with a centered content column.
 */
export default function MarketingPageShell({
  title,
  subtitle,
  eyebrow,
  children,
}: MarketingPageShellProps) {
  return (
    <div className="min-h-screen bg-white">
      <LandingHeader />
      <main className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 py-16 lg:py-24">
        <header className="mb-10">
          {eyebrow && (
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-accent">
              {eyebrow}
            </p>
          )}
          <h1 className="font-display text-4xl font-semibold text-text sm:text-5xl">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-4 text-lg leading-relaxed text-textSecondary">
              {subtitle}
            </p>
          )}
        </header>
        <div className="space-y-5 text-base leading-relaxed text-textSecondary [&_a]:text-accent [&_a]:underline [&_a:hover]:opacity-80 [&_h2]:mt-10 [&_h2]:mb-2 [&_h2]:font-display [&_h2]:text-2xl [&_h2]:font-semibold [&_h2]:text-text [&_h3]:mt-6 [&_h3]:mb-1 [&_h3]:text-lg [&_h3]:font-semibold [&_h3]:text-text [&_ul]:list-disc [&_ul]:pl-6 [&_ul]:space-y-2 [&_strong]:text-text">
          {children}
        </div>
      </main>
      <LandingFooter />
    </div>
  );
}
