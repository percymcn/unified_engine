# TradeFlow User Journey Map

Complete flow of how users interact with the TradeFlow platform from discovery to active trading.

---

## 🌊 Complete User Flow

```
┌─────────────────┐
│  Landing Page   │ ← User discovers TradeFlow
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │ Signup │ ← Creates account
    └────┬───┘
         │
         ▼
┌──────────────────┐
│ Plan Selection   │ ← Chooses Starter/Pro/Elite
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Connect Broker   │ ← Links trading account(s)
└────────┬─────────┘
         │
         ▼
    ┌──────────┐
    │ Dashboard│ ← Starts using the platform
    └──────────┘
```

---

## 📍 Journey Stages

### Stage 1: Discovery (Landing Page)

**Goal:** Understand what TradeFlow offers

**User sees:**
- Hero section with value proposition
- Animated TradingView alert flow
- "How It Works" (3 simple steps)
- Platform capabilities (5 features)
- Pricing comparison (3 plans)
- Supported brokers (5 platforms)
- FAQ section

**Key decisions:**
- Is this for me?
- Which plan do I need?
- Does it support my broker?

**CTAs:**
- "Start Free Trial" (primary)
- "Login" (secondary)
- "Watch How It Works" (tertiary)

**Page components:**
```tsx
<LandingPage 
  onNavigateToLogin={() => setView('login')}
  onNavigateToSignup={() => setView('signup')}
/>
```

---

### Stage 2: Authentication

#### 2a. New User → Signup

**Goal:** Create account quickly and securely

**Form fields:**
- Email address
- Password (with strength indicator)
- Full name
- Accept terms & conditions

**Features:**
- Supabase authentication
- Email validation
- Password requirements
- Google OAuth (future)

**What happens:**
1. User fills form
2. Frontend validates input
3. Calls Supabase auth
4. Creates user profile in backend
5. Auto-logs in
6. Redirects to onboarding

**Page component:**
```tsx
<SignupPage
  onSignup={async (email, password, name) => {
    await signup(email, password, name, 'trial');
  }}
  onNavigateToLogin={() => setView('login')}
/>
```

#### 2b. Existing User → Login

**Goal:** Quick access to dashboard

**Form fields:**
- Email
- Password

**Features:**
- Remember me
- Forgot password
- Social login (future)

**What happens:**
1. User enters credentials
2. Supabase authenticates
3. Fetches user profile
4. Redirects to dashboard

**Page component:**
```tsx
<LoginPage
  onLogin={async (email, password) => {
    await login(email, password);
  }}
/>
```

---

### Stage 3: Onboarding (New Users Only)

#### 3a. Plan Selection

**Goal:** Choose the right subscription tier

**User sees:**
- 3 plan cards with features
- Visual comparison
- Trial information (3 days or 100 trades)
- Current selection highlighted

**Plans:**
1. **Starter ($20/mo)**
   - 1 broker
   - BYO strategy
   - Basic features

2. **Pro ($40/mo)** ⭐ Most Popular
   - 2 brokers
   - 1 Fluxeo strategy
   - Advanced features

3. **Elite ($60/mo)**
   - 3 brokers
   - 3 Fluxeo strategies
   - Premium features + API

**What happens:**
1. User selects a plan (or skips)
2. Plan saved to user profile
3. Proceeds to broker connection

**Page component:**
```tsx
<OnboardingPlanSelection
  onPlanSelected={(plan) => {
    setUser({ ...user, plan });
    setView('connect-broker');
  }}
  onSkip={() => setView('dashboard')}
/>
```

#### 3b. Connect Broker

**Goal:** Link at least one trading account

**User sees:**
- Tabs for 4 broker types
- Connection forms per broker
- Status indicators
- EA download (for MT4/MT5)

**Brokers:**
1. **TradeLocker**
   - Username
   - Password
   - Server
   - Status: Direct API ✅

2. **Topstep (ProjectX)**
   - Username
   - Password
   - Account ID (optional)
   - Status: Direct API ✅

3. **MetaTrader 4**
   - Username
   - Password
   - Server (optional)
   - Status: Requires EA ⚠️

4. **MetaTrader 5**
   - Username
   - Password
   - Server (optional)
   - Status: Requires EA ⚠️

