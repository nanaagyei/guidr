'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getProfileCompletion, ProfileCompletion } from '@/utils/api';
import { useAuth } from './AuthContext';

interface ProfileCompletionContextType {
  completion: ProfileCompletion | null;
  loading: boolean;
  /** Re-fetch completion from server (call after profile updates). */
  refresh: () => Promise<void>;
}

const DEFAULT_COMPLETION: ProfileCompletion = {
  percent: 0,
  level: 0,
  missing_fields: ['intended_degree', 'primary_field_of_study'],
  unlocks: {
    dashboard: false,
    recommendations: false,
    professors: false,
    funding: false,
  },
};

const ProfileCompletionContext = createContext<ProfileCompletionContextType | undefined>(undefined);

export function ProfileCompletionProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [completion, setCompletion] = useState<ProfileCompletion | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCompletion = useCallback(async () => {
    if (!user) {
      setCompletion(null);
      setLoading(false);
      return;
    }
    try {
      const data = await getProfileCompletion();
      setCompletion(data);
    } catch {
      setCompletion(DEFAULT_COMPLETION);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchCompletion();
  }, [fetchCompletion]);

  const refresh = useCallback(async () => {
    await fetchCompletion();
  }, [fetchCompletion]);

  return (
    <ProfileCompletionContext.Provider value={{ completion, loading, refresh }}>
      {children}
    </ProfileCompletionContext.Provider>
  );
}

export function useProfileCompletion() {
  const context = useContext(ProfileCompletionContext);
  if (context === undefined) {
    throw new Error('useProfileCompletion must be used within a ProfileCompletionProvider');
  }
  return context;
}
