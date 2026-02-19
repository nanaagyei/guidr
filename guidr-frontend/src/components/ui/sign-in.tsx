'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { Eye, EyeOff } from 'lucide-react';

// --- HELPER COMPONENTS (ICONS) ---

const GoogleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 48 48">
    <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s12-5.373 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-2.641-.21-5.236-.611-7.743z" />
    <path fill="#FF3D00" d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z" />
    <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z" />
    <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C42.022 35.026 44 30.038 44 24c0-2.641-.21-5.236-.611-7.743z" />
  </svg>
);

// --- TYPE DEFINITIONS ---

export interface Testimonial {
  avatarSrc: string;
  name: string;
  handle: string;
  text: string;
}

interface SignInPageProps {
  title?: React.ReactNode;
  description?: React.ReactNode;
  heroImageSrc?: string;
  testimonials?: Testimonial[];
  onSignIn?: (event: React.FormEvent<HTMLFormElement>) => void;
  onGoogleSignIn?: () => void;
  onResetPassword?: () => void;
  onCreateAccount?: () => void;
  isRegister?: boolean;
  isResetPassword?: boolean;  // Flag to indicate this is a reset password page
  error?: string;
  loading?: boolean;
  customContent?: React.ReactNode;  // Custom content to replace the form
}

// --- SUB-COMPONENTS ---

const GlassInputWrapper = ({ children }: { children: React.ReactNode }) => (
  <div className="rounded-2xl border border-border/30 bg-card/50 backdrop-blur-sm transition-colors focus-within:border-primary/70 focus-within:bg-primary/10">
    {children}
  </div>
);

const TestimonialCard = ({ testimonial, delay }: { testimonial: Testimonial, delay: string }) => (
  <div className={`animate-testimonial ${delay} flex items-start gap-3 rounded-3xl bg-card/60 backdrop-blur-xl border border-white/20 p-5 w-64 shadow-lg`}>
    <Image 
      src={testimonial.avatarSrc} 
      width={40} 
      height={40} 
      className="h-10 w-10 object-cover rounded-2xl" 
      alt="avatar"
      unoptimized
    />
    <div className="text-sm leading-snug">
      <p className="flex items-center gap-1 font-medium text-text">{testimonial.name}</p>
      <p className="text-gray-700/70">{testimonial.handle}</p>
      <p className="mt-1 text-gray-700">{testimonial.text}</p>
    </div>
  </div>
);

// --- MAIN COMPONENT ---

