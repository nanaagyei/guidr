'use client';

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/contexts/ToastContext';
import { motion } from 'framer-motion';
import { getProgram } from '@/utils/api';
import { DataQualityBadge } from '@/components/ui/data-quality';
import { PageLoadingState } from '@/components/ui/loading-skeleton';
import { ErrorState } from '@/components/ui/empty-state';
import { Button } from '@/components/ui/button';
import { EnrichmentBadge } from '@/components/ui/enrichment-badge';

export default function ProgramDetailPage() {
  const { user } = useAuth();
  const router = useRouter();
  const params = useParams();
  const toast = useToast();
  const programId = params.id as string;
  
  const [loading, setLoading] = useState(true);
  const [program, setProgram] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!user) {
      router.push('/auth/login');
      return;
    }
    loadProgram();
  }, [user, router, programId]);

  async function loadProgram() {
    try {
      const data = await getProgram(programId);
      setProgram(data);
    } catch (err: any) {
      setError(err.message);
      toast.error('Unable to load program details');
    } finally {
      setLoading(false);
    }
  }

  function handleCopyLink() {
    navigator.clipboard.writeText(window.location.href);
    toast.success('Link copied to clipboard');
  }

  if (loading) {
    return <PageLoadingState message="Loading program details..." />;
  }

  if (error || !program) {
    return (
      <div className="max-w-4xl mx-auto">
        <ErrorState
          title="Program not found"
          description={error || "We couldn't find the program you're looking for."}
          onRetry={() => {
            setError('');
            setLoading(true);
            loadProgram();
          }}
        />
      </div>
    );
  }

  const deadlineInfo = program.application_deadline_primary 
    ? new Date(program.application_deadline_primary)
    : null;
  const isDeadlineSoon = deadlineInfo && deadlineInfo <= new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
  const isDeadlinePassed = deadlineInfo && deadlineInfo < new Date();

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back Button */}
      <motion.button
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        onClick={() => router.back()}
        className="flex items-center gap-2 text-textSecondary hover:text-text transition-colors mb-6 group"
      >
        <svg className="w-5 h-5 group-hover:-translate-x-0.5 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
        </svg>
        <span className="text-sm font-medium">Back to search</span>
      </motion.button>

      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-8 mb-6 relative overflow-hidden"
      >
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-mesh-pattern opacity-30" />
        
        <div className="relative">
          <div className="flex flex-col md:flex-row md:items-start gap-6">
            {/* Institution Avatar */}
            <div className="w-20 h-20 rounded-2xl bg-primaryLight flex items-center justify-center flex-shrink-0 border border-border/50 shadow-soft">
              <span className="text-3xl font-display font-semibold text-primary">
                {program.institution?.name?.charAt(0) || 'U'}
              </span>
            </div>
            
            <div className="flex-1">
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className={`badge ${program.degree_level === 'phd' ? 'badge-accent' : 'badge-primary'}`}>
                  {program.degree_level === 'phd' ? 'PhD' : 'Masters'}
                </span>
                {program.field_of_study && (
                  <span className="badge bg-muted text-textSecondary">
                    {program.field_of_study}
                  </span>
                )}
                {program.delivery_mode && (
                  <span className="badge bg-muted text-textSecondary capitalize">
                    {program.delivery_mode}
                  </span>
                )}
                <DataQualityBadge score={program.data_completeness_score || 60} />
                <EnrichmentBadge
                  entityKind="program"
                  entityId={programId}
                  enrichmentData={program.enrichment}
                  onRefreshComplete={loadProgram}
                />
              </div>
              
              <h1 className="text-2xl md:text-3xl font-display font-semibold text-text mb-2">
                {program.name}
              </h1>
              
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-textSecondary">
                <span className="font-medium">{program.institution?.name}</span>
                <span className="text-border">|</span>
                <span className="flex items-center gap-1.5">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                  </svg>
                  {program.institution?.city}, {program.institution?.country}
                </span>
              </div>
            </div>
            
            {/* Actions */}
            <div className="flex gap-2 md:flex-col">
              <Button variant="outline" size="sm" onClick={handleCopyLink}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 100 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186l9.566-5.314m-9.566 7.5l9.566 5.314m0 0a2.25 2.25 0 103.935 2.186 2.25 2.25 0 00-3.935-2.186zm0-12.814a2.25 2.25 0 103.933-2.185 2.25 2.25 0 00-3.933 2.185z" />
                </svg>
                Share
              </Button>
              <Button variant="outline" size="sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
                </svg>
                Save
              </Button>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Key Stats Bar */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6"
      >
        {/* Deadline */}
        <div className={`card p-4 ${isDeadlinePassed ? 'border-error/30' : isDeadlineSoon ? 'border-warning/30' : ''}`}>
          <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Application Deadline</p>
          {deadlineInfo ? (
            <p className={`font-semibold ${isDeadlinePassed ? 'text-error' : isDeadlineSoon ? 'text-warning' : 'text-text'}`}>
              {deadlineInfo.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </p>
          ) : (
            <p className="text-textSecondary">Not specified</p>
          )}
          {isDeadlinePassed && <p className="text-2xs text-error mt-0.5">Deadline passed</p>}
          {isDeadlineSoon && !isDeadlinePassed && <p className="text-2xs text-warning mt-0.5">Deadline approaching</p>}
        </div>

        {/* Tuition */}
        <div className="card p-4">
          <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Tuition (Est.)</p>
          {program.tuition_estimate_per_year ? (
            <p className="font-semibold text-text">
              ${parseFloat(program.tuition_estimate_per_year).toLocaleString()}<span className="text-textSecondary font-normal">/year</span>
            </p>
          ) : (
            <p className="text-textSecondary">Not available</p>
          )}
        </div>

        {/* Application Fee */}
        <div className="card p-4">
          <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Application Fee</p>
          {program.application_fee ? (
            <p className="font-semibold text-text">${parseFloat(program.application_fee).toLocaleString()}</p>
          ) : (
            <p className="text-textSecondary">Not specified</p>
          )}
        </div>

        {/* Program Style */}
        <div className="card p-4">
          <p className="text-2xs uppercase tracking-wider text-textMuted mb-1">Program Style</p>
          <p className="font-semibold text-text capitalize">
            {program.research_or_coursework || 'Mixed'}
          </p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="lg:col-span-2 space-y-6"
        >
          {/* About Section */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z" />
              </svg>
              About This Program
            </h2>
            {program.description ? (
              <p className="text-textSecondary leading-relaxed whitespace-pre-wrap">
                {program.description}
              </p>
            ) : (
              <div className="bg-muted rounded-xl p-6 text-center">
                {/* LOTTIE PLACEHOLDER: Add "no content" or "coming soon" animation here */}
                <p className="text-textSecondary">
                  Detailed program description coming soon.
                </p>
                <p className="text-sm text-textMuted mt-2">
                  Visit the program website for more information.
                </p>
              </div>
            )}
          </div>

          {/* Program Features */}
          {program.tags && program.tags.length > 0 && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.568 3H5.25A2.25 2.25 0 003 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 005.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 009.568 3z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 6h.008v.008H6V6z" />
                </svg>
                Program Features
              </h2>
              <div className="flex flex-wrap gap-2">
                {program.tags.map((tag: any, index: number) => (
                  <span key={index} className="badge badge-primary">
                    {tag.value}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Requirements Section - Placeholder */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-text mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" />
              </svg>
              Admission Requirements
            </h2>
            <div className="bg-muted rounded-xl p-6 text-center">
              {/* LOTTIE PLACEHOLDER: Add "checklist" animation here */}
              <svg className="w-12 h-12 mx-auto mb-3 text-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-textSecondary">
                Requirements data is being collected.
              </p>
              <p className="text-sm text-textMuted mt-2">
                Check the program website for detailed requirements.
              </p>
            </div>
          </div>
        </motion.div>

        {/* Sidebar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          {/* Quick Actions */}
          <div className="card p-6">
            <h3 className="font-semibold text-text mb-4">Quick Actions</h3>
            <div className="space-y-3">
              {program.website_url && (
                <Button asChild className="w-full">
                  <a
                    href={program.website_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                    </svg>
                    Visit Program Website
                  </a>
                </Button>
              )}
              <Button variant="outline" className="w-full">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
                Add to My List
              </Button>
              <Button variant="ghost" className="w-full">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
                </svg>
                Report an Issue
              </Button>
            </div>
          </div>

          {/* Important Dates */}
          <div className="card p-6">
            <h3 className="font-semibold text-text mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
              </svg>
              Important Dates
            </h3>
            <div className="space-y-3">
              {program.application_deadline_primary && (
                <div className="flex items-center justify-between p-3 bg-muted rounded-xl">
                  <span className="text-sm text-textSecondary">Primary Deadline</span>
                  <span className="text-sm font-medium text-text">
                    {new Date(program.application_deadline_primary).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              )}
              {program.application_deadline_secondary && (
                <div className="flex items-center justify-between p-3 bg-muted rounded-xl">
                  <span className="text-sm text-textSecondary">Secondary Deadline</span>
                  <span className="text-sm font-medium text-text">
                    {new Date(program.application_deadline_secondary).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              )}
              {!program.application_deadline_primary && !program.application_deadline_secondary && (
                <p className="text-sm text-textMuted text-center py-2">No dates available</p>
              )}
            </div>
          </div>

          {/* Institution Info */}
          <div className="card p-6">
            <h3 className="font-semibold text-text mb-4">About the Institution</h3>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center">
                <span className="text-xl font-semibold text-primary">
                  {program.institution?.name?.charAt(0)}
                </span>
              </div>
              <div>
                <p className="font-medium text-text">{program.institution?.name}</p>
                <p className="text-sm text-textSecondary">
                  {program.institution?.city}, {program.institution?.country}
                </p>
              </div>
            </div>
            <button className="btn-ghost w-full justify-center text-sm">
              View all programs at this institution
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
