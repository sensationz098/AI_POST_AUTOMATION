# Production-Ready AI Social Media Automation Platform (Facebook & Instagram)

An enterprise-grade, full-stack AI-powered social media automation platform designed for Facebook Pages and Instagram Business accounts. Features multi-tenant brand profile management, AI content copy generation (captions, hashtags, CTAs, SEO keywords, image prompts), AI visual graphic generation (OpenAI DALL-E 3), rich interactive post previews (Facebook & Instagram), approval and scheduling workflows, asynchronous Celery multi-account batch publishing via Meta Graph API, real-time byte-level media upload progress tracking for 300MB+ long videos, exponential retry logic, real-time analytics dashboard, and system audit logging.

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
5. **Real-Time Byte-Level Media Upload Progress (300MB+ Large Videos)**:
   - dedicated device-to-storage transfer progress bar with loaded/total byte metrics and stage machine (`UPLOADING` ➔ `PROCESSING` ➔ `READY`).
   - Memory-safe disk file streaming to Cloudinary CDN via `upload_large()` chunking (6 MB chunks) for videos > 100 MB without RAM inflation.
   - Configurable size limits (`MAX_VIDEO_UPLOAD_BYTES: 500 MB`, `MAX_IMAGE_UPLOAD_BYTES: 30 MB`) with `HTTP 413` validation responses.
   - Dedicated 10-minute client upload timeout (`MEDIA_UPLOAD_TIMEOUT_MS: 600,000 ms`).
6. **Asynchronous Celery Multi-Account Batch Publishing**:
   - Offloads multi-account publishing jobs to background Celery tasks via `POST /api/v1/posts/publish-multi`.
   - Real-time client polling (`GET /api/v1/posts/batch/{batch_id}`) tracking job execution state (`PENDING` ➔ `PROCESSING` ➔ `SUCCESS` / `PARTIAL_SUCCESS` / `FAILED`).
   - Extended 300-second publishing timeout (`PUBLISHING_TIMEOUT_MS: 300,000 ms`) for Meta video container processing.
7. **Meta Graph API Client**:
   - **Facebook Page API**: Photo/feed & video publishing via `POST /{page-id}/photos` and `POST /{page-id}/videos`.
   - **Instagram Business API**: 2-step media container creation (`POST /{ig-user-id}/media`) and container publishing (`POST /{ig-user-id}/media_publish`) with status polling.
   - **Sandbox Fallback Mode**: Graceful mock simulation mode for local testing without active API credits or Meta tokens.
8. **Celery Worker & Celery Beat Task Queue**:
   - Background worker processes scheduled posts every 60 seconds.
   - Exponential retry logic for failed posts up to maximum retry counts.
   - Automated sync for Facebook & Instagram performance metrics.
9. **Analytics Dashboard**:
   - Key metrics: Total Reach, Impressions, Engagement Rate, Interactions, and Growth.
   - Interactive Recharts area trend charts and daily interaction breakdown.
10. **Audit Trail**: Detailed compliance logs recording user activity, IP addresses, resource IDs, and action timestamps.

---

## 🛠️ Tech Stack

- **Frontend**: Next.js 14/15, React 18, TypeScript, TailwindCSS, Lucide Icons, Recharts, Axios (with custom multi-stage timeout handlers).
- **Backend**: FastAPI (Python 3.11), Pydantic v2, SQLAlchemy ORM, Alembic.
- **Database**: PostgreSQL 16.
- **Cache & Queue**: Redis 7 + Celery + Celery Beat.
- **AI Integrations**: OpenAI GPT-4o & DALL-E 3 (with smart simulation fallback).
- **File & Media Storage**: Cloudinary SDK (with chunked `upload_large()` streaming for large media).
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
- Real-time media upload (`/api/v1/posts/upload-media`) and Cloudinary chunked upload routing (`<=100MB` vs `>100MB`).
- Asynchronous multi-account batch publishing (`/api/v1/posts/publish-multi` and `/api/v1/posts/batch/{id}`).
- Meta Graph API mock publication flows.

---

