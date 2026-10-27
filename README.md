# 🌍 API_World 

##  Modular FastAPI Authentication & User Backend

**API_World** is a production-ready, asynchronous, and modular REST API backend built with **FastAPI**, **PostgreSQL 16 (Async SQLAlchemy 2.0)**, and **Docker**. 

It implements a complete, hardened Authentication & User Management system (`Register`, `Email Verify`, `Login`, `Refresh Token Rotation`, `Logout`, `Forgot Password`, `Reset Password`, and `Public/Private User Profiles`) designed with a plug-and-play modular architecture so new microservice-like API modules can be added effortlessly in the future.

---

## Key Features

- **🔐 Complete Authentication Flow:**
  - User Registration with reserved-username protection & background email verification dispatch.
  - Email Verification using purpose-isolated, time-limited JWT tokens (`verify_email`).
  - Dual-Identifier Login (log in with either **Username** or **Email**).
  - Stateful Refresh Token Rotation stored in PostgreSQL (`refresh_tokens` table) with revocation on Logout.
  - Forgot Password & Reset Password flow that automatically revokes all active sessions across devices upon password change.
- **👤 User & Profile Management:**
  - Protected `/api/v1/users/profile` endpoints (`GET` & `PATCH`) for authenticated users to view and update their private profile details.
  - Public `/api/v1/users/profile/{username}` endpoint to look up any active user's public profile without exposing sensitive fields.
- **🐳 Hardened Docker Infrastructure:**
  - Non-root container execution (`appuser`) for container security.
  - Integrated **PostgreSQL 16** with automated healthchecks (`pg_isready`) and persistent volumes.
  - Localhost-bound **pgAdmin 4** (`127.0.0.1:5050`) for visual database inspection.
  - Compatible with Hitesh Choudhary's [`justPostgres`](https://github.com/hiteshchoudhary/justPostgres.git) container setup.
- **🧱 Scalable Modular Architecture:**
  - Clean separation of concerns (`models.py`, `schemas.py`, `controller.py`, `router.py`, `dependencies.py`) inside `app/modules/`.

---

## 📂 Project Folder Structure

```text
API_World/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entrypoint, Lifespan DB init & Router mounting
│   ├── core/                        # Global configuration, DB engine, and cryptography
│   │   ├── __init__.py
│   │   ├── config.py                # Pydantic BaseSettings (.env loader)
│   │   ├── database.py              # Async SQLAlchemy 2.0 Engine & get_db session dependency
│   │   └── security.py              # Bcrypt password hashing & purpose-typed JWT encoding/decoding
│   ├── common/                      # Shared utilities across modules
│   │   ├── __init__.py
│   │   └── email.py                 # Async SMTP email sender + local console token logger
│   └── modules/                     # Plug-and-play feature modules
│       ├── __init__.py
│       ├── auth/                    # Authentication Module
│       │   ├── __init__.py
│       │   ├── models.py            # RefreshToken SQLAlchemy model
│       │   ├── schemas.py           # Auth Pydantic v2 request/response schemas & validators
│       │   ├── controller.py        # Core business logic for Register, Login, Verify, Reset, Logout
│       │   ├── router.py            # /api/v1/auth HTTP endpoints
│       │   └── dependencies.py      # Reusable get_current_user Bearer token guard
│       └── users/                   # Users & Profile Module
│           ├── __init__.py
│           ├── models.py            # User SQLAlchemy model
│           ├── schemas.py           # Public & Private profile Pydantic schemas
│           ├── controller.py        # Profile lookup and update logic
│           └── router.py            # /api/v1/users HTTP endpoints
├── Dockerfile                       # Hardened Python 3.11-slim image with non-root appuser
├── docker-compose.yml               # Orchestrates PostgreSQL 16, pgAdmin 4, and FastAPI backend
├── .dockerignore                    # Excludes local .venv, .env, and cache from Docker context
├── requirements.txt                 # Pinned Python dependencies
├── .env                             # Environment variables (DB, JWT secrets, SMTP)
├── pdr.md                           # Project Design & Requirements Document
└── README.md                        # Project documentation

```
.env.example
```
PROJECT_NAME="FastAPI Modular Auth API"
VERSION="1.0.0"
API_V1_STR="/api/v1"
FRONTEND_URL="http://localhost:3000"

# PostgreSQL Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=auth_db
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/auth_db

# pgAdmin 4 Credentials
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=adminpassword

# JWT Security Configuration
JWT_SECRET_KEY=secretaccesskey
JWT_REFRESH_SECRET_KEY=secretrefresh
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=20
REFRESH_TOKEN_EXPIRE_DAYS=5
EMAIL_TOKEN_EXPIRE_MINUTES=20

# Email / SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=username
SMTP_PASSWORD=password
EMAILS_FROM_EMAIL=noreply@yourdomain.com
EMAILS_FROM_NAME="Auth System"
```
# Quick Start with Docker

```
git clone https://github.com/HimanshuKumarShahi/API_World.git

cd API_World
```
## Build and start the containers:
```
Run containers in background (detached mode)

docker compose up -d --build

View live FastAPI logs (to copy email verification/reset tokens)

docker logs -f fastapi_auth_backend

Stop containers
docker compose down

Stop containers and wipe database volumes (fresh start)

docker compose down -v
```
## Access the Application:

Swagger Docs: http://localhost:8000/docs

ReDoc UI: http://localhost:8000/redoc

pgAdmin 4 Dashboard: http://localhost:5050

# Managing Data with pgAdmin 4
Open http://localhost:5050 in your browser and log in with your pgAdmin credentials (admin@admin.com / adminpassword).

Click Add New Server:

General Tab: FastAPI DB.

## Connection Tab:

Host name/address: db

Port: 5432

Maintenance database: auth_db

Username: postgres

Password: supersecretpassword

Check Save password? and click Save.

#### Expand Servers ➔ FastAPI DB ➔ Databases ➔ auth_db ➔ Schemas ➔ public ➔ Tables to view the users and refresh_tokens tables.

# API Endpoints Overview
```
Authentication (/api/v1/auth)
POST /register — Register a new user account.

POST /verify-email — Verify account using email token.

POST /login — Log in with username/email and password.

POST /refresh — Rotate refresh token for a new access token.

POST /logout — Revoke active session token.

POST /forgot-password — Request a password reset email link.

POST /reset-password — Set a new password using reset token.

```
```
Users & Profiles (/api/v1/users)
GET /profile — Get currently logged-in user's private profile (Requires Bearer Token).

PATCH /profile — Update logged-in user's profile details (Requires Bearer Token).

GET /profile/{username} — Public profile lookup by username (No auth required).
```