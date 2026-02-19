'use client';

import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';

const FOOTER_COLUMNS = [
  {
    title: 'Products',
    links: [
      { label: 'School Search', href: '/schools' },
      { label: 'Application Tracker', href: '/dashboard' },
      { label: 'AI Recommendations', href: '/recommendations' },
      { label: 'Faculty Matching', href: '/faculty' },
      { label: 'Funding Discovery', href: '/funding' },
    ],
  },
  {
    title: 'Explore',
    links: [
      { label: 'Blog', href: '/blog' },
      { label: 'Resources', href: '/resources' },
      { label: 'Success Stories', href: '/stories' },
      { label: 'Universities', href: '/universities' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '/about' },
      { label: 'Careers', href: '/careers' },
      { label: 'Press', href: '/press' },
      { label: 'Contact', href: '/contact' },
    ],
  },
  {
    title: 'Other',
    links: [
      { label: 'API Documentation', href: '/docs' },
      { label: 'Help Center', href: '/help' },
      { label: 'Pricing', href: '/#pricing' },
    ],
  },
];

// Social media icons as SVG components
function TwitterIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

function LinkedInIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
    </svg>
  );
}

function DiscordIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189z" />
    </svg>
  );
}

export function LandingFooter() {
  return (
    <footer className="bg-white border-t border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        {/* Main footer content */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-6 gap-8 lg:gap-12"
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
                width={100}
                height={34}
                className="h-18 w-auto object-contain"
              />
            </Link>
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
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            {/* Social icons and app store */}
            <div className="flex items-center gap-4">
              {/* App Store placeholder */}
              <div className="h-10 px-4 bg-text text-white rounded-lg flex items-center gap-2 text-xs font-medium">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
                </svg>
                <div>
                  <span className="block text-[10px] opacity-80">Download on the</span>
                  <span className="block text-xs font-semibold -mt-0.5">App Store</span>
                </div>
              </div>

              {/* Social icons */}
              <div className="flex items-center gap-2">
                <a
                  href="https://discord.gg/guidr"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-10 h-10 rounded-full border border-border flex items-center justify-center text-textSecondary hover:text-text hover:border-borderHover transition-colors"
                >
                  <DiscordIcon className="h-5 w-5" />
                </a>
                <a
                  href="https://twitter.com/guidr"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-10 h-10 rounded-full border border-border flex items-center justify-center text-textSecondary hover:text-text hover:border-borderHover transition-colors"
                >
                  <TwitterIcon className="h-4 w-4" />
                </a>
                <a
                  href="https://linkedin.com/company/guidr"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-10 h-10 rounded-full border border-border flex items-center justify-center text-textSecondary hover:text-text hover:border-borderHover transition-colors"
                >
                  <LinkedInIcon className="h-4 w-4" />
                </a>
              </div>
            </div>

            {/* CTAs */}
            <div className="flex items-center gap-3">
              <Button
                size="sm"
                className="rounded-full px-6 text-xs uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
                asChild
              >
                <Link href="/auth/register">Sign Up</Link>
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="rounded-full px-6 text-xs uppercase tracking-wide font-medium"
                asChild
              >
                <Link href="/contact">Contact Us</Link>
              </Button>
            </div>
          </div>

          {/* Copyright and legal */}
          <div className="mt-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <p className="text-xs text-textMuted uppercase tracking-wide">
              &copy; {new Date().getFullYear()}, Guidr Inc. All rights reserved.
            </p>

            <div className="flex items-center gap-6">
              <Link
                href="/terms"
                className="text-xs text-textMuted hover:text-text transition-colors uppercase tracking-wide"
              >
                Terms of Use
              </Link>
              <span className="text-textMuted">|</span>
              <Link
                href="/privacy"
                className="text-xs text-textMuted hover:text-text transition-colors uppercase tracking-wide"
              >
                Privacy Policy
              </Link>
              <span className="text-textMuted">|</span>
              {/* System status indicator */}
              <a
                href="/status"
                className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-border text-xs text-textMuted hover:text-text transition-colors"
              >
                <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                <span className="uppercase tracking-wide">System Status</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
