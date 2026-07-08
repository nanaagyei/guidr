import type { Metadata } from 'next';
import Link from 'next/link';
import MarketingPageShell from '@/components/marketing/MarketingPageShell';

export const metadata: Metadata = {
  title: 'About · Guidr',
  description:
    'Guidr helps graduate applicants find the right programs, faculty, and funding — matched to their research and goals.',
};

export default function AboutPage() {
  return (
    <MarketingPageShell
      eyebrow="About"
      title="Graduate school search, done right."
      subtitle="Guidr helps applicants find programs, faculty, and funding that actually match their research interests and goals — without the endless spreadsheets."
    >
      <h2>Why we built Guidr</h2>
      <p>
        Finding the right graduate program is hard. The information is scattered
        across hundreds of department websites, faculty pages, and PDFs, and none
        of it is connected to <em>you</em> — your background, your research
        interests, or where you want to go.
      </p>
      <p>
        Guidr brings it together. We combine trusted institutional data with
        research-alignment matching so you can see, at a glance, which programs
        and professors are worth your time.
      </p>

      <h2>What you can do today</h2>
      <ul>
        <li>Search accredited universities and graduate programs.</li>
        <li>Discover faculty whose research aligns with yours, with fit scores.</li>
        <li>Get AI-powered program recommendations tailored to your profile.</li>
        <li>Draft outreach emails to professors you want to work with.</li>
      </ul>
      <p>
        We&rsquo;re just getting started — more is on the way. Have feedback or an
        idea? <Link href="/contact">We&rsquo;d love to hear from you</Link>.
      </p>
    </MarketingPageShell>
  );
}
