# Prectice

Clinic desk rewrite (FastAPI + Nuxt 4 + Nuxt UI + PostgreSQL 15).

Replaces the daily path of the old **Next.js + PHP/MySQL** stack (`prectice` + `patient.quantumdental/api`) for pilot use. Old app stays for features not yet ported.

---

## Status: done vs left

### Done (Goes 1 → 4.5) — shippable v1 desk

| Go | What |
|----|------|
| **1** | Auth (JWT), multi-tenant `clinic_id`, patients, check-in/out, notes, desk summary |
| **2** | Doctors/services/schedules, appointments, slots, day calendar, status changes |
| **3** | Bills, money receipts, prescriptions + medicine templates, tasks |
| **4** | Aarogyam MySQL→Postgres import, indexes, `docker-compose.prod.yml` + Caddy |
| **4.5** | UX parity: teal desk shell, sidebar, header search/Add/Book, patients master–detail + timeline, 5-step book modal, keyboard shortcuts |

**Working locally today:** real Aarogyam data imported (~2k patients, appts, bills, Rx, tasks). Login break-glass `admin` / `admin123` or staff MySQL usernames/passwords.

### Not done yet (phase 2+)

| Area | Notes |
|------|--------|
| Treatment plans + public share `/p/...` | Still on old Next/PHP |
| Dental labs | Still on old app |
| WhatsApp inbox / sends | Still on old app |
| Google Calendar sync | Still on old app |
| Call / lead intelligence | Still on old app |
| Desk bot / MCP | Still on old app |
| Heavy reports / filter builder | Still on old app |
| SSO (Google) | Password + remember only for now |
| Mobile bottom-nav app | Desktop desk only in Nuxt |
| Warranty cards | Desk CRUD + WhatsApp send (templates settings later) |
| PDF Rx / media proxy polish | Not ported |
| Alembic migrations | `create_all` + SQL indexes for now |
| Automated backups | Ops still manual |

### Known gaps / polish later

- Billing/Rx create UI lives partly in older patient tabs; timeline is read + notes + check-in focused
- Calendar is day-board (not full month grid like old desk)
- Prod Postgres password with special URL characters must be URL-encoded in `DATABASE_URL` (compose builds it from env — avoid exotic chars or encode)
- Rotate MySQL password if it was shared in chat; restrict DB host by IP

---

## Repo layout

```
apps/api/                 FastAPI (Python 3.12)
  app/                    routes, models, auth
  scripts/
    seed.py               demo data
    import_mysql.py       Aarogyam (or any clinic_id) import
    apply_indexes.py/.sql
apps/web/                 Nuxt 4 + Nuxt UI
docker-compose.yml        local API+Postgres (optional)
docker-compose.prod.yml   VPS default: db + api + caddy (no Vue — UI on Vercel)
docker-compose.full.yml   optional VPS UI: also builds Nuxt web
Caddyfile                 API-only hosts (prod)
Caddyfile.full            full stack (proxies UI to web)
.env.production.example   template for VPS secrets
docs/deploy-vercel-vps.md Vercel + VPS API deploy notes
```

---

## Local run (dev machine)

```bash
# Postgres 15 running; apps/api/.env → DATABASE_URL for local user
cd apps/api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

cd apps/web && pnpm install && pnpm dev
```

Open http://127.0.0.1:3000 → desk.

Re-import Aarogyam:

```bash
cd apps/api && source .venv/bin/activate
export MYSQL_HOST=... MYSQL_USER=... MYSQL_PASSWORD=... MYSQL_DATABASE=prctc_mngmt_pt
python scripts/import_mysql.py --clinic-id 1 --replace --keep-admin
python scripts/apply_indexes.py
```

---

## Deployment TLDR (for you or another agent)

**Yes — another agent can deploy this with Docker** if the VPS has Docker + Compose, a domain pointing at the VPS, and ports 80/443 open. Compose file is ready; empty DB boots, then import data.

### Vercel frontend + VPS API

See **[docs/deploy-vercel-vps.md](docs/deploy-vercel-vps.md)**.

| Compose file | Services |
|--------------|----------|
| **`docker-compose.prod.yml`** (default) | `db` + `api` + `caddy` — **no Vue** |
| `docker-compose.full.yml` | adds Nuxt `web` (optional; recreate later if needed) |

A naïve “deploy `docker-compose.prod.yml`” will **not** build the frontend.

### 1) On the VPS (all-in-one Docker)

```bash
# clone/copy this repo onto the VPS
cd prectice-pin
cp .env.production.example .env.production
```

Edit `.env.production` (required):

| Variable | Example |
|----------|---------|
| `POSTGRES_PASSWORD` | strong password (prefer alphanumeric) |
| `JWT_SECRET` | long random ≥32 chars |
| `CADDY_DOMAIN` | `desk.yourdomain.com` (DNS A record → VPS IP) |
| `CADDY_EMAIL` | for Let’s Encrypt |
| `CORS_ORIGINS` | `https://desk.yourdomain.com` |

### 2) Start stack

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Services: `db` (internal only) · `api` (:8000 inside) · `web` (:3000 inside) · `caddy` (:80/:443 public).

Check: `https://CADDY_DOMAIN/api/health` → `{"ok":true,...,"go":"4.5"}`.

### 3) Import clinic data (after containers are healthy)

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec \
  -e MYSQL_HOST=db.pratikp.com \
  -e MYSQL_USER=... \
  -e MYSQL_PASSWORD=... \
  -e MYSQL_DATABASE=prctc_mngmt_pt \
  api python scripts/import_mysql.py --clinic-id 1 --replace --keep-admin

docker compose -f docker-compose.prod.yml --env-file .env.production exec \
  api python scripts/apply_indexes.py
```

Login: `admin` / `admin123` (break-glass) or real staff usernames from MySQL.

### 4) What the deploying agent must verify

- [ ] Docker Engine + Compose plugin installed on VPS  
- [ ] DNS `CADDY_DOMAIN` → VPS  
- [ ] Firewall allows 80/443  
- [ ] `.env.production` filled (never commit it)  
- [ ] `docker compose ... up -d --build` succeeds  
- [ ] `/api/health` OK  
- [ ] MySQL import run once (VPS must reach MySQL host; MySQL must allow VPS IP or use TLS as script does)  
- [ ] Hard-refresh browser; sign in; open Patients  

### What will *not* auto-happen

- Import does not run on `up` — must exec import once  
- Old Next/PHP app is separate — leave it running for labs/WA/plans  
- No CI/CD in repo yet — deploy is manual compose on VPS  

---

## Parallel run (recommended)

| Use | App |
|-----|-----|
| Daily desk (patients, calendar, bills, Rx, tasks) | **This Nuxt app** |
| Treatment plans, labs, WA inbox, bot, reports | **Old Next + PHP** until phase 2 |

---

## Suggested next work

1. Deploy VPS + import (ops)  
2. Staff trial day → fix UX nits they call out  
3. Phase 2 feature order: treatment plans → labs → WhatsApp → reports  

---

## Stack versions (pinned in repo)

- Python 3.12 / FastAPI / SQLAlchemy 2 / Postgres 15  
- Nuxt 4.5 / Nuxt UI 4 / pnpm  
- Caddy 2 for TLS reverse proxy  
