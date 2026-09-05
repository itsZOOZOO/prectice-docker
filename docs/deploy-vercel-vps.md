# Deploy: Nuxt on Vercel + API/DB on VPS Docker

Trial layout (no second Docker stack):

| Host | Role |
|------|------|
| `https://*.vercel.app` | Nuxt frontend |
| `https://api.dental.navapp.in` | FastAPI only (same compose) |
| `https://dental.navapp.in` | Existing Docker Nuxt + API (rollback) |
| Postgres | Same `db` container |

## Do not create a new Docker stack

Update the **existing** `docker-compose.prod.yml` deploy: new Caddy host + CORS. Same `api` + `db` + `web`.

---

## 1) DNS

Add **A** (or CNAME) for `api.dental.navapp.in` → same VPS IP as `dental.navapp.in`.

---

## 2) VPS `.env.production` (edit, then recreate)

```env
CADDY_DOMAIN=dental.navapp.in
CADDY_API_DOMAIN=api.dental.navapp.in
CADDY_EMAIL=you@example.com

CORS_ORIGINS=https://dental.navapp.in
CORS_ORIGIN_REGEX=https://.*\.vercel\.app$
```

Then:

```bash
cd /path/to/prectice-pin
git pull
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Smoke:

```bash
curl -sS https://api.dental.navapp.in/api/health
# expect {"ok":true} or similar
```

---

## 3) Vercel (frontend only)

1. Import this GitHub repo in Vercel.
2. **Root Directory:** `apps/web`
3. Framework: Nuxt (auto).
4. Env var (Production + Preview):

| Name | Value |
|------|--------|
| `NUXT_PUBLIC_API_BASE` | `https://api.dental.navapp.in/api` |

5. Deploy. Open the `*.vercel.app` URL → login against VPS API.

Optional later: point `dental.navapp.in` (or `app.…`) at Vercel; keep Docker `web` until you are happy.

---

## 4) Checklist

- [ ] DNS for `api.dental.navapp.in`
- [ ] VPS env + compose rebuild
- [ ] `curl https://api.dental.navapp.in/api/health`
- [ ] Vercel project root = `apps/web`
- [ ] `NUXT_PUBLIC_API_BASE` set
- [ ] Login works from Vercel URL

Rollback: use `https://dental.navapp.in` (unchanged all-in-one host).
