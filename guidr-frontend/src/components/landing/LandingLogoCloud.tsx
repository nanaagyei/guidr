'use client';

import { useState } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { ParallaxLayer } from '@/components/landing/ParallaxLayer';
import { cn } from '@/lib/utils';

const PARTNER_LOGOS = [
  { name: 'Harvard University', src: '/images/harvard.png', initials: 'H' },
  { name: 'Stanford University', src: '/images/stanford.png', initials: 'S' },
  { name: 'MIT', src: '/images/mit.png', initials: 'MIT' },
  { name: 'Yale University', src: '/images/yale.webp', initials: 'Y' },
  { name: 'Princeton University', src: '/images/princeton.png', initials: 'P' },
  { name: 'Columbia University', src: '/images/columbia.png', initials: 'C' },
  { name: 'UC Berkeley', src: '/images/ucb.png', initials: 'UCB' },
  { name: 'University of Chicago', src: '/images/uchicago.png', initials: 'UC' },
] as const;

const LOGO_PX = 100;

function LogoMarqueeItem({ logo }: { logo: (typeof PARTNER_LOGOS)[number] }) {
  const [hasError, setHasError] = useState(false);

  return (
    <div
      className="flex shrink-0 items-center gap-3 sm:gap-4 pr-10 sm:pr-14 md:pr-16 grayscale opacity-[0.72] transition-all duration-300 motion-safe:hover:grayscale-0 motion-safe:hover:opacity-100"
      title={logo.name}
    >
      <div className="relative flex h-14 w-14 shrink-0 items-center justify-center sm:h-16 sm:w-16 md:h-[4.5rem] md:w-[4.5rem]">
        {hasError ? (
          <div className="flex h-full w-full items-center justify-center rounded-full bg-muted">
            <span className="text-xs font-bold text-textSecondary sm:text-sm">{logo.initials}</span>
          </div>
        ) : (
          <Image
            src={logo.src}
            alt=""
            width={LOGO_PX}
            height={LOGO_PX}
            className="max-h-full max-w-full object-contain p-1"
            onError={() => setHasError(true)}
            unoptimized
          />
        )}
      </div>
      <span className="whitespace-nowrap text-left text-xs font-medium text-textSecondary sm:text-sm md:text-base">
        {logo.name}
      </span>
    </div>
  );
}

function MarqueeStrip({
  'aria-hidden': ariaHidden,
  className,
}: {
  'aria-hidden'?: boolean;
  className?: string;
}) {
  return (
    <div className={cn('flex shrink-0 items-center', className)} aria-hidden={ariaHidden}>
      {PARTNER_LOGOS.map((logo) => (
        <LogoMarqueeItem key={logo.name} logo={logo} />
      ))}
    </div>
  );
}

export function LandingLogoCloud() {
  return (
    <section
      className="relative overflow-hidden border-y border-border/30 bg-white py-12 sm:py-16 md:py-20"
      aria-label="Universities applicants use Guidr for"
    >
      <ParallaxLayer
        scrollRange={[200, 800]}
        offsetRange={[0, 40]}
        className="pointer-events-none absolute inset-0"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-landingMint/20 to-transparent" />
      </ParallaxLayer>

      <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <motion.p
          className="mb-8 text-center text-xs font-semibold uppercase tracking-widest-plus text-textMuted sm:mb-10"
          initial={{ opacity: 0, y: 8 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-40px' }}
          transition={{ duration: 0.45 }}
        >
          Trusted by applicants to
        </motion.p>

        <div className="relative -mx-4 sm:-mx-6 lg:-mx-8">
          <div
            className="pointer-events-none absolute inset-y-0 left-0 z-10 w-10 bg-gradient-to-r from-white to-transparent sm:w-14 md:w-20"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-gradient-to-l from-white to-transparent sm:w-14 md:w-20"
            aria-hidden
          />

          <div className="overflow-hidden">
            <div
              className="flex w-max will-change-transform animate-logo-marquee-slow motion-reduce:mx-auto motion-reduce:animate-none"
              style={{ backfaceVisibility: 'hidden' }}
            >
              <MarqueeStrip />
              <MarqueeStrip aria-hidden className="motion-reduce:hidden" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