**What happens:**
1. User selects broker tab
2. Fills in credentials
3. Clicks "Connect"
4. API validates credentials
5. Generates secure API key
6. Shows success message
7. Can connect more brokers or continue

**Page component:**
```tsx
<ConnectBrokerPage
  standalone={true}
  onComplete={() => setView('dashboard')}
  onSkip={() => setView('dashboard')}
/>
```

---

### Stage 4: Dashboard (Active Use)

**Goal:** Manage trading automation

#### Main Navigation

```
┌─────────────────────────────────────┐
│  🏠 Dashboard       Overview        │
│  📊 Analytics       KPIs & Charts   │
│  🔗 Connect Broker  Add more        │
│  👥 Accounts        Manage accounts │
│  🔔 Webhooks        TradingView     │
│  ⚙️  Trading Config  Settings       │
│  📋 Orders          Order history   │
│  📈 Positions       Open positions  │
│  🛡️  Risk            Risk controls   │
│  🔑 API Keys        Manage keys     │
│  💳 Billing         Subscription    │
│  👤 Admin           (Admin only)    │
│  📜 Logs            Activity logs   │
└─────────────────────────────────────┘
```

#### 4a. Dashboard Overview

**User sees:**
- Portfolio summary (balance, equity, margin)
- Account cards (all connected brokers)
- Recent orders (last 10)
- Open positions (real-time)
- Quick stats (total P&L, win rate)

**Quick actions:**
- Create order
- Close position
- Generate API key
- Connect new broker

#### 4b. Analytics Page 📊 NEW

**User sees:**
- KPI cards (4 metrics)
- Charts (4 visualizations)
- Top strategies table
- Time range filter
- Broker filter

**Admin view:**
- System-wide metrics
- All users aggregated
- Revenue & MRR

**Regular user view:**
- Personal metrics only
- Individual performance

**Charts:**
1. Trades Over Time (Area)
2. P&L Distribution (Bar)
3. Broker Distribution (Pie)
4. Alerts Per Day (Line)

#### 4c. Connect Broker Page 🔗 NEW

**User sees:**
- All broker tabs
- Connection forms
- Connected accounts list
- Disconnect buttons

**Can:**
- Add new brokers
- Disconnect existing
- Download EA (MT4/MT5)
- View connection status

#### 4d. Billing Page 💳 ENHANCED

**User sees:**
- Current plan highlighted
- Available plans
- Subscription details
- Payment method
- Invoice history

**Can do:**
- Upgrade plan (→ Stripe Checkout)
- Downgrade plan
- Cancel subscription
- Update payment method
- Manage billing (→ Stripe Portal)

**Integrations:**
- ✅ Stripe Checkout for upgrades
- ✅ Stripe Customer Portal for management
- ✅ Webhook handling for events

---

## 🎯 User Goals by Role

### Regular Trader

**Primary goals:**
1. Automate TradingView strategies
2. Monitor positions across brokers
3. Control risk per trade
4. Track performance

**Key features used:**
- Webhooks (TradingView alerts)
- Trading Config (risk settings)
- Positions (real-time monitoring)
- Analytics (performance tracking)

**Typical session:**
```
Login → Check positions → Review analytics → 
Adjust risk settings → Create webhook → Logout
```

### Admin User

**Primary goals:**
1. Monitor system health
2. Manage all users
3. Track revenue
4. Support users

**Key features used:**
- Admin Panel (user management)
- Analytics (system metrics)
- Logs (troubleshooting)

**Typical session:**
```
Login → Check system metrics → Review user activity → 
Handle support request → Check logs → Logout
```

---

## 🔄 Common User Paths

### Path 1: Quick Start (Minimal)
```
Signup → Skip plan → Skip broker → Dashboard → 
Connect broker later → Generate API key → Set webhook
```
**Time:** ~2 minutes

### Path 2: Full Onboarding
```
Signup → Choose Pro → Connect TradeLocker → 
Dashboard → Configure risk → Generate API key → 
Create webhook → First trade
```
**Time:** ~5 minutes

