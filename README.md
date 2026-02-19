<p align="center">
  <img src="https://img.shields.io/badge/Guidr-Graduate%20School%20Platform-3B82F6?style=for-the-badge&logo=graduationcap" alt="Guidr" />
</p>

<h1 align="center">Guidr</h1>
<p align="center">
  <strong>AI-powered graduate school discovery and application platform</strong>
</p>

<p align="center">
  <a href="#"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Node.js-18+-339933?style=flat-square&logo=node.js&logoColor=white" alt="Node.js" /></a>
  <a href="#"><img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="#"><img src="https://img.shields.io/badge/Next.js-14+-000000?style=flat-square&logo=next.js&logoColor=white" alt="Next.js" /></a>
  <a href="#"><img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL" /></a>
  <a href="#"><img src="https://img.shields.io/badge/TypeScript-5+-3178C6?style=flat-square&logo=typescript&logoColor=white" alt="TypeScript" /></a>
  <a href="#"><img src="https://img.shields.io/badge/License-MIT-yellow?style=flat-square" alt="License" /></a>
</p>

---

## About

**Guidr** helps graduate and undergraduate applicants find schools, explore programs, and streamline their application process with AI-powered recommendations. The platform combines official education data, intelligent web scraping, and machine learning to deliver personalized program matches, essay feedback, and professor outreach tools.

## Features

| Area | Capabilities |
|------|--------------|
| **Discover** | Search 2,000+ US graduate schools, 30K+ programs, and 100K+ faculty profiles |
| **Data Pipeline** | College Scorecard + IPEDS ingestion, Firecrawl/LLM web scraping, structured extraction |
| **AI-Powered** | LLM-driven program discovery, transcript/resume extraction, essay feedback, cold email drafts |
| **Recommendations** | Heuristic + ML scoring with Dream/Reach/Target/Safety tiers |
| **Documents** | Upload to R2, OCR, and schema validation |
| **Search** | Full-text search via Meilisearch across institutions, programs, and funding |

## Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy, Alembic |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Radix UI |
| **Data** | PostgreSQL, Redis, Meilisearch |
| **Pipeline** | Celery, Scrapy, Playwright, LangChain, Firecrawl |
| **Infra** | Docker, MinIO/R2, GitHub Actions |

## Repository Structure

```
guidr/
├── guidr-backend/     # FastAPI API, data pipeline, Celery workers
├── guidr-frontend/    # Next.js app (App Router)
└── README.md
```

- **Backend:** API routes, models, pipeline (ingestion, scraping, extraction), enrichment, search indexing  
- **Frontend:** App shell, auth flows, search UI, program/school detail pages, design system  

## Getting Started

Setup instructions live in each package:

- **[Backend setup](guidr-backend/README.md)** — Docker, migrations, env vars
- **[Frontend setup](guidr-frontend/README.md)** — Dependencies, dev server
- **[Pipeline guide](guidr-backend/docs/PIPELINE_GUIDE.md)** — Data architecture, ingestion, scraping
- **[Quick start](guidr-backend/docs/QUICK_START.md)** — Minimal setup for local development

## Project Status

Guidr is in active development. See the [roadmap](guidr-frontend/ROADMAP.md) for milestones and planned features.

---

<p align="center">
  <sub>Built for graduate applicants · <a href="https://guidr.app">guidr.app</a></sub>
</p>
