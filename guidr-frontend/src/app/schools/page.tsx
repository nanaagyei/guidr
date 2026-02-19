'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { motion, AnimatePresence } from 'framer-motion';
import { searchPrograms } from '@/utils/api';
import ProgramCard from '@/components/ProgramCard';
import { ProgramCardSkeleton, FilterSidebarSkeleton } from '@/components/ui/loading-skeleton';
import { NoResultsState, ErrorState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';

const DEGREE_OPTIONS = [
  { value: '', label: 'All Degrees' },
  { value: 'masters', label: 'Masters' },
  { value: 'phd', label: 'PhD' },
];

const COUNTRY_OPTIONS = [
  { value: '', label: 'All Countries' },
  { value: 'USA', label: 'United States' },
  { value: 'Canada', label: 'Canada' },
  { value: 'UK', label: 'United Kingdom' },
  { value: 'Germany', label: 'Germany' },
  { value: 'Australia', label: 'Australia' },
];

const FIELD_OPTIONS = [
  { value: '', label: 'All Fields' },
  { value: 'Computer Science', label: 'Computer Science' },
  { value: 'Business', label: 'Business & MBA' },
  { value: 'Engineering', label: 'Engineering' },
  { value: 'Data Science', label: 'Data Science' },
  { value: 'Medicine', label: 'Medicine & Health' },
  { value: 'Law', label: 'Law' },
  { value: 'Education', label: 'Education' },
  { value: 'Psychology', label: 'Psychology' },
  { value: 'Arts', label: 'Arts & Humanities' },
];

export default function SchoolsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
  
  const [loading, setLoading] = useState(true);
  const [programs, setPrograms] = useState<any[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [hasSearched, setHasSearched] = useState(false);

  const [filters, setFilters] = useState({
    keyword: '',
    degree_level: '',
    field_of_study: '',
    country: '',
    min_tuition: '',
    max_tuition: '',
  });

  const [debouncedKeyword, setDebouncedKeyword] = useState('');
  const [showFilters, setShowFilters] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
  }, [user, router]);

  // Debounce keyword search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedKeyword(filters.keyword);
    }, 400);
    return () => clearTimeout(timer);
  }, [filters.keyword]);

  // Use ref for toast to avoid re-triggering effects
  const toastRef = useRef(toast);
  toastRef.current = toast;

  const loadPrograms = useCallback(async () => {
    setLoading(true);

    try {
      const params: any = {
        page: currentPage,
        page_size: 12,
      };

      if (debouncedKeyword) params.keyword = debouncedKeyword;
      if (filters.degree_level) params.degree_level = filters.degree_level;
      if (filters.field_of_study) params.field_of_study = filters.field_of_study;
      if (filters.country) params.country = filters.country;
      if (filters.min_tuition) params.min_tuition = parseFloat(filters.min_tuition);
      if (filters.max_tuition) params.max_tuition = parseFloat(filters.max_tuition);

      const data = await searchPrograms(params);
      setPrograms(data.results || []);
      setTotalPages(data.total_pages || 1);
      setTotalResults(data.total_results || 0);
      setHasSearched(true);
    } catch (err: any) {
      // Only show error once, don't retry
      toastRef.current.error(err.message || 'Unable to load programs. Please try again.');
      setPrograms([]);
    } finally {
      setLoading(false);
    }
  }, [currentPage, debouncedKeyword, filters.degree_level, filters.field_of_study, filters.country, filters.min_tuition, filters.max_tuition]);

  useEffect(() => {
    if (user) {
      loadPrograms();
    }
  }, [user, loadPrograms]);

  function handleFilterChange(key: string, value: string) {
    setFilters({ ...filters, [key]: value });
    setCurrentPage(1);
  }

  function clearFilters() {
    setFilters({
      keyword: '',
      degree_level: '',
      field_of_study: '',
      country: '',
      min_tuition: '',
      max_tuition: '',
    });
    setCurrentPage(1);
    toast.info('Filters cleared');
  }

  const hasActiveFilters = useMemo(() => {
    return Object.values(filters).some(v => v !== '');
  }, [filters]);

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
          Explore Programs
        </h1>
        <p className="text-textSecondary">
          Discover graduate programs that match your academic goals and preferences.
        </p>
      </motion.div>

      <div className="flex gap-6">
        {/* Filter Sidebar */}
        <AnimatePresence>
          {showFilters && (
            <motion.aside
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="w-72 flex-shrink-0"
            >
              <div className="card p-5 sticky top-6">
                <div className="flex items-center justify-between mb-5">
                  <h2 className="font-semibold text-text">Filters</h2>
                  {hasActiveFilters && (
                    <button
                      onClick={clearFilters}
                      className="text-xs text-primary hover:text-primaryHover font-medium"
                    >
                      Clear all
                    </button>
                  )}
                </div>
                
                <div className="space-y-5">
                  {/* Degree Level */}
                  <div>
                    <label className="block text-sm font-medium text-textSecondary mb-2">
                      Degree Level
                    </label>
                    <select
                      value={filters.degree_level}
                      onChange={(e) => handleFilterChange('degree_level', e.target.value)}
                      className="input text-sm py-2.5"
                    >
                      {DEGREE_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Field of Study */}
                  <div>
                    <label className="block text-sm font-medium text-textSecondary mb-2">
                      Field of Study
                    </label>
                    <select
                      value={filters.field_of_study}
                      onChange={(e) => handleFilterChange('field_of_study', e.target.value)}
                      className="input text-sm py-2.5"
                    >
                      {FIELD_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Country */}
                  <div>
                    <label className="block text-sm font-medium text-textSecondary mb-2">
                      Country
                    </label>
                    <select
                      value={filters.country}
                      onChange={(e) => handleFilterChange('country', e.target.value)}
                      className="input text-sm py-2.5"
                    >
                      {COUNTRY_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Tuition Range */}
                  <div>
                    <label className="block text-sm font-medium text-textSecondary mb-2">
                      Tuition Range ($/year)
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        value={filters.min_tuition}
                        onChange={(e) => handleFilterChange('min_tuition', e.target.value)}
                        placeholder="Min"
                        className="input text-sm py-2.5 flex-1"
                      />
                      <span className="text-textMuted">-</span>
                      <input
                        type="number"
                        value={filters.max_tuition}
                        onChange={(e) => handleFilterChange('max_tuition', e.target.value)}
                        placeholder="Max"
                        className="input text-sm py-2.5 flex-1"
                      />
                    </div>
                  </div>
                </div>

                {/* Quick Stats - Placeholder for future Lottie animation */}
                <div className="mt-6 pt-5 border-t border-border">
                  <div className="bg-primaryLight/50 rounded-xl p-4 text-center">
                    {/* LOTTIE PLACEHOLDER: Add animated search/filter illustration here */}
                    <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-primary/10 flex items-center justify-center">
                      <svg className="w-6 h-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
                      </svg>
                    </div>
                    <p className="text-xs text-primary font-medium">
                      Refine your search
                    </p>
                    <p className="text-2xs text-textSecondary mt-1">
                      Use filters to narrow down programs
                    </p>
                  </div>
                </div>
              </div>
            </motion.aside>
          )}
        </AnimatePresence>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          {/* Search Bar & Controls */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="mb-6"
          >
            <div className="flex gap-3">
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
                  value={filters.keyword}
                  onChange={(e) => handleFilterChange('keyword', e.target.value)}
                  placeholder="Search by program name, university, or keyword..."
                  className="input pl-12 text-base"
                />
                {filters.keyword && (
                  <button
                    onClick={() => handleFilterChange('keyword', '')}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-muted transition-colors"
                  >
                    <svg className="w-4 h-4 text-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
              
              <Button
                variant="outline"
                onClick={() => setShowFilters(!showFilters)}
                className={!showFilters ? 'bg-primary/5' : ''}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6h9.75M10.5 6a1.5 1.5 0 11-3 0m3 0a1.5 1.5 0 10-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m-9.75 0h9.75" />
                </svg>
                <span className="hidden sm:inline">Filters</span>
              </Button>
            </div>
            
            {/* Results count */}
            {hasSearched && !loading && (
              <motion.p 
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-sm text-textSecondary mt-3"
              >
                {totalResults > 0 
                  ? `Found ${totalResults.toLocaleString()} program${totalResults !== 1 ? 's' : ''}`
                  : 'No programs found'
                }
                {hasActiveFilters && ' matching your criteria'}
              </motion.p>
            )}
          </motion.div>

          {/* Results Grid */}
          {loading ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <ProgramCardSkeleton />
                </motion.div>
              ))}
            </div>
          ) : programs.length === 0 ? (
            <NoResultsState
              query={filters.keyword || undefined}
              onClearFilters={hasActiveFilters ? clearFilters : undefined}
            />
          ) : (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <AnimatePresence mode="popLayout">
                  {programs.map((program, index) => (
                    <ProgramCard key={program.id} {...program} index={index} />
                  ))}
                </AnimatePresence>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center justify-center gap-2 mt-8"
                >
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                    </svg>
                    Previous
                  </Button>
                  
                  <div className="flex items-center gap-1 px-2">
                    {Array.from({ length: Math.min(5, totalPages) }).map((_, i) => {
                      let pageNum;
                      if (totalPages <= 5) {
                        pageNum = i + 1;
                      } else if (currentPage <= 3) {
                        pageNum = i + 1;
                      } else if (currentPage >= totalPages - 2) {
                        pageNum = totalPages - 4 + i;
                      } else {
                        pageNum = currentPage - 2 + i;
                      }
                      
                      return (
                        <button
                          key={pageNum}
                          onClick={() => setCurrentPage(pageNum)}
                          className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                            currentPage === pageNum
                              ? 'bg-primary text-white'
                              : 'text-textSecondary hover:bg-muted'
                          }`}
                        >
                          {pageNum}
                        </button>
                      );
                    })}
                  </div>
                  
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  </Button>
                </motion.div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
