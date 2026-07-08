'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, Suspense } from 'react';
import SettingsSidebar from '@/components/settings/SettingsSidebar';
import ProfileSettings from '@/components/settings/ProfileSettings';
import AcademicSettings from '@/components/settings/AcademicSettings';
import ApplicationSettings from '@/components/settings/ApplicationSettings';
import PrivacySettings from '@/components/settings/PrivacySettings';

function SettingsContent() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const section = searchParams.get('section') || 'profile';

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  const renderSection = () => {
    switch (section) {
      case 'profile':
        return <ProfileSettings />;
      case 'academic':
        return <AcademicSettings />;
      case 'application':
        return <ApplicationSettings />;
      case 'privacy':
        return <PrivacySettings />;
      default:
        return <ProfileSettings />;
    }
  };

  return (
    <div className="max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-text mb-2">Settings</h1>
        <p className="text-textSecondary">Manage your account settings and preferences.</p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        <div className="lg:w-64 flex-shrink-0">
          <SettingsSidebar />
        </div>
        <div className="flex-1">
          {renderSection()}
        </div>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <SettingsContent />
    </Suspense>
  );
}
