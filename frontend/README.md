# PaceAlyzer Frontend

Next.js frontend for PaceAlyzer. It includes the landing page, authentication flow, dashboard, calendar, day view, metrics pages and chat UI.

## Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

## Required Environment Variables

Client-side:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_BACKEND_URL`
- `NEXT_PUBLIC_STRAVA_CLIENT_ID`
- `NEXT_PUBLIC_STRAVA_REDIRECT_URI`

Server-side routes:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `STRAVA_CLIENT_ID`
- `STRAVA_CLIENT_SECRET`
- `STRAVA_REDIRECT_URI`
- `BASE_URL`
- `BACKEND_URL`

