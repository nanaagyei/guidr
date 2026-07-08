'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import {
  getProfessors,
  generateProfessorEmail,
  updateOutreachEmail,
  getOutreachEmails,
  getInstitutions,
} from '@/utils/api';
import ProfessorCard from '@/components/ProfessorCard';
import EmailDraftModal from '@/components/EmailDraftModal';
import { Button } from '@/components/ui/button';
import { GraduationCap, Search, Filter, X, Loader2, AlertCircle } from 'lucide-react';
import ProfileHealthBanner from '@/components/ProfileHealthBanner';

export default function ProfessorsPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [professors, setProfessors] = useState<any[]>([]);
  const [institutions, setInstitutions] = useState<any[]>([]);
  const [error, setError] = useState('');
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);

  const [filters, setFilters] = useState({
    institution_id: '',
    country: '',
    research_keyword: '',
  });

  const [searchKeyword, setSearchKeyword] = useState('');
  const [debouncedKeyword, setDebouncedKeyword] = useState('');

  // Simple debounce implementation
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedKeyword(searchKeyword);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchKeyword]);

  const [selectedEmailDraft, setSelectedEmailDraft] = useState<any>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [generatingEmail, setGeneratingEmail] = useState(false);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadInstitutions();
    loadProfessors();
  }, [user, router]);

  useEffect(() => {
    loadProfessors();
  }, [debouncedKeyword, filters.institution_id, filters.country, currentPage]);

  async function loadInstitutions() {
    try {
      const data = await getInstitutions();
      setInstitutions(data);
    } catch (err) {
      console.error('Failed to load institutions:', err);
    }
  }

  async function loadProfessors() {
    setLoading(true);
    setError('');
    try {
      const params: any = {
        page: currentPage,
        page_size: 20,
      };

      if (filters.institution_id) {
        params.institution_id = filters.institution_id;
      }

      if (filters.country) {
        params.country = filters.country;
      }

      if (debouncedKeyword) {
        params.research_keyword = debouncedKeyword;
      }

      const data = await getProfessors(params);
      setProfessors(data.results || []);
      setTotalPages(data.total_pages || 1);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateEmail(professorId: string) {
    setGeneratingEmail(true);
    setError('');
    try {
      const draft = await generateProfessorEmail(professorId);
      setSelectedEmailDraft(draft);
      setShowEmailModal(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGeneratingEmail(false);
    }
  }

  async function handleSaveEmail(subject: string, body: string) {
    if (!selectedEmailDraft) return;
    try {
      await updateOutreachEmail(selectedEmailDraft.id, subject, body);
    } catch (err: any) {
      setError(err.message);
      throw err;
    }
  }

  const handleCopyEmail = () => {
    // Copy functionality handled in modal
  };

  const clearFilter = (key: string) => {
    setFilters(prev => ({ ...prev, [key]: '' }));
    setCurrentPage(1);
  };

  // Get unique countries from institutions
  const countries = Array.from(
    new Set(institutions.map(inst => inst.country).filter(Boolean))
  ).sort();

  return (
    <div className="max-w-7xl mx-auto">
      <ProfileHealthBanner requiredLevel={2} featureName="Professors" />
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-semibold text-text mb-2">Professors</h1>
          <p className="text-textSecondary">Find professors and generate personalized outreach emails</p>
        </div>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-errorLight border border-error/30 text-error px-4 py-3 rounded-xl mb-6 flex items-start gap-3"
        >
          <AlertCircle className="h-5 w-5 flex-shrink-0 mt-0.5" />
          <span>{error}</span>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Filters Sidebar */}
        <div className="lg:col-span-1">
          <div className="card p-5 sticky top-6">
            <div className="flex items-center gap-2 mb-4">
              <Filter className="h-5 w-5 text-text" />
              <h2 className="text-lg font-semibold text-text">Filters</h2>
            </div>

            <div className="space-y-5">
              {/* Search */}
              <div>
                <label className="block text-sm font-medium text-textSecondary mb-2">
                  Search Research Area
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-textMuted" />
                  <input
                    type="text"
                    value={searchKeyword}
                    onChange={(e) => setSearchKeyword(e.target.value)}
                    placeholder="e.g., machine learning"
                    className="input pl-10 text-sm py-2.5"
                  />
                  {searchKeyword && (
                    <button
                      onClick={() => setSearchKeyword('')}
                      className="absolute right-3 top-1/2 transform -translate-y-1/2 text-textMuted hover:text-textSecondary"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Institution Filter */}
              <div>
                <label className="block text-sm font-medium text-textSecondary mb-2">
                  Institution
                </label>
                <select
                  value={filters.institution_id}
                  onChange={(e) => {
                    setFilters({ ...filters, institution_id: e.target.value });
                    setCurrentPage(1);
                  }}
                  className="input text-sm py-2.5"
                >
                  <option value="">All Institutions</option>
                  {institutions.map((inst) => (
                    <option key={inst.id} value={inst.id}>
                      {inst.name}
                    </option>
                  ))}
                </select>
                {filters.institution_id && (
                  <button
                    onClick={() => clearFilter('institution_id')}
                    className="mt-2 text-xs text-primary hover:text-primaryHover font-medium"
                  >
                    Clear
                  </button>
                )}
              </div>

              {/* Country Filter */}
              <div>
                <label className="block text-sm font-medium text-textSecondary mb-2">
                  Country
                </label>
                <select
                  value={filters.country}
                  onChange={(e) => {
                    setFilters({ ...filters, country: e.target.value });
                    setCurrentPage(1);
                  }}
                  className="input text-sm py-2.5"
                >
                  <option value="">All Countries</option>
                  {countries.map((country) => (
                    <option key={country} value={country}>
                      {country}
                    </option>
                  ))}
                </select>
                {filters.country && (
                  <button
                    onClick={() => clearFilter('country')}
                    className="mt-2 text-xs text-primary hover:text-primaryHover font-medium"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                className="h-8 w-8 border-4 border-primary border-t-transparent rounded-full"
              />
            </div>
          ) : professors.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-card rounded-xl p-12 text-center border-2 border-dashed border-primary/20"
            >
              <GraduationCap className="h-16 w-16 text-text/40 mx-auto mb-4" />
              <p className="text-lg text-text mb-2 font-medium">No professors found</p>
              <p className="text-sm text-textSecondary">
                Try adjusting your filters or search terms
              </p>
            </motion.div>
          ) : (
            <>
              <div className="mb-4 text-sm text-textSecondary">
                Found {professors.length} professor{professors.length !== 1 ? 's' : ''}
              </div>

              <div className="grid grid-cols-1 gap-4 mb-6">
                {professors.map((prof, index) => (
                  <ProfessorCard
                    key={prof.id}
                    professor={prof}
                    onGenerateEmail={handleGenerateEmail}
                    index={index}
                  />
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-textSecondary px-4">
                    Page {currentPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    Next
                  </Button>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* Email Draft Modal */}
      {showEmailModal && selectedEmailDraft && (
        <EmailDraftModal
          isOpen={showEmailModal}
          onClose={() => {
            setShowEmailModal(false);
            setSelectedEmailDraft(null);
          }}
          emailDraft={selectedEmailDraft}
          onSave={handleSaveEmail}
          onCopy={handleCopyEmail}
        />
      )}
    </div>
  );
}
