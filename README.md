# Production-Ready AI Social Media Automation Platform (Facebook & Instagram)

An enterprise-grade, full-stack AI-powered social media automation platform designed for Facebook Pages and Instagram Business accounts. Features multi-tenant brand profile management, AI content copy generation (captions, hashtags, CTAs, SEO keywords, image prompts), AI visual graphic generation (OpenAI DALL-E 3), rich interactive post previews (Facebook & Instagram), approval and scheduling workflows, automated Celery background publishing via Meta Graph API, exponential retry logic, real-time analytics dashboard, and system audit logging.

---

## 🌟 Key Features

1. **JWT Authentication & RBAC**: Role-Based Access Control (`Admin`, `Editor`) with secure password hashing (bcrypt) and token generation.
2. **Brand Voice Profile Studio**: Configure tone of voice, target audience, brand color tokens, industry, and CTA styles per brand.
3. **AI Generation Engine (OpenAI GPT & DALL-E)**:
   - Automated high-converting captions tailored to brand voice.
   - Targeted hashtag lists & SEO keywords.
   - Actionable Call-To-Action (CTA) statements.
   - AI Image Prompt engineering & DALL-E 3 high-res graphic generation.
4. **Rich Social Media Previews**:
   - **Facebook Page Preview**: Verified badge, post header, dynamic text, callout banner, and interactive like/comment/share UI.
   - **Instagram Feed Preview**: Realistic mobile header, 1:1 image container, heart double-tap styling, and engagement metrics.
5. **Post Workflow & Scheduler**:
   - Lifecycle state machine: `DRAFT` ➔ `APPROVED` ➔ `SCHEDULED` ➔ `PUBLISHED` / `FAILED`.
   - Instant publication or automated background execution at scheduled times.
6. **Meta Graph API Client**:
   - **Facebook Page API**: Photo/feed publishing via `POST /{page-id}/photos`.
   - **Instagram Business API**: 2-step media container creation (`POST /{ig-user-id}/media`) and container publishing (`POST /{ig-user-id}/media_publish`).
   - **Sandbox Fallback Mode**: Graceful mock simulation mode for local testing without active API credits or Meta tokens.
7. **Celery Worker & Celery Beat Task Queue**:
   - Background worker processes scheduled posts every 60 seconds.
   - Exponential retry logic for failed posts up to maximum retry counts.
   - Automated sync for Facebook & Instagram performance metrics.
8. **Analytics Dashboard**:
   - Key metrics: Total Reach, Impressions, Engagement Rate, Interactions, and Growth.
   - Interactive Recharts area trend charts and daily interaction breakdown.
9. **Audit Trail**: Detailed compliance logs recording user activity, IP addresses, resource IDs, and action timestamps.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 14/15, React 18, TypeScript, TailwindCSS, Lucide Icons, Recharts, Axios.
- **Backend**: FastAPI (Python 3.11), Pydantic v2, SQLAlchemy ORM, Alembic.
- **Database**: PostgreSQL 16.
- **Cache & Queue**: Redis 7 + Celery + Celery Beat.
- **AI Integrations**: OpenAI GPT-4o & DALL-E 3 (with smart simulation fallback).
- **File Storage**: Cloudinary (with fallback image engine).
- **Social Graph API**: Meta Graph API (Facebook Page & Instagram Business).
- **Containerization**: Docker & Docker Compose.

---

## 🚀 Quick Start (Docker Compose)

The entire application stack (PostgreSQL, Redis, FastAPI Backend, Celery Worker, Celery Beat, and Next.js Frontend) can be launched with a single command:

```bash
# 1. Clone repository & configure environment variables
cp .env.example .env

# 2. Build and start all containers
docker-compose up --build
```

Access services:
- **Frontend App**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Backend API**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc API Docs**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 💻 Standalone Local Setup

### 1. Backend Setup (FastAPI & Celery)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run SQLite standalone mode (for instant local testing without Postgres)
$env:USE_SQLITE="true"
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup (Next.js)

```bash
cd frontend

# Install Node dependencies
npm install

# Run dev server
npm run dev
```

---

## 🧪 Running Unit Tests

Execute the Pytest backend test suite:

```bash
cd backend
python -m pytest -v
```

Test coverage includes:
- Authentication (`/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/me`).
- Brand profile CRUD.
- AI Content & Image Generation pipeline.
- Post Lifecycle State Machine (`DRAFT` -> `APPROVED` -> `PUBLISHED`).
- Meta Graph API mock publication flows.

---

## 📂 Project Architecture

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/         # FastAPI endpoints (auth, brands, posts, ai, meta, analytics, audit)
│   │   ├── core/           # Config, database setup, JWT security, Celery app
│   │   ├── models/         # SQLAlchemy ORM models (User, Brand, Post, MetaAccount, Analytics, Audit)
│   │   ├── repositories/   # Clean Repository pattern (User, Brand, Post, Analytics, Audit)
│   │   ├── schemas/        # Pydantic v2 schemas
│   │   ├── services/       # Business logic (Auth, Brand, AI, Storage, Meta Graph, Post, Analytics)
│   │   ├── tasks/          # Celery background tasks & beat schedules
│   │   └── main.py         # FastAPI application entrypoint
│   ├── tests/              # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages (Studio, Posts, Dashboard, Brands, Meta, Audit)
│   │   ├── components/     # UI components & Facebook / Instagram Rich Preview cards
│   │   └── lib/            # API client & TypeScript interfaces
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 📄 API Endpoints Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user |
| `POST` | `/api/v1/auth/login` | Authenticate & get JWT token |
| `GET` | `/api/v1/auth/me` | Current user profile |
| `GET/POST` | `/api/v1/brands/` | List or create brand profile |
| `POST` | `/api/v1/ai/generate-content` | Generate caption, hashtags, CTA & image prompt |
| `POST` | `/api/v1/ai/generate-image` | Generate AI visual graphic (DALL-E) |
| `POST` | `/api/v1/posts/` | Create draft post |
| `POST` | `/api/v1/posts/{id}/publish-now` | Publish immediately to FB & IG via Meta API |
| `POST` | `/api/v1/posts/{id}/retry` | Retry failed publication |
| `POST` | `/api/v1/meta/connect` | Link Facebook Page & Instagram Account |
| `GET` | `/api/v1/analytics/brand/{id}` | Fetch dashboard metrics & daily trends |
| `GET` | `/api/v1/audit/logs` | Fetch system audit history |

---

## 📜 License

MIT License. Built for Production AI Social Media Automation.
