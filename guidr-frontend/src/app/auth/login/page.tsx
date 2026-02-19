'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { postLogin, send2FACode, verifyCredentials } from '@/utils/api';
import { useAuth } from '@/contexts/AuthContext';
import { SignInPage, Testimonial } from '@/components/ui/sign-in';
import TwoFactorVerification from '@/components/TwoFactorVerification';
import { useToast } from '@/contexts/ToastContext';

const sampleTestimonials: Testimonial[] = [
  {
    avatarSrc: "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop&crop=faces",
    name: "Sarah Chen",
    handle: "@sarahdigital",
    text: "Guidr helped me find the perfect graduate program. The recommendations were spot-on!"
  },
  {
    avatarSrc: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=faces",
    name: "Marcus Johnson",
    handle: "@marcustech",
    text: "The essay review feature is incredible. It helped me refine my application essays perfectly."
  },
  {
    avatarSrc: "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=faces",
    name: "David Martinez",
    handle: "@davidcreates",
    text: "Found my dream program through Guidr's personalized recommendations. Highly recommend!"
  },
];

export default function LoginPage() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [show2FA, setShow2FA] = useState(false);
  const [formData, setFormData] = useState<{ email: string; password: string; rememberMe: boolean } | null>(null);
  const router = useRouter();
  const { login } = useAuth();
  const toast = useToast();

  async function handleSignIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);

    const formDataObj = new FormData(event.currentTarget);
    const email = formDataObj.get('email') as string;
    const password = formDataObj.get('password') as string;
    const rememberMe = formDataObj.get('rememberMe') === 'on';

    // Store form data (including rememberMe) for later use
    setFormData({ email, password, rememberMe });

    try {
      // First verify credentials are correct before sending 2FA code
      await verifyCredentials({ email, password });
      
      // Credentials are valid, now send 2FA code
      await send2FACode({ email, purpose: 'login' });
      setShow2FA(true);
    } catch (err: any) {
      const message =
        err?.message === 'Failed to fetch'
          ? 'We couldn\'t reach the server. Please check your connection and try again.'
          : err?.message || 'Invalid email or password';
      setError(message);
      toast.error(message);
      setFormData(null); // Clear form data on error
    } finally {
      setLoading(false);
    }
  }

  async function handle2FAVerified(code: string) {
    if (!formData) return;

    setLoading(true);
    setError('');

    try {
      const user = await postLogin({
        email: formData.email,
        password: formData.password,
        verification_code: code,
        // Persist session longer when user opts into "Keep me signed in"
        remember_me: formData.rememberMe,
      });
      login(user);
      router.push('/dashboard');
    } catch (err: any) {
      const message =
        err?.message === 'Failed to fetch'
          ? 'We couldn\'t complete the login. Please check your connection and try again.'
          : err?.message || 'Login failed';
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
    router.push('/auth/reset-password');
  }

  function handleCreateAccount() {
    router.push('/auth/register');
  }

  if (show2FA && formData) {
    return (
      <SignInPage
        title={<span className="font-light text-text tracking-tighter">Verify Your Email</span>}
        description="Enter the 6-digit code sent to your email"
        heroImageSrc="https://images.unsplash.com/photo-1627556704302-624286467c65?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
        testimonials={sampleTestimonials}
        onSignIn={(e) => e.preventDefault()}
        error={error}
        loading={loading}
        customContent={
          <div className="w-full max-w-md mx-auto">
            <TwoFactorVerification
              email={formData.email}
              purpose="login"
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
      title={<span className="font-light text-text tracking-tighter">Welcome Back</span>}
      description="Sign in to continue your graduate school journey"
      heroImageSrc="https://images.unsplash.com/photo-1627556704302-624286467c65?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
      testimonials={sampleTestimonials}
      onSignIn={handleSignIn}
      onGoogleSignIn={handleGoogleSignIn}
      onResetPassword={handleResetPassword}
      onCreateAccount={handleCreateAccount}
      error={error}
      loading={loading}
    />
  );
}

