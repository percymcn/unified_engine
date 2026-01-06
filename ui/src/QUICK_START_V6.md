# 🚀 Quick Start Guide - TradeFlow v6.0

Get up and running with the new v6.0 features in under 10 minutes.

---

## ⚡ 3-Minute Setup

### Step 1: Configure API Client (1 min)

Open `/utils/api-client.ts`:

```typescript
// Change this to use your backend
const API_BASE_URL = 'https://unified.fluxeo.net/api/unify/v1';

// Set to false for production
const USE_MOCK_BACKEND = false;
```

### Step 2: Configure Stripe (2 min)

Open `/utils/stripe-helpers.ts`:

```typescript
// Replace with your Stripe Price IDs
export const STRIPE_PRICE_IDS = {
  starter: 'price_1ABC123def456',  // Get from Stripe Dashboard
  pro: 'price_2DEF456ghi789',
  elite: 'price_3GHI789jkl012'
};

// Update checkout base URL
export const STRIPE_CHECKOUT_BASE = 'https://checkout.stripe.com';
```

**How to get Price IDs:**
1. Go to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to Products
3. Create 3 products: Starter ($20), Pro ($40), Elite ($60)
4. Set to recurring monthly
5. Copy the Price ID for each

### Step 3: Test Locally (30 sec)

```bash
npm install
npm run dev
```

Open http://localhost:5173

**Done! 🎉**

---

## 🧪 Test the New Features

### 1. Test Onboarding Flow

```
1. Click "Start Free Trial"
2. Fill signup form
3. See plan selection page ✅
4. Choose a plan (or skip)
5. See connect broker page ✅
6. Connect a broker (or skip)
7. Land on dashboard
```

**Expected:** Smooth flow with animations, no errors

### 2. Test Analytics Page

```
1. Login to dashboard
2. Click "Analytics" in sidebar
3. See 4 KPI cards ✅
4. See 4 charts rendering ✅
5. Change time range filter
6. Change broker filter
7. See data update
```

**Expected:** All charts render, filters work

### 3. Test Connect Broker

```
1. Click "Connect Broker" in sidebar
2. See 4 broker tabs ✅
3. Click TradeLocker tab
4. Fill in credentials:
   - Username: test_user
   - Password: test_pass
   - Server: demo.tradelocker.com
5. Click "Connect TradeLocker"
6. See success message ✅
```

**Expected:** Connection status updates

### 4. Test Billing Integration

```
1. Click "Billing" in sidebar
2. See current plan highlighted ✅
3. Click "Upgrade" on Elite plan
4. Get redirected to Stripe (or see placeholder) ✅
5. Click "Manage Billing"
6. Open Stripe Portal (or see placeholder) ✅
```

**Expected:** Stripe URLs work (after configuration)

---

## 🔧 Customization

### Change Colors

Edit `/styles/globals.css`:

```css
:root {
  /* Change primary color */
  --primary: #00ffc2;  /* Your brand color */
  
  /* Change background */
  --background: #001f29;  /* Your dark theme */
}
```

### Change Plans

Edit plan data in:
- `/components/OnboardingPlanSelection.tsx`
- `/components/BillingPortal.tsx`
- `/components/LandingPage.tsx`

```typescript
const plans = [
  {
    id: 'starter',
    name: 'Starter',
    price: '$25',  // Change price
    features: [
      'Your feature 1',
      'Your feature 2'
    ]
  }
];
```

### Add/Remove Brokers

Edit `/components/ConnectBrokerPage.tsx`:

```typescript
const brokers = [
  { 
    id: 'yourbroker', 
    name: 'Your Broker', 
    icon: Activity,  // Choose icon
    requiresEA: false  // Or true if needs EA
  }
];
```

---

## 🔗 Backend Integration

### Quick Backend Checklist

- [ ] Implement `/register/*` endpoints
- [ ] Implement `/metrics` endpoint
- [ ] Implement `/reports/pnl` endpoint
- [ ] Set up Stripe webhooks
- [ ] Add authentication middleware
- [ ] Test with frontend

### Minimal Backend Example

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/register/tradelocker")
async def register_tradelocker(
    username: str,
    password: str,
    server: str
):
    # Your logic here
    return {
        "success": True,
        "apiKey": "generated-key",
        "message": "Connected successfully"
    }

@app.get("/metrics")
async def get_metrics(time_range: str = "7d"):
    return {
        "totalTrades": 1248,
        "activeUsers": 189,
        "totalPnL": 45230.50,
        "winRate": 67.8
    }
```

Run:
```bash
uvicorn main:app --reload
```

---

## 🎨 UI Customization

### Change Logo

Replace `/figma:asset/27ac89...` imports with your logo:

```typescript
// In components that use logo
import yourLogo from '/public/your-logo.png';

<img src={yourLogo} alt="Your Brand" />
```

### Change Animations

Edit motion settings in components:

```typescript
// Less motion
<motion.div
  initial={{ opacity: 0 }}
  animate={{ opacity: 1 }}
  transition={{ duration: 0.2 }}  // Faster
