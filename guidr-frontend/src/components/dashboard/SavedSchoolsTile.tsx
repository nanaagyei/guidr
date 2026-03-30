'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { School, MapPin, ExternalLink, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { getSavedRecommendations, unsaveRecommendation } from '@/utils/api';

function ResearchStatus({ status }: { status: string }) {
  switch (status) {
    case 'completed':
      return (
        <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
          <CheckCircle2 className="h-3 w-3" />
          Research done
        </span>
      );
    case 'running':
      return (
        <span className="inline-flex items-center gap-1 text-xs text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full">
          <Loader2 className="h-3 w-3 animate-spin" />
          Researching...
        </span>
      );
    case 'failed':
      return (
        <span className="inline-flex items-center gap-1 text-xs text-red-700 bg-red-50 px-2 py-0.5 rounded-full">
          <AlertCircle className="h-3 w-3" />
          Research failed
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 text-xs text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full">
          Pending
        </span>
      );
  }
}

export default function SavedSchoolsTile() {
  const [schools, setSchools] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSavedRecommendations()
      .then((rows) => setSchools(Array.isArray(rows) ? rows : []))
      .catch(() => setSchools([]))
      .finally(() => setLoading(false));
  }, []);

  const handleRemove = async (savedId: string) => {
    try {
      await unsaveRecommendation(savedId);
      setSchools((prev) => prev.filter((s) => s.saved_id !== savedId));
    } catch {
      // Optimistic removal on error too
      setSchools((prev) => prev.filter((s) => s.saved_id !== savedId));
    }
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Saved Schools"
          actionLabel="View All"
          actionHref="/recommendations"
          icon={<School className="h-5 w-5" />}
        />
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : schools.length === 0 ? (
          <EmptyState
            illustration={<School className="h-12 w-12 text-textMuted" />}
            title="No saved schools"
            description="Get recommendations and save schools to research them"
            action={
              <Button asChild>
                <Link href="/recommendations">Get Recommendations</Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-3 flex-1">
            {schools.slice(0, 5).map((school) => (
              <div
                key={school.saved_id}
                className="p-3 rounded-xl border border-border hover:border-primary/30 transition-colors bg-muted/30 group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-1">
                      <School className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                      <h3 className="font-semibold text-text text-sm truncate">
                        {school.school_name || school.institution_name || 'Unknown School'}
                      </h3>
                    </div>
                    {school.program_name && (
                      <p className="text-xs text-textSecondary mb-1 ml-6 truncate">
                        {school.program_name}
                      </p>
                    )}
                    {(school.institution_city || school.institution_country) && (
                      <div className="flex items-center gap-1 text-xs text-textSecondary mb-1 ml-6">
                        <MapPin className="h-3 w-3" />
                        <span>
                          {[school.institution_city, school.institution_country]
                            .filter(Boolean)
                            .join(', ')}
                        </span>
                      </div>
                    )}
                    <div className="ml-6 mt-1">
                      <ResearchStatus status={school.research_status} />
                    </div>
                  </div>
                  <button
                    onClick={() => handleRemove(school.saved_id)}
                    className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center text-textMuted hover:text-error opacity-0 group-hover:opacity-100 transition-opacity rounded-lg hover:bg-error/10"
                    title="Remove"
                    aria-label="Remove from saved"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                {school.institution_id && (
                  <div className="mt-2 pt-2 border-t border-border">
                    <Link
                      href={`/institutions/${school.institution_id}`}
                      className="text-xs text-primary hover:text-primaryHover font-medium inline-flex items-center gap-1"
                    >
                      View Details
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
