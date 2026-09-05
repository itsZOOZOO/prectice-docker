# plan-web (mypln.in)

Patient-facing treatment plan viewer. Separate from desk (`apps/web`).

## Local

```bash
cd apps/plan-web
pnpm install
# API at :8000 — set if needed:
# export NUXT_PUBLIC_API_BASE=http://127.0.0.1:8000/api
pnpm dev   # http://localhost:3001
```

Open a share URL like `http://localhost:3001/{7code}/{slug}`.

## Vercel

1. New project → same repo  
2. **Root Directory:** `apps/plan-web`  
3. Domains: add `www.mypln.in` as primary; add `mypln.in` and set it to **redirect to www** (Vercel Domains UI)  
4. Env: `NUXT_PUBLIC_API_BASE=https://api.dental.navapp.in/api`  
5. On API VPS `.env.production`:  
   `CORS_ORIGINS=…,https://mypln.in,https://www.mypln.in`  
   `PLAN_PUBLIC_BASE_URL=https://www.mypln.in`  

Desk stays Root Directory `apps/web` → `dental.navapp.in`.

WhatsApp still uses the existing Meta template host + path-only button params until a dedicated `mypln.in` template is approved.
