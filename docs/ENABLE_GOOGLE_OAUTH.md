# Google OAuth Quick Enable Guide

## Quick Setup

To enable Google OAuth, you need to:

1. **Get Google OAuth Credentials**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID
   - Set redirect URI: `https://tradeflow.fluxeo.net/api/auth/google/callback`

2. **Set Environment Variables**

   **Option A: Use the interactive script**
   ```bash
   ./scripts/enable_google_oauth.sh
   ```

   **Option B: Manual setup**
   ```bash
   # Add to .env file (create if doesn't exist)
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   GOOGLE_REDIRECT_URI=https://tradeflow.fluxeo.net/api/auth/google/callback
   ```

3. **Restart Backend**
   ```bash
   # Docker
   docker-compose restart api
   
   # Systemd
   systemctl restart unified-engine-api
   
   # Direct
   # Kill existing process and restart
   python3 -m uvicorn app.main:app --reload
   ```

4. **Verify**
   ```bash
   ./scripts/verify_oauth_providers.sh
   ```

## Current Status

Run this to check if Google OAuth is enabled:
```bash
curl http://localhost:8765/api/v1/oauth/providers | jq .
```

If Google is configured, you should see:
```json
{
  "providers": [
    {
      "provider": "google",
      "name": "Google",
      "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
    }
  ]
}
```

If not configured, you'll see:
```json
{
  "providers": []
}
```

## Frontend

The frontend will automatically show/hide the Google sign-in button based on the `/api/v1/oauth/providers` endpoint response.

## Troubleshooting

- **"Google OAuth not configured"**: Check GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set in .env
- **"redirect_uri_mismatch"**: Ensure redirect URI in Google Console matches GOOGLE_REDIRECT_URI
- **Button not showing**: Check backend is running and providers endpoint returns Google
