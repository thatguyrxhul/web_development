# DevBoard

A project-management platform (Jira/Trello-style) built with Django. Teams create
projects, assign tasks through a four-stage workflow, and track everything on a
kanban board with a project activity feed — all guarded by project-level
authorization.

Built for the Verveox Technologies take-home assessment.

## Features

- **Email-based authentication** (`USERNAME_FIELD = email`) with session logins
- **Three roles:** Administrator, Project Manager, Developer
- **Projects** with manager, members, status, priority, start date and deadline
- **Tasks** with assignee, priority, deadline, labels, comments and attachments
- **Four-stage workflow:** Todo → In Progress → In Review → Completed (one step at a time, enforced server-side)
- **Kanban board** per project with live column counts
- **Role-scoped "My Tasks"** with counts, overdue highlighting and filters
- **Dashboard** with workload/status charts and recent activity
- **Project activity feed** visible only to project members
- **Toast notifications** for success/error feedback (auto-dismiss)
- **Responsive layout** (desktop sidebar collapses to a mobile top bar)
- **Demo seed command** that populates realistic data in one line

## Roles & permissions

| Capability | Admin | Project Manager | Developer |
|---|---|---|---|
| View all projects / users | ✔ | — | — |
| Create & edit projects | ✔ | own projects only | — |
| Manage project members | ✔ | own projects only | — |
| Create / edit / assign tasks | ✔ | own projects only | — |
| Create & edit task labels | ✔ | ✔ | — (403) |
| Move a task through the workflow | ✔ | manager of its project | **assignee only** |
| Comment on a task | member/manager/admin of its project | ✔ | ✔ |
| User administration | ✔ | — | — |

## Core challenge: project-level authorization

Every query and mutating action passes through a single permission layer,
`projects/permissions.py`, so URL manipulation cannot leak data:

```python
can_access_project(user, project)   # admin OR project manager OR member  -> else 404
can_manage_project(user, project)   # admin OR project manager            -> else 404
can_edit_task(user, task)           # manager of project OR assignee      -> else 404
user_projects(user)                 # scoped project queryset per role
```

Design choices worth noting:

- **404 instead of 403 for object access.** Probing an ID reveals nothing —
  foreign projects and tasks "do not exist" for you. Role-level gates
  (e.g. a developer opening label management) return 403.
- **Denials are enforced in the view, not the template.** Hiding buttons is UX;
  the 404/403 is the security boundary.
- **Workflow transitions are validated on the server** (`VALID_NEXT` map in
  `tasks/views.py`). A forged POST that skips "In Review" is rejected with an
  error toast — the client cannot bypass the state machine.
- **Assignees must be project members.** Task creation looks the user up with
  `project_memberships__project=project`, so cross-project assignment 404s.

## Task workflow

```
TODO ──► IN_PROGRESS ──► IN_REVIEW ──► COMPLETED
   └── any other target = rejected ("Invalid transition: ...")
```

## Tech stack

- **Backend:** Django 6.1.2 (Python 3.13), gunicorn
- **Database:** SQLite locally (zero-config) · PostgreSQL on Render · MySQL/MariaDB 10.11+ opt-in via `DJANGO_DB_ENGINE`
- **Frontend:** server-rendered Django templates, vanilla JS, custom CSS design system (no framework)
- **Static:** WhiteNoise (compressed, collected to `STATIC_ROOT`)
- **Testing:** Django test framework (23 tests)

## Architecture

```
Request → URLconf → View (login_required → permission layer → business logic)
       → ActivityLog.log(...)   (every mutation is audited)
       → Template (scoped context only)
```

| App | Responsibility |
|---|---|
| `accounts` | Custom `User` (email login, roles), dashboards, user admin, seed command |
| `projects` | `Project`, `ProjectMember`, **permission layer** + authorization tests |
| `tasks` | `Task`, `Label`, comments, attachments, kanban, workflow + tests |
| `activity` | Project-scoped activity feed |
| `devboard` | Settings, root URLs, WSGI (Render boot hook: migrate + seed) |

Key files: `projects/permissions.py` (authorization), `tasks/views.py`
(workflow + role scoping), `devboard/settings.py` (env-driven config),
`devboard/wsgi.py` (deployment boot init), `accounts/management/commands/seed_demo.py`.

## Local setup

Prerequisites: Python 3.13, Git. No database server needed — the default is SQLite.

```powershell
git clone https://github.com/thatguyrxhul/web_development.git
cd web_development

python -m venv virtualm
virtualm\Scripts\activate          # Windows
pip install -r requirements.txt

py manage.py migrate
py manage.py seed_demo             # idempotent demo data

py manage.py runserver             # http://127.0.0.1:8000
py manage.py test                  # 23 tests, all green
```

Prefer MySQL/MariaDB? The `mysql` branch in `settings.py` is kept: set
`DJANGO_DB_ENGINE=mysql` and `pip install mysqlclient` — requires MariaDB 10.11+
(Django 6.1 dropped older versions).

## Demo credentials

| Role | Email | Password |
|---|---|---|
| Administrator | `rahul@gmail.com` | `rahul@123` |
| Project Manager | `martin@test.com` | `martin@123` |
| Project Manager | `priya@test.com` | `priya@123` |
| Developer | `arjun@test.com` | `arjun@123` |
| Developer | `sneha@test.com` | `sneha@123` |

