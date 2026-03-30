'use client';

import Link from 'next/link';
import { ArrowLeft, BookOpen, User, GraduationCap, FileText, Sparkles } from 'lucide-react';

const steps = [
  {
    icon: <User className="h-6 w-6 text-primary" />,
    title: '1. Complete Your Profile',
    description:
      'Tell us about your academic goals, preferred countries, research interests, and career plans. The more complete your profile, the better your recommendations.',
    href: '/profile',
    cta: 'Go to Profile',
  },
  {
    icon: <GraduationCap className="h-6 w-6 text-primary" />,
    title: '2. Add Academic Records',
    description:
      'Enter your academic history manually or upload a transcript. We\'ll extract GPA, institution, and degree details automatically.',
    href: '/academic-records',
    cta: 'Add Records',
  },
  {
    icon: <FileText className="h-6 w-6 text-primary" />,
    title: '3. Upload Documents',
    description:
      'Upload your resume, transcripts, and essays. Our AI will parse and extract key information to enrich your profile.',
    href: '/documents',
    cta: 'Upload Documents',
  },
  {
    icon: <Sparkles className="h-6 w-6 text-primary" />,
    title: '4. Get Recommendations',
    description:
      'Once your profile reaches Level 2, you can generate personalized school and program recommendations based on your goals and qualifications.',
    href: '/recommendations',
    cta: 'View Recommendations',
  },
];

export default function GettingStartedPage() {
  return (
    <div className="max-w-3xl mx-auto">
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-2 text-sm text-textSecondary hover:text-text mb-6 transition"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Dashboard
      </Link>

      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 bg-primaryLight rounded-xl">
          <BookOpen className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-3xl font-semibold text-text">Getting Started with Guidr</h1>
      </div>

      <p className="text-textSecondary mb-8 text-lg leading-relaxed">
        Guidr helps you find and apply to graduate programs that match your goals. Follow these
        steps to get the most out of the platform.
      </p>

      <div className="space-y-6">
        {steps.map((step) => (
          <div
            key={step.title}
            className="bg-card rounded-xl p-6 border border-border hover:border-primary/30 transition"
          >
            <div className="flex items-start gap-4">
              <div className="p-2 bg-primaryLight rounded-lg flex-shrink-0">{step.icon}</div>
              <div className="flex-1">
                <h2 className="text-lg font-semibold text-text mb-2">{step.title}</h2>
                <p className="text-textSecondary text-sm mb-4">{step.description}</p>
                <Link
                  href={step.href}
                  className="inline-flex px-4 py-2 bg-primary text-white text-sm font-semibold rounded-lg hover:bg-primaryHover transition"
                >
                  {step.cta}
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
