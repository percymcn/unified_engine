#!/bin/bash
# enable_google_oauth.sh - Interactive script to enable Google OAuth

set -e

echo "=== Google OAuth Setup ==="
echo ""
echo "This script will help you enable Google OAuth for Tradeflow."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
fi

echo "To enable Google OAuth, you need:"
echo "1. Google Cloud Console credentials (Client ID and Secret)"
echo "2. Configure authorized redirect URI in Google Console"
echo ""
echo "📋 Steps to get Google OAuth credentials:"
echo ""
echo "1. Go to: https://console.cloud.google.com/apis/credentials"
echo "2. Create a new OAuth 2.0 Client ID"
echo "3. Set authorized redirect URI to:"
echo "   Production: https://tradeflow.fluxeo.net/api/auth/google/callback"
echo "   Development: http://localhost:3456/api/auth/google/callback"
echo "4. Copy the Client ID and Client Secret"
echo ""
read -p "Do you have Google OAuth credentials ready? (y/n): " has_creds

if [ "$has_creds" != "y" ] && [ "$has_creds" != "Y" ]; then
    echo ""
    echo "Please get your credentials from Google Cloud Console first."
    echo "See docs/GOOGLE_OAUTH_SETUP.md for detailed instructions."
    exit 0
fi

echo ""
read -p "Enter Google Client ID: " client_id
read -p "Enter Google Client Secret: " client_secret

if [ -z "$client_id" ] || [ -z "$client_secret" ]; then
    echo "❌ Client ID and Secret are required"
    exit 1
fi

# Update .env file
echo ""
echo "Updating .env file..."

# Use sed to update or add GOOGLE_CLIENT_ID
if grep -q "^GOOGLE_CLIENT_ID=" .env; then
    sed -i "s|^GOOGLE_CLIENT_ID=.*|GOOGLE_CLIENT_ID=$client_id|" .env
else
    echo "GOOGLE_CLIENT_ID=$client_id" >> .env
fi

# Use sed to update or add GOOGLE_CLIENT_SECRET
if grep -q "^GOOGLE_CLIENT_SECRET=" .env; then
    sed -i "s|^GOOGLE_CLIENT_SECRET=.*|GOOGLE_CLIENT_SECRET=$client_secret|" .env
else
    echo "GOOGLE_CLIENT_SECRET=$client_secret" >> .env
fi

# Ensure GOOGLE_REDIRECT_URI is set
if ! grep -q "^GOOGLE_REDIRECT_URI=" .env; then
    echo "GOOGLE_REDIRECT_URI=https://tradeflow.fluxeo.net/api/auth/google/callback" >> .env
fi

echo "✅ Google OAuth credentials added to .env"
echo ""
echo "⚠️  IMPORTANT: Make sure .env is in .gitignore and never commit it!"
echo ""
echo "Next steps:"
echo "1. Restart the backend service to load new environment variables"
echo "2. Verify OAuth is enabled: ./scripts/verify_oauth_providers.sh"
echo "3. Test the login flow on the frontend"
echo ""
echo "To restart backend:"
echo "  docker-compose restart api"
echo "  OR"
echo "  systemctl restart unified-engine-api"
echo "  OR"
echo "  python3 -m uvicorn app.main:app --reload"
