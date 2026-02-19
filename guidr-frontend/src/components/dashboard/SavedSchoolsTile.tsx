'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { School, MapPin, ExternalLink, X } from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { getMockSavedSchools, type MockSavedSchool } from '@/utils/mockData';

export default function SavedSchoolsTile() {
  const [schools, setSchools] = useState<MockSavedSchool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSchools = async () => {
      setLoading(true);
      setTimeout(() => {
        const data = getMockSavedSchools();
        setSchools(data);
        setLoading(false);
      }, 500);
    };

    fetchSchools();
  }, []);

  const handleRemove = (id: string) => {
    setSchools((prev) => prev.filter((s) => s.id !== id));
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Saved Schools"
          actionLabel="Browse Schools"
          actionHref="/schools"
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
            description="Browse and save schools to track them here"
            action={
              <Button asChild>
                <Link href="/schools">Browse Schools</Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-3 flex-1">
            {schools.map((school) => (
              <div
                key={school.id}
                className="p-3 rounded-xl border border-border hover:border-primary/30 transition-colors bg-muted/30 group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start gap-2 mb-1">
                      <School className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                      <h3 className="font-semibold text-text text-sm truncate">
                        {school.name}
                      </h3>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-textSecondary mb-1">
                      <MapPin className="h-3 w-3" />
                      <span>{school.location}</span>
                    </div>
                    <p className="text-xs text-textMuted">
                      {school.program_count} program{school.program_count !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <button
                    onClick={() => handleRemove(school.id)}
                    className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center text-textMuted hover:text-error opacity-0 group-hover:opacity-100 transition-opacity rounded-lg hover:bg-error/10"
                    title="Remove"
                    aria-label="Remove from saved"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-2 pt-2 border-t border-border">
                  <Link
                    href={`/schools/${school.id}`}
                    className="text-xs text-primary hover:text-primaryHover font-medium inline-flex items-center gap-1"
                  >
                    View Details
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
