# Deploy: Nuxt on Vercel + API/DB on VPS Docker

| Host | Role |
|------|------|
| Vercel | Nuxt frontend |
| `https://api.dental.navapp.in` | FastAPI |
| Postgres | Docker `db` volume |

| Compose | What it builds |
|---------|----------------|
| **`docker-compose.prod.yml`** (default) | `db` + `api` + `caddy` — **no Vue** |
| `docker-compose.full.yml` | also Nuxt `web` (only if you need VPS UI again) |

nginx TLS → `127.0.0.1:8080` (Caddy), Host preserved.

---

## New / naïve VPS deploy

```
cd /root/prectice-docker
git pull
# .env.production: secrets + CADDY_* + CORS_* + CADDY_HTTP_PORT=8080

docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build

curl -sS https://api.dental.navapp.in/api/health
# Frontend is on Vercel — do not expect Docker web.
```

If an old `web` container is still running from a previous full stack:

```
docker compose -f docker-compose.full.yml --env-file .env.production stop web || true
docker rm -f $(docker ps -aq --filter name=web) 2>/dev/null || true
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

---

## Day-to-day

| Change | Action |
|--------|--------|
| `apps/web/**` | Vercel auto |
| `apps/api/**` | VPS: pull + rebuild `api` via `docker-compose.prod.yml` |
| Caddyfile / compose | rebuild `caddy` |

## Vercel

- Root: `apps/web`
- `NUXT_PUBLIC_API_BASE=https://api.dental.navapp.in/api`
- Optional SSO overrides (defaults are fine for prod):
  - `NUXT_PUBLIC_SSO_AUTH_BASE_URL=https://auth.pratikp.com`
  - `NUXT_PUBLIC_SSO_APP_SLUG=navapp-dental`
  - `NUXT_PUBLIC_SSO_CALLBACK_URL=https://dental.navapp.in/sso/callback.php` (or leave empty to use `origin + /sso/callback.php`)

## SSO (API on VPS)

In `.env.production`:

```
SSO_AUTH_BASE_URL=https://auth.pratikp.com
SSO_APP_SLUG=navapp-dental
SSO_APP_SECRET=<from auth.pratikp.com>
JWT_EXPIRE_HOURS=12
JWT_REMEMBER_EXPIRE_HOURS=720
```

Register callbacks on the auth app (exact match, no trailing slash):

- `https://dental.navapp.in/sso/callback.php`
- `http://localhost:3000/sso/callback.php`

Staff Google email must match an active `users.email`.
