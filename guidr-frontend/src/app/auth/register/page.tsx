'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { postRegister, send2FACode, checkEmail } from '@/utils/api';
import { useAuth } from '@/contexts/AuthContext';
import { SignInPage, Testimonial } from '@/components/ui/sign-in';
import TwoFactorVerification from '@/components/TwoFactorVerification';
import { useToast } from '@/contexts/ToastContext';

const sampleTestimonials: Testimonial[] = [
  {
    avatarSrc: "https://ui-avatars.com/api/?name=Sylvester&background=E8B4A0&color=1C2127&size=150&font-size=0.4&bold=true",
    name: "Sylvester",
    handle: "@geek_sly",
    text: "Guidr's recommendations pointed me to programs I'd never have found on my own. Genuinely saved me weeks of searching."
  },
  {
    avatarSrc: "https://ui-avatars.com/api/?name=Derrick&background=4A7C74&color=ffffff&size=150&font-size=0.4&bold=true",
    name: "Derrick",
    handle: "@derrick",
    text: "The faculty matching and fit scores made it obvious which labs actually aligned with my research. Huge time-saver."
  },
  {
    avatarSrc: "https://ui-avatars.com/api/?name=Nana+Kwame&background=1C2127&color=ffffff&size=150&font-size=0.4&bold=true",
    name: "Nana Kwame",
    handle: "@nkay",
    text: "Everything I needed in one place — schools, programs, and professors matched to my goals. This is how the search should feel."
  },
];

export default function RegisterPage() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [show2FA, setShow2FA] = useState(false);
  const [emailExists, setEmailExists] = useState(false);
  const [formData, setFormData] = useState<{ email: string; password: string; fullName: string } | null>(null);
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();

  async function handleSignIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setEmailExists(false);
    setLoading(true);

    const formDataObj = new FormData(event.currentTarget);
    const email = formDataObj.get('email') as string;
    const password = formDataObj.get('password') as string;
    const fullName = formDataObj.get('fullName') as string;

    // Store form data for later use
    setFormData({ email, password, fullName });

    try {
      // 1) Check if email already exists
      const result = await checkEmail({ email });
      if (result.exists) {
        setError(result.message);
        setEmailExists(true);
        toast.error(result.message);
        return;
      }

      // 2) Email not in DB: send 2FA code for new account
      await send2FACode({ email, purpose: 'register' });
      setShow2FA(true);
    } catch (err: any) {
      const message =
        err?.message === 'Failed to fetch'
          ? 'We couldn\'t send the verification code. Please check your connection and try again.'
          : err?.message || 'Failed to send verification code';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  }

  async function handle2FAVerified(code: string) {
    if (!formData) return;

    setLoading(true);
    setError('');

    try {
      const user = await postRegister({
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName,
        verification_code: code,
      });
      login(user);
      router.push('/dashboard');
    } catch (err: any) {
      const message =
        err?.message === 'Failed to fetch'
          ? 'We couldn\'t complete your registration. Please check your connection and try again.'
          : err?.message || 'Registration failed';
      setError(message);
      toast.error(message);
      setShow2FA(false);
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleSignIn() {
    // TODO: Implement Google OAuth
    console.log('Google sign-in clicked');
  }

  function handleResetPassword() {
    // Not applicable for registration
  }

  function handleCreateAccount() {
    router.push('/auth/login');
  }

  if (show2FA && formData) {
    return (
      <SignInPage
        title={<span className="font-light text-text tracking-tighter">Verify Your Email</span>}
        description="Enter the 6-digit code sent to your email"
        heroImageSrc="https://images.unsplash.com/photo-1671709141384-446544c292ca?q=80&w=688&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
        testimonials={sampleTestimonials}
        onSignIn={(e) => e.preventDefault()}
        isRegister={true}
        error={error}
        loading={loading}
        customContent={
          <div className="w-full max-w-md mx-auto">
            <TwoFactorVerification
              email={formData.email}
              purpose="register"
              onVerified={handle2FAVerified}
              onCancel={() => {
                setShow2FA(false);
                setFormData(null);
              }}
              error={error}
            />
          </div>
        }
      />
    );
  }

  return (
    <SignInPage
      title={<span className="font-light text-text tracking-tighter">Create Account</span>}
      description="Join Guidr and start your journey to graduate school"
      heroImageSrc="https://images.unsplash.com/photo-1671709141384-446544c292ca?q=80&w=688&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
      testimonials={sampleTestimonials}
      onSignIn={handleSignIn}
      onGoogleSignIn={handleGoogleSignIn}
      onResetPassword={handleResetPassword}
      onCreateAccount={handleCreateAccount}
      isRegister={true}
      error={error}
      loading={loading}
      customContent={
        emailExists && (
          <div className="mt-4 space-y-3 text-center">
            <p className="text-sm text-gray-700/80">
              An account already exists with this email. You can log in or reset your password.
            </p>
            <div className="flex justify-center gap-3">
              <button
                type="button"
                onClick={() => router.push('/auth/login')}
                className="px-4 py-2 rounded-xl border border-border/40 text-text text-sm hover:bg-card/60 transition"
              >
                Go to Login
              </button>
              <button
                type="button"
                onClick={() => router.push('/auth/reset-password')}
                className="px-4 py-2 rounded-xl bg-primary text-white text-sm font-semibold hover:bg-primaryHover transition"
              >
                Reset Password
              </button>
            </div>
          </div>
        )
      }
    />
  );
}

