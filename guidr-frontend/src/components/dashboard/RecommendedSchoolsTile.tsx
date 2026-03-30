'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { Button } from '@/components/ui/button';
import RecommendationCard from '@/components/RecommendationCard';
import { getLatestRecommendations } from '@/utils/api';
import { Sparkles } from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';

export default function RecommendedSchoolsTile() {
  const [recommendations, setRecommendations] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const toast = useToast();

  useEffect(() => {
    const fetchRecommendations = async () => {
      setLoading(true);
      try {
        const data = await getLatestRecommendations();
        setRecommendations(data);
      } catch (error) {
        console.error('Failed to fetch recommendations:', error);
        toast.error('We couldn\'t load your recommendations. Please try again in a few minutes.');
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, []);

  const recCount = recommendations?.results?.length || 0;
  const topRecommendations = recommendations?.results?.slice(0, 3) || [];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Recommended Programs"
          actionLabel="View All"
          actionHref="/recommendations"
          icon={<Sparkles className="h-5 w-5" />}
        />
      </CardHeader>
      <CardContent className="flex-1 pt-0 flex flex-col">
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="p-4 border border-border rounded-xl">
                <div className="flex items-start gap-3">
                  <Skeleton className="w-10 h-10 rounded-xl" />
                  <div className="flex-1">
                    <Skeleton variant="text" className="w-3/4 h-4 mb-2" />
                    <Skeleton variant="text" className="w-1/2 h-3" />
                  </div>
                  <Skeleton className="w-16 h-6 rounded-full" />
                </div>
              </div>
            ))}
          </div>
        ) : recCount === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center min-h-[220px]">
            <EmptyState
              title="No recommendations yet"
              description="Complete your profile to get personalized program recommendations"
              action={
                <Button asChild>
                  <Link href="/profile">Complete Profile</Link>
                </Button>
              }
            />
          </div>
        ) : (
          <div className="space-y-3 flex-1">
            {topRecommendations.map((rec: any, index: number) => (
              <div key={rec.program_id} className="transition-transform hover:translate-x-0.5">
                <RecommendationCard recommendation={rec} index={index} />
              </div>
            ))}
            {recCount > 3 && (
              <div className="pt-3 border-t border-border text-center">
                <p className="text-xs text-textSecondary">
                  +{recCount - 3} more recommendation{recCount - 3 !== 1 ? 's' : ''} available
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