>
```

### Change Chart Colors

Edit in `/components/AnalyticsPage.tsx`:

```typescript
const brokerDistribution = [
  { name: 'TradeLocker', value: 45, color: '#YOUR_COLOR' },
  { name: 'Topstep', value: 35, color: '#YOUR_COLOR' },
  { name: 'MT4/MT5', value: 20, color: '#YOUR_COLOR' }
];
```

---

## 🐛 Troubleshooting

### Issue: "Failed to fetch"

**Solution:** Check CORS settings in your backend

```python
allow_origins=["http://localhost:5173", "https://yourdomain.com"]
```

### Issue: Charts not rendering

**Solution:** Check if Recharts is installed

```bash
npm install recharts
```

### Issue: Stripe redirect not working

**Solution:** Update stripe-helpers.ts with real URLs

```typescript
export const STRIPE_CHECKOUT_BASE = 'https://checkout.stripe.com/c/pay/cs_live_...';
```

### Issue: Onboarding skips to dashboard

**Solution:** User already has a plan. Clear user data or test with new account.

### Issue: Analytics shows no data

**Solution:** Backend not returning data. Check:
1. API_BASE_URL is correct
2. Backend is running
3. Authentication token is valid
4. Endpoint returns correct format

---

## 📱 Mobile Testing

### Quick Mobile Test

1. Open Chrome DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select "iPhone 14 Pro"
4. Reload page
5. Test all features

**Should see:**
- Hamburger menu ✅
- Stacked cards ✅
- Responsive charts ✅
- Bottom sheets for selectors ✅

---

## 🚀 Production Checklist

Before deploying to production:

### Frontend
- [ ] Set `USE_MOCK_BACKEND = false`
- [ ] Update `API_BASE_URL` to production
- [ ] Add Stripe live keys
- [ ] Test all flows
- [ ] Enable error tracking (Sentry)
- [ ] Configure environment variables
- [ ] Build and test: `npm run build`

### Backend
- [ ] All endpoints working
- [ ] Authentication enabled
- [ ] Rate limiting active
- [ ] CORS configured
- [ ] Stripe webhooks setup
- [ ] Database migrations run
- [ ] SSL certificate active

### Stripe
- [ ] Switch to live mode
- [ ] Update webhook secret
- [ ] Test live checkout
- [ ] Configure email receipts
- [ ] Set up Customer Portal

### Monitoring
- [ ] Error tracking active
- [ ] Performance monitoring
- [ ] Uptime monitoring
- [ ] Log aggregation

---

## 🎓 Learning Resources

### New to the Stack?

**React:**
- [React Docs](https://react.dev)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app)

**Tailwind CSS:**
- [Tailwind Docs](https://tailwindcss.com)
- [Tailwind v4 Beta](https://tailwindcss.com/blog/tailwindcss-v4-alpha)

**Shadcn UI:**
- [Shadcn Docs](https://ui.shadcn.com)
- [Component Examples](https://ui.shadcn.com/examples)

**Stripe:**
- [Stripe Docs](https://stripe.com/docs)
- [Stripe Checkout](https://stripe.com/docs/payments/checkout)

**Supabase:**
- [Supabase Docs](https://supabase.com/docs)
- [Auth Guide](https://supabase.com/docs/guides/auth)

---

## 💡 Pro Tips

### 1. Use Mock Backend for Development

Keep `USE_MOCK_BACKEND = true` while building UI:
- No backend needed
- Instant responses
- Pre-filled data
- Easy testing

### 2. Incremental Integration

Integrate one feature at a time:
1. Start with authentication
2. Add broker connections
3. Enable analytics
4. Set up billing last

### 3. Test with Real Stripe Checkout

Use Stripe test mode:
- Test card: 4242 4242 4242 4242
- Any future expiry
- Any CVC

### 4. Monitor Performance

Add performance tracking:
```typescript
console.time('Component Render');
// ... component code
console.timeEnd('Component Render');
```

### 5. Debug API Calls

Log all API requests:
```typescript
// In api-client.ts
console.log('API Request:', endpoint, payload);
console.log('API Response:', response);
```

---

## 🎯 Next Steps

After basic setup:

1. **Customize branding**
   - Update logo and colors
   - Change copy and messaging
   - Add your domain

2. **Configure backend**
   - Implement all endpoints
   - Set up database
   - Configure webhooks

3. **Set up Stripe**
   - Create products
   - Configure billing
   - Test subscriptions

4. **Add features**
   - Social auth
   - Email notifications
   - Advanced analytics

5. **Deploy**
   - Frontend to Vercel
   - Backend to your infra
   - Set up monitoring

---

## 📚 Additional Docs

- [V6 Upgrade Summary](V6_UPGRADE_SUMMARY.md)
- [Backend Integration Guide](BACKEND_INTEGRATION_GUIDE.md)
- [User Journey Map](USER_JOURNEY_MAP.md)
- [Full README](README_V6.md)

---

## ❓ Need Help?

**Can't find what you need?**

1. Check existing docs (see above)
2. Review code comments
3. Check component props
4. Email: support@fluxeo.net

---

**Happy Building! 🚀**

Last Updated: October 17, 2025  
Version: 6.0.0
