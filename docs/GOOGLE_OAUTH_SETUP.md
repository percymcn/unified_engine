# Google OAuth Configuration Guide

## Overview
Google OAuth allows users to sign in with their Google account. This document describes the setup and callback URLs required.

## Environment Variables

Add these to your `.env` file:

```bash
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://tradeflow.fluxeo.net/api/auth/google/callback
```

## Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID
3. Configure authorized redirect URIs:

### Production
```
https://tradeflow.fluxeo.net/api/auth/google/callback
```

### Development (localhost)
```
http://localhost:3456/api/auth/google/callback
```

### API Subdomain (if used)
```
https://api.tradeflow.fluxeo.net/api/auth/google/callback
```

## OAuth Flow

1. User clicks "Sign in with Google" on login/register page
2. User is redirected to Google authorization page
3. After authorization, Google redirects to: `/api/auth/google/callback?code=...`
4. Frontend BFF route (`ui-next/src/app/api/auth/google/callback/route.ts`) exchanges code for tokens via backend
5. Backend endpoint (`/api/v1/oauth/callback/google`) exchanges code for access token and creates user session
6. Frontend sets HTTP-only cookie and redirects to dashboard

## Backend Endpoints

- `GET /api/v1/oauth/providers` - Returns available OAuth providers (checks `GOOGLE_CLIENT_ID`)
- `GET /api/v1/oauth/callback/google?code=...` - Exchanges authorization code for session token

## Frontend Routes

- `GET /api/auth/google/callback` - BFF route that handles Google redirect and sets cookie

## Testing

1. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`
2. Ensure redirect URI matches in Google Cloud Console
3. Visit `/login` page - Google button should be enabled
4. Click "Sign in with Google"
5. Complete Google authorization
6. Should redirect to `/dashboard` with authenticated session

## Troubleshooting

- **"Google OAuth not configured"**: Check `GOOGLE_CLIENT_ID` is set
- **"redirect_uri_mismatch"**: Ensure redirect URI in Google Console matches `GOOGLE_REDIRECT_URI`
- **"invalid_grant"**: Authorization code may have expired (try again)
