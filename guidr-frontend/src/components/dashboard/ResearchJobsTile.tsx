'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Badge } from '@/components/ui/badge';
import { getLatestRecommendations } from '@/utils/api';
import { motion } from 'framer-motion';
import { Activity, ArrowRight, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Job {
  id: string;
  type: string;
  status: string;
  created_at?: string;
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: {
    icon: <Clock className="h-3.5 w-3.5" />,
    color: 'warning',
    label: 'Pending',
  },
  running: {
    icon: <Loader2 className="h-3.5 w-3.5 animate-spin" />,
    color: 'info',
    label: 'Running',
  },
  completed: {
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
    color: 'success',
    label: 'Completed',
  },
  failed: {
    icon: <XCircle className="h-3.5 w-3.5" />,
    color: 'danger',
    label: 'Failed',
  },
};

export default function ResearchJobsTile() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchJobs() {
      try {
        const data = await getLatestRecommendations();
        // Build a list of "jobs" from recommendation sessions
        if (data) {
          const sessionJobs: Job[] = [];
          if (data.session_id) {
            sessionJobs.push({
              id: data.session_id,
              type: 'Recommendations',
              status: data.status || 'completed',
              created_at: data.created_at,
            });
          }
          setJobs(sessionJobs);
        }
      } catch {
        // No jobs to show
      } finally {
        setLoading(false);
      }
    }
    fetchJobs();
  }, []);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          icon={<Activity className="h-5 w-5" />}
          title="Research Jobs"
          actionLabel="View All"
          actionHref="/recommendations"
        />
      </CardHeader>
      <CardContent className="flex-1 flex flex-col pt-0">
        {loading ? (
          <div className="space-y-3">
            <Skeleton variant="text" className="w-full h-10" />
            <Skeleton variant="text" className="w-full h-10" />
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState
            illustration={<Activity className="h-8 w-8 text-textMuted" />}
            title="No active jobs"
            description="Generate recommendations or run enrichment to see jobs here."
          />
        ) : (
          <div className="space-y-2">
            {jobs.map((job, idx) => {
              const config = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
              return (
                <motion.div
                  key={job.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="flex items-center justify-between p-3 rounded-lg border border-border bg-card hover:bg-card/80 transition"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-textMuted">{config.icon}</span>
                    <div>
                      <p className="text-sm font-medium text-text">{job.type}</p>
                      {job.created_at && (
                        <p className="text-xs text-textMuted">
                          {new Date(job.created_at).toLocaleDateString()}
                        </p>
                      )}
                    </div>
                  </div>
                  <Badge variant={config.color as any}>{config.label}</Badge>
                </motion.div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
