# Deploying the Guidr frontend to Vercel

The frontend is a Next.js 14 App Router app in `guidr-frontend/`. It talks to the
Railway-hosted API via a single env var, `NEXT_PUBLIC_API_URL`.

> Deploy the backend first (see `guidr-backend/DEPLOY_RAILWAY.md`) so you have the
> API URL ready.

---

## 1. Import the project

1. Vercel → **Add New → Project** → import this GitHub repo.
2. **Root Directory:** set to `guidr-frontend` (this is a monorepo with the
   backend alongside). Vercel auto-detects Next.js — leave build/output defaults.

## 2. Environment variable

Add one env var (Production + Preview):

| Name | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | your Railway API URL, e.g. `https://guidr-api.up.railway.app` (no trailing slash) |

> It's `NEXT_PUBLIC_*`, so it's inlined at **build time** — if you change it,
> redeploy. Locally it defaults to `http://localhost:8000` (see `.env.example`).

## 3. Deploy, then wire CORS back to the backend

1. Deploy. Note your Vercel domain, e.g. `https://guidr.vercel.app`.
2. In Railway, add that exact origin to the API's `ALLOWED_ORIGINS`
   (comma-separated, **no trailing slash**) and redeploy the API.
   - Auth uses httpOnly cross-site cookies, so the origin must match exactly for
     `allow_credentials` to work.
3. If you add a custom domain later, add it to `ALLOWED_ORIGINS` too.

## 4. Smoke test

- Landing page loads; footer/nav links all resolve (no 404s).
- Register a user → you're taken through onboarding → dashboard.
- Browse `/schools` and `/institutions` → results load from the API.
- Sign-in/sign-up show the real testimonials.

## Notes

- External images: `next.config.js` allows `images.unsplash.com` (auth hero) and
  `logo.clearbit.com`; testimonial avatars (`ui-avatars.com`) use `unoptimized`,
  so no config change is needed.
- No other env vars are required by the frontend.
