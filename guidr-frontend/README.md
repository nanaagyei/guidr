# Guidr Frontend

Frontend application for Guidr - A graduate school application platform.

## Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Deployment:** Vercel (recommended)

## Setup

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```

3. **Access the app:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000 (configure in `.env.local`)

## Project Structure

```
guidr-frontend/
├── src/
│   ├── app/              # Next.js App Router pages
│   ├── components/       # React components
│   ├── hooks/            # Custom React hooks
│   ├── utils/            # Utility functions
│   └── styles/           # Global styles
├── public/               # Static assets
├── tailwind.config.js    # Tailwind configuration
└── next.config.js        # Next.js configuration
```

## Development

- **Dev server:** `npm run dev`
- **Build:** `npm run build`
- **Lint:** `npm run lint`
- **Start production:** `npm start`

## Design System

Guidr uses a minimalistic, modern color palette:
- **Background:** #FAFAFA (off-white background)
- **Card:** #FFFFFF (white cards)
- **Sidebar:** #1F2937 (dark sidebar)
- **Primary:** #3B82F6 (blue accent)
- **Text:** #111827 (dark text)
- **Text Secondary:** #6B7280 (secondary text)
- **Border:** #E5E7EB (light borders)

See `STYLEGUIDE.md` for detailed design guidelines.

## CI/CD

GitHub Actions workflow runs on push/PR to main/dev branches:
- Linting (ESLint)
- Build verification

![Frontend CI](https://github.com/your-org/guidr-frontend/actions/workflows/frontend-ci.yml/badge.svg)

