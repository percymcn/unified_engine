# 🚀 TradeFlow by Fluxeo - Local Setup Guide

## 📦 Step 1: Export from Figma Make

### Download Your Project

1. **In Figma Make**, click the **Download** or **Export** button (usually top-right)
2. This will download a ZIP file containing all your project files
3. Extract the ZIP to your desired location (e.g., `~/Projects/tradeflow-platform`)

---

## 💻 Step 2: Set Up Local Development Environment

### Prerequisites

Install these if you haven't already:

```bash
# Node.js (v18 or higher) - Check version
node --version

# If not installed, download from: https://nodejs.org/
# Or use nvm:
nvm install 18
nvm use 18

# Verify npm
npm --version
```

### Initialize Project

```bash
# Navigate to your project folder
cd ~/Projects/tradeflow-platform

# Install dependencies
npm install

# This will install:
# - React 18
# - Tailwind CSS v4
# - Shadcn/ui components
# - Lucide icons
# - All other dependencies
```

---

## 🔧 Step 3: Environment Configuration

### Create `.env.local` File

Create a file named `.env.local` in the root directory:

```bash
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here

# Stripe Configuration (for billing)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Backend API URLs (your existing backends)
NEXT_PUBLIC_TRADELOCKER_API=https://your-tradelocker-api.com
NEXT_PUBLIC_TOPSTEP_API=https://your-topstep-api.com
NEXT_PUBLIC_TRUFOREX_API=https://your-truforex-api.com

# Optional: Development mode
NODE_ENV=development
```

### Get Your Supabase Credentials

1. Go to [https://supabase.com](https://supabase.com)
2. Sign in / Create account
3. Create a new project or use existing
4. Go to **Project Settings** → **API**
5. Copy:
   - **Project URL** → `NEXT_PUBLIC_SUPABASE_URL`
   - **anon public** key → `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - **service_role** key → `SUPABASE_SERVICE_ROLE_KEY`

---

## 🗄️ Step 4: Set Up Supabase Database

### Deploy the Schema

```bash
# Option 1: Using psql (if you have PostgreSQL client)
psql "postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres" < supabase_schema_v5.sql

# Option 2: Using Supabase Dashboard
# 1. Go to your Supabase project
# 2. Click "SQL Editor" in left sidebar
# 3. Copy contents of supabase_schema_v5.sql
# 4. Paste and click "Run"
```

### Verify Tables Created

In Supabase Dashboard → **Table Editor**, you should see:
- profiles
- broker_accounts
- risk_settings
- trading_config
- orders
- positions
- logs
- webhook_events
- subscriptions
- admin_actions
- equity_history

---

## 🔌 Step 5: Connect to Your Existing Backends

### Update API Integration Files

Create `/utils/api.ts`:

```typescript
// API client for your existing backends
const TRADELOCKER_API = process.env.NEXT_PUBLIC_TRADELOCKER_API;
const TOPSTEP_API = process.env.NEXT_PUBLIC_TOPSTEP_API;
const TRUFOREX_API = process.env.NEXT_PUBLIC_TRUFOREX_API;

export const api = {
  tradelocker: {
    async placeOrder(order: any) {
      const response = await fetch(`${TRADELOCKER_API}/hub/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order)
      });
      return response.json();
    },
    async getPositions() {
      const response = await fetch(`${TRADELOCKER_API}/positions`);
      return response.json();
    }
  },
  
  topstep: {
    async placeOrder(order: any) {
      const response = await fetch(`${TOPSTEP_API}/api/order/place`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order)
      });
      return response.json();
    },
    async getContracts() {
      const response = await fetch(`${TOPSTEP_API}/fetch_active_contracts`);
      return response.json();
    }
  },
  
  truforex: {
    async sendSignal(signal: any) {
      const response = await fetch(`${TRUFOREX_API}/mt4_signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(signal)
      });
      return response.json();
    }
  }
};
```

### Create Supabase Client

Create `/utils/supabase/client.ts`:

```typescript
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

### Update Components to Use Real Data

Example: Update `/components/PositionsMonitor.tsx`:

