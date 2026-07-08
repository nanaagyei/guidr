import type { Metadata } from 'next';
import Link from 'next/link';
import MarketingPageShell from '@/components/marketing/MarketingPageShell';

export const metadata: Metadata = {
  title: 'Privacy Policy · Guidr',
  description: 'How Guidr collects, uses, and protects your information.',
};

const LAST_UPDATED = 'July 7, 2026';
const CONTACT_EMAIL = 'hello@guidr.app';

export default function PrivacyPage() {
  return (
    <MarketingPageShell
      eyebrow="Legal"
      title="Privacy Policy"
      subtitle={`Last updated ${LAST_UPDATED}`}
    >
      <p>
        This Privacy Policy explains what information Guidr collects, how we use
        it, and the choices you have. By using Guidr, you agree to the practices
        described here.
      </p>

      <h2>Information we collect</h2>
      <h3>Information you provide</h3>
      <ul>
        <li>Account details such as your name and email address.</li>
        <li>Profile information such as academic background, research interests, and preferences.</li>
        <li>Content you upload, such as documents, and any messages you send us.</li>
      </ul>
      <h3>Information collected automatically</h3>
      <ul>
        <li>Basic usage and device information to keep the Service secure and reliable.</li>
        <li>Cookies used for authentication and to remember your session.</li>
      </ul>

      <h2>How we use your information</h2>
      <ul>
        <li>To provide core features like search, matching, and recommendations.</li>
        <li>To personalize results based on your profile and research interests.</li>
        <li>To secure accounts, prevent abuse, and support two-factor authentication.</li>
        <li>To communicate with you about your account and respond to your requests.</li>
        <li>To improve the Service.</li>
      </ul>

      <h2>How we share information</h2>
      <p>
        We do not sell your personal information. We share it only with service
        providers who help us operate Guidr (for example, hosting, email, and
        analytics), under appropriate confidentiality obligations, or when
        required by law.
      </p>
      <p>
        Some features rely on third-party APIs (for example, academic and
        research data providers). When those features run, limited, relevant
        query information may be sent to those providers to return results.
      </p>

      <h2>Data retention</h2>
      <p>
        We keep your information for as long as your account is active or as needed
        to provide the Service. You can request deletion of your account and
        associated personal data at any time.
      </p>

      <h2>Your choices</h2>
      <ul>
        <li>Access, update, or delete your profile information from your account settings.</li>
        <li>Request a copy or deletion of your data by emailing us.</li>
        <li>Manage cookies through your browser settings.</li>
      </ul>

      <h2>Security</h2>
      <p>
        We use reasonable technical and organizational measures to protect your
        information, including hashed passwords and optional two-factor
        authentication. No system is perfectly secure, so we cannot guarantee
        absolute security.
      </p>

      <h2>Children</h2>
      <p>
        Guidr is not intended for children under 16, and we do not knowingly
        collect personal information from them.
      </p>

      <h2>Changes to this policy</h2>
      <p>
        We may update this Privacy Policy from time to time. We will update the
        &ldquo;last updated&rdquo; date above when we do.
      </p>

      <h2>Contact</h2>
      <p>
        Questions or requests? Email us at{' '}
        <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>. See also our{' '}
        <Link href="/terms">Terms of Service</Link>.
      </p>
    </MarketingPageShell>
  );
}
