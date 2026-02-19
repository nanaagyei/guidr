'use client';

import { useState } from 'react';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { ParallaxLayer } from '@/components/landing/ParallaxLayer';

const PARTNER_LOGOS = [
  { name: 'Harvard University', domain: 'harvard.edu', initials: 'H' },
  { name: 'Stanford University', domain: 'stanford.edu', initials: 'S' },
  { name: 'MIT', domain: 'mit.edu', initials: 'MIT' },
  { name: 'Yale University', domain: 'yale.edu', initials: 'Y' },
  { name: 'Princeton University', domain: 'princeton.edu', initials: 'P' },
  { name: 'Columbia University', domain: 'columbia.edu', initials: 'C' },
  { name: 'UC Berkeley', domain: 'berkeley.edu', initials: 'UCB' },
  { name: 'University of Chicago', domain: 'uchicago.edu', initials: 'UC' },
];

function LogoItem({ logo }: { logo: (typeof PARTNER_LOGOS)[0] }) {
  const [hasError, setHasError] = useState(false);

  if (hasError) {
    return (
      <div
        className="flex items-center justify-center h-12 w-full grayscale opacity-60 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
        title={logo.name}
      >
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
            <span className="text-xs font-bold text-textSecondary">{logo.initials}</span>
          </div>
          <span className="text-sm font-medium text-textSecondary hidden lg:block">{logo.name.split(' ')[0]}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex items-center justify-center gap-2 h-12 w-full grayscale opacity-60 hover:grayscale-0 hover:opacity-100 transition-all duration-300"
      title={logo.name}
    >
      <div className="relative w-10 h-10 shrink-0 flex items-center justify-center">
        <Image
          src={`https://logo.clearbit.com/${logo.domain}`}
          alt={logo.name}
          width={40}
          height={40}
          className="object-contain"
          onError={() => setHasError(true)}
          unoptimized
        />
      </div>
      <span className="text-sm font-medium text-textSecondary hidden lg:block">{logo.name.split(' ')[0]}</span>
    </div>
  );
}

export function LandingLogoCloud() {
  return (
    <section className="relative py-16 sm:py-20 bg-white border-y border-border/30 overflow-hidden">
      <ParallaxLayer
        scrollRange={[200, 800]}
        offsetRange={[0, 40]}
        className="absolute inset-0 pointer-events-none"
      >
        <div className="absolute inset-0 bg-gradient-to-b from-transparent via-landingMint/20 to-transparent" />
      </ParallaxLayer>
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section label */}
        <p className="text-center text-xs font-semibold uppercase tracking-widest-plus text-textMuted mb-10">
          Trusted by applicants to
        </p>

        {/* Logo grid */}
        <motion.div
          className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-8 items-center justify-items-center"
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: '-50px' }}
          variants={{
            visible: {
              transition: {
                staggerChildren: 0.08,
                delayChildren: 0.1,
              },
            },
          }}
        >
          {PARTNER_LOGOS.map((logo) => (
            <motion.div
              key={logo.name}
              variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0 },
              }}
              transition={{ duration: 0.4 }}
            >
              <LogoItem logo={logo} />
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
