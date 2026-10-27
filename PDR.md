# Project Design & Requirements Document (PDR)
**Project Name:** FastAPI Modular Auth & Core Backend  
**Architecture Pattern:** Domain-Driven Modular Architecture (Router $\rightarrow$ Controller/Service $\rightarrow$ Repository/Model)  
**Database Engine:** PostgreSQL (via Docker / `justPostgres`)  

---

## 1. Database Selection & `justPostgres` Analysis

### 1.1 PostgreSQL vs. MongoDB for Authentication & Modular Apps
**Recommendation: Go with PostgreSQL.**

Here is why PostgreSQL is the superior choice for your use case:
1. **Strict Data Integrity & ACID Compliance:** Authentication systems deal with sensitive state changes (e.g., verifying emails, revoking refresh tokens, resetting passwords). Relational guarantees prevent race conditions and orphaned states.
2. **Relational Scalability for Future APIs:** As you add new modules (e.g., E-commerce, Blogs, SaaS Subscriptions, or Social graphs), almost everything links back to `user_id` via Foreign Keys. PostgreSQL handles complex joins and relational constraints natively.
3. **JSONB Support (Best of Both Worlds):** If a future module needs unstructured, MongoDB-like flexible documents, PostgreSQL's `JSONB` data type allows you to store, index, and query NoSQL documents right alongside your relational tables.

### 1.2 Understanding Hitesh Sir's `justPostgres` Repository
**Repository:** `https://github.com/hiteshchoudhary/justPostgres.git`

* **What it is:** `justPostgres` is a lightweight, self-hosted PostgreSQL control plane/hub. Unlike heavy Backend-as-a-Service (BaaS) platforms like Supabase (which force you to run their auth, edge functions, and storage), `justPostgres` focuses **strictly on the database**.
* **Why it pairs perfectly with your project:** Because `justPostgres` intentionally omits a built-in user-auth service ("Not a BaaS. There is no user-auth service..."), **building your own custom FastAPI Auth & API backend is the exact way `justPostgres` is meant to be used!**
* **Key Features You Get from `justPostgres`:**
  * **Multi-Project Hub:** Spin up isolated PostgreSQL 16/17/18 databases in seconds with a single click.
  * **Connection Pooling:** Gives you both a direct connection string (for migrations like Alembic) and a transaction-pooled connection string (so FastAPI async workers never exhaust DB connections).
  * **Database Branching & Point-in-Time Restore:** You can fork your database to test a new FastAPI module migration safely and throw the branch away afterward.
  * **Built-in Table View:** Inspect your `users` and `tokens` tables directly in its UI without needing pgAdmin or DBeaver.

#### How to use Docker for your DB:
* **Local Development (Lightweight):** Use a standard `docker-compose.yml` running `postgres:17-alpine` and `redis:alpine` on your laptop for low RAM usage.
* **Staging / ProductionVPS (or Local DB Hub):** Run `justPostgres` on your Docker daemon/VPS, create a new project inside its dashboard, and copy the **Connection String** into your FastAPI `.env` file (`DATABASE_URL=postgresql+asyncpg://...`).

---

## 2. Scalable Modular Directory Structure

Instead of grouping files by type (putting *all* routes in one folder and *all* models in another), we group by **Domain/Feature** (`src/modules/`). 

**Why?** When you want to add a `blogs`, `payments`, or `notifications` API in the future, you simply create a new folder inside `src/modules/` without cluttering your existing auth code.

```text
fastapi-modular-backend/
├── docker-compose.yml          # Postgres, Redis (optional), and FastAPI container setup
├── Dockerfile                  # Production-ready multi-stage Python image
├── .env.example                # Environment variables template
├── requirements.txt            # Project dependencies (or pyproject.toml)
├── alembic.ini                 # Database migration configuration
├── alembic/                    # Auto-generated DB schema migrations
│
└── src/
    ├── main.py                 # FastAPI app initialization, CORS, Global Exception Handlers
    │
    ├── core/                   # Global application configurations & utilities
    │   ├── config.py           # Pydantic BaseSettings reading from .env
    │   ├── database.py         # Async SQLAlchemy engine, SessionLocal, Base declarative
    │   ├── security.py         # JWT creation/decoding, Argon2/Bcrypt password hashing
    │   ├── exceptions.py       # Standardized HTTP Exceptions (401, 403, 404, 400)
    │   └── mail.py             # Async SMTP / Email sending helper (FastAPI-Mail / Resend)
    │
    └── modules/                # FEATURE MODULES (Add future APIs here!)
        ├── auth/
        │   ├── router.py       # API Endpoints (/register, /login, /logout, etc.)
        │   ├── controller.py   # Business logic & orchestration
        │   ├── models.py       # Auth-specific DB tables (RefreshTokens, VerificationCodes)
        │   ├── schemas.py      # Pydantic Request & Response validation models
        │   ├── dependencies.py # get_current_user, require_verified_user injectors
        │   └── utils.py        # OTP generator, token hash helpers
        │
        ├── users/
        │   ├── router.py       # API Endpoints (/profile/{username}, /me)
        │   ├── controller.py   # Profile fetching and updating logic
        │   ├── models.py       # User DB Table
        │   └── schemas.py      # UserProfilePublic, UserProfilePrivate, UserUpdate
        │
        └── [future_module]/    # e.g., products/, orders/, posts/
            ├── router.py
            ├── controller.py
            ├── models.py
            └── schemas.py
```

