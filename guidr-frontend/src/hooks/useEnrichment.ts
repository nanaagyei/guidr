'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { triggerEnrichment, pollJobStatus } from '@/utils/api';

interface EnrichmentState {
  isEnriching: boolean;
  lastUpdated: string | null;
  isStale: boolean;
  jobId: string | null;
  jobStatus: string | null;
  error: string | null;
}

interface UseEnrichmentOptions {
  entityKind: string;
  entityId: string;
  enrichmentData?: {
    last_updated: string | null;
    is_stale: boolean;
  } | null;
  autoRefreshIfStale?: boolean;
}

const POLL_INTERVAL = 3000; // 3 seconds
const MAX_POLL_ATTEMPTS = 60; // 3 minutes max

export function useEnrichment({
  entityKind,
  entityId,
  enrichmentData,
  autoRefreshIfStale = false,
}: UseEnrichmentOptions) {
  const [state, setState] = useState<EnrichmentState>({
    isEnriching: false,
    lastUpdated: enrichmentData?.last_updated ?? null,
    isStale: enrichmentData?.is_stale ?? true,
    jobId: null,
    jobStatus: null,
    error: null,
  });

  const pollRef = useRef<NodeJS.Timeout | null>(null);
  const pollCountRef = useRef(0);

  // Update state when enrichmentData prop changes
  useEffect(() => {
    if (enrichmentData) {
      setState((prev) => ({
        ...prev,
        lastUpdated: enrichmentData.last_updated,
        isStale: enrichmentData.is_stale,
      }));
    }
  }, [enrichmentData?.last_updated, enrichmentData?.is_stale]);

  // Poll job status when we have an active job
  const startPolling = useCallback((jobId: string) => {
    pollCountRef.current = 0;

    const poll = async () => {
      if (pollCountRef.current >= MAX_POLL_ATTEMPTS) {
        setState((prev) => ({
          ...prev,
          isEnriching: false,
          error: 'Enrichment timed out',
        }));
        return;
      }

      try {
        pollCountRef.current += 1;
        const status = await pollJobStatus(jobId);

        setState((prev) => ({
          ...prev,
          jobStatus: status.status,
        }));

        if (status.status === 'succeeded') {
          setState((prev) => ({
            ...prev,
            isEnriching: false,
            isStale: false,
            lastUpdated: new Date().toISOString(),
            error: null,
          }));
          return;
        }

        if (status.status === 'failed' || status.status === 'canceled') {
          setState((prev) => ({
            ...prev,
            isEnriching: false,
            error: status.error || 'Enrichment failed',
          }));
          return;
        }

        // Still running — continue polling
        pollRef.current = setTimeout(poll, POLL_INTERVAL);
      } catch {
        setState((prev) => ({
          ...prev,
          isEnriching: false,
          error: 'Failed to check enrichment status',
        }));
      }
    };

    pollRef.current = setTimeout(poll, POLL_INTERVAL);
  }, []);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, []);

  const triggerRefresh = useCallback(async () => {
    if (state.isEnriching) return;

    setState((prev) => ({
      ...prev,
      isEnriching: true,
      error: null,
    }));

    try {
      const result = await triggerEnrichment(entityKind, entityId);

      if (result.status === 'cache_hit') {
        setState((prev) => ({
          ...prev,
          isEnriching: false,
          isStale: false,
          lastUpdated: result.cache?.computed_at || new Date().toISOString(),
        }));
        return;
      }

      if (result.status === 'quota_exceeded') {
        setState((prev) => ({
          ...prev,
          isEnriching: false,
          error: result.message || 'Enrichment limit reached',
        }));
        return;
      }

      if (result.status === 'enqueued' || result.status === 'dedup_in_progress') {
        const jobId = result.job?.job_id;
        setState((prev) => ({
          ...prev,
          jobId,
          jobStatus: result.job?.status || 'queued',
        }));
        if (jobId) {
          startPolling(jobId);
        }
        return;
      }
    } catch (err: any) {
      setState((prev) => ({
        ...prev,
        isEnriching: false,
        error: err.message || 'Failed to trigger enrichment',
      }));
    }
  }, [entityKind, entityId, state.isEnriching, startPolling]);

  // Auto-trigger if stale and option is enabled
  useEffect(() => {
    if (autoRefreshIfStale && state.isStale && !state.isEnriching && entityId) {
      triggerRefresh();
    }
  }, [autoRefreshIfStale, state.isStale, entityId]);

  return {
    isEnriching: state.isEnriching,
    lastUpdated: state.lastUpdated,
    isStale: state.isStale,
    jobStatus: state.jobStatus,
    error: state.error,
    triggerRefresh,
  };
}
