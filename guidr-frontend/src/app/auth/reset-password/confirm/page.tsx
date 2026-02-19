'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { resetPassword } from '@/utils/api';
import PasswordStrengthMeter from '@/components/PasswordStrengthMeter';
import { SignInPage, Testimonial } from '@/components/ui/sign-in';
import { Eye, EyeOff } from 'lucide-react';
import { cn } from '@/lib/utils';

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

function ResetPasswordConfirmContent() {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState('');
  const [isPasswordValid, setIsPasswordValid] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const email = searchParams.get('email');
  const token = searchParams.get('token');

  useEffect(() => {
    if (!email || !token) {
      router.push('/auth/reset-password');
    }
  }, [email, token, router]);

  async function handleResetPassword(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');

    if (!email || !token) {
      setError('Invalid reset link');
      return;
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    // Check minimum requirements (backend will validate full strength)
    if (password.length < 8) {
      setError('Password must be at least 8 characters long');
      return;
    }

    setLoading(true);

    try {
      await resetPassword({
        email,
        reset_token: token,
        new_password: password,
      });
      router.push('/auth/login?reset=success');
    } catch (err: any) {
      setError(err.message || 'Failed to reset password');
    } finally {
      setLoading(false);
    }
  }

  if (!email || !token) {
    return null;
  }

  return (
    <SignInPage
      title={<span className="font-light text-text tracking-tighter">Create New Password</span>}
      description="Enter your new password below"
      heroImageSrc="https://images.unsplash.com/photo-1627556704302-624286467c65?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
      testimonials={sampleTestimonials}
      onSignIn={handleResetPassword}
      error={error}
      loading={loading}
      customContent={
        <form onSubmit={handleResetPassword} className="space-y-5">
          <div>
            <label className="text-sm font-medium text-gray-700/80">New Password</label>
            <div className="rounded-2xl border border-border/30 bg-card/50 backdrop-blur-sm transition-colors focus-within:border-primary/70 focus-within:bg-primary/10 mt-1">
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter new password"
                  required
                  className="w-full bg-transparent text-sm p-4 pr-12 rounded-2xl focus:outline-none text-gray-900 placeholder-gray-500"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-3 flex items-center"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5 text-gray-700/60 hover:text-text transition-colors" />
                  ) : (
                    <Eye className="w-5 h-5 text-gray-700/60 hover:text-text transition-colors" />
                  )}
                </button>
              </div>
            </div>
            {password && (
              <div className="mt-2">
                <PasswordStrengthMeter
                  password={password}
                  onStrengthChange={(strength, isValid) => {
                    setPasswordStrength(strength);
                    setIsPasswordValid(isValid);
                  }}
                />
              </div>
            )}
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700/80">Confirm Password</label>
            <div className="rounded-2xl border border-border/30 bg-card/50 backdrop-blur-sm transition-colors focus-within:border-primary/70 focus-within:bg-primary/10 mt-1">
              <input
                type={showPassword ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm new password"
                required
                className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none text-gray-900 placeholder-gray-500"
              />
            </div>
            {confirmPassword && password !== confirmPassword && (
              <p className="text-red-600 text-xs mt-1">Passwords do not match</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !password || !confirmPassword || password !== confirmPassword}
            className={cn(
              "w-full rounded-2xl py-4 font-semibold transition-colors",
              loading || !password || !confirmPassword || password !== confirmPassword
                ? "bg-gray-700/30 text-gray-700/50 cursor-not-allowed"
                : isPasswordValid
                ? "bg-primary text-white hover:bg-primaryHover"
                : "bg-yellow-400/50 text-text hover:bg-yellow-400"
            )}
          >
            {loading ? 'Resetting password...' : 'Reset Password'}
          </button>
          
          {password && confirmPassword && password === confirmPassword && !isPasswordValid && (
            <p className="text-yellow-700 text-xs mt-1 text-center">
              Password strength is weak. Consider adding uppercase, lowercase, numbers, and special characters.
            </p>
          )}

          <div className="text-center">
            <a href="/auth/login" className="text-sm text-gray-700/70 hover:text-text transition">
              Back to Login
            </a>
          </div>
        </form>
      }
    />
  );
}

export default function ResetPasswordConfirmPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background flex items-center justify-center" />}>
      <ResetPasswordConfirmContent />
    </Suspense>
  );
}