## 📂 Project Architecture

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/         # FastAPI endpoints (auth, brands, posts, ai, meta, analytics, audit)
│   │   ├── core/           # Config, database setup, JWT security, Celery app
│   │   ├── models/         # SQLAlchemy ORM models (User, Brand, Post, MetaAccount, Analytics, Audit, PublishingBatch, PublishingJob)
│   │   ├── repositories/   # Clean Repository pattern (User, Brand, Post, Analytics, Audit, Publishing)
│   │   ├── schemas/        # Pydantic v2 schemas
│   │   ├── services/       # Business logic (Auth, Brand, AI, Cloudinary Storage, Meta Graph, Publisher, Analytics)
│   │   ├── tasks/          # Celery background tasks & beat schedules
│   │   └── main.py         # FastAPI application entrypoint
│   ├── tests/              # Pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/            # Next.js App Router pages (Studio, Posts, Dashboard, Brands, Meta, Audit)
│   │   ├── components/     # UI components & Facebook / Instagram Rich Preview cards
│   │   └── lib/            # API client (with timeout tiers) & TypeScript interfaces
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
| `POST` | `/api/v1/posts/upload-media` | Upload media with progress reporting & Cloudinary streaming |
| `POST` | `/api/v1/posts/` | Create draft post |
| `POST` | `/api/v1/posts/publish-multi` | Queue asynchronous multi-account batch publishing |
| `GET` | `/api/v1/posts/batch/{batch_id}` | Poll publishing batch status and job progress |
| `POST` | `/api/v1/posts/{id}/retry` | Retry failed publication |
| `POST` | `/api/v1/meta/connect` | Link Facebook Page & Instagram Account |
| `GET` | `/api/v1/analytics/brand/{id}` | Fetch dashboard metrics & daily trends |
| `GET` | `/api/v1/audit/logs` | Fetch system audit history |

---

## ⚙️ Timeout Architecture & Size Configurations

The system enforces structured timeout windows across API interaction layers:

- **Standard REST API Calls**: `15 seconds` (`DEFAULT_API_TIMEOUT_MS = 15000`)
- **Meta Video Publishing**: `300 seconds` (`PUBLISHING_TIMEOUT_MS = 300000`) matching Meta's video container processing window.
- **Device-to-Storage Media Uploads**: `600 seconds` (`MEDIA_UPLOAD_TIMEOUT_MS = 600000`) allowing up to 10 minutes for 300MB+ transfers.

### Configurable Media Upload Limits (Environment Variables)
```env
MAX_VIDEO_UPLOAD_BYTES=524288000   # 500 MB max limit for videos
MAX_IMAGE_UPLOAD_BYTES=31457280     # 30 MB max limit for photos
```

---

## 🔐 Meta Developer Setup Guide (OAuth 2.0 Integration)

To connect real Facebook Pages and Instagram Professional accounts using official Meta OAuth 2.0 authorization, follow these setup steps:

### 1. Create Meta Developer App
1. Go to [Meta for Developers](https://developers.facebook.com/) and log in with your Facebook account.
2. Click **My Apps** ➔ **Create App**.
3. Select **Other** ➔ **Business** as the app type.
4. Give your app a name (e.g. `Social AI Automation Platform`) and link your Business Manager account.

### 2. Configure Products & Permissions
In your Meta App Dashboard:
1. Add **Facebook Login for Business** product.
2. Add **Instagram Graph API** product.
3. Under **Facebook Login for Business Settings**, add your backend callback redirect URI under **Valid OAuth Redirect URIs**:
   - For local development: `http://localhost:8000/api/v1/meta/oauth/callback`
   - For production: `https://your-domain.com/api/v1/meta/oauth/callback`

### 3. Required Meta Permissions
The OAuth authorization flow requests only the essential permissions needed to publish content to authorized Pages and linked Instagram Professional accounts:
- `pages_show_list`: Allows discovering Facebook Pages managed by the user.
- `pages_read_engagement`: Allows fetching page engagement & profile details.
- `pages_manage_posts`: Grants permission to post photo, video reels & text status updates to authorized Pages.
- `instagram_basic`: Allows reading linked Instagram Business account IDs and profile handles.
- `instagram_content_publish`: Grants permission to publish photo and video Reels to Instagram Business feeds.

### 4. Configure Environment Variables
Copy your Meta App credentials from **App Settings ➔ Basic**:
```env
META_APP_ID="your_15_digit_app_id"
META_APP_SECRET="your_32_character_app_secret"
META_GRAPH_API_VERSION="v19.0"
META_OAUTH_REDIRECT_URI="http://localhost:8000/api/v1/meta/oauth/callback"
FRONTEND_URL="http://localhost:3000"
```

### 5. Local Testing & App Review Requirements
- **Development Mode Testing**: While your Meta App is in Development mode, you can test OAuth authorization using your own Facebook account, App Admins, Developers, or added Test Users in **Roles ➔ Roles**.
- **Instagram Account Eligibility**: The Instagram account MUST be converted to a **Professional Account** (Business or Creator) and linked directly to your Facebook Page in Facebook Page Settings (Linked Accounts ➔ Instagram).
- **Production App Review**: To allow public users outside your Meta App Roles to connect their Facebook Pages & Instagram accounts, submit your app for Meta App Review for the permissions listed above.

---

## 📜 License

MIT License. Built for Production AI Social Media Automation.