---

## 3. Database Models & Requirements

We use **SQLAlchemy 2.0 (Async)** with `asyncpg` for non-blocking database queries.

### 3.1 `User` Model (`src/modules/users/models.py`)
Stores core identity and profile metadata.
| Field | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key, Default `uuid4` | Prevents ID enumeration attacks on URLs |
| `username` | `String(50)` | Unique, Indexed, Not Null | Used for `/profile/{username}` lookup |
| `email` | `String(255)`| Unique, Indexed, Not Null | Primary login & communication identifier |
| `password_hash`| `String(255)`| Not Null | Argon2 or Bcrypt hashed password |
| `full_name` | `String(100)`| Nullable | Display name on user profile |
| `bio` | `Text` | Nullable | Short user biography |
| `avatar_url` | `String(500)`| Nullable | Link to profile picture |
| `is_verified` | `Boolean` | Default `False` | Becomes `True` after `/emailverify` |
| `is_active` | `Boolean` | Default `True` | Soft-ban or account deactivation flag |
| `created_at` | `DateTime` | Default `func.now()` | Account creation timestamp |
| `updated_at` | `DateTime` | OnUpdate `func.now()` | Last modification timestamp |

### 3.2 `RefreshToken` Model (`src/modules/auth/models.py`)
Since JWTs are stateless, you cannot truly "logout" or invalidate a compromised session without tracking refresh tokens in the database.
| Field | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | Unique token record ID |
| `user_id` | `UUID` | ForeignKey(`users.id`, CASCADE) | Owner of the session |
| `token_hash` | `String(255)`| Unique, Indexed, Not Null | SHA-256 hash of the refresh token |
| `expires_at` | `DateTime` | Not Null | Expiration timestamp (e.g., +7 days) |
| `is_revoked` | `Boolean` | Default `False` | Set to `True` on `/logout` or password reset |
| `created_at` | `DateTime` | Default `func.now()` | Session start time |

### 3.3 `VerificationToken` Model (`src/modules/auth/models.py`)
Handles one-time tokens/OTPs for both **Email Verification** and **Forgot Password**.
| Field | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `UUID` | Primary Key | Record ID |
| `user_id` | `UUID` | ForeignKey(`users.id`, CASCADE) | Associated user |
| `token_hash` | `String(255)`| Indexed, Not Null | Hashed OTP or URL token |
| `purpose` | `Enum` | `'EMAIL_VERIFY'`, `'PASSWORD_RESET'`| Prevents using an email token to reset a password |
| `expires_at` | `DateTime` | Not Null | Short lifespan (e.g., 15 minutes) |
| `is_used` | `Boolean` | Default `False` | Prevents replay attacks |

---

## 4. Pydantic Schemas (Validation Layer)

Pydantic V2 enforces strict input validation before any request reaches your controller.

* **Auth Schemas (`src/modules/auth/schemas.py`):**
  * `RegisterRequest`: `username` (alphanumeric regex, 3-30 chars), `email` (`EmailStr`), `password` (min 8 chars, 1 uppercase, 1 number), `full_name` (optional).
  * `LoginRequest`: `identifier` (accepts either email or username), `password`.
  * `TokenResponse`: `access_token`, `refresh_token`, `token_type: "bearer"`.
  * `VerifyEmailRequest`: `email` (`EmailStr`), `token` (6-digit OTP or URL token string).
  * `ForgotPasswordRequest`: `email` (`EmailStr`).
  * `ResetPasswordRequest`: `email` (`EmailStr`), `token` (string), `new_password` (min 8 chars).
* **User Schemas (`src/modules/users/schemas.py`):**
  * `UserPublicProfileResponse`: `username`, `full_name`, `bio`, `avatar_url`, `created_at` (Excludes email, password_hash, and internal flags).
  * `UserPrivateProfileResponse`: Inherits `UserPublicProfileResponse` + includes `id`, `email`, `is_verified`.

