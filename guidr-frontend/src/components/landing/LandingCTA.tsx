'use client';

import { useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { ParallaxLayer } from '@/components/landing/ParallaxLayer';

export function LandingCTA() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSubmitted, setIsSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setIsSubmitting(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSubmitting(false);
    setIsSubmitted(true);
    setEmail('');
  };

  return (
    <>
      {/* Main CTA Section with gradient background */}
      <section className="relative py-20 sm:py-28 overflow-hidden">
        {/* Gradient background with parallax */}
        <ParallaxLayer
          scrollRange={[800, 1400]}
          offsetRange={[0, 60]}
          className="absolute inset-0 bg-gradient-cta"
        />

        <motion.div
          className="relative max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.5 }}
        >
          <span className="inline-block px-4 py-1.5 mb-6 text-xs font-semibold uppercase tracking-widest-plus text-text bg-white/60 backdrop-blur-sm rounded-full">
            Playground
          </span>

          <h2 className="text-3xl sm:text-4xl lg:text-[48px] font-display font-semibold text-text leading-tight mb-6">
            The smartest way to find and apply to graduate school
          </h2>

          <p className="text-lg text-textSecondary mb-8 max-w-2xl mx-auto">
            Start discovering programs that match your goals, track your applications, and get AI-powered recommendations to maximize your chances.
          </p>

          <Button
            size="lg"
            className="rounded-full px-8 text-sm uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
            asChild
          >
            <Link href="/auth/register">Get Started For Free Today</Link>
          </Button>
        </motion.div>
      </section>

      {/* Newsletter Section */}
      <section className="py-12 sm:py-16 bg-muted/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="bg-white rounded-2xl p-8 sm:p-10 shadow-soft">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-8">
              {/* Text */}
              <div className="lg:max-w-md">
                <h3 className="text-lg font-semibold text-text mb-2">
                  Sign up for our newsletter to hear our latest application tips and product updates
                </h3>
              </div>

              {/* Form */}
              <div className="flex-1 lg:max-w-md">
                {isSubmitted ? (
                  <div className="flex items-center gap-3 px-4 py-3 bg-successLight rounded-xl">
                    <span className="text-sm text-success font-medium">
                      Thanks for subscribing! We&apos;ll keep you updated.
                    </span>
                  </div>
                ) : (
                  <form onSubmit={handleSubmit} className="flex gap-3">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="Enter email for updates*"
                      required
                      className="flex-1 px-4 py-3 bg-muted border border-border rounded-xl text-sm text-text placeholder:text-textMuted focus:outline-none focus:border-text focus:ring-1 focus:ring-text transition-colors"
                    />
                    <Button
                      type="submit"
                      disabled={isSubmitting}
                      className="rounded-xl px-6 text-xs uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90 disabled:opacity-50"
                    >
                      {isSubmitting ? 'Submitting...' : 'Submit'}
                    </Button>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
