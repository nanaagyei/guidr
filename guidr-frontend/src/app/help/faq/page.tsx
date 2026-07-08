'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, HelpCircle, ChevronDown } from 'lucide-react';

const faqs = [
  {
    q: 'How does Guidr generate recommendations?',
    a: 'Guidr uses your profile information — academic background, research interests, preferred countries, and career goals — to match you with graduate programs. The more complete your profile, the better your recommendations.',
  },
  {
    q: 'What are profile completion levels?',
    a: 'There are 3 levels. Level 1 (Basics) unlocks the dashboard by providing your degree and field of study. Level 2 (Targeting) unlocks recommendations by adding research areas and country preferences. Level 3 (Complete) unlocks professor matching by adding academic records.',
  },
  {
    q: 'How do I add my academic records?',
    a: 'Go to Academic Records and click "Add Manually" to enter your institution, degree, GPA, and dates. This information helps unlock professor matching and improves your recommendations.',
  },
  {
    q: 'Which features are coming soon?',
    a: 'Automatic document parsing (auto-filling your profile from an uploaded CV or transcript), AI essay feedback, and funding discovery are in active development. You\'ll see a "Coming soon" label on these until they\'re ready.',
  },
  {
    q: 'How do I get better recommendations?',
    a: 'Complete your profile to Level 2 or higher, add your academic records, specify your research interests, and set your country and funding preferences. The recommendation engine considers all of these factors.',
  },
  {
    q: 'Can I save schools I\'m interested in?',
    a: 'Yes! When viewing a program, click the "Save" button to add it to your saved schools list. You can view all saved schools from your dashboard.',
  },
  {
    q: 'How does professor matching work?',
    a: 'Once your profile reaches Level 3 (with academic records), you can browse professors filtered by research area and institution. You can also generate personalized outreach email drafts.',
  },
  {
    q: 'Is my data secure?',
    a: 'Yes. Your information is stored securely, passwords are hashed, and we support two-factor authentication. Your personal information is never sold or shared with third parties, and you can delete your data at any time from the Settings page.',
  },
];

export default function FAQPage() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="max-w-3xl mx-auto">
      <Link
        href="/help"
        className="inline-flex items-center gap-2 text-sm text-textSecondary hover:text-text mb-6 transition"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Help Center
      </Link>

      <div className="flex items-center gap-3 mb-8">
        <div className="p-2 bg-primaryLight rounded-xl">
          <HelpCircle className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-3xl font-semibold text-text">Frequently Asked Questions</h1>
      </div>

      <div className="space-y-3">
        {faqs.map((faq, index) => (
          <div
            key={index}
            className="bg-card rounded-xl border border-border overflow-hidden"
          >
            <button
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
              className="w-full flex items-center justify-between p-5 text-left hover:bg-muted/50 transition"
            >
              <span className="font-medium text-text pr-4">{faq.q}</span>
              <ChevronDown
                className={`h-5 w-5 text-textSecondary flex-shrink-0 transition-transform ${
                  openIndex === index ? 'rotate-180' : ''
                }`}
              />
            </button>
            {openIndex === index && (
              <div className="px-5 pb-5 pt-0">
                <p className="text-textSecondary text-sm leading-relaxed">{faq.a}</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
