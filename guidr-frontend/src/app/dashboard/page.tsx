'use client';

import { useAuth } from '@/contexts/AuthContext';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { motion } from 'framer-motion';
import CalendarTile from '@/components/dashboard/CalendarTile';
import SavedSchoolsTile from '@/components/dashboard/SavedSchoolsTile';
import RecommendedSchoolsTile from '@/components/dashboard/RecommendedSchoolsTile';
import ProfileCompletionTile from '@/components/dashboard/ProfileCompletionTile';
import AppliedSchoolsTile from '@/components/dashboard/AppliedSchoolsTile';
import TipsTile from '@/components/dashboard/TipsTile';
import ProfessorsTile from '@/components/dashboard/ProfessorsTile';
import ResearchJobsTile from '@/components/dashboard/ResearchJobsTile';

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push('/auth/login');
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full"
        />
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Welcome Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-semibold text-text mb-2">
          Welcome back, {user.full_name || user.email}!
        </h1>
        <p className="text-textSecondary">Here is an overview of your graduate school application journey.</p>
      </motion.div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Row 1: Profile Completion - Full Width on Large */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-1"
        >
          <ProfileCompletionTile />
        </motion.div>

        {/* Calendar Tile */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="lg:col-span-1"
        >
          <CalendarTile />
        </motion.div>

        {/* Tips Tile */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-1"
        >
          <TipsTile />
        </motion.div>

        {/* Recommended Schools - Spans 2 columns on large */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="lg:col-span-2"
        >
          <RecommendedSchoolsTile />
        </motion.div>

        {/* Saved Schools */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="lg:col-span-1"
        >
          <SavedSchoolsTile />
        </motion.div>

        {/* Applied Schools - Spans 2 columns */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="lg:col-span-2"
        >
          <AppliedSchoolsTile />
        </motion.div>

        {/* Professors Tile - Sits beside Applied Schools on large */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="lg:col-span-1"
        >
          <ProfessorsTile />
        </motion.div>

        {/* Research Jobs Tile */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.45 }}
          className="lg:col-span-1"
        >
          <ResearchJobsTile />
        </motion.div>
      </div>
    </div>
  );
}
