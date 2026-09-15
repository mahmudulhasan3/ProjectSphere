# ProjectSphere

**ProjectSphere** is a Student Project & Thesis Management System backend that
streamlines the entire academic thesis workflow — from group formation and
supervisor assignment to proposal submission, task tracking, and final thesis
publication.

Built for universities/departments to replace scattered email/paper-based thesis
coordination with a single structured platform for **Students**,
**Supervisors**, and **Admins**.

---

## ✨ Features

- **Authentication** — Email/password login with JWT access tokens, email
  verification via a 6-digit code (hashed at rest, with rate-limit lockout after
  repeated wrong attempts), password reset via email link, unverified accounts
  auto-delete after 24 hours
- **Student Workflow**
  - Create or join a group via invite code (max 3 members, must match
    department/level/term/section)
  - Select research area and rank 3 preferred supervisors
  - Submit thesis/project proposals (1–3 topic options with PDF upload)
  - Track tasks assigned by supervisor, submit evidence, view progress %
  - Chat with the assigned supervisor
  - Submit final thesis/project manuscript
  - Browse published Thesis Repository and Project Repository (separate)
- **Supervisor Workflow**
  - View assigned groups
  - Review and approve/reject proposals with feedback, or assign a topic
    directly after repeated rejection
  - Assign tasks with deadlines and optional reference files
  - Review task submissions (verify / request changes)
  - Chat with student groups
  - Approve final thesis, request revision, or escalate to admin
- **Admin Workflow**
  - Create supervisor accounts (email invite to set their own password)
  - Bulk-import students via CSV
  - Manage semesters (deadlines, auto-delete period) — one active at a time
  - Resolve supervisor assignment conflicts, grant capacity overrides
  - Manage groups: lock/unlock, approve leaves, reallocate students, assign
    leftover (ungrouped) students, extend deadlines
  - Resolve escalated thesis cases, publish/unpublish approved work
  - Deactivate/reactivate any student or supervisor account
- **Notifications** — Email alerts for task deadlines (warning + overdue),
  proposal decisions, new tasks, submissions, group at-risk status, and thesis
  auto-delete warnings, sent via an hourly background job
- **Thesis & Project Repository** — Two separate, browsable archives of
  published work

---

## 🛠️ Tech Stack

| Component    | Technology                           |
| ------------ | ------------------------------------ |
| Language     | Python 3.12                          |
| Framework    | FastAPI                              |
| Database     | PostgreSQL                           |
| ORM          | SQLAlchemy 2.x                       |
| Migrations   | Alembic                              |
| Auth         | PyJWT (JWT), pwdlib (Argon2 hashing) |
| PDF Handling | pypdf                                |
| Validation   | Pydantic / pydantic-settings         |

---

## 📁 Project Structure

```
ProjectSphere/
├── alembic/
│   ├── versions/
│   └── env.py
│
├── app/
│   ├── main.py
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   └── services/
│
├── alembic.ini
├── requirements.txt
├── .env.example
└── README.md
```

> Everything lives at the repo root — all internal imports use the `app...`
> path (not `backend.app...`). Run all commands below from the **repo root**
> (`ProjectSphere/`).

---

## ⚙️ Prerequisites

- **Python 3.12+**
- **PostgreSQL** (installed and running locally) →
  [Download here](https://www.postgresql.org/download/)
- **Git**

---

## 🌐 Live API

ProjectSphere backend is deployed on Render.

- **Base URL:** https://projectsphere-39m1.onrender.com
- **Swagger UI:** https://projectsphere-39m1.onrender.com/docs
- **Health Check:** https://projectsphere-39m1.onrender.com/

---

## 🚀 Getting Started (Local Setup)

### 1. Clone the repository

```bash
git clone https://github.com/mahmudulhasan3/ProjectSphere.git
cd ProjectSphere
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL database

Open `psql` or any PostgreSQL client and create a database:

```sql
CREATE DATABASE projectsphere;
CREATE USER projectsphere_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE projectsphere TO projectsphere_user;
```

### 5. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` — these are the **actual** variables the app reads
(`app/core/config.py`):

```env
# Database
DATABASE_URL=postgresql://projectsphere_user:your_password@localhost:5432/projectsphere

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Email Restriction
ALLOWED_EMAIL_DOMAIN=niter.edu.bd

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com

# Frontend
FRONTEND_URL=http://localhost:8000
```

> Never commit a real `.env` file — only `.env.example` should be in git.

### 6. Run database migrations

```bash
python -m alembic upgrade head
```

### 7. Start the development server

```bash
uvicorn app.main:app --reload
```

The API will be live at:

http://127.0.0.1:8000

Interactive API docs (Swagger UI, grouped by Student / Supervisor / Admin):

http://127.0.0.1:8000/docs

---

## 🔑 Authentication Flow

1. Register with a university email → a 6-digit verification code is emailed
2. Verify email with the code (5 wrong attempts locks verification for 15
   minutes) → account activated, welcome email sent
3. Login → receive a JWT **access token**; send it as
   `Authorization: Bearer <token>` on every subsequent request
4. Token expires after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` — log in again to get a
   new one (there is currently no refresh-token flow)
5. Forgot password → reset link sent via email
6. Accounts that never verify within 24 hours are automatically deleted by the
   hourly background job

---

## 🧪 Running Migrations (for future schema changes)

Run all of these from the **repo root**:

```bash
# Generate a new migration after model changes
python -m alembic revision --autogenerate -m "describe your change"

# Apply migrations
python -m alembic upgrade head

# Roll back last migration
python -m alembic downgrade -1
```

> ⚠️ Always `cat` a freshly generated migration file before running
> `upgrade head` — if a new model wasn't imported in `alembic/env.py`,
> autogenerate silently produces an **empty** migration that does nothing.

---

## 📌 Status

- [x] Auth (JWT + email verification, hashed codes, rate-limit lockout,
      auto-delete unverified accounts)
- [x] Student portal (group, proposal, tasks, chat, final submission)
- [x] Supervisor portal (proposal review, task management, thesis review)
- [x] Admin portal (supervisors, students, groups, semesters, publishing,
      account management)
- [x] Rule-based duplicate proposal-title detection (no ML)
- [x] Thesis Repository + Project Repository (separate, public browsing)
- [ ] Automated tests
- [ ] Frontend (not started)

---

## 🤝 Contributing

This is currently a group academic project. Suggestions and issues are welcome
via GitHub Issues.

---

## 📄 License

This project is licensed under the MIT License — feel free to use and modify
with attribution.

## 👤 Backend Author

**Mahmudul Hasan** CSE Student, NITER | Aspiring AI Engineer GitHub:
[@mahmudulhasan3](https://github.com/mahmudulhasan3) LinkedIn:
[@mahmudulhasan03](https://www.linkedin.com/in/mahmudulhasan03/)
