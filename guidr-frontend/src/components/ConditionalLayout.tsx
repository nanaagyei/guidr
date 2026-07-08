'use client';

import { usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useState } from 'react';
import AppSidebar from '@/components/Sidebar';
import OnboardingGuard from '@/components/OnboardingGuard';
import { Menu, X } from 'lucide-react';

export default function ConditionalLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Hide sidebar on auth pages, onboarding, and landing
  const isAuthPage = pathname?.startsWith('/auth');
  const isOnboardingPage = pathname === '/onboarding';
  const isLandingPage = pathname === '/';
  // Public marketing/legal pages render their own header + footer (no sidebar)
  const MARKETING_ROUTES = ['/about', '/contact', '/terms', '/privacy'];
  const isMarketingPage = MARKETING_ROUTES.includes(pathname ?? '');

  // Show sidebar only if user is authenticated and not on auth/onboarding/landing/marketing pages
  const showSidebar =
    !isAuthPage && !isOnboardingPage && !isLandingPage && !isMarketingPage && !loading && user;

  if (isAuthPage || isOnboardingPage || isLandingPage || isMarketingPage) {
    // Full screen layout for auth, onboarding, landing, and marketing pages
    return <>{children}</>;
  }

  // Standard layout with sidebar for authenticated pages
  return (
    <OnboardingGuard>
      <div className="flex min-h-screen h-screen overflow-hidden">
        {/* Desktop Sidebar - Always visible on desktop */}
        {showSidebar && (
          <div className="hidden lg:block">
            <AppSidebar />
          </div>
        )}

        {/* Mobile Sidebar - Overlay drawer (only visible on mobile) */}
        {showSidebar && (
          <div className="lg:hidden">
            <AppSidebar open={mobileSidebarOpen} setOpen={setMobileSidebarOpen} mobile={true} />
          </div>
        )}

        <main className={`${showSidebar ? 'flex-1 overflow-y-auto' : 'w-full'} bg-background relative`}>
          {/* Mobile Hamburger Button */}
          {showSidebar && (
            <button
              data-hamburger
              onClick={() => setMobileSidebarOpen(!mobileSidebarOpen)}
              className="lg:hidden fixed top-4 left-4 z-30 p-2 bg-sidebar text-text rounded-lg shadow-lg hover:bg-sidebarHover transition-colors"
              aria-label="Toggle menu"
            >
              {mobileSidebarOpen ? (
                <X className="h-6 w-6" />
              ) : (
                <Menu className="h-6 w-6" />
              )}
            </button>
          )}
          <div className={`${showSidebar ? 'pt-20 sm:pt-24 lg:pt-8' : 'pt-8 sm:pt-10'} px-4 sm:px-6 lg:px-8 pb-6 sm:pb-8 lg:pb-10`}>
            {children}
          </div>
        </main>
      </div>
    </OnboardingGuard>
  );
}
