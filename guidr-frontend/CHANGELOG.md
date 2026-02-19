# CHANGELOG

All notable changes to Guidr Frontend will be documented in this file.

## [Unreleased]

### Added
- [2025-02-03] feat(landing): Visual and scroll enhancements
  - Hero section: light green gradient (gradient-hero-green) replacing peach
  - College logos: Clearbit API for Harvard, Stanford, MIT, Yale, Princeton, Columbia, Berkeley, UChicago with fallback to initials
  - Stock images: Unsplash for blog cards and FeatureVisual (campus/study imagery)
  - Parallax effects: Hero, LogoCloud, CTA gradient backgrounds via ParallaxLayer (useScroll, useTransform); disabled on mobile
  - Scroll-aware CTA: Header primary button switches from "Get Started" to "Explore Programs" when scrolled past hero
  - Scroll-triggered animations: whileInView staggered reveals for LogoCloud, Features, Blog, CTA, Footer
  - Next.js images.remotePatterns for images.unsplash.com, logo.clearbit.com
  - Files: tailwind.config.js, next.config.js, LandingHero, LandingLogoCloud, LandingFeatures, LandingBlog, LandingCTA, LandingHeader, LandingFooter, ParallaxLayer

- [2025-02-03] feat(ui): Toast-based errors for auth and recommendations
  - Login and registration pages now use global Toasts for network and validation errors
  - Recommended Programs dashboard tile surfaces API failures via a friendly toast instead of only logging
  - Files: `src/app/auth/login/page.tsx`, `src/app/auth/register/page.tsx`, `src/components/dashboard/RecommendedSchoolsTile.tsx`

- [2025-02-03] feat(landing): Hume-style professional landing page at root route
  - Full-bleed layout for `/` (no sidebar) via ConditionalLayout
  - LandingHeader: sticky nav, Guidr logo, Schools/How it works/Pricing/Resources, Contact + Log in/Get started (or Dashboard when logged in), mobile hamburger
  - LandingHero: headline, sub-headline, primary CTA (Get started / Go to Dashboard)
  - LandingFeatures: three pastel cards (Find programs, Track applications, Get recommendations) with Lucide icons
  - LandingCTA: strip with “Get started free” button
  - LandingFooter: logo, Product/Company/Resources/Legal columns, Sign up/Contact us, copyright
  - Tailwind: landingLavender, landingPeach, landingMuted for feature card backgrounds
  - Files: `src/components/ConditionalLayout.tsx`, `src/app/page.tsx`, `src/components/landing/*.tsx`, `tailwind.config.js`

- [2025-02-03] feat(branding): Use guidr-logo.png for sidebar, login and sign up pages
  - Sidebar Logo and LogoIcon now use `/images/guidr-logo.png` via Next.js Image
  - Sign-in page (login/register) logo updated from guidr-logo1.png to guidr-logo.png
  - Favicon unchanged per plan
  - Files: `src/components/Sidebar.tsx`, `src/components/ui/sign-in.tsx`

- [2025-02-03] feat(ui): shadcn-style components and dashboard redesign
  - Initialized shadcn-style setup (components.json, Tailwind integration)
  - Added Button, Card, Skeleton, Label components using existing Guidr theme
  - Rebuilt dashboard and all 7 tiles with Card, Button, no emojis, Lucide icons
  - Added funding API client (getFundingOpportunities, getFundingOpportunity, getFundingByInstitution)
  - Added Funding nav item and /funding page with filters and responsive card grid
  - Files: components.json, src/components/ui/button.tsx, card.tsx, skeleton.tsx, label.tsx; src/components/dashboard/*.tsx; src/app/dashboard/page.tsx; src/app/funding/page.tsx; src/utils/api.ts; src/components/Sidebar.tsx

### Changed
- [2025-02-03] style(branding): Light sidebar theme and larger logos
  - Sidebar background updated to light academic tone so the green Guidr logo is clearly visible
  - Active sidebar links use a subtle highlight and the recommendation tile icon sits centered in a circular badge
  - Landing header/footer and dashboard sidebar logos increased in size for stronger branding
  - Files: `tailwind.config.js`, `src/components/ui/sidebar.tsx`, `src/components/Sidebar.tsx`, `src/components/landing/LandingHeader.tsx`, `src/components/landing/LandingFooter.tsx`, `src/components/ui/tile-header.tsx`, `src/components/dashboard/ProfessorsTile.tsx`

- [2025-02-03] refactor(ui): Badge variants use theme colors (primaryLight, successLight, etc.)
- [2025-02-03] refactor(ui): loading-skeleton uses shared Skeleton from skeleton.tsx
- [2025-02-03] style(globals): button cursor pointer in base layer
- [2025-02-03] refactor(pages): schools, recommendations, programs/[id], settings use Button and theme tokens
- [2025-02-03] refactor(ui): TileHeader renders Link/button explicitly for correct types
- [2025-02-03] fix(auth): reset-password/confirm wrapped in Suspense for useSearchParams
- [2025-02-03] fix(ui): unescaped apostrophes in academic-records, OnboardingWizard, PrivacySettings, TwoFactorVerification
- [2025-02-03] fix(ui): TwoFactorVerification ref callback returns void
- [2025-02-03] fix(profile): preferred_start_year onChange uses string for form state
- [2025-02-03] style: border-moss/20 replaced with border-primary/20; program hero gradient replaced with solid primaryLight

## [0.0.1] – 2024-01-01

### Added
- Initialized Next.js project with TypeScript and App Router
- Configured Tailwind CSS with Guidr brand colors (Moss, Mustard, Eggshell, Olive, Ecru, Champagne)
- Created base layout with sidebar navigation
- Set up GitHub Actions CI pipeline for linting and building
- Created initial welcome page

