'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { requestPasswordReset } from '@/utils/api';
import { SignInPage, Testimonial } from '@/components/ui/sign-in';
import TwoFactorVerification from '@/components/TwoFactorVerification';

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

export default function ResetPasswordRequestPage() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [show2FA, setShow2FA] = useState(false);
  const [email, setEmail] = useState('');
  const router = useRouter();

  async function handleRequestReset(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);

    const formData = new FormData(event.currentTarget);
    const emailValue = (formData.get('email') as string) || email;
    if (!emailValue) {
      setError('Email is required');
      setLoading(false);
      return;
    }
    setEmail(emailValue);

    try {
      const response = await requestPasswordReset({ email: emailValue });
      
      // Check if account exists based on message
      if (response.message.includes('No account found')) {
        setError(response.message + ' If you haven\'t registered yet, please create an account first.');
        setLoading(false);
        return;
      }
      
      // Account exists and code was sent, show 2FA verification
      setShow2FA(true);
    } catch (err: any) {
      // Handle rate limiting and other errors
      if (err.message.includes('429') || err.message.includes('wait')) {
        setError('Please wait a moment before requesting another code.');
      } else {
        setError(err.message || 'Failed to request password reset');
      }
    } finally {
      setLoading(false);
    }
  }

  async function handle2FAVerified(code: string) {
    // Verify the code and get reset token
    try {
      const { verifyPasswordResetCode } = await import('@/utils/api');
      const result = await verifyPasswordResetCode({ email, code });
      // Redirect to reset page with token
      router.push(`/auth/reset-password/confirm?email=${encodeURIComponent(email)}&token=${encodeURIComponent(result.reset_token)}`);
    } catch (err: any) {
      setError(err.message || 'Failed to verify code');
      setShow2FA(false);
    }
  }

  if (show2FA && email) {
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
              email={email}
              purpose="password_reset"
              onVerified={handle2FAVerified}
              onCancel={() => {
                setShow2FA(false);
                setEmail('');
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
      title={<span className="font-light text-text tracking-tighter">Reset Password</span>}
      description="Enter your email address and we'll send you a verification code"
      heroImageSrc="https://images.unsplash.com/photo-1627556704302-624286467c65?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
      testimonials={sampleTestimonials}
      onSignIn={handleRequestReset}
      isRegister={false}
      isResetPassword={true}
      error={error}
      loading={loading}
      customContent={
        <div className="space-y-4">
          {error && error.includes('No account found') && (
            <div className="text-center">
              <a 
                href="/auth/register" 
                className="inline-block px-4 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
              >
                Create Account
              </a>
            </div>
          )}
          <div className="text-center">
            <a href="/auth/login" className="text-sm text-gray-700/70 hover:text-text transition">
              Back to Login
            </a>
          </div>
        </div>
      }
    />
  );
}

