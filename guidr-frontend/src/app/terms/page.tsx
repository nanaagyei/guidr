import type { Metadata } from 'next';
import Link from 'next/link';
import MarketingPageShell from '@/components/marketing/MarketingPageShell';

export const metadata: Metadata = {
  title: 'Terms of Service · Guidr',
  description: 'The terms that govern your use of Guidr.',
};

const LAST_UPDATED = 'July 7, 2026';
const CONTACT_EMAIL = 'hello@guidr.app';

export default function TermsPage() {
  return (
    <MarketingPageShell
      eyebrow="Legal"
      title="Terms of Service"
      subtitle={`Last updated ${LAST_UPDATED}`}
    >
      <p>
        Welcome to Guidr. These Terms of Service (&ldquo;Terms&rdquo;) govern your
        access to and use of the Guidr website and services (the
        &ldquo;Service&rdquo;). By creating an account or using the Service, you
        agree to these Terms. If you do not agree, please do not use the Service.
      </p>

      <h2>1. Who can use Guidr</h2>
      <p>
        You must be at least 16 years old and able to form a binding contract to
        use Guidr. If you use the Service on behalf of an organization, you
        represent that you are authorized to accept these Terms on its behalf.
      </p>

      <h2>2. Your account</h2>
      <p>
        You are responsible for maintaining the confidentiality of your account
        credentials and for all activity that occurs under your account. Please
        notify us promptly at <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>{' '}
        if you suspect unauthorized use.
      </p>

      <h2>3. Acceptable use</h2>
      <p>You agree not to:</p>
      <ul>
        <li>Use the Service for any unlawful purpose or in violation of any rights.</li>
        <li>Scrape, harvest, or resell data from the Service without permission.</li>
        <li>Attempt to disrupt, reverse-engineer, or gain unauthorized access to the Service.</li>
        <li>Upload content you do not have the right to share.</li>
      </ul>

      <h2>4. Content and data accuracy</h2>
      <p>
        Guidr aggregates information about schools, programs, faculty, and funding
        from public and third-party sources, and provides recommendations and fit
        scores generated in part by automated systems. This information may be
        incomplete, out of date, or inaccurate. Guidr is a research and discovery
        tool — always verify important details (deadlines, requirements, funding)
        directly with the institution before making decisions.
      </p>

      <h2>5. Your content</h2>
      <p>
        You retain ownership of the content you submit (such as profile details
        and documents). You grant Guidr a limited license to use that content to
        operate and improve the Service. We do not sell your personal content.
      </p>

      <h2>6. Service changes</h2>
      <p>
        We are actively developing Guidr and may add, change, or remove features
        at any time. Some features may be labeled &ldquo;coming soon&rdquo; or
        offered on a beta basis.
      </p>

      <h2>7. Disclaimers</h2>
      <p>
        The Service is provided &ldquo;as is&rdquo; without warranties of any
        kind. Guidr does not guarantee any particular outcome, including admission
        to any program or receipt of any funding.
      </p>

      <h2>8. Limitation of liability</h2>
      <p>
        To the maximum extent permitted by law, Guidr will not be liable for any
        indirect, incidental, or consequential damages arising from your use of
        the Service.
      </p>

      <h2>9. Termination</h2>
      <p>
        You may stop using Guidr at any time. We may suspend or terminate access
        if you violate these Terms or use the Service in a way that could harm
        Guidr or other users.
      </p>

      <h2>10. Contact</h2>
      <p>
        Questions about these Terms? Email us at{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. See also our{' '}
        <Link href="/privacy">Privacy Policy</Link>.
      </p>
    </MarketingPageShell>
  );
}