```typescript
import { useEffect, useState } from 'react';
import { supabase } from '../utils/supabase/client';
import { api } from '../utils/api';

export function PositionsMonitor({ broker }: { broker: string }) {
  const [positions, setPositions] = useState([]);
  
  useEffect(() => {
    // Fetch from your backend
    async function fetchPositions() {
      let data;
      if (broker === 'tradelocker') {
        data = await api.tradelocker.getPositions();
      } else if (broker === 'topstep') {
        data = await api.topstep.getContracts();
      } else {
        data = []; // truforex logic
      }
      setPositions(data);
    }
    
    fetchPositions();
    
    // Subscribe to Supabase realtime updates
    const channel = supabase
      .channel(`positions:${broker}`)
      .on('postgres_changes', {
        event: '*',
        schema: 'public',
        table: 'positions',
        filter: `broker=eq.${broker}`
      }, (payload) => {
        console.log('Position update:', payload);
        fetchPositions(); // Re-fetch or update state
      })
      .subscribe();
      
    return () => { supabase.removeChannel(channel); };
  }, [broker]);
  
  // ... rest of component
}
```

---

## 🏃 Step 6: Run Development Server

```bash
# Start the development server
npm run dev

# Your app will be available at:
# http://localhost:3000
```

### Expected Console Output:

```
  ▲ Next.js 14.x.x
  - Local:        http://localhost:3000
  - Ready in 2.1s
```

### Open in Browser:

Navigate to `http://localhost:3000`

You should see:
- ✅ TradeFlow by Fluxeo logo in header
- ✅ Three broker tabs (TradeLocker, Topstep, TruForex)
- ✅ Dashboard with metrics
- ✅ Sidebar navigation

---

## 🔐 Step 7: Authentication Setup

### Create Your First User

```typescript
// In Supabase Dashboard → SQL Editor, run:
INSERT INTO profiles (id, email, name, role, plan_tier)
VALUES (
  gen_random_uuid(),
  'your-email@example.com',
  'Your Name',
  'admin',
  'elite'
);
```

### Update UserContext

In `/contexts/UserContext.tsx`, replace mock user with real auth:

```typescript
import { useEffect, useState } from 'react';
import { supabase } from '../utils/supabase/client';

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  
  useEffect(() => {
    // Get current session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        // Fetch user profile from profiles table
        supabase
          .from('profiles')
          .select('*')
          .eq('email', session.user.email)
          .single()
          .then(({ data }) => {
            setUser(data);
          });
      }
    });
    
    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        if (session?.user) {
          supabase
            .from('profiles')
            .select('*')
            .eq('email', session.user.email)
            .single()
            .then(({ data }) => setUser(data));
        } else {
          setUser(null);
        }
      }
    );
    
    return () => subscription.unsubscribe();
  }, []);
  
  // ... rest of context
}
```

---

## 📡 Step 8: Connect Webhooks to Your Backends

### TradeLocker Webhook Integration

In your TradeLocker backend, add route to sync with Supabase:

```python
# Your TradeLocker backend (Python/FastAPI example)
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

@app.post("/hub/order")
async def place_order(order: OrderRequest):
    # 1. Place order with TradeLocker API
    result = await tradelocker_client.place_order(order)
    
    # 2. Log to Supabase
    supabase.table('orders').insert({
        'user_id': order.user_id,
        'broker': 'tradelocker',
        'symbol': order.symbol,
        'side': order.side,
        'qty': order.qty,
        'status': result.status,
        'broker_order_id': result.order_id
    }).execute()
    
    # 3. Return result
    return result
```

### Topstep Webhook Integration

Similar pattern for Topstep:

```python
@app.post("/api/order/place")
async def place_projectx_order(order: OrderRequest):
    # Place via ProjectX API
    result = await projectx_client.place_order(order)
    
    # Log to Supabase
    supabase.table('orders').insert({
        'user_id': order.user_id,
        'broker': 'topstep',
        # ... fields
    }).execute()
    
    return result
```

---

## 🎨 Step 9: Customization (Optional)

### Update Logo

Replace the logo by editing `/App.tsx`:

```typescript
// If you want to use a local file instead of Figma asset:
import logoImage from './assets/tradeflow-logo.png';
```

### Adjust Colors

Edit `/styles/globals.css` to customize theme:

```css
:root {
  --background: #002b36;     /* Dark teal background */
  --foreground: #ffffff;     /* White text */
  --primary: #00ffc2;        /* Cyan accent */
  /* ... customize other colors */
}
```

### Add Custom Pages

Create new routes in Next.js:

```bash
# Create pages directory (if using Next.js pages router)
mkdir pages
touch pages/strategies.tsx   # Fluxeo strategies page
touch pages/analytics.tsx    # Custom analytics
```

---

## 🧪 Step 10: Testing

### Test Checklist

