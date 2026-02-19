'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { motion, AnimatePresence } from 'framer-motion';
import { getInstitutions } from '@/utils/api';
import InstitutionCard from '@/components/InstitutionCard';
import InstitutionModal from '@/components/InstitutionModal';
import { InstitutionCardSkeleton } from '@/components/ui/loading-skeleton';
import { NoResultsState } from '@/components/ui/empty-state';

const COUNTRY_OPTIONS = [
  { value: '', label: 'All Countries' },
  { value: 'USA', label: 'United States' },
  { value: 'Canada', label: 'Canada' },
  { value: 'UK', label: 'United Kingdom' },
  { value: 'Germany', label: 'Germany' },
  { value: 'Australia', label: 'Australia' },
];

const TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'university', label: 'University' },
  { value: 'college', label: 'College' },
  { value: 'institute', label: 'Institute' },
];

const CONTROL_OPTIONS = [
  { value: '', label: 'Public & Private' },
  { value: 'public', label: 'Public Only' },
  { value: 'private', label: 'Private Only' },
];

export default function InstitutionsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
  
  const [loading, setLoading] = useState(true);
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [filteredInstitutions, setFilteredInstitutions] = useState<any[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  
  // Modal state
  const [selectedInstitution, setSelectedInstitution] = useState<any>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [filters, setFilters] = useState({
    search: '',
    country: '',
    type: '',
    control: '',
  });

  const [debouncedSearch, setDebouncedSearch] = useState('');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 12;

  // Use ref for toast to avoid re-triggering effects
  const toastRef = useRef(toast);
  toastRef.current = toast;

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
  }, [user, router]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(filters.search);
    }, 300);
    return () => clearTimeout(timer);
  }, [filters.search]);

  const loadInstitutions = useCallback(async () => {
    setLoading(true);

    try {
      const data = await getInstitutions();
      setInstitutions(data || []);
      setHasSearched(true);
    } catch (err: any) {
      toastRef.current.error(err.message || 'Unable to load institutions');
      setInstitutions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      loadInstitutions();
    }
  }, [user, loadInstitutions]);

  // Client-side filtering
  useEffect(() => {
    let result = [...institutions];

    if (debouncedSearch) {
      const searchLower = debouncedSearch.toLowerCase();
      result = result.filter(inst => 
        inst.name?.toLowerCase().includes(searchLower) ||
        inst.city?.toLowerCase().includes(searchLower) ||
        inst.state_or_province?.toLowerCase().includes(searchLower)
      );
    }

    if (filters.country) {
      result = result.filter(inst => 
        inst.country?.toLowerCase().includes(filters.country.toLowerCase())
      );
    }

    if (filters.type) {
      result = result.filter(inst => 
        inst.institution_type?.toLowerCase() === filters.type.toLowerCase()
      );
    }

    if (filters.control) {
      result = result.filter(inst => 
        inst.public_private?.toLowerCase() === filters.control.toLowerCase()
      );
    }

    setFilteredInstitutions(result);
    setCurrentPage(1); // Reset to first page when filters change
  }, [institutions, debouncedSearch, filters.country, filters.type, filters.control]);

  // Calculate pagination
  const totalPages = Math.ceil(filteredInstitutions.length / ITEMS_PER_PAGE);
  const paginatedInstitutions = useMemo(() => {
    const start = (currentPage - 1) * ITEMS_PER_PAGE;
    return filteredInstitutions.slice(start, start + ITEMS_PER_PAGE);
  }, [filteredInstitutions, currentPage]);

  function handleFilterChange(key: string, value: string) {
    setFilters({ ...filters, [key]: value });
    setCurrentPage(1);
  }

  function clearFilters() {
    setFilters({
      search: '',
      country: '',
      type: '',
      control: '',
    });
    toast.info('Filters cleared');
  }

  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some(v => v !== '');
  }, [filters]);

  function handleInstitutionClick(institution: any) {
    setSelectedInstitution(institution);
    setIsModalOpen(true);
  }

  function handleCloseModal() {
    setIsModalOpen(false);
    // Clear institution after animation completes (150ms)
    setTimeout(() => setSelectedInstitution(null), 150);
  }

  function handleViewPrograms(institutionId: string, institutionName: string) {
    handleCloseModal();
    router.push(`/schools?country=${encodeURIComponent(selectedInstitution?.country || '')}`);
    toast.info(`Showing programs in ${selectedInstitution?.country || 'selected region'}`);
  }

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-7xl mx-auto">
      {/* Page Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-semibold text-text mb-2 font-display">
          Institutions
        </h1>
        <p className="text-textSecondary">
          Browse universities and colleges from around the world.
        </p>
      </motion.div>

      {/* Search and Filters Bar */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-4 mb-6"
      >
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search */}
          <div className="relative flex-1">
            <svg 
              className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-textMuted" 
              fill="none" 
              viewBox="0 0 24 24" 
              stroke="currentColor" 
              strokeWidth={1.5}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
            </svg>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              placeholder="Search institutions by name or location..."
              className="input pl-12"
            />
            {filters.search && (
              <button
                onClick={() => handleFilterChange('search', '')}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-muted transition-colors"
              >
                <svg className="w-4 h-4 text-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <select
              value={filters.country}
              onChange={(e) => handleFilterChange('country', e.target.value)}
              className="input text-sm py-2.5 w-auto min-w-[140px]"
            >
              {COUNTRY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            <select
              value={filters.type}
              onChange={(e) => handleFilterChange('type', e.target.value)}
              className="input text-sm py-2.5 w-auto min-w-[120px]"
            >
              {TYPE_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            <select
              value={filters.control}
              onChange={(e) => handleFilterChange('control', e.target.value)}
              className="input text-sm py-2.5 w-auto min-w-[140px]"
            >
              {CONTROL_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>

            {hasActiveFilters && (
              <button
                onClick={clearFilters}
                className="btn-ghost btn-sm text-primary"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Results count */}
        {hasSearched && !loading && (
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm text-textSecondary mt-4 pt-4 border-t border-border/50"
          >
            {filteredInstitutions.length > 0 
              ? `Showing ${((currentPage - 1) * ITEMS_PER_PAGE) + 1}-${Math.min(currentPage * ITEMS_PER_PAGE, filteredInstitutions.length)} of ${filteredInstitutions.length.toLocaleString()} institution${filteredInstitutions.length !== 1 ? 's' : ''}`
              : 'No institutions found'
            }
            {hasActiveFilters && ' matching your criteria'}
          </motion.p>
        )}
      </motion.div>

      {/* Results Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {Array.from({ length: 9 }).map((_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
            >
              <InstitutionCardSkeleton />
            </motion.div>
          ))}
        </div>
      ) : filteredInstitutions.length === 0 ? (
        <NoResultsState
          query={filters.search || undefined}
          onClearFilters={hasActiveFilters ? clearFilters : undefined}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            <AnimatePresence mode="popLayout">
              {paginatedInstitutions.map((institution, index) => (
                <InstitutionCard
                  key={institution.id}
                  {...institution}
                  index={index}
                  onClick={() => handleInstitutionClick(institution)}
                />
              ))}
            </AnimatePresence>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center justify-center gap-2 mt-8"
            >
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="btn-ghost px-3 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>

              <div className="flex items-center gap-1">
                {/* First page */}
                {currentPage > 3 && (
                  <>
                    <button
                      onClick={() => setCurrentPage(1)}
                      className="btn-ghost w-10 h-10"
                    >
                      1
                    </button>
                    {currentPage > 4 && <span className="px-2 text-textMuted">...</span>}
                  </>
                )}

                {/* Page numbers around current */}
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(page => page >= currentPage - 2 && page <= currentPage + 2)
                  .map(page => (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`w-10 h-10 rounded-lg transition-colors ${
                        page === currentPage
                          ? 'bg-primary text-white font-semibold'
                          : 'btn-ghost'
                      }`}
                    >
                      {page}
                    </button>
                  ))}

                {/* Last page */}
                {currentPage < totalPages - 2 && (
                  <>
                    {currentPage < totalPages - 3 && <span className="px-2 text-textMuted">...</span>}
                    <button
                      onClick={() => setCurrentPage(totalPages)}
                      className="btn-ghost w-10 h-10"
                    >
                      {totalPages}
                    </button>
                  </>
                )}
              </div>

              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="btn-ghost px-3 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
            </motion.div>
          )}
        </>
      )}

      {/* Stats Section */}
      {!loading && filteredInstitutions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mt-12 card p-8 text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primaryLight flex items-center justify-center">
            <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-text mb-2">
            Explore {institutions.length.toLocaleString()}+ Institutions
          </h3>
          <p className="text-textSecondary max-w-md mx-auto">
            Our database is continuously updated with new institutions and programs from IPEDS and College Scorecard data.
          </p>
        </motion.div>
      )}

      {/* Institution Modal */}
      <InstitutionModal
        institution={selectedInstitution}
        isOpen={isModalOpen}
        onClose={handleCloseModal}
        onViewPrograms={handleViewPrograms}
      />
    </div>
  );
}
