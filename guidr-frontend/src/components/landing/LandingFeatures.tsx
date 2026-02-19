'use client';

import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ChevronRight, Search, FileText, Brain, GraduationCap, Users, Building2, BookOpen, Target, TrendingUp } from 'lucide-react';

// For Students Section
const STUDENT_FEATURES = [
  {
    id: 'search',
    title: 'Smart Program Search',
    description: 'Discover graduate programs that match your interests, qualifications, and career goals. Filter by field, location, funding, and more.',
    icon: Search,
    active: true,
  },
  {
    id: 'tracker',
    title: 'Application Tracker',
    description: 'Keep track of deadlines, required documents, and recommendation letters. Get reminders and stay organized throughout your application journey.',
    icon: FileText,
  },
  {
    id: 'recommendations',
    title: 'AI Recommendations',
    description: 'Receive personalized program suggestions based on your academic profile, research interests, and preferences.',
    icon: Brain,
  },
];

// For Researchers Section
const RESEARCHER_FEATURES = [
  {
    id: 'faculty',
    title: 'Faculty Matching',
    description: 'Find professors whose research aligns with your interests. Explore their publications, lab focus, and mentorship style.',
    icon: Users,
    active: true,
  },
  {
    id: 'funding',
    title: 'Funding Discovery',
    description: 'Discover funding opportunities including fellowships, grants, and assistantships. Never miss a funding deadline.',
    icon: TrendingUp,
  },
  {
    id: 'programs',
    title: 'Research Programs',
    description: 'Explore PhD and research-focused programs with detailed information about research areas, lab facilities, and collaboration opportunities.',
    icon: BookOpen,
  },
];

// Feature cards for the three-column section
const FEATURE_CARDS = [
  {
    title: 'Program Search API',
    description: 'Our intelligent search understands what programs mean in context, helping you discover schools that truly match your goals and qualifications.',
    details: [
      '2,000+ graduate schools',
      '30,000+ programs',
      'Real-time data updates',
    ],
    bgClass: 'bg-landingLavender',
    textClass: 'text-dream',
  },
  {
    title: 'Recommendation Engine',
    description: 'AI-powered recommendations that understand your academic background, research interests, and career aspirations to suggest ideal programs.',
    details: [
      'Personalized matching',
      '94% accuracy rate',
      'Continuous learning',
    ],
    bgClass: 'bg-landingPeach',
    textClass: 'text-secondary',
  },
  {
    title: 'Application Management',
    description: 'Comprehensive tools to track your applications, manage deadlines, and organize documents across multiple programs.',
    details: [
      'Deadline reminders',
      'Document tracking',
      'Progress analytics',
    ],
    bgClass: 'bg-landingCream',
    textClass: 'text-warning',
  },
];

interface FeatureItem {
  id: string;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  active?: boolean;
}