Tip: `sneha` is a member of *DevBoard Platform* only — opening the *Client
Portal* project by hand-typed URL as `sneha` returns 404 (live proof of
project-level authorization).

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | insecure dev key | **Set your own in production** |
| `DJANGO_DEBUG` | `1` | `0` disables debug, enables secure cookies/HSTS |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated hosts (use `.onrender.com` on Render) |
| `DJANGO_DB_ENGINE` | `sqlite3` | `sqlite3` \| `postgresql` \| `mysql` (MariaDB 10.11+) |
| `DJANGO_DB_NAME` / `DJANGO_DB_USER` / `DJANGO_DB_PASSWORD` / `DJANGO_DB_HOST` / `DJANGO_DB_PORT` | — | PostgreSQL connection (used when engine = `postgresql`) |
| `SEED_DEMO` | `1` | On Render, seed demo data at boot (`0` to skip) |
| `RENDER` | set by Render | Triggers migrate+seed boot hook in `wsgi.py` |

Generate a production secret key:

```powershell
py -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Deployment (Render)

1. Push the repository to GitHub and set it to **Public**.
2. On Render: **New → Web Service** → import the repository.
3. Plan: **Free**. Build command: `pip install -r requirements.txt`.
   Start command: `gunicorn devboard.wsgi`.
4. **New → PostgreSQL → Free**, in the **same region** as the web service.
5. On the web service **Environment** tab add:

   | Key | Value |
   |---|---|
   | `DJANGO_SECRET_KEY` | generated key (see above) |
   | `DJANGO_DEBUG` | `0` |
   | `DJANGO_ALLOWED_HOSTS` | `.onrender.com` |
   | `DJANGO_DB_ENGINE` | `postgresql` |
   | `DJANGO_DB_NAME` / `DJANGO_DB_USER` / `DJANGO_DB_PASSWORD` / `DJANGO_DB_HOST` / `DJANGO_DB_PORT` | copy from the PostgreSQL instance's *Connections* info (use the **internal** host) |

6. Deploy. On boot, `wsgi.py` runs `migrate` + `seed_demo` automatically
   (the free plan has no shell — this is why they run at boot).
7. Verify in a private window: login as each role, and confirm a foreign-project
   URL returns 404 on the live site.

Notes for the free tier:

- The web service **spins down after ~15 min idle** — first request takes ~1 min (cold start).
- PostgreSQL instances on the free plan are **removed after 30 days** — recreate
  the database, re-enter the same env-var names, redeploy: migrations and seed
  re-run at boot and the app URL does not change.
- The disk is **ephemeral**: uploaded attachments are demo-only locally (see
  Security & limitations).

## Testing

```powershell
py manage.py test
```

- `projects/tests.py` — 13 authorization tests (foreign-URL 404s, role-scoped
  lists, workflow attempts, role gates, inactive login).
- `tasks/tests.py` — 10 tests (valid/invalid/skipped transitions + toast message,
  non-assignee 404, per-role My Tasks scoping, task-creation guards).

## Security & edge-case handling

- Secrets and hosts read from environment variables (nothing sensitive committed)
- Object-level denial via **404** (no existence leak); role gates via **403**
- `@login_required` on every view; `LOGIN_URL = 'login'`
- All forms POST with CSRF; outputs escaped (`escapejs`, `textContent`) to block XSS
- Server-side workflow state machine (client cannot skip stages)
- Assignee must be a member of the task's project
- Password validators + inactive accounts cannot log in
- Duplicate labels surface an error toast; overdue tasks are highlighted;
  empty states include helpful calls-to-action
- Secure cookies + HSTS when `DEBUG=0`; WhiteNoise serves hashed static files

**Known limitation:** uploaded attachments live on the server disk — fine locally
and acceptable for a demo, but production would move media to object storage
(e.g. S3), and the Render free disk is ephemeral.

## Project structure

```
devboard/
├── accounts/                  # Custom User (email login), roles, dashboards, user admin
│   ├── management/commands/seed_demo.py
│   ├── templates/accounts/    # base, login, dashboard, user list/create
│   ├── models.py  views.py  urls.py  tests.py
├── activity/                  # Project activity feed (member-scoped)
│   └── templates/activity/
├── projects/                  # Projects, members, permission layer
│   ├── permissions.py         # can_access / can_manage / can_edit / user_projects
│   ├── templates/projects/    # list, form, detail
│   ├── models.py  views.py  urls.py  tests.py
├── tasks/                     # Tasks, labels, kanban, comments, attachments
│   ├── templates/tasks/       # my_tasks, task form/detail, kanban, labels
│   ├── models.py  views.py  urls.py  tests.py
├── devboard/                  # settings.py, urls.py, wsgi.py (Render boot hook)
├── static/
│   ├── css/style.css          # design system
│   └── img/
├── requirements.txt
└── README.md
```

## Screen recording

**Recording:** `https://www.dropbox.com/scl/fi/y4tbvjv78c5rufsucfcns/devboard-demo.mp4?rlkey=qws39tsdmwjlt3y1fwfeu34b9&st=7eug31g0&e=1&dl=0`

## Live deployment

`https://devboard-eez9.onrender.com/`

## AI usage policy

AI tools were used strictly as a development aid — drafting, debugging and
reviewing code — as permitted by the assessment brief. All architecture, feature
design, database decisions and explanations in this repository are my own work,
and I can explain every part of this codebase.

---

**Author:** `RAHULRAJ P`