### Path 3: Upgrade Journey
```
Login → Analytics (see limits) → Billing → 
Choose Elite → Stripe Checkout → Payment → 
Connect 2nd broker → Enable more strategies
```
**Time:** ~3 minutes

### Path 4: Admin Management
```
Login → Admin Panel → Search user → 
Edit account → Check logs → Close positions → 
Export data → Logout
```
**Time:** ~10 minutes

---

## 📱 Mobile Experience

### Key Differences

**Landing Page:**
- Stacked navigation
- Larger touch targets
- Simplified hero

**Onboarding:**
- Single column plan cards
- Larger form inputs
- Bottom sheet menus

**Dashboard:**
- Hamburger menu
- Bottom nav (future)
- Swipeable cards
- Collapsible sections

**Analytics:**
- Responsive charts
- Scrollable tables
- Simplified metrics

---

## 🎨 Visual Journey

### Color Coding

**Status indicators:**
- 🟢 Green = Connected/Success/Profit
- 🔴 Red = Error/Loss
- 🟡 Yellow = Warning/Trial
- 🔵 Blue = Info
- 🟣 Purple = Admin
- 🟦 Cyan (#00ffc2) = Primary actions

**Plan tiers:**
- Starter = Default styling
- Pro = Highlighted with cyan border
- Elite = Premium styling

---

## ⏱️ Time to Value

**From signup to first automated trade:**

| Step | Time | Cumulative |
|------|------|------------|
| Signup | 1 min | 1 min |
| Plan selection | 1 min | 2 min |
| Connect broker | 2 min | 4 min |
| Configure risk | 1 min | 5 min |
| Generate API key | 30 sec | 5.5 min |
| Set TradingView webhook | 2 min | 7.5 min |
| **First trade executes** | 0 sec | **7.5 min** |

**Goal:** Under 10 minutes from zero to automated trading ✅

---

## 🚨 Error Handling

### Common Issues & Solutions

**Issue:** Broker connection fails
- **Message:** "Failed to connect. Please check credentials."
- **Action:** Show detailed error, link to support

**Issue:** Trial expired
- **Message:** "Trial limit reached (3 days or 100 trades)"
- **Action:** Redirect to billing, highlight upgrade

**Issue:** API key invalid
- **Message:** "Invalid API key. Please regenerate."
- **Action:** Show API key manager, generate button

**Issue:** Payment failed
- **Message:** "Payment unsuccessful. Please update card."
- **Action:** Open Stripe Portal for payment update

---

## 📊 Success Metrics

### KPIs to Track

**Acquisition:**
- Signups per day
- Trial starts
- Plan selection rate

**Activation:**
- % completing onboarding
- Time to first broker connection
- Time to first trade

**Retention:**
- Daily active users
- Weekly active users
- Churn rate

**Revenue:**
- Trial → Paid conversion
- MRR (Monthly Recurring Revenue)
- ARPU (Average Revenue Per User)

**Engagement:**
- Trades per user
- Brokers per user
- Dashboard sessions

---

## 🎓 User Education

### In-App Guidance

**Tooltips:**
- Hover over icons for explanations
- Form field help text
- Risk setting warnings

**Empty States:**
- No brokers: "Connect your first broker to get started"
- No positions: "Your open positions will appear here"
- No orders: "Order history will show here"

**Alerts:**
- Trial warnings at 80% usage
- Connection errors with solutions
- Success confirmations

---

## 🔮 Future Enhancements

### Planned Improvements

1. **Onboarding tour:** Interactive guide on first login
2. **Quick setup wizard:** 3-step guided flow
3. **Video tutorials:** Embedded help videos
4. **Live chat:** Real-time support
5. **Notifications:** Real-time trade alerts
6. **Mobile app:** Native iOS/Android
7. **Template library:** Pre-built strategies
8. **Social features:** Share performance

---

## 📞 Support Touchpoints

**Throughout journey:**
- Landing page: FAQ section
- Signup: Email support link
- Onboarding: Help tooltips
- Dashboard: Settings → Support
- Error states: Contact support button

**Email:** support@fluxeo.net  
**Response time:**
- Starter: 24 hours
- Pro: 12 hours (priority)
- Elite: 2 hours (24/7)

---

**Last Updated:** October 17, 2025  
**Version:** 6.0.0
