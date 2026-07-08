'use client';

import Link from 'next/link';
import { ArrowLeft, HelpCircle, Rocket, MessageCircleQuestion, Mail } from 'lucide-react';

const CARDS = [
  {
    href: '/help/getting-started',
    icon: Rocket,
    title: 'Getting Started',
    description: 'Set up your profile and unlock recommendations in a few minutes.',
  },
  {
    href: '/help/faq',
    icon: MessageCircleQuestion,
    title: 'FAQ',
    description: 'Answers to the most common questions about how Guidr works.',
  },
  {
    href: '/contact',
    icon: Mail,
    title: 'Contact Us',
    description: "Can't find what you need? Reach the team directly.",
  },
];

export default function HelpCenterPage() {
  return (
    <div className="max-w-4xl mx-auto">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-text hover:text-gray-700 transition font-medium mb-8"
      >
        <ArrowLeft className="h-5 w-5" />
        Back
      </Link>

      <div className="mb-10">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-accent/15 text-accent">
          <HelpCircle className="h-6 w-6" />
        </div>
        <h1 className="font-display text-3xl font-semibold text-text sm:text-4xl">
          Help Center
        </h1>
        <p className="mt-3 text-lg text-textSecondary">
          Everything you need to get the most out of Guidr.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CARDS.map(({ href, icon: Icon, title, description }) => (
          <Link
            key={href}
            href={href}
            className="group rounded-2xl border border-border bg-white p-6 shadow-soft transition hover:border-borderHover hover:shadow-soft-lg"
          >
            <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-muted text-text transition group-hover:bg-accent/15 group-hover:text-accent">
              <Icon className="h-5 w-5" />
            </div>
            <h2 className="text-base font-semibold text-text">{title}</h2>
            <p className="mt-1.5 text-sm leading-relaxed text-textSecondary">{description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
