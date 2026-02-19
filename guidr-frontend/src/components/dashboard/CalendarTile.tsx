'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Calendar, Clock } from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getMockDeadlines, type MockDeadline } from '@/utils/mockData';

export default function CalendarTile() {
  const [deadlines, setDeadlines] = useState<MockDeadline[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDeadlines = async () => {
      setLoading(true);
      setTimeout(() => {
        const data = getMockDeadlines();
        setDeadlines(data);
        setLoading(false);
      }, 500);
    };

    fetchDeadlines();
  }, []);

  const getUrgencyBadge = (urgency: string) => {
    switch (urgency) {
      case 'high':
        return <Badge variant="danger">Urgent</Badge>;
      case 'medium':
        return <Badge variant="warning">Soon</Badge>;
      case 'low':
        return <Badge variant="success">Upcoming</Badge>;
      default:
        return <Badge>{urgency}</Badge>;
    }
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
          actionHref="/dashboard/calendar"
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
                  {getUrgencyBadge(deadline.urgency)}
                </div>
                <div className="flex items-center gap-2 text-xs text-textSecondary">
                  <Clock className="h-3 w-3" />
                  <span className="font-medium">{formatDate(deadline.deadline_date)}</span>
                  <span className="text-textMuted">•</span>
                  <span>
                    {deadline.days_until === 0
                      ? 'Due today'
                      : deadline.days_until === 1
                        ? 'Due tomorrow'
                        : `${deadline.days_until} days left`}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
