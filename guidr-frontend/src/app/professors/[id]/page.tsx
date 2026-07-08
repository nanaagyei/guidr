'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  GraduationCap,
  MapPin,
  Mail,
  ExternalLink,
  Globe,
  BookOpen,
  Sparkles,
  DollarSign,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Tag,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import FitScoreCard from '@/components/FitScoreCard';
import EmailDraftModal from '@/components/EmailDraftModal';
import {
  getProfessorDetail,
  getProfessorFitScore,
  generateProfessorEmail,
} from '@/utils/api';

export default function ProfessorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const professorId = params.id as string;

  const [professor, setProfessor] = useState<any>(null);
  const [fitScore, setFitScore] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [fitLoading, setFitLoading] = useState(true);
  const [error, setError] = useState('');

  const [emailDraft, setEmailDraft] = useState<any>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [generatingEmail, setGeneratingEmail] = useState(false);

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadData();
  }, [user, professorId]);

  // Auto-open email draft if action=draft-email
  useEffect(() => {
    if (searchParams.get('action') === 'draft-email' && professor && !emailDraft) {
      handleGenerateEmail();
    }
  }, [professor, searchParams]);

  async function loadData() {
    setLoading(true);
    setFitLoading(true);

    // Load professor detail and fit score in parallel
    const detailPromise = getProfessorDetail(professorId)
      .then((data) => {
        setProfessor(data);
        setError('');
      })
      .catch((err) => setError(err.message || 'Failed to load professor'))
      .finally(() => setLoading(false));

    const fitPromise = getProfessorFitScore(professorId)
      .then((data) => setFitScore(data))
      .catch(() => setFitScore(null))
      .finally(() => setFitLoading(false));

    await Promise.all([detailPromise, fitPromise]);
  }

  async function handleGenerateEmail() {
    if (generatingEmail) return;
    setGeneratingEmail(true);
    try {
      const draft = await generateProfessorEmail(professorId);
      setEmailDraft(draft);
      setShowEmailModal(true);
    } catch (err: any) {
      console.error('Failed to generate email:', err);
    } finally {
      setGeneratingEmail(false);
    }
  }

  if (!user) return null;

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-textSecondary hover:text-text transition mb-6 cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="animate-pulse space-y-6">
          <div className="flex items-start gap-4">
            <div className="h-16 w-16 rounded-2xl bg-muted" />
            <div className="flex-1 space-y-2">
              <div className="h-7 w-64 bg-muted rounded" />
              <div className="h-4 w-48 bg-muted rounded" />
              <div className="h-4 w-32 bg-muted rounded" />
            </div>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-4">
              <div className="h-32 bg-muted rounded-2xl" />
              <div className="h-24 bg-muted rounded-2xl" />
            </div>
            <div className="h-80 bg-muted rounded-2xl" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !professor) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 text-sm text-textSecondary hover:text-text transition mb-6 cursor-pointer"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </button>
        <div className="bg-errorLight rounded-2xl border border-error/20 p-8 text-center">
          <AlertCircle className="h-10 w-10 text-error mx-auto mb-3" />
          <p className="text-sm font-medium text-text mb-1">Professor Not Found</p>
          <p className="text-xs text-textSecondary">{error || 'This professor could not be loaded.'}</p>
          <Button onClick={() => router.push('/professors')} className="mt-4">
            Browse Professors
          </Button>
        </div>
      </div>
    );
  }

  const inst = professor.institution || {};
  const location = [inst.city, inst.country].filter(Boolean).join(', ');
  const enrichment = professor.enrichment || {};
  const tags = professor.tags || [];
  const recentPapers = enrichment.recent_papers || [];
  const fundingOpps = professor.funding_opportunities || [];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Back */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-textSecondary hover:text-text transition mb-6 cursor-pointer"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Professors
      </button>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col sm:flex-row items-start gap-4 mb-8"
      >
        <div className="p-4 bg-primary/10 rounded-2xl flex-shrink-0">
          <GraduationCap className="h-8 w-8 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-2xl sm:text-3xl font-display font-bold text-text mb-1">
            {professor.full_name}
          </h1>
          {professor.title && (
            <p className="text-base text-textSecondary mb-2">{professor.title}</p>
          )}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-textSecondary">
            {inst.name && (
              <span className="flex items-center gap-1.5 font-medium">
                <GraduationCap className="h-4 w-4" />
                {inst.name}
              </span>
            )}
            {location && (
              <span className="flex items-center gap-1.5">
                <MapPin className="h-4 w-4" />
                {location}
              </span>
            )}
          </div>

          {/* Badges */}
          <div className="flex flex-wrap gap-2 mt-3">
            {professor.is_accepting_students === true && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-successLight text-success text-xs font-medium rounded-lg border border-success/20">
                <CheckCircle2 className="h-3 w-3" />
                Accepting Students
              </span>
            )}
            {professor.funding_count > 0 && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-successLight text-success text-xs font-medium rounded-lg border border-success/20">
                <DollarSign className="h-3 w-3" />
                Funding Available
              </span>
            )}
            {enrichment.is_stale && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-warningLight text-warning text-xs font-medium rounded-lg border border-warning/20">
                <AlertCircle className="h-3 w-3" />
                Data may be outdated
              </span>
            )}
          </div>
        </div>
      </motion.div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column — Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Research Summary */}
          {professor.research_summary && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-card rounded-2xl border border-border p-6"
            >
              <h2 className="text-sm font-semibold text-text uppercase tracking-wider mb-3 flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-textMuted" />
                Research
              </h2>
              <p className="text-sm text-textSecondary leading-relaxed">
                {professor.research_summary}
              </p>
            </motion.section>
          )}

          {/* Tags */}
          {tags.length > 0 && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="bg-card rounded-2xl border border-border p-6"
            >
              <h2 className="text-sm font-semibold text-text uppercase tracking-wider mb-3 flex items-center gap-2">
                <Tag className="h-4 w-4 text-textMuted" />
                Research Interests
              </h2>
              <div className="flex flex-wrap gap-2">
                {tags.map((tag: string, i: number) => (
                  <span
                    key={i}
                    className="px-3 py-1.5 bg-primary/8 text-primary text-xs font-medium rounded-lg border border-primary/15"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </motion.section>
          )}

          {/* Recent Papers */}
          {recentPapers.length > 0 && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="bg-card rounded-2xl border border-border p-6"
            >
              <h2 className="text-sm font-semibold text-text uppercase tracking-wider mb-3 flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-textMuted" />
                Recent Publications
              </h2>
              <div className="space-y-3">
                {recentPapers.map((paper: any, i: number) => (
                  <div key={i} className="p-3 rounded-xl bg-muted/50 border border-border/50">
                    <p className="text-sm font-medium text-text leading-snug mb-1">
                      {paper.title}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-textMuted">
                      {paper.year && (
                        <span className="flex items-center gap-1">
                          <Calendar className="h-3 w-3" />
                          {paper.year}
                        </span>
                      )}
                      {paper.citation_count != null && (
                        <span>{paper.citation_count} citations</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </motion.section>
          )}

          {/* Funding Opportunities */}
          {fundingOpps.length > 0 && (
            <motion.section
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="bg-card rounded-2xl border border-border p-6"
            >
              <h2 className="text-sm font-semibold text-text uppercase tracking-wider mb-3 flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-textMuted" />
                Funding at {inst.name || 'Institution'}
              </h2>
              <div className="space-y-2">
                {fundingOpps.map((f: any) => (
                  <div key={f.id} className="flex items-center justify-between p-3 rounded-xl bg-successLight/50 border border-success/10">
                    <div>
                      <p className="text-sm font-medium text-text">{f.name}</p>
                      {f.type && <p className="text-xs text-textMuted capitalize">{f.type}</p>}
                    </div>
                    {f.amount && (
                      <span className="text-sm font-semibold text-success">{f.amount}</span>
                    )}
                  </div>
                ))}
              </div>
            </motion.section>
          )}

          {/* External Links & Actions */}
          <motion.section
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-card rounded-2xl border border-border p-6"
          >
            <h2 className="text-sm font-semibold text-text uppercase tracking-wider mb-4 flex items-center gap-2">
              <Globe className="h-4 w-4 text-textMuted" />
              Links & Actions
            </h2>
            <div className="flex flex-wrap gap-3">
              <Button
                onClick={handleGenerateEmail}
                disabled={generatingEmail}
                className="gap-2"
              >
                {generatingEmail ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4" />
                    Generate Email Draft
                  </>
                )}
              </Button>

              {professor.email && (
                <a
                  href={`mailto:${professor.email}`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-muted text-text font-medium rounded-lg hover:bg-border transition text-sm cursor-pointer"
                >
                  <Mail className="h-4 w-4" />
                  {professor.email}
                </a>
              )}

              {professor.personal_page_url && (
                <a
                  href={professor.personal_page_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-muted text-text font-medium rounded-lg hover:bg-border transition text-sm cursor-pointer"
                >
                  <Globe className="h-4 w-4" />
                  Personal Page
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}

              {professor.scholar_profile_url && (
                <a
                  href={professor.scholar_profile_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-muted text-text font-medium rounded-lg hover:bg-border transition text-sm cursor-pointer"
                >
                  <GraduationCap className="h-4 w-4" />
                  Google Scholar
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>

            {/* Enrichment metadata */}
            {enrichment.last_updated && (
              <p className="text-2xs text-textMuted mt-4">
                Last updated: {new Date(enrichment.last_updated).toLocaleDateString()}
                {enrichment.h_index != null && ` · h-index: ${enrichment.h_index}`}
                {enrichment.citation_count != null && ` · ${enrichment.citation_count.toLocaleString()} citations`}
              </p>
            )}
          </motion.section>
        </div>

        {/* Right column — Fit Score (sticky on desktop) */}
        <div className="lg:sticky lg:top-20 lg:self-start space-y-4">
          <FitScoreCard data={fitScore} loading={fitLoading} />
        </div>
      </div>

      {/* Email Draft Modal */}
      {showEmailModal && emailDraft && (
        <EmailDraftModal
          isOpen={showEmailModal}
          emailDraft={emailDraft}
          onClose={() => setShowEmailModal(false)}
        />
      )}
    </div>
  );
}
