'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import { Skeleton } from '@/components/ui/skeleton';
import { getFundingOpportunities } from '@/utils/api';
import { DollarSign, Search, Building2, Calendar, ExternalLink } from 'lucide-react';

const FUNDING_TYPES = [
  { value: '', label: 'All types' },
  { value: 'fellowship', label: 'Fellowship' },
  { value: 'assistantship', label: 'Assistantship' },
  { value: 'scholarship', label: 'Scholarship' },
  { value: 'grant', label: 'Grant' },
  { value: 'waiver', label: 'Waiver' },
];

export default function FundingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [opportunities, setOpportunities] = useState<any[]>([]);
  const [totalResults, setTotalResults] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [fundingType, setFundingType] = useState('');
  const [country, setCountry] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const loadFunding = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getFundingOpportunities({
        keyword: keyword || undefined,
        funding_type: fundingType || undefined,
        country: country || undefined,
        page,
        page_size: 12,
      });
      setOpportunities(data.results || []);
      setTotalResults(data.total_results ?? 0);
      setTotalPages(data.total_pages ?? 1);
      setHasSearched(true);
    } catch (err) {
      console.error('Failed to load funding:', err);
      setOpportunities([]);
      setTotalResults(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  }, [keyword, fundingType, country, page]);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadFunding();
  }, [user, router, loadFunding]);

  const formatAmount = (min?: number | null, max?: number | null, period?: string | null) => {
    if (min == null && max == null) return 'Amount varies';
    const periodStr = period ? `/${period}` : '';
    if (min != null && max != null && min === max) return `$${min.toLocaleString()}${periodStr}`;
    if (min != null && max != null) return `$${min.toLocaleString()} - $${max.toLocaleString()}${periodStr}`;
    if (min != null) return `From $${min.toLocaleString()}${periodStr}`;
    if (max != null) return `Up to $${max.toLocaleString()}${periodStr}`;
    return 'Amount varies';
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return null;
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  if (!user) return null;

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-semibold text-text mb-2">
          Funding Opportunities
        </h1>
        <p className="text-textSecondary">
          Search and filter graduate funding by type, institution, and location.
        </p>
      </div>

      <Card className="mb-6 p-4 sm:p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-2">
            <label htmlFor="funding-keyword" className="text-sm font-medium text-text mb-1.5 block">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-textMuted" />
              <input
                id="funding-keyword"
                type="text"
                placeholder="Keyword (name or description)"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadFunding()}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-card text-text placeholder:text-textMuted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              />
            </div>
          </div>
          <div>
            <label htmlFor="funding-type" className="text-sm font-medium text-text mb-1.5 block">
              Type
            </label>
            <select
              id="funding-type"
              value={fundingType}
              onChange={(e) => setFundingType(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-card text-text focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            >
              {FUNDING_TYPES.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="funding-country" className="text-sm font-medium text-text mb-1.5 block">
              Country
            </label>
            <input
              id="funding-country"
              type="text"
              placeholder="e.g. USA"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && loadFunding()}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-card text-text placeholder:text-textMuted focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
            />
          </div>
        </div>
        <div className="mt-4 flex justify-end">
          <Button onClick={loadFunding}>Apply filters</Button>
        </div>
      </Card>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="p-6">
              <Skeleton className="h-5 w-32 mb-3" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-3/4 mb-4" />
              <Skeleton className="h-8 w-24 rounded-lg" />
            </Card>
          ))}
        </div>
      ) : opportunities.length === 0 ? (
        <Card className="p-12">
          <EmptyState
            illustration={<DollarSign className="h-12 w-12 text-textMuted" />}
            title={hasSearched ? 'No funding opportunities found' : 'Search for funding'}
            description={
              hasSearched
                ? 'Try adjusting your filters or search keyword.'
                : 'Use the filters above to find funding opportunities.'
            }
            action={
              <Button variant="outline" onClick={loadFunding}>
                Refresh
              </Button>
            }
          />
        </Card>
      ) : (
        <>
          <p className="text-sm text-textSecondary mb-4">
            {totalResults} opportunity{totalResults !== 1 ? 'ies' : ''} found
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {opportunities.map((opp) => (
              <Card key={opp.id} className="flex flex-col hover:border-primary/30 transition-colors">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base line-clamp-2">{opp.name}</CardTitle>
                    <Badge variant="secondary" className="shrink-0 capitalize">
                      {opp.funding_type}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 pt-0 space-y-3">
                  {opp.institution_name && (
                    <div className="flex items-center gap-2 text-sm text-textSecondary">
                      <Building2 className="h-4 w-4 shrink-0" />
                      <span className="truncate">{opp.institution_name}</span>
                    </div>
                  )}
                  <p className="text-sm text-text">
                    {formatAmount(opp.amount_min, opp.amount_max, opp.amount_period)}
                  </p>
                  {opp.deadline && (
                    <div className="flex items-center gap-2 text-sm text-textSecondary">
                      <Calendar className="h-4 w-4 shrink-0" />
                      <span>Deadline: {formatDate(opp.deadline)}</span>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {opp.covers_tuition && (
                      <Badge variant="outline" className="text-xs">Tuition</Badge>
                    )}
                    {opp.covers_stipend && (
                      <Badge variant="outline" className="text-xs">Stipend</Badge>
                    )}
                  </div>
                  {opp.website_url && (
                    <a
                      href={opp.website_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primaryHover mt-2"
                    >
                      Learn more
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          {totalPages > 1 && (
            <div className="mt-8 flex items-center justify-center gap-2">
              <Button
                variant="outline"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-sm text-textSecondary px-4">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
