'use client';

import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';

const CONTACT_EMAIL = 'hello@guidr.app';

const FOOTER_COLUMNS = [
  {
    title: 'Product',
    links: [
      { label: 'School Search', href: '/schools' },
      { label: 'Universities', href: '/institutions' },
      { label: 'AI Recommendations', href: '/recommendations' },
      { label: 'Faculty Matching', href: '/professors' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '/about' },
      { label: 'Contact', href: '/contact' },
      { label: 'Help Center', href: '/help' },
    ],
  },
  {
    title: 'Get Started',
    links: [
      { label: 'Sign In', href: '/auth/login' },
      { label: 'Create Account', href: '/auth/register' },
    ],
  },
];

export function LandingFooter() {
  return (
    <footer className="bg-white border-t border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        {/* Main footer content */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-5 gap-8 lg:gap-12"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.4 }}
        >
          {/* Logo and description */}
          <div className="col-span-2">
            <Link href="/" className="inline-block" aria-label="Guidr home">
              <Image
                src="/images/guidr-logo.png"
                alt="Guidr"
                width={140}
                height={48}
                className="h-10 w-auto object-contain"
              />
            </Link>
            <p className="mt-4 max-w-xs text-sm text-textSecondary leading-relaxed">
              The smarter way to find graduate programs, faculty, and funding —
              matched to your research and goals.
            </p>
            <a
              href={`mailto:${CONTACT_EMAIL}`}
              className="mt-4 inline-block text-sm font-medium text-text hover:text-accent transition-colors"
            >
              {CONTACT_EMAIL}
            </a>
          </div>

          {/* Link columns */}
          {FOOTER_COLUMNS.map(({ title, links }) => (
            <div key={title}>
              <h3 className="text-sm font-medium text-text mb-4">
                {title}
              </h3>
              <ul className="space-y-3">
                {links.map(({ label, href }) => (
                  <li key={href}>
                    <Link
                      href={href}
                      className="text-sm text-textSecondary hover:text-text transition-colors"
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </motion.div>

        {/* Bottom section */}
        <div className="mt-12 pt-8 border-t border-border">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            {/* Copyright */}
            <p className="text-xs text-textMuted uppercase tracking-wide">
              &copy; {new Date().getFullYear()} Guidr. All rights reserved.
            </p>

            {/* Legal + CTA */}
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
              <Link
                href="/terms"
                className="text-xs text-textMuted hover:text-text transition-colors uppercase tracking-wide"
              >
                Terms of Service
              </Link>
              <Link
                href="/privacy"
                className="text-xs text-textMuted hover:text-text transition-colors uppercase tracking-wide"
              >
                Privacy Policy
              </Link>
              <Button
                size="sm"
                className="rounded-full px-6 text-xs uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
                asChild
              >
                <Link href="/auth/register">Sign Up</Link>
              </Button>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
