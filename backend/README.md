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

- **Authentication** — Email/password login with JWT (access + refresh tokens),
  email verification via 6-digit code, password reset via email link
- **Student Workflow**
  - Create or join a group via invite code (max 3 members)
  - Select research area and preferred supervisors
  - Submit thesis proposals (1–3 topic options with file upload)
  - Track tasks assigned by supervisor with deadlines
  - Submit final thesis manuscript
- **Supervisor Workflow**
  - Accept/reject group preferences within capacity limits
  - Review and approve/reject proposals with feedback
  - Assign tasks with optional reference files
  - Approve final thesis or request revisions
- **Admin Workflow**
  - Manage semesters, supervisors, and research areas
  - Finalize supervisor assignments, handle capacity overrides
  - Publish/unpublish approved theses to the public Thesis Repository
  - Monitor at-risk groups (low member count / missed deadlines)
- **Notifications** — In-app + email alerts for deadlines, submissions,
  approvals, and escalations
- **Thesis Repository** — Browsable, searchable archive of approved and
  published theses

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
| Validation   | Pydantic                             |

---

## 📁 Project Structure

```
ProjectSphere/
├── alembic/                # Database migration scripts
│   ├── versions/
│   └── env.py
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Environment/config settings
│   ├── database.py          # DB session & engine setup
│   ├── models/               # SQLAlchemy models
│   ├── schemas/               # Pydantic request/response schemas
│   ├── routers/                # API route handlers (auth, group, thesis, admin, etc.)
│   ├── services/                # Business logic
│   └── utils/                    # JWT, hashing, email helpers
├── alembic.ini
├── requirements.txt
├── .env.example
└── README.md
```

> ⚠️ Adjust this tree to match your actual folder layout before pushing.

---

## ⚙️ Prerequisites

Before you start, make sure you have installed:

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

## 🚀 Getting Started (Local Setup)

### 1. Clone the repository

```bash
git clone https://github.com/<mahmudulhasan3>/ProjectSphere.git
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

Copy the example env file and fill in your own values:

```bash
cp .env.example .env
```

`.env` should contain:

```env
DATABASE_URL=postgresql://projectsphere_user:your_password@localhost:5432/projectsphere
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email (SMTP) config for verification/notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 6. Run database migrations

```bash
alembic upgrade head
```

### 7. Start the development server

```bash
uvicorn app.main:app --reload
```

The API will be live at:

```
http://127.0.0.1:8000
```

Interactive API docs (Swagger UI):

```
http://127.0.0.1:8000/docs
```

---

## 🔑 Authentication Flow

1. Register with a university email → verification email sent with 6-digit code
2. Verify email → account activated, welcome email sent
3. Login → receive **access token** (30 min) + **refresh token** (7 days,
   HTTP-only cookie)
4. Use `/auth/refresh` to silently get a new access token without re-login
5. Forgot password → reset link sent via email

---

## 🧪 Running Migrations (for future schema changes)

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Apply migrations
alembic upgrade head

# Roll back last migration
alembic downgrade -1
```

---

## 📌 Roadmap

- [x] Auth (JWT + email verification)
- [x] Student portal (group, proposal, tasks)
- [ ] Supervisor portal
- [ ] Admin portal
- [ ] AI-assisted duplicate proposal detection (rule-based)
- [ ] Thesis Repository (public browsing)

---

## 🤝 Contributing

This is currently a solo academic project. Suggestions and issues are welcome
via GitHub Issues.

---

## 📄 License

This project is licensed under the MIT License — feel free to use and modify
with attribution.

---

## 👤 Author

**Mahmudul Hasan** CSE Student, NITER | Aspiring AI Engineer GitHub:
[@mahmudulhasan3](https://github.com/mahmudulhasan3) LinkedIn:
[@mahmudulhasan03](https://www.linkedin.com/in/mahmudulhasan03/)
