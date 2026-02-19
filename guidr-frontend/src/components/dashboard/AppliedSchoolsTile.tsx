'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { FileCheck, Clock } from 'lucide-react';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { EmptyState } from '@/components/ui/empty-state';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getMockAppliedSchools, type MockAppliedSchool } from '@/utils/mockData';

export default function AppliedSchoolsTile() {
  const [applications, setApplications] = useState<MockAppliedSchool[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchApplications = async () => {
      setLoading(true);
      setTimeout(() => {
        const data = getMockAppliedSchools();
        setApplications(data);
        setLoading(false);
      }, 500);
    };

    fetchApplications();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'applied':
        return <Badge variant="success">Applied</Badge>;
      case 'in_progress':
        return <Badge variant="warning">In Progress</Badge>;
      case 'interested':
        return <Badge variant="info">Interested</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const getDaysUntil = (dateString: string) => {
    const today = new Date();
    const deadline = new Date(dateString);
    const diffTime = deadline.getTime() - today.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Applied Schools"
          actionLabel="Manage Applications"
          actionHref="/dashboard/applications"
          icon={<FileCheck className="h-5 w-5" />}
        />
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          </div>
        ) : applications.length === 0 ? (
          <EmptyState
            illustration={<FileCheck className="h-12 w-12 text-textMuted" />}
            title="No applications yet"
            description="Start applying to schools and track your progress here"
            action={
              <Button asChild>
                <Link href="/schools">Browse Schools</Link>
              </Button>
            }
          />
        ) : (
          <div className="space-y-3 flex-1">
            {applications.map((app) => {
              const daysUntil = app.application_deadline
                ? getDaysUntil(app.application_deadline)
                : null;

              return (
                <div
                  key={app.id}
                  className="p-3 rounded-xl border border-border hover:border-primary/30 transition-colors bg-muted/30"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-text text-sm mb-1 truncate">
                        {app.school_name}
                      </h3>
                      <p className="text-xs text-textSecondary truncate mb-2">
                        {app.program_name}
                      </p>
                    </div>
                    {getStatusBadge(app.status)}
                  </div>
                  {app.application_deadline && (
                    <div className="flex items-center gap-2 text-xs text-textSecondary">
                      <Clock className="h-3 w-3" />
                      <span>
                        Deadline: {formatDate(app.application_deadline)}
                        {daysUntil !== null && daysUntil >= 0 && (
                          <span className="ml-1">
                            ({daysUntil === 0
                              ? 'Due today'
                              : daysUntil === 1
                                ? '1 day left'
                                : `${daysUntil} days left`})
                          </span>
                        )}
                      </span>
                    </div>
                  )}
                  {app.applied_date && (
                    <div className="text-xs text-textMuted mt-1">
                      Applied: {formatDate(app.applied_date)}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
