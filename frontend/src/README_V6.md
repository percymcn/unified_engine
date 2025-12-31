# 🚀 TradeFlow v6.0 - Enterprise SaaS Platform

> **Complete multi-broker trading automation platform with unified API, analytics, and Stripe billing**

[![Version](https://img.shields.io/badge/version-6.0.0-blue.svg)](https://github.com/fluxeo/tradeflow)
[![Status](https://img.shields.io/badge/status-production--ready-green.svg)](https://github.com/fluxeo/tradeflow)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](https://github.com/fluxeo/tradeflow)

---

## 📋 Table of Contents

- [Overview](#overview)
- [What's New in v6.0](#whats-new-in-v60)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [API Integration](#api-integration)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [Support](#support)

---

## 🌟 Overview

TradeFlow by Fluxeo is a unified trading automation platform that consolidates **TradeLocker**, **Topstep (ProjectX)**, **TruForex**, **MT4**, and **MT5** into a single enterprise-ready interface.

### Key Capabilities

✅ **Multi-Broker Support** - Connect up to 3 brokers per account  
✅ **TradingView Integration** - Webhook-based strategy automation  
✅ **Real-Time Analytics** - Advanced charts and performance metrics  
✅ **Risk Management** - Precision controls with 0.01% accuracy  
✅ **Stripe Billing** - Subscription management with 3 pricing tiers  
✅ **Role-Based Access** - Admin and user permissions  
✅ **Trial System** - 3 days or 100 trades, whichever comes first  

---

## 🎉 What's New in v6.0

### New Features

#### 1. **Onboarding Flow** 🎯
Beautiful step-by-step onboarding for new users:
- Plan selection with visual comparison
- Broker connection wizard
- Skip options for flexibility
- Smooth transitions and animations

#### 2. **Analytics Dashboard** 📊
Comprehensive analytics with:
- 4 KPI cards (Trades, Users, P&L, Win Rate)
- 4 interactive charts (Area, Bar, Pie, Line)
- Top performing strategies table
- Time range and broker filters
- Role-based data views (admin vs user)

#### 3. **Connect Broker Page** 🔗
Dedicated broker management:
- Support for 4 broker types
- Secure credential forms
- Real-time connection status
- EA download for MetaTrader
- Disconnect functionality

#### 4. **Stripe Integration** 💳
Full billing management:
- Checkout session creation
- Customer portal access
- Subscription upgrades/downgrades
- Cancellation handling
- Webhook event processing

### Enhanced Components

- **Dashboard** - Added Analytics and Connect Broker navigation
- **BillingPortal** - Integrated Stripe checkout and portal
- **App.tsx** - New routing with onboarding flow
- **UserContext** - Enhanced user state management

---

## ✨ Features

### For Traders

#### 🤖 **Trading Automation**
- Connect TradingView strategies via webhooks
- Automatic position sizing based on risk %
- Stop loss and take profit automation
- Multi-broker order routing

#### 📊 **Performance Tracking**
- Real-time P&L across all accounts
- Win rate and performance metrics
- Trade history and analytics
- Strategy performance comparison

#### 🛡️ **Risk Management**
- Adjustable SL/TP sliders (0.01% precision)
- Maximum position size limits
- Risk per trade controls
- Account balance protection

#### 🔔 **Alerts & Notifications**
- TradingView webhook templates
- Real-time trade notifications
- Risk alert triggers
- Trial limit warnings

### For Administrators

#### 👥 **User Management**
- View all users and accounts
- Edit user details and permissions
- Delete users and sync accounts
- Role-based access control

#### 📈 **System Analytics**
- Total users and active count
- System-wide P&L
- Revenue and MRR tracking
- Performance metrics

#### 🔍 **Monitoring**
- Webhook logs
- Trade activity logs
- System health metrics
- Error tracking

---

## 🛠️ Tech Stack

### Frontend
- **React 18** - UI library
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Styling
- **Shadcn UI** - Component library
- **Motion** (Framer Motion) - Animations
- **Recharts** - Data visualization
- **Lucide React** - Icons

### Backend
- **Supabase** - Authentication & Database
- **FastAPI** - REST API (your existing backend)
- **Stripe** - Payment processing
- **PostgreSQL** - Database
- **NATS** - Real-time messaging (optional)

### Infrastructure
- **Vercel/Netlify** - Frontend hosting (recommended)
- **Supabase Cloud** - Backend services
- **Stripe** - Payment processing
- **Redis** - Caching (optional)

---

## 🚀 Getting Started

### Prerequisites

```bash
Node.js >= 18
npm or yarn
Supabase account
Stripe account (for billing)
```

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/fluxeo/tradeflow.git
cd tradeflow
```

2. **Install dependencies**
```bash
npm install
```

3. **Set up environment variables**
```bash
# Create .env file
cp .env.example .env

# Add your credentials
VITE_SUPABASE_URL=your-project-url
VITE_SUPABASE_ANON_KEY=your-anon-key
VITE_STRIPE_PUBLISHABLE_KEY=your-stripe-key
```

4. **Update API configuration**
```typescript
// In /utils/api-client.ts
const API_BASE_URL = 'https://your-backend.com/api/v1';
const USE_MOCK_BACKEND = false; // Set to false for production
```

5. **Configure Stripe**
```typescript
// In /utils/stripe-helpers.ts
export const STRIPE_PRICE_IDS = {
  starter: 'price_your_starter_id',
  pro: 'price_your_pro_id',
  elite: 'price_your_elite_id'
};
```

6. **Run development server**
```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🏗️ Architecture

### Frontend Architecture

```
/
├── components/
│   ├── OnboardingPlanSelection.tsx    (NEW)
│   ├── ConnectBrokerPage.tsx          (NEW)
│   ├── AnalyticsPage.tsx              (NEW)
│   ├── Dashboard.tsx                  (ENHANCED)
│   ├── BillingPortal.tsx              (ENHANCED)
│   ├── LandingPage.tsx
│   ├── LoginPage.tsx
│   ├── SignupPage.tsx
│   └── ui/                            (Shadcn components)
├── contexts/
│   ├── UserContext.tsx                (ENHANCED)
│   └── ThemeContext.tsx
├── utils/
│   ├── api-client.ts
│   ├── stripe-helpers.ts              (NEW)
│   ├── mock-backend.ts
│   └── supabase/
└── App.tsx                            (ENHANCED)
```

### Data Flow

```
User Action
    ↓
React Component
    ↓
API Client (utils/api-client.ts)
    ↓
Backend API (FastAPI)
    ↓
Database (PostgreSQL)
    ↓
Response to Frontend
    ↓
UI Update
```

### Authentication Flow

```
Login/Signup
    ↓
Supabase Auth
    ↓
Get Access Token
    ↓
Fetch User Profile (Backend)
    ↓
Store in UserContext
    ↓
Render Dashboard
```

---

## 🔌 API Integration

### Required Endpoints

Your backend must implement these endpoints:

#### Authentication
```
POST /auth/signup          - Create new user
GET  /user/profile         - Get user profile
```

#### Broker Management
```
POST /register/tradelocker - Register TradeLocker account
POST /register/projectx    - Register Topstep account
POST /register/mtx         - Register MT4/MT5 account
```

#### Analytics
```
GET  /metrics              - Get KPI metrics
GET  /reports/pnl          - Get P&L data
GET  /analytics/trades     - Get trade history
GET  /analytics/strategies - Get strategy performance
```

#### Billing
```
POST /billing/create-checkout-session - Create Stripe session
POST /billing/create-portal-session   - Create portal session
POST /billing/webhook                 - Handle Stripe webhooks
GET  /billing/usage                   - Get usage stats
```

### API Request Example

```typescript
// Register a broker
const response = await apiClient.post('/register/tradelocker', {
  username: 'user123',
  password: 'secure_password',
  server: 'live.tradelocker.com'
});

// Get analytics
const metrics = await apiClient.get('/metrics?time_range=7d&broker=all');
```

See [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md) for detailed implementation.

---

## 📦 Deployment

### Frontend Deployment (Vercel)

1. **Connect repository to Vercel**
```bash
vercel login
vercel
```

2. **Set environment variables**
```
VITE_SUPABASE_URL
VITE_SUPABASE_ANON_KEY
VITE_STRIPE_PUBLISHABLE_KEY
```

3. **Deploy**
```bash
vercel --prod
```

### Backend Deployment

See your FastAPI backend deployment guide.

### Stripe Setup

1. Create products in Stripe Dashboard
2. Get Price IDs for each plan
3. Update `stripe-helpers.ts`
4. Set up webhook endpoint
5. Test with Stripe test mode

---

## 📚 Documentation

### Core Documentation
- [V6 Upgrade Summary](V6_UPGRADE_SUMMARY.md) - What's new
- [Backend Integration Guide](BACKEND_INTEGRATION_GUIDE.md) - API integration
- [User Journey Map](USER_JOURNEY_MAP.md) - User flow

### Previous Documentation
- [README v5](README_V5_ENTERPRISE.md) - Previous version
- [Testing Checklist](TESTING_CHECKLIST.md) - QA guide
- [Function Reference](QUICK_FUNCTION_REFERENCE.md) - Code reference
- [Accessibility Guide](ACCESSIBILITY_COMPLIANCE.md) - A11y compliance

### API Documentation
- [OpenAPI Spec](openapi_v5.yaml) - REST API spec
- [Blueprint](unified_blueprint_v5.json) - Data structures

---

## 🎨 Design System

### Colors

```css
/* Dark Theme */
--background: #001f29, #002b36, #0a0f1a
--primary: #00ffc2 (cyan/teal)
--success: #10B981 (green)
--warning: #F59E0B (orange)
--error: #EF4444 (red)

/* Light Theme (Landing) */
--accent: #00C2A8
```

### Typography

All typography is defined in `styles/globals.css`:
- H1-H4: Inter/SF Pro
- Body: 16px base (14px mobile)
- Responsive scaling

### Components

Built with Shadcn UI:
- Cards, Buttons, Forms
- Tabs, Dialogs, Alerts
- Charts (Recharts)
- Icons (Lucide)

---

## 🧪 Testing

### Run Tests

```bash
# Unit tests
npm run test

# E2E tests
npm run test:e2e

# Accessibility audit
npm run a11y
```

### Manual Testing Checklist

See [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) for complete checklist.

**Critical paths:**
- [ ] Signup → Onboarding → Dashboard
- [ ] Connect broker (all 4 types)
- [ ] Analytics charts render
- [ ] Billing upgrade flow
- [ ] Admin panel access

---

## 🔒 Security

### Best Practices

✅ **Never expose service role keys** in frontend  
✅ **Validate all inputs** before API calls  
✅ **Use HTTPS** everywhere  
✅ **Implement rate limiting** on API  
✅ **Hash API keys** before storage  
✅ **Encrypt broker credentials**  
✅ **Enable CORS** properly  
✅ **Use secure Stripe webhooks**  

### Reporting Security Issues

Email: security@fluxeo.net

---

## 📊 Monitoring

### Recommended Tools

- **Sentry** - Error tracking
- **Datadog** - Performance monitoring
- **LogRocket** - Session replay
- **Stripe Dashboard** - Payment monitoring

### Key Metrics

- User signups
- Trial → Paid conversion
- Churn rate
- API response times
- Error rates
- MRR growth

---

## 🤝 Contributing

This is a proprietary project. Internal contributors should follow:

1. Create feature branch
2. Make changes with tests
3. Submit PR for review
4. Wait for approval
5. Merge to main

### Code Style

- Use TypeScript
- Follow ESLint rules
- Write component tests
- Document new features

---

## 📞 Support

### For Users
- **Email:** support@fluxeo.net
- **Response time:**
  - Starter: 24 hours
  - Pro: 12 hours
  - Elite: 2 hours (24/7)

### For Developers
- **Docs:** See `/docs` folder
- **API Spec:** `openapi_v5.yaml`
- **Internal wiki:** (Link to internal docs)

---

## 🗺️ Roadmap

### Q4 2025
- ✅ v6.0 Release (Current)
- 🔄 Real-time notifications via WebSocket
- 🔄 Mobile app (React Native)
- 🔄 Social auth (Google, GitHub)

### Q1 2026
- ⏳ Team accounts (multi-user)
- ⏳ Strategy marketplace
- ⏳ Advanced AI risk alerts
- ⏳ White-label options

### Q2 2026
- ⏳ Multi-currency support
- ⏳ Prop firm partnerships
- ⏳ Trading journal
- ⏳ Copy trading features

---

## 📝 License

**Proprietary** - © 2025 Fluxeo Technologies. All rights reserved.

Unauthorized copying, distribution, or use is strictly prohibited.

---

## 🙏 Acknowledgments

Built with:
- React Team
- Shadcn UI
- Tailwind Labs
- Supabase
- Stripe
- Recharts

---

## 📈 Version History

### v6.0.0 (2025-10-17) - Current
- ✨ Added onboarding flow
- ✨ Added analytics dashboard
- ✨ Added connect broker page
- ✨ Integrated Stripe billing
- 🔧 Enhanced dashboard navigation
- 🔧 Improved user context
- 📚 Comprehensive documentation

### v5.0.0 (2025-10-14)
- Initial enterprise release
- Multi-broker support
- Basic analytics
- Admin panel

---

**Built with ❤️ by the Fluxeo Team**

For more information, visit [fluxeo.net](https://fluxeo.net)
