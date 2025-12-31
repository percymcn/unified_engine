# ⚡ TradeFlow - 5-Minute Quick Start

## Download & Install

```bash
# 1. Extract ZIP from Figma Make
unzip tradeflow-platform.zip
cd tradeflow-platform

# 2. Install dependencies
npm install

# 3. Create environment file
cat > .env.local << EOF
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
EOF

# 4. Start development server
npm run dev
```

## Fix Logo for Local Development

**Replace Figma asset import with local file:**

1. Save logo image to `/public/tradeflow-logo.png`
2. Edit `/App.tsx` line 24:

```typescript
// Change from:
import logoImage from 'figma:asset/f7866ab97db19eb1a62777d359b5a006726b94c2.png';

// To:
const logoImage = '/tradeflow-logo.png';
```

## Set Up Database

```bash
# In Supabase Dashboard → SQL Editor, paste contents of:
supabase_schema_v5.sql

# Then click "Run"
```

## Open in Browser

Navigate to: **http://localhost:3000**

✅ You should see the TradeFlow dashboard!

---

## Connect Your Existing Backends

Create `/utils/api.ts`:

```typescript
export const api = {
  tradelocker: {
    baseUrl: 'https://your-tradelocker-api.com',
    async placeOrder(order) {
      return fetch(`${this.baseUrl}/hub/order`, {
        method: 'POST',
        body: JSON.stringify(order)
      }).then(r => r.json());
    }
  },
  // ... topstep and truforex
};
```

Update components to use `api.tradelocker.placeOrder()` instead of mock data.

---

## Deploy to Vercel

```bash
vercel --prod
```

Done! 🎉

For detailed setup, see **LOCAL_SETUP_GUIDE.md**
