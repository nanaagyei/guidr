'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { ChevronDown, Menu, X } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useMotionValueEvent, useScroll } from 'framer-motion';

const NAV_LINKS = [
  {
    label: 'Product',
    href: '#',
    dropdown: [
      { label: 'School Search', href: '/schools', description: 'Find your perfect graduate program' },
      { label: 'AI Recommendations', href: '/recommendations', description: 'Get personalized suggestions' },
      { label: 'Faculty Matching', href: '/professors', description: 'Find professors aligned to your research' },
      { label: 'Fit Scores', href: '/professors', description: 'See how well each lab matches you' },
    ],
  },
  { label: 'How it works', href: '/#how-it-works' },
  {
    label: 'Resources',
    href: '#',
    dropdown: [
      { label: 'Getting Started', href: '/help/getting-started', description: 'Set up your profile in minutes' },
      { label: 'Help Center', href: '/help', description: 'Guides and support' },
      { label: 'FAQ', href: '/help/faq', description: 'Answers to common questions' },
    ],
  },
  {
    label: 'Company',
    href: '#',
    dropdown: [
      { label: 'About', href: '/about', description: 'Our mission and story' },
      { label: 'Contact', href: '/contact', description: 'Get in touch with the team' },
    ],
  },
];

interface DropdownItem {
  label: string;
  href: string;
  description?: string;
}

interface NavLink {
  label: string;
  href: string;
  dropdown?: DropdownItem[];
}

function NavDropdown({ item, isOpen, onToggle }: { item: NavLink; isOpen: boolean; onToggle: () => void }) {
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        if (isOpen) onToggle();
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onToggle]);

  if (!item.dropdown) {
    return (
      <Link
        href={item.href}
        className="flex items-center gap-1 text-[13px] font-medium text-text hover:text-textSecondary transition-colors tracking-wide uppercase"
      >
        {item.label}
      </Link>
    );
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={onToggle}
        className="flex items-center gap-1 text-[13px] font-medium text-text hover:text-textSecondary transition-colors tracking-wide uppercase"
      >
        {item.label}
        <ChevronDown className={`h-3.5 w-3.5 text-textMuted transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-64 bg-white rounded-xl shadow-lg border border-border/50 py-2 z-50 animate-fade-in">
          {item.dropdown.map((dropItem) => (
            <Link
              key={dropItem.href}
              href={dropItem.href}
              className="block px-4 py-3 hover:bg-muted transition-colors"
              onClick={onToggle}
            >
              <span className="block text-sm font-medium text-text">{dropItem.label}</span>
              {dropItem.description && (
                <span className="block text-xs text-textMuted mt-0.5">{dropItem.description}</span>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

const HERO_SCROLL_THRESHOLD = 500;

export function LandingHeader() {
  const { user } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [isPastHero, setIsPastHero] = useState(false);

  const { scrollY } = useScroll();
  useMotionValueEvent(scrollY, 'change', (latest) => {
    setIsPastHero(latest > HERO_SCROLL_THRESHOLD);
  });

  return (
    <header className="sticky top-0 z-50 w-full bg-white/95 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 lg:h-[72px]">
          {/* Logo */}
          <Link href="/" className="flex items-center shrink-0" aria-label="Guidr home">
            <Image
              src="/images/guidr-logo.png"
              alt="Guidr"
              width={175}
              height={65}
              className="h-20 w-auto object-contain"
              priority
            />
          </Link>

          {/* Desktop nav */}
          <nav className="hidden lg:flex items-center gap-8" aria-label="Main navigation">
            {NAV_LINKS.map((item) => (
              <NavDropdown
                key={item.label}
                item={item}
                isOpen={openDropdown === item.label}
                onToggle={() => setOpenDropdown(openDropdown === item.label ? null : item.label)}
              />
            ))}
          </nav>

          {/* Desktop CTAs */}
          <div className="hidden lg:flex items-center gap-3">
            <Button
              variant="outline"
              size="sm"
              className="rounded-full px-5 text-[13px] uppercase tracking-wide font-medium border-text/20 hover:border-text/40"
              asChild
            >
              <Link href="/contact">Contact Us</Link>
            </Button>
            {user ? (
              <Button
                size="sm"
                className="rounded-full px-5 text-[13px] uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
                asChild
              >
                <Link href="/dashboard">Dashboard</Link>
              </Button>
            ) : isPastHero ? (
              <Button
                size="sm"
                className="rounded-full px-5 text-[13px] uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
                asChild
              >
                <Link href="/schools">Explore Programs</Link>
              </Button>
            ) : (
              <Button
                size="sm"
                className="rounded-full px-5 text-[13px] uppercase tracking-wide font-medium bg-text text-white hover:bg-text/90"
                asChild
              >
                <Link href="/auth/register">Get Started</Link>
              </Button>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            type="button"
            className="lg:hidden p-2 rounded-lg text-text hover:bg-muted transition-colors"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle menu"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile nav */}
        {mobileMenuOpen && (
          <div className="lg:hidden py-4 border-t border-border animate-slide-down">
            <nav className="flex flex-col gap-1" aria-label="Mobile navigation">
              {NAV_LINKS.map((item) => (
                <div key={item.label}>
                  {item.dropdown ? (
                    <div className="py-2">
                      <span className="px-3 text-xs font-semibold uppercase tracking-wider text-textMuted">
                        {item.label}
                      </span>
                      <div className="mt-2 space-y-1">
                        {item.dropdown.map((dropItem) => (
                          <Link
                            key={dropItem.href}
                            href={dropItem.href}
                            className="block px-3 py-2 text-sm text-text hover:bg-muted rounded-lg"
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            {dropItem.label}
                          </Link>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <Link
                      href={item.href}
                      className="block px-3 py-2 text-sm font-medium text-text hover:bg-muted rounded-lg"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      {item.label}
                    </Link>
                  )}
                </div>
              ))}
              <div className="flex flex-col gap-2 pt-4 mt-2 border-t border-border">
                <Button variant="outline" size="sm" className="w-full rounded-full" asChild>
                  <Link href="/contact" onClick={() => setMobileMenuOpen(false)}>Contact Us</Link>
                </Button>
                {user ? (
                  <Button size="sm" className="w-full rounded-full bg-text text-white" asChild>
                    <Link href="/dashboard" onClick={() => setMobileMenuOpen(false)}>Dashboard</Link>
                  </Button>
                ) : (
                  <>
                    <Button size="sm" className="w-full rounded-full bg-text text-white" asChild>
                      <Link href="/auth/register" onClick={() => setMobileMenuOpen(false)}>Get Started</Link>
                    </Button>
                    <Button variant="ghost" size="sm" className="w-full rounded-full" asChild>
                      <Link href="/auth/login" onClick={() => setMobileMenuOpen(false)}>Login</Link>
                    </Button>
                  </>
                )}
              </div>
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