---

## 5. API Routes, Controllers, and Detailed Working Logic

In FastAPI, **Routers** handle HTTP requests/responses and dependency injection, while **Controllers** contain pure business logic and database queries.

### 5.1 Register User
* **Route:** `POST /api/v1/auth/register`
* **Status Code:** `201 Created`
* **Controller (`AuthController.register_user`) Working Logic:**
  1. Check if `email` or `username` already exists in the `users` table (case-insensitive query). If found, raise `409 Conflict`.
  2. Hash the plain-text password using `pwd_context.hash(password)` (Argon2/Bcrypt).
  3. Create a new `User` instance with `is_verified=False` and flush to DB.
  4. Generate a cryptographically secure 6-digit OTP or 32-byte URL-safe token (`secrets.token_urlsafe(32)`).
  5. Hash the token with SHA-256 and store it in `verification_tokens` with `purpose="EMAIL_VERIFY"` and `expires_at = now() + 15 minutes`.
  6. Trigger FastAPI `BackgroundTasks` to send the verification email asynchronously so the API responds immediately without waiting for the SMTP server.
  7. Commit transaction and return success message.

### 5.2 Email Verification
* **Route:** `POST /api/v1/auth/emailverify`
* **Status Code:** `200 OK`
* **Controller (`AuthController.verify_email`) Working Logic:**
  1. Find the user by `email`. If not found, raise `400 Bad Request`. If `user.is_verified` is already `True`, return early with a message `"Email already verified"`.
  2. Hash the incoming `token` and query `verification_tokens` matching `user_id`, `token_hash`, `purpose="EMAIL_VERIFY"`, and `is_used=False`.
  3. Check if the token exists and `expires_at > datetime.now(timezone.utc)`. If invalid or expired, raise `400 Bad Request ("Invalid or expired verification token")`.
  4. Update `user.is_verified = True` and `verification_token.is_used = True`.
  5. Commit changes to PostgreSQL and return `"Email verified successfully. You may now log in."`

### 5.3 Login User
* **Route:** `POST /api/v1/auth/login`
* **Status Code:** `200 OK`
* **Controller (`AuthController.login_user`) Working Logic:**
  1. Query the `users` table where `email == identifier` OR `username == identifier`.
  2. If no user is found, or `verify_password(plain_password, user.password_hash)` returns `False`, raise `401 Unauthorized ("Invalid credentials")`. *(Always use the same error message to prevent username/email enumeration).*
  3. Check if `user.is_verified` is `False`. If so, raise `403 Forbidden ("Please verify your email address before logging in")`.
  4. Check if `user.is_active` is `False`. If so, raise `403 Forbidden ("Account disabled")`.
  5. Generate a short-lived **Access Token** (JWT signed with `HS256`, payload: `{"sub": str(user.id), "username": user.username, "type": "access"}`, expiry: `15 minutes`).
  6. Generate a long-lived **Refresh Token** (JWT or random opaque string, expiry: `7 days`).
  7. Hash the Refresh Token and save a record in the `refresh_tokens` table.
  8. Return the `access_token` and `refresh_token` (or set the `refresh_token` in an `HttpOnly`, `Secure`, `SameSite=Lax` cookie).

### 5.4 Logout User
* **Route:** `POST /api/v1/auth/logout`
* **Dependencies:** Requires valid `access_token` (`Depends(get_current_user)`) and the `refresh_token`.
* **Status Code:** `200 OK`
* **Controller (`AuthController.logout_user`) Working Logic:**
  1. Receive the user's `refresh_token` from the request body or `HttpOnly` cookie.
  2. Hash the `refresh_token` and look it up in the `refresh_tokens` table for the current `user_id`.
  3. Set `is_revoked = True` (or delete the row from the database).
  4. Commit to DB and clear auth cookies on the response object. Even if someone steals the refresh token later, they cannot generate new access tokens.

### 5.5 Forgot Password
* **Route:** `POST /api/v1/auth/forgotpassword`
* **Status Code:** `200 OK`
* **Controller (`AuthController.forgot_password`) Working Logic:**
  1. Look up the user by `email`.
  2. **Security Rule:** If the email *does not* exist in the database, **do not** return a 404 error. Return the exact same `200 OK` message (`"If an account with that email exists, a password reset link has been sent."`) to prevent attackers from scraping registered emails.
  3. If the user *does* exist, invalidate any previous unused `PASSWORD_RESET` tokens for that user.
  4. Generate a new secure reset token/OTP, hash it, and store it in `verification_tokens` with `purpose="PASSWORD_RESET"` and `expires_at = now() + 15 minutes`.
  5. Dispatch the password reset email via `BackgroundTasks`.

