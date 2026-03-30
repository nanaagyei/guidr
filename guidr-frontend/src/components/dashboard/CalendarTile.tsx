'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Calendar, Clock } from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getUpcomingDeadlines } from '@/utils/api';

export default function CalendarTile() {
  const [deadlines, setDeadlines] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUpcomingDeadlines()
      .then((rows) => setDeadlines(Array.isArray(rows) ? rows : []))
      .catch(() => setDeadlines([]))
      .finally(() => setLoading(false));
  }, []);

  const getDaysUntil = (dateString: string) => {
    const today = new Date();
    const deadline = new Date(dateString);
    return Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  };

  const getUrgencyBadge = (dateString: string) => {
    const days = getDaysUntil(dateString);
    if (days <= 7) return <Badge variant="danger">Urgent</Badge>;
    if (days <= 21) return <Badge variant="warning">Soon</Badge>;
    return <Badge variant="success">Upcoming</Badge>;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Upcoming Deadlines"
          actionLabel="View All"
          actionHref="/schools"
          icon={<Calendar className="h-5 w-5" />}
        />
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : deadlines.length === 0 ? (
          <EmptyState
            illustration={<Calendar className="h-12 w-12 text-textMuted" />}
            title="No upcoming deadlines"
            description="Add schools and programs to track application deadlines"
            action={
              <Button asChild>
                <Link href="/schools">Browse Schools</Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-4 flex-1">
            {deadlines.slice(0, 5).map((deadline) => (
              <div
                key={deadline.id}
                className="p-4 rounded-xl border border-border hover:border-primary/30 transition-colors bg-muted/30"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-text text-sm mb-1 truncate">
                      {deadline.school_name}
                    </h3>
                    <p className="text-xs text-textSecondary truncate">
                      {deadline.program_name}
                    </p>
                  </div>
                  {getUrgencyBadge(deadline.deadline_date)}
                </div>
                <div className="flex items-center gap-2 text-xs text-textSecondary">
                  <Clock className="h-3 w-3" />
                  <span className="font-medium">{formatDate(deadline.deadline_date)}</span>
                  <span className="text-textMuted">•</span>
                  <span>
                    {(() => {
                      const d = getDaysUntil(deadline.deadline_date);
                      if (d <= 0) return 'Due today';
                      if (d === 1) return 'Due tomorrow';
                      return `${d} days left`;
                    })()}
                  </span>
                </div>
                {deadline.is_verified === false && (
                  <p className="text-xs text-amber-500 mt-1">Data may be incomplete — verify with school</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
