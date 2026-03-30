'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  requestRecommendations,
  getLatestRecommendations,
  getRecommendationSession,
  saveRecommendation,
} from '@/utils/api';
import { getProfile } from '@/utils/api';
import RecommendationCard from '@/components/RecommendationCard';
import TierBadge from '@/components/TierBadge';
import { Sparkles, Loader2, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useProfileCompletion } from '@/contexts/ProfileCompletionContext';
import RecommendationExplainModal from '@/components/RecommendationExplainModal';

export default function RecommendationsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const { completion } = useProfileCompletion();
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [recommendations, setRecommendations] = useState<any>(null);
  const [profile, setProfile] = useState<any>(null);
  const [error, setError] = useState('');
  const [pollingSessionId, setPollingSessionId] = useState<string | null>(null);
  const pollingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pollingStartRef = useRef<number>(0);
  const POLLING_TIMEOUT_MS = 120_000; // 2 minutes max
  const [showConfirm, setShowConfirm] = useState(false);
  const [explainRec, setExplainRec] = useState<any>(null);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadProfile();
    loadRecommendations();
  }, [user, router]);

  useEffect(() => {
    // Poll for session completion if generating
    if (pollingSessionId && !pollingIntervalRef.current) {
      pollingStartRef.current = Date.now();
      pollingIntervalRef.current = setInterval(() => {
        // Stop polling after timeout
        if (Date.now() - pollingStartRef.current > POLLING_TIMEOUT_MS) {
          clearInterval(pollingIntervalRef.current!);
          pollingIntervalRef.current = null;
          setPollingSessionId(null);
          setGenerating(false);
          setError('Request timed out. The pipeline may still be processing — try refreshing in a moment.');
          return;
        }
        checkSessionStatus(pollingSessionId);
      }, 3000); // Poll every 3 seconds
    }

    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [pollingSessionId]);

  async function loadProfile() {
    try {
      const data = await getProfile();
      setProfile(data);
    } catch (err: any) {
      console.error('Failed to load profile:', err);
    }
  }

  async function loadRecommendations() {
    setLoading(true);
    setError('');
    try {
      const data = await getLatestRecommendations();
      if (data) {
        setRecommendations(data);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function checkSessionStatus(sessionId: string) {
    try {
      const session = await getRecommendationSession(sessionId);
      if (session.status === 'completed') {
        setPollingSessionId(null);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setGenerating(false);
        await loadRecommendations();
      } else if (session.status === 'failed') {
        setPollingSessionId(null);
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
        setGenerating(false);
        setError(session.error_message || 'Failed to generate recommendations');
      }
    } catch (err: any) {
      console.error('Failed to check session status:', err);
    }
  }

  async function handleGenerateRecommendations() {
    setGenerating(true);
    setError('');
    setPollingSessionId(null);

    try {
      const response = await requestRecommendations('dashboard_button');
      if (response.status === 'failed') {
        setGenerating(false);
        setError(response.error_message || 'Failed to generate recommendations');
        return;
      }
      if (response.session_id) {
        if (response.status === 'completed') {
          // Completed synchronously — reload results
          setGenerating(false);
          await loadRecommendations();
          return;
        }
        setPollingSessionId(response.session_id);
        // Check immediately, then polling will take over
        setTimeout(() => checkSessionStatus(response.session_id), 2000);
      }
    } catch (err: any) {
      setGenerating(false);
      setError(err.message);
    }
  }

  async function handleSaveSchool(resultId: string) {
    try {
      await saveRecommendation(resultId);
      // Update local state to mark as saved
      setRecommendations((prev: any) => {
        if (!prev?.results) return prev;
        return {
          ...prev,
          results: prev.results.map((r: any) =>
            r.result_id === resultId ? { ...r, is_saved: true } : r
          ),
        };
      });
    } catch (err: any) {
      setError(err.message || 'Failed to save school');
      throw err;
    }
  }

  const completionScore = completion?.percent ?? profile?.profile_completion_score ?? 0;
  const canGenerate = (completion?.level ?? 0) >= 2;

  // Group recommendations by tier
  const tierGroups = recommendations?.results?.reduce((acc: any, rec: any) => {
    const tier = rec.tier;
    if (!acc[tier]) {
      acc[tier] = [];
    }
    acc[tier].push(rec);
    return acc;
  }, {}) || {};

  const tierOrder = ['dream', 'reach', 'target', 'safety'];
  const tierLabels = {
    dream: 'Dream Programs',
    reach: 'Reach Programs',
    target: 'Target Programs',
    safety: 'Safety Programs',
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-center min-h-[400px]">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full"
          />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-text mb-2">Recommendations</h1>
          <p className="text-textSecondary">Get personalized program recommendations based on your profile.</p>
        </div>
        <Button
          onClick={() => {
            if (recommendations) {
              setShowConfirm(true);
            } else {
              handleGenerateRecommendations();
            }
          }}
          disabled={!canGenerate || generating}
        >
          {generating ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5" />
              {recommendations ? 'Regenerate' : 'Get Recommendations'}
            </>
          )}
        </Button>
      </div>

      {/* Profile Completion Warning */}
      {!canGenerate && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-warningLight border border-warning/30 rounded-xl p-4 mb-6 flex items-start gap-3"
        >
          <AlertCircle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-text mb-1">Profile Incomplete</p>
            <p className="text-sm text-textSecondary">
              Complete your profile (60%+) and upload at least one transcript to get recommendations.
              Current completion: {completionScore}%
            </p>
            <button
              onClick={() => router.push('/profile')}
              className="mt-2 text-sm font-medium text-primary hover:text-primaryHover underline"
            >
              Go to Profile
            </button>
          </div>
        </motion.div>
      )}

      {/* Error */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-errorLight border border-error/30 text-error px-4 py-3 rounded-xl mb-6 flex items-start gap-3"
        >
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p>{error}</p>
          </div>
        </motion.div>
      )}

      {/* Generating State */}
      {generating && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="bg-card rounded-xl p-12 text-center mb-6 border-2 border-dashed border-primary/20"
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            className="flex justify-center mb-4"
          >
            <Loader2 className="h-12 w-12 text-text" />
          </motion.div>
          <p className="text-lg font-medium text-text mb-2">Researching programs...</p>
          <p className="text-sm text-textSecondary">This may take 30-60 seconds as we analyze programs for you</p>
        </motion.div>
      )}

      {/* Recommendations Display */}
      {recommendations && recommendations.results && recommendations.results.length > 0 && (
        <div className="space-y-8">
          {/* Summary */}
          <div className="bg-card rounded-xl p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-semibold text-text mb-2">Your Recommendations</h2>
                <p className="text-sm text-textSecondary">
                  {recommendations.results.length} programs recommended based on your profile.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {tierOrder.map((tier) => {
                  const count = tierGroups[tier]?.length || 0;
                  return count > 0 ? (
                    <TierBadge key={tier} tier={tier as any} count={count} />
                  ) : null;
                })}
              </div>
            </div>
          </div>

          {/* Tier Groups */}
          {tierOrder.map((tier) => {
            const tierRecs = tierGroups[tier];
            if (!tierRecs || tierRecs.length === 0) return null;

            return (
              <div key={tier} className="space-y-4">
                <motion.h2
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="text-2xl font-semibold text-text flex items-center gap-3"
                >
                  <TierBadge tier={tier as any} count={tierRecs.length} />
                  <span>{tierLabels[tier as keyof typeof tierLabels]}</span>
                </motion.h2>
                <div className="grid grid-cols-1 gap-4">
                  {tierRecs.map((rec: any, index: number) => (
                    <RecommendationCard
                      key={rec.result_id || rec.program_id || index}
                      recommendation={rec}
                      index={index}
                      onExplain={setExplainRec}
                      onSave={handleSaveSchool}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty State */}
      {!recommendations && !generating && canGenerate && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-card rounded-xl p-12 text-center border-2 border-dashed border-primary/20"
        >
          <motion.div
            animate={{ y: [0, -10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="flex justify-center mb-4"
          >
            <Sparkles className="h-16 w-16 text-text/40" />
          </motion.div>
          <p className="text-lg text-text mb-2 font-medium">No recommendations yet</p>
          <p className="text-sm text-textSecondary mb-6">
            Click the button above to generate personalized program recommendations
          </p>
        </motion.div>
      )}
      {/* Confirmation dialog for regeneration */}
      {showConfirm && (
        <>
          <div className="fixed inset-0 bg-black/40 z-50" onClick={() => setShowConfirm(false)} />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-card rounded-2xl border border-border shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-display font-semibold text-text mb-2">Regenerate Recommendations?</h3>
              <p className="text-sm text-textSecondary mb-6">
                This may take 30-60 seconds. Your current results will be preserved until new ones are ready.
              </p>
              <div className="flex items-center justify-end gap-3">
                <button
                  onClick={() => setShowConfirm(false)}
                  className="px-4 py-2 text-sm font-medium text-textSecondary hover:text-text transition"
                >
                  Cancel
                </button>
                <Button
                  onClick={() => {
                    setShowConfirm(false);
                    handleGenerateRecommendations();
                  }}
                >
                  <RefreshCw className="h-4 w-4" />
                  Regenerate
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Explain recommendation modal */}
      <RecommendationExplainModal
        recommendation={explainRec}
        open={!!explainRec}
        onClose={() => setExplainRec(null)}
      />
    </div>
  );
}