function FeatureSidebar({ features, activeId, onSelect }: { features: FeatureItem[]; activeId: string; onSelect: (id: string) => void }) {
  return (
    <div className="space-y-2">
      {features.map((feature) => {
        const Icon = feature.icon;
        const isActive = feature.id === activeId;
        return (
          <button
            key={feature.id}
            onClick={() => onSelect(feature.id)}
            className={`w-full text-left p-5 rounded-xl transition-all duration-200 ${
              isActive
                ? 'bg-text text-white shadow-lg'
                : 'bg-white hover:bg-muted border border-border/50'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className={`font-semibold ${isActive ? 'text-white' : 'text-text'}`}>
                  {feature.title}
                </h4>
                <p className={`mt-2 text-sm leading-relaxed ${isActive ? 'text-white/80' : 'text-textSecondary'}`}>
                  {feature.description}
                </p>
              </div>
              <ChevronRight className={`h-5 w-5 ml-4 shrink-0 ${isActive ? 'text-white' : 'text-textMuted'}`} />
            </div>
          </button>
        );
      })}
    </div>
  );
}

const FEATURE_IMAGE_URL = 'https://images.unsplash.com/photo-1541339907198-e08756dedf3f?w=600&q=80';

function FeatureVisual({ activeFeature, variant = 'lavender' }: { activeFeature: string; variant?: 'lavender' | 'peach' }) {
  const bgClass = variant === 'lavender' ? 'bg-landingLavender' : 'bg-landingPeach';

  return (
    <div className="relative">
      {/* Stacked cards effect */}
      <div className={`absolute -right-4 -bottom-4 w-full h-full ${bgClass} rounded-2xl opacity-50`} />
      <div className={`absolute -right-2 -bottom-2 w-full h-full ${bgClass} rounded-2xl opacity-75`} />

      {/* Main card */}
      <div className={`relative ${bgClass} rounded-2xl p-8 min-h-[300px] flex items-center justify-center`}>
        {/* Feature card with stock image */}
        <div className="relative bg-white rounded-xl shadow-soft p-6 max-w-sm w-full">
          <div className="relative rounded-lg overflow-hidden mb-4 aspect-video">
            <Image
              src={FEATURE_IMAGE_URL}
              alt="Campus and research"
              fill
              sizes="(max-width: 768px) 100vw, 400px"
              className="object-cover"
            />
          </div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
              <GraduationCap className="h-5 w-5 text-textSecondary" />
            </div>
            <div>
              <p className="text-sm font-medium text-text">Stanford University</p>
              <p className="text-xs text-textMuted">Computer Science, PhD</p>
            </div>
          </div>
          <p className="text-sm text-textSecondary leading-relaxed">
            World-renowned AI research program with leading faculty in machine learning, NLP, and computer vision.
          </p>
          <div className="mt-4 flex items-center gap-2">
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-successLight text-success">
              Strong Match
            </span>
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-infoLight text-info">
              Funded
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function LandingFeatures() {
  const [activeStudentFeature, setActiveStudentFeature] = useState('search');
  const [activeResearcherFeature, setActiveResearcherFeature] = useState('faculty');

  return (
    <>
      {/* For Students Section */}
      <section id="how-it-works" className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section header */}
          <div className="mb-12">
            <p className="text-xs font-semibold uppercase tracking-widest-plus text-textMuted mb-3">
              For Students
            </p>
            <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-display font-semibold text-text leading-tight max-w-xl">
              Navigate your graduate school journey with confidence
            </h2>
          </div>

          {/* Two-column layout */}
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
          >
            {/* Feature sidebar */}
            <div>
              <FeatureSidebar
                features={STUDENT_FEATURES}
                activeId={activeStudentFeature}
                onSelect={setActiveStudentFeature}
              />
            </div>

            {/* Feature visual */}
            <div>
              <FeatureVisual activeFeature={activeStudentFeature} variant="lavender" />
            </div>
          </motion.div>
        </div>
      </section>

      {/* For Researchers Section */}
      <section className="py-20 sm:py-28 bg-muted/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section header */}
          <div className="mb-12">
            <p className="text-xs font-semibold uppercase tracking-widest-plus text-textMuted mb-3">
              For Researchers
            </p>
            <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-display font-semibold text-text leading-tight max-w-xl">
              Find the right research environment for your goals
            </h2>
          </div>

          {/* Two-column layout (reversed) */}
          <motion.div
            className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5 }}
          >
            {/* Feature visual */}
            <div className="order-2 lg:order-1">
              <FeatureVisual activeFeature={activeResearcherFeature} variant="peach" />
            </div>

            {/* Feature sidebar */}
            <div className="order-1 lg:order-2">
              <FeatureSidebar
                features={RESEARCHER_FEATURES}
                activeId={activeResearcherFeature}
                onSelect={setActiveResearcherFeature}
              />
            </div>
          </motion.div>

          {/* CTA */}
          <div className="mt-12 flex items-center gap-4">
            <Button variant="outline" className="rounded-full" asChild>
              <Link href="/docs">
                <span className="text-xs uppercase tracking-wide font-medium">View Documentation</span>
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Feature Cards Section */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Section header */}
          <div className="text-center mb-12">
            <p className="text-xs font-semibold uppercase tracking-widest-plus text-textMuted mb-3">
              Platform Features
            </p>
            <h2 className="text-3xl sm:text-4xl lg:text-[42px] font-display font-semibold text-text leading-tight max-w-2xl mx-auto">
              Everything you need to succeed in your applications
            </h2>
          </div>

          {/* Feature cards grid */}
          <motion.div
            className="grid md:grid-cols-3 gap-6"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: true, margin: '-50px' }}
            variants={{
              visible: {
                transition: { staggerChildren: 0.1, delayChildren: 0.1 },
              },
            }}
          >
            {FEATURE_CARDS.map((card) => (
              <motion.div
                key={card.title}
                variants={{ hidden: { opacity: 0, y: 20 }, visible: { opacity: 1, y: 0 } }}
                transition={{ duration: 0.4 }}
                className={`${card.bgClass} rounded-2xl p-6 sm:p-8 transition-all duration-300 hover:shadow-soft-lg hover:-translate-y-1`}
              >
                <h3 className={`text-lg font-semibold ${card.textClass} mb-3`}>
                  {card.title}
                </h3>
                <p className="text-sm text-textSecondary leading-relaxed mb-6">
                  {card.description}
                </p>
                <ul className="space-y-2">
                  {card.details.map((detail) => (
                    <li key={detail} className="flex items-center gap-2 text-sm text-text">
                      <span className={`w-1.5 h-1.5 rounded-full ${card.textClass.replace('text-', 'bg-')}`} />
                      {detail}
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>
    </>
  );
}
