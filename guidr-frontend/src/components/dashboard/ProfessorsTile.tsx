'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { GraduationCap, Mail, ExternalLink, MapPin } from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { getMockProfessors, type MockProfessor } from '@/utils/mockData';
import { useRouter } from 'next/navigation';

export default function ProfessorsTile() {
  const router = useRouter();
  const [professors, setProfessors] = useState<MockProfessor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfessors = async () => {
      setLoading(true);
      setTimeout(() => {
        const data = getMockProfessors();
        setProfessors(data);
        setLoading(false);
      }, 500);
    };

    fetchProfessors();
  }, []);

  const handleDraftEmail = async (professorId: string) => {
    router.push(`/professors/${professorId}?action=draft-email`);
  };

  const handleLearnMore = (professorId: string) => {
    router.push(`/professors/${professorId}`);
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Recommended Professors"
          actionLabel="Browse All"
          actionHref="/professors"
          icon={<GraduationCap className="h-5 w-5" />}
        />
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : professors.length === 0 ? (
          <EmptyState
            illustration={<GraduationCap className="h-12 w-12 text-textMuted" />}
            title="No recommended professors"
            description="Complete your profile to get professor recommendations"
            action={
              <Button asChild>
                <Link href="/professors">Browse Professors</Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-3 flex-1">
            {professors.slice(0, 3).map((professor) => (
              <div
                key={professor.id}
                className="p-3 rounded-xl border border-border hover:border-primary/30 transition-colors bg-muted/30"
              >
                <div className="flex items-start gap-3 mb-2">
                  <div className="p-2 bg-primary/10 rounded-xl flex-shrink-0">
                    <GraduationCap className="h-4 w-4 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-text text-sm mb-1 truncate">
                      {professor.full_name}
                    </h3>
                    {professor.title && (
                      <p className="text-xs text-textSecondary mb-2">{professor.title}</p>
                    )}
                    <div className="flex items-center gap-1 text-xs text-textSecondary mb-1">
                      <MapPin className="h-3 w-3" />
                      <span className="font-medium">{professor.school_name}</span>
                    </div>
                    {professor.department && (
                      <p className="text-xs text-textMuted mb-2">{professor.department}</p>
                    )}
                    <p className="text-xs text-text">{professor.research_area}</p>
                  </div>
                </div>
                <div className="flex gap-2 pt-2 border-t border-border">
                  <Button
                    size="sm"
                    onClick={() => handleDraftEmail(professor.id)}
                  >
                    <Mail className="h-3 w-3" />
                    Draft
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleLearnMore(professor.id)}
                  >
                    View
                    <ExternalLink className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