export const SignInPage: React.FC<SignInPageProps> = ({
  title = <span className="font-light text-text tracking-tighter">Welcome</span>,
  description = "Access your account and continue your journey with us",
  heroImageSrc,
  testimonials = [],
  onSignIn,
  onGoogleSignIn,
  onResetPassword,
  onCreateAccount,
  isRegister = false,
  isResetPassword = false,
  error,
  loading = false,
  customContent,
}) => {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="h-[100dvh] flex flex-col md:flex-row font-geist w-[100dvw] bg-background">
      {/* Logo at top left */}
      <div className="absolute top-6 left-6 z-10">
        <Image 
          src="/images/guidr-logo.png" 
          alt="Guidr Logo" 
          width={350} 
          height={140}
          className="h-24 w-auto"
          priority
        />
      </div>
      
      {/* Left column: sign-in form */}
      <section className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-md">
          <div className="flex flex-col gap-6">
            <h1 className="animate-element animate-delay-100 text-4xl md:text-5xl font-semibold leading-tight text-text">{title}</h1>
            <p className="animate-element animate-delay-200 text-gray-700/80">{description}</p>

            {error && (
              <div className="animate-element animate-delay-250 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {customContent && !isResetPassword ? (
              customContent
            ) : (
              <>
                <form className="space-y-5" onSubmit={onSignIn}>
                  {isRegister && (
                    <div className="animate-element animate-delay-300">
                      <label className="text-sm font-medium text-gray-700/80">Full Name</label>
                      <GlassInputWrapper>
                        <input name="fullName" type="text" placeholder="Enter your full name" className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none text-gray-900 placeholder-gray-500" />
                      </GlassInputWrapper>
                    </div>
                  )}

                  <div className="animate-element animate-delay-300">
                    <label className="text-sm font-medium text-gray-700/80">Email Address</label>
                    <GlassInputWrapper>
                      <input name="email" type="email" placeholder="Enter your email address" className="w-full bg-transparent text-sm p-4 rounded-2xl focus:outline-none text-gray-900 placeholder-gray-500" />
                    </GlassInputWrapper>
                  </div>

                  {!isResetPassword && (
                    <div className="animate-element animate-delay-400">
                      <label className="text-sm font-medium text-gray-700/80">Password</label>
                      <GlassInputWrapper>
                        <div className="relative">
                          <input name="password" type={showPassword ? 'text' : 'password'} placeholder="Enter your password" className="w-full bg-transparent text-sm p-4 pr-12 rounded-2xl focus:outline-none text-gray-900 placeholder-gray-500" />
                          <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-3 flex items-center">
                            {showPassword ? <EyeOff className="w-5 h-5 text-gray-700/60 hover:text-text transition-colors" /> : <Eye className="w-5 h-5 text-gray-700/60 hover:text-text transition-colors" />}
                          </button>
                        </div>
                      </GlassInputWrapper>
                    </div>
                  )}

                  {!isRegister && !isResetPassword && (
                    <div className="animate-element animate-delay-500 flex items-center justify-between text-sm">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" name="rememberMe" className="custom-checkbox" />
                        <span className="text-gray-700">Keep me signed in</span>
                      </label>
                      <a href="#" onClick={(e) => { e.preventDefault(); onResetPassword?.(); }} className="hover:underline text-text transition-colors">Reset password</a>
                    </div>
                  )}

                  <button type="submit" disabled={loading} className="animate-element animate-delay-600 w-full rounded-2xl bg-primary text-white py-4 font-semibold hover:bg-primaryHover transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                    {loading 
                      ? (isRegister ? 'Registering...' : isResetPassword ? 'Sending code...' : 'Signing in...') 
                      : (isRegister ? 'Create Account' : isResetPassword ? 'Send Verification Code' : 'Sign In')
                    }
                  </button>
                </form>
                
                {isResetPassword && customContent && (
                  customContent
                )}
              </>
            )}

            {!customContent && onGoogleSignIn && (
              <>
                <div className="animate-element animate-delay-700 relative flex items-center justify-center">
                  <span className="w-full border-t border-border/30"></span>
                  <span className="px-4 text-sm text-gray-700/70 bg-background absolute">Or continue with</span>
                </div>

                <button onClick={onGoogleSignIn} className="animate-element animate-delay-800 w-full flex items-center justify-center gap-3 border border-border/30 rounded-2xl py-4 hover:bg-card/50 transition-colors text-gray-700">
                  <GoogleIcon />
                  Continue with Google
                </button>
              </>
            )}

            <p className="animate-element animate-delay-900 text-center text-sm text-gray-700/70">
              {isRegister ? (
                <>
                  Already have an account? <a href="/auth/login" onClick={(e) => { e.preventDefault(); onCreateAccount?.(); }} className="text-text hover:underline transition-colors">Sign In</a>
                </>
              ) : (
                <>
                  New to our platform? <a href="/auth/register" onClick={(e) => { e.preventDefault(); onCreateAccount?.(); }} className="text-text hover:underline transition-colors">Create Account</a>
                </>
              )}
            </p>
          </div>
        </div>
      </section>

      {/* Right column: hero image + testimonials */}
      {heroImageSrc && (
        <section className="hidden md:block flex-1 relative p-4">
          <div className="animate-slide-right animate-delay-300 absolute inset-4 rounded-3xl bg-cover bg-center shadow-2xl" style={{ backgroundImage: `url(${heroImageSrc})` }}></div>
          {testimonials.length > 0 && (
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex gap-4 px-8 w-full justify-center">
              <TestimonialCard testimonial={testimonials[0]} delay="animate-delay-1000" />
              {testimonials[1] && <div className="hidden xl:flex"><TestimonialCard testimonial={testimonials[1]} delay="animate-delay-1200" /></div>}
              {testimonials[2] && <div className="hidden 2xl:flex"><TestimonialCard testimonial={testimonials[2]} delay="animate-delay-1400" /></div>}
            </div>
          )}
        </section>
      )}
    </div>
  );
};

