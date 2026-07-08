import type { Metadata } from 'next';
import MarketingPageShell from '@/components/marketing/MarketingPageShell';

export const metadata: Metadata = {
  title: 'Contact · Guidr',
  description: 'Get in touch with the Guidr team.',
};

const CONTACT_EMAIL = 'hello@guidr.app';

export default function ContactPage() {
  return (
    <MarketingPageShell
      eyebrow="Contact"
      title="Get in touch"
      subtitle="Questions, feedback, or ideas? We read every message and usually reply within a day or two."
    >
      <h2>Email us</h2>
      <p>
        The fastest way to reach us is by email at{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. Whether
        you&rsquo;ve found a bug, want a feature, or just want to share how your
        search is going — we want to hear it.
      </p>

      <h2>Partnerships &amp; press</h2>
      <p>
        Interested in working with Guidr or writing about us? Reach out to{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a> and we&rsquo;ll
        point you to the right person.
      </p>

      <div className="mt-8">
        <a
          href={`mailto:${CONTACT_EMAIL}`}
          className="inline-flex items-center justify-center rounded-full bg-text px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-text/90 no-underline"
        >
          Email {CONTACT_EMAIL}
        </a>
      </div>
    </MarketingPageShell>
  );
}
