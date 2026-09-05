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
3. Domain: `mypln.in` / `www.mypln.in`  
4. Env: `NUXT_PUBLIC_API_BASE=https://api.dental.navapp.in/api`  

Desk stays Root Directory `apps/web` → `dental.navapp.in`.
