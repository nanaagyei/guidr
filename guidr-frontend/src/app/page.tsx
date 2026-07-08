'use client';

import {
  LandingHeader,
  LandingHero,
  LandingLogoCloud,
  LandingFeatures,
  LandingCTA,
  LandingFooter,
} from '@/components/landing';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <LandingHeader />
      <main className="flex-1">
        <LandingHero />
        <LandingLogoCloud />
        <LandingFeatures />
        <LandingCTA />
      </main>
      <LandingFooter />
    </div>
  );
}
