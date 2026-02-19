'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { ParallaxLayer } from '@/components/landing/ParallaxLayer';
import { Search, GraduationCap, FileText, Brain, Play, ChevronRight } from 'lucide-react';

const FEATURE_TABS = [
  { id: 'search', label: 'School Search', icon: Search },
  { id: 'tracker', label: 'Application Tracker', icon: FileText },
  { id: 'ai', label: 'AI Recommendations', icon: Brain },
  { id: 'programs', label: 'Program Matching', icon: GraduationCap },
];

const DEMO_CONTENT: Record<string, { title: string; subtitle: string; sampleText: string; tag: string }> = {
  search: {
    title: 'School Search',
    subtitle: 'Find your perfect graduate program',
    sampleText: 'I\'m looking for a Computer Science PhD program with strong AI research, funding opportunities, and a collaborative environment in the Boston area...',
    tag: 'AI-POWERED',
  },
  tracker: {
    title: 'Application Tracker',
    subtitle: 'Manage your applications',
    sampleText: 'Track deadlines, required documents, recommendation letters, and application status all in one place. Never miss a deadline again.',
    tag: 'ORGANIZED',
  },
  ai: {
    title: 'AI Recommendations',
    subtitle: 'Personalized program suggestions',
    sampleText: 'Based on your academic background, research interests, and career goals, we recommend programs that match your profile with 94% accuracy.',
    tag: 'PERSONALIZED',
  },
  programs: {
    title: 'Program Matching',
    subtitle: 'Discover programs that fit',
    sampleText: 'Filter by research areas, faculty expertise, funding availability, location, acceptance rates, and more to find programs aligned with your goals.',
    tag: 'COMPREHENSIVE',
  },
};

export function LandingHero() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('search');

  return (
    <section className="relative overflow-hidden">
      {/* Light green gradient background with parallax */}
      <ParallaxLayer
        scrollRange={[0, 600]}
        offsetRange={[0, 80]}
        className="absolute inset-0 bg-gradient-hero-green"
      />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 pb-16 sm:pt-16 sm:pb-24">
        {/* Announcement badge */}
        <div className="flex justify-center mb-8 animate-element">
          <Link
            href="/blog/launch"
            className="inline-flex items-center gap-2 px-4 py-2 bg-white/80 backdrop-blur-sm rounded-full border border-border/50 hover:bg-white transition-colors group"
          >
            <span className="text-xs font-semibold uppercase tracking-wider text-primary bg-primaryLight px-2 py-0.5 rounded-full">
              New
            </span>
            <span className="text-sm text-text">Introducing Guidr 2.0 with AI-powered recommendations</span>
            <ChevronRight className="h-4 w-4 text-textMuted group-hover:translate-x-0.5 transition-transform" />
          </Link>
        </div>

        {/* Main headline */}
        <div className="text-center max-w-4xl mx-auto">
          <h1 className="text-4xl sm:text-5xl lg:text-[56px] font-display font-semibold text-text tracking-tight leading-[1.1] animate-element animate-delay-100">
            The smartest way to find
            <br />
            & apply to graduate school
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-textSecondary max-w-2xl mx-auto animate-element animate-delay-200">
            AI-powered platform for discovering programs, tracking applications, and getting personalized recommendations. Your path to graduate school starts here.
          </p>
        </div>

        {/* Feature tabs */}
        <div className="flex flex-wrap justify-center gap-2 mt-10 animate-element animate-delay-300">
          {FEATURE_TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-full text-sm font-medium transition-all duration-200 ${
                activeTab === id
                  ? 'bg-text text-white shadow-lg'
                  : 'bg-white/80 text-text hover:bg-white border border-border/50'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Interactive demo card */}
        <div className="mt-10 max-w-3xl mx-auto animate-element animate-delay-400">
          <div className="relative bg-white rounded-2xl shadow-soft-lg border border-border/30 overflow-hidden">
            {/* Card header */}
            <div className="px-6 py-4 border-b border-border/50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text">{DEMO_CONTENT[activeTab].title}</span>
                <span className="text-xs text-textMuted">·</span>
                <span className="text-xs text-textMuted">{DEMO_CONTENT[activeTab].subtitle}</span>
              </div>
            </div>

            {/* Card content */}
            <div className="p-6 min-h-[180px]">
              <p className="text-text leading-relaxed">
                {DEMO_CONTENT[activeTab].sampleText}
              </p>
            </div>

            {/* Card footer */}
            <div className="px-6 py-4 bg-muted/30 border-t border-border/50 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <button className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-full text-xs font-medium text-text border border-border/50 hover:border-border transition-colors">
                  <span className="w-4 h-4 flex items-center justify-center">
                    <GraduationCap className="h-3 w-3" />
                  </span>
                  {DEMO_CONTENT[activeTab].tag}
                </button>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-xs text-textMuted hidden sm:inline">172/500</span>
                <div className="flex items-center gap-2">
                  <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-border/50">
                    <span className="text-xs text-textMuted uppercase tracking-wide">Language</span>
                    <span className="text-xs font-medium text-text">English</span>
                  </div>
                </div>
                {/* Play button */}
                <button className="w-11 h-11 flex items-center justify-center bg-text text-white rounded-full shadow-lg hover:bg-text/90 transition-colors">
                  <Play className="h-5 w-5 ml-0.5" fill="currentColor" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* CTA banner */}
        <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4 animate-element animate-delay-500">
          <p className="text-sm text-textSecondary">
            Get started with the smartest way to find graduate programs
          </p>
          {user ? (
            <Button
              size="sm"
              className="rounded-full px-6 text-sm uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
              asChild
            >
              <Link href="/dashboard">Go to Dashboard</Link>
            </Button>
          ) : (
            <Button
              size="sm"
              className="rounded-full px-6 text-sm uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
              asChild
            >
              <Link href="/auth/register">Sign Up For Free</Link>
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