- [ ] Logo displays correctly
- [ ] All three broker tabs work
- [ ] Dashboard shows metrics
- [ ] Navigation between sections works
- [ ] Billing portal shows plans ($20, $40, $60)
- [ ] Can view orders (even if empty)
- [ ] Can view positions (even if empty)
- [ ] Risk controls sliders move smoothly
- [ ] Trading config saves settings
- [ ] Webhook templates display
- [ ] API keys can be generated
- [ ] Logs viewer displays entries

### Connect Real Data

1. **Register a broker account** in Accounts tab
2. **Generate API key** in API Keys tab
3. **Copy webhook URL** from Webhooks tab
4. **Set up TradingView alert** with webhook
5. **Place a test order** via webhook
6. **Verify order appears** in Orders tab
7. **Check Supabase** for order record

---

## 🚀 Step 11: Deployment to Production

### Option 1: Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# Deploy
vercel --prod

# Set environment variables in Vercel dashboard
# Project Settings → Environment Variables
```

### Option 2: Docker

```bash
# Build Docker image
docker build -t tradeflow-frontend .

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_SUPABASE_URL=$SUPABASE_URL \
  -e NEXT_PUBLIC_SUPABASE_ANON_KEY=$ANON_KEY \
  tradeflow-frontend
```

### Option 3: Traditional Hosting

```bash
# Build for production
npm run build

# Output will be in .next/ or out/ directory
# Upload to your hosting (Netlify, AWS, etc.)
```

---

## 🔧 Troubleshooting

### Logo Not Showing

**Problem**: Logo shows broken image icon

**Solution**:
1. The Figma asset import only works in Figma Make environment
2. For local development, save the logo to `/public/logo.png`
3. Update import:
   ```typescript
   import logoImage from '/logo.png';
   // Or use Next.js Image:
   <Image src="/logo.png" alt="TradeFlow" width={180} height={48} />
   ```

### Supabase Connection Error

**Problem**: `Failed to fetch` or CORS errors

**Solution**:
1. Check `.env.local` has correct Supabase URL
2. Verify anon key is correct
3. In Supabase Dashboard → Authentication → URL Configuration
4. Add `http://localhost:3000` to **Site URL**
5. Add `http://localhost:3000/**` to **Redirect URLs**

### Backend API Not Connecting

**Problem**: Orders/positions not loading

**Solution**:
1. Check backend URLs in `.env.local`
2. Verify backends are running
3. Test endpoints with curl:
   ```bash
   curl https://your-tradelocker-api.com/positions
   ```
4. Check CORS headers in backend (must allow `http://localhost:3000`)

### CSS Not Loading

**Problem**: Styles look broken

**Solution**:
1. Ensure Tailwind CSS is installed:
   ```bash
   npm install -D tailwindcss@next @tailwindcss/vite
   ```
2. Verify `globals.css` is imported in main file
3. Clear cache and restart:
   ```bash
   rm -rf .next
   npm run dev
   ```

---

## 📞 Getting Help

### Resources

- **Next.js Docs**: https://nextjs.org/docs
- **Supabase Docs**: https://supabase.com/docs
- **Tailwind CSS v4**: https://tailwindcss.com/docs
- **Shadcn/ui**: https://ui.shadcn.com

### Common Issues

1. **"Module not found"** → Run `npm install`
2. **"Cannot find module 'figma:asset'"** → Replace with local image
3. **Port 3000 in use** → Use `npm run dev -- -p 3001`

---

## ✅ Final Checklist

Before going live:

- [ ] All environment variables set
- [ ] Supabase schema deployed
- [ ] Database RLS policies active
- [ ] Stripe products created ($20, $40, $60)
- [ ] Stripe webhooks configured
- [ ] Backend APIs connected
- [ ] Logo displays correctly
- [ ] Authentication works
- [ ] Can register broker accounts
- [ ] Can place test orders
- [ ] Webhooks receive alerts
- [ ] Billing portal functional
- [ ] Admin panel accessible (admin users only)
- [ ] Mobile responsive (test on phone)
- [ ] SSL certificate active (production)

---

## 🎉 You're Ready!

Your TradeFlow by Fluxeo platform is now running locally and connected to your infrastructure!

**Next steps:**
1. Invite beta users
2. Set up monitoring (Sentry, LogRocket)
3. Configure email notifications
4. Add Google Analytics
5. Launch! 🚀

---

**Last Updated**: 2025-10-14  
**Version**: TradeFlow V5  
**Support**: support@fluxeo.com
