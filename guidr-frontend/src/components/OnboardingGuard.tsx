'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { checkOnboardingStatus } from '@/utils/api';

interface OnboardingGuardProps {
  children: React.ReactNode;
}

export default function OnboardingGuard({ children }: OnboardingGuardProps) {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    async function checkOnboarding() {
      // Don't redirect if already on onboarding page
      if (pathname === '/onboarding') {
        setChecking(false);
        return;
      }

      // Wait for auth to load
      if (authLoading) {
        return;
      }

      // If not authenticated, let auth handle redirect
      if (!user) {
        setChecking(false);
        return;
      }

      try {
        const { needsOnboarding } = await checkOnboardingStatus();
        if (needsOnboarding) {
          router.push('/onboarding');
        }
      } catch (error) {
        console.error('Failed to check onboarding status:', error);
        // If check fails, allow access (fail open)
      } finally {
        setChecking(false);
      }
    }

    checkOnboarding();
  }, [user, authLoading, pathname, router]);

  // Show loading while checking
  if (checking || authLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}