### 5.6 Reset Password
* **Route:** `POST /api/v1/auth/resetpassword`
* **Status Code:** `200 OK`
* **Controller (`AuthController.reset_password`) Working Logic:**
  1. Find the user by `email`.
  2. Hash the incoming reset `token` and query `verification_tokens` for a matching, unused, non-expired token with `purpose="PASSWORD_RESET"`.
  3. If invalid or expired, raise `400 Bad Request`.
  4. Hash the `new_password` and update `user.password_hash`.
  5. Mark the verification token as `is_used = True`.
  6. **Crucial Security Step:** Execute an `UPDATE` query on the `refresh_tokens` table for this `user_id`, setting `is_revoked = True` on **all** active sessions. This immediately logs out all other devices in case the account was compromised.
  7. Commit transaction and return `"Password reset successful"`.

### 5.7 User Details by Username (`/profile/{username}`)
* **Route:** `GET /api/v1/profile/{username}`
* **Dependencies:** Optional authentication (`Depends(get_optional_current_user)`).
* **Status Code:** `200 OK`
* **Controller (`UserController.get_profile_by_username`) Working Logic:**
  1. Query the `users` table for `username == username` and `is_active == True`.
  2. If no user is found, raise `404 Not Found ("User profile not found")`.
  3. **Smart Context Switching:**
     * If the requester is **logged in** AND `current_user.username == username` (viewing their own profile), serialize the data using `UserPrivateProfileResponse` (which returns their private details like `email` and verification status).
     * If the requester is a **guest** or **another user**, serialize the data using `UserPublicProfileResponse` (which strips sensitive fields and returns only `username`, `full_name`, `bio`, `avatar_url`, and `created_at`).

---

## 6. How to Add New Modules in the Future

Because of this modular design, adding a new feature (for example, a **Task Manager** or **Blog Posts** API) requires zero changes to your existing authentication logic:

1. **Create Module Folder:** Create `src/modules/posts/`.
2. **Define DB Model (`models.py`):** Create a `Post` model with `author_id = Column(UUID, ForeignKey("users.id"))`.
3. **Protect Endpoints (`router.py`):** Import `get_current_user` from `src.modules.auth.dependencies`:
   ```python
   from fastapi import APIRouter, Depends
   from src.modules.auth.dependencies import get_current_user
   from src.modules.users.models import User

   router = APIRouter(prefix="/posts", tags=["Posts"])

   @router.post("/")
   async def create_post(current_user: User = Depends(get_current_user)):
       # current_user is automatically validated, fetched from Postgres, and injected!
       return {"author": current_user.username}
   ```
4. **Register Router (`src/main.py`):** Add `app.include_router(posts_router, prefix="/api/v1")` in your main entry file.

---

## 7. Docker & Environment Blueprint

### 7.1 `docker-compose.yml` (Local Dev Stack)
If you aren't connecting to a remote `justPostgres` instance yet, this `docker-compose.yml` spins up PostgreSQL 17 and your FastAPI app locally:

```yaml
services:
  db:
    image: postgres:17-alpine
    container_name: fastapi_postgres_db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-fastapi_auth_db}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build: .
    container_name: fastapi_auth_backend
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./src:/app/src

volumes:
  postgres_data:
```

### 7.2 Required Python Packages (`requirements.txt`)
```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy[asyncio]>=2.0.35
asyncpg>=0.29.0
alembic>=1.13.2
pydantic[email]>=2.9.0
pydantic-settings>=2.5.0
pyjwt>=2.9.0
passlib[argon2]>=1.7.4
python-multipart>=0.0.12
fastapi-mail>=1.4.1
```

# 🎭 PDR: Jokes Module (`app/modules/jokes`) — API_World

## 1. Module Overview
The **Jokes Module** serves two purposes inside `API_World`:
1. **Zero-Auth Public Playground (Frontend Practice):** Anyone can fetch a random joke, browse paginated jokes, filter by category (`programming`, `dad_joke`, `pun`, `dark`, `one_liner`), or search by keyword without needing an access token.
2. **Authenticated Community Interaction (Full-Stack Practice):** Logged-in users (`Depends(get_current_user)`) can submit their own jokes, update/delete jokes they authored, and toggle **Like / Dislike** reactions on any joke.

---

## 2. Module Directory Structure
```text
app/modules/jokes/
├── __init__.py
├── models.py          # SQLAlchemy tables: Joke & JokeReaction
├── schemas.py         # Pydantic v2 schemas (Pagination, Create, Update, Response)
├── controller.py      # Business logic, random SQL selector, reaction toggler & DB seeder
└── router.py          # /api/v1/jokes HTTP endpoints