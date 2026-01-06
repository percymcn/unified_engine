# ui/README.md
# 🚀 TradeFlow - Enterprise-Ready SaaS Trading Platform

**Version 5.0** - Complete Unified Trading Dashboard

A comprehensive, production-ready SaaS platform for unified trading across multiple brokers including TradeLocker, Topstep (ProjectX), TruForex, MT4, and MT5.

---

## ✨ Features

### 🎯 Core Functionality
- ✅ **Multi-Broker Support** - Connect and manage accounts across 5 brokers
- ✅ **Real-Time Position Monitoring** - Track all positions in one dashboard
- ✅ **Advanced Analytics** - P&L reports, win rates, and performance metrics
- ✅ **Risk Management** - Configurable SL/TP, risk limits, and emergency stop
- ✅ **Webhook Integration** - TradingView alerts and custom webhooks
- ✅ **API Key Management** - Generate and manage webhook API keys
- ✅ **Billing & Subscriptions** - Stripe integration with trial support
- ✅ **Responsive Design** - Mobile-first, works on all devices

### 🛡️ Business Logic & Guards
- ✅ **Billing Guard** - Blocks trading when payment fails
- ✅ **Trial Banner** - Shows trial limits (100 trades / 3 days)
- ✅ **Emergency Stop** - Kill switch to close all positions instantly

### 📊 Analytics & Reporting
- ✅ Dashboard overview with KPIs
- ✅ P&L reports with charts
- ✅ Trade history and analytics
- ✅ Symbol-by-symbol breakdown
- ✅ Daily/weekly/monthly views

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn/pnpm
- Git

### Installation

1. **Clone or navigate to the project:**
```bash
cd "Enterprise-Ready SaaS Upgrade (5)"
```

2. **Install dependencies:**
```bash
npm install
```

3. **Set up environment variables:**
```bash
# Copy the example file
cp .env.example .env.local

# Edit .env.local with your configuration
# (See Configuration section below)
```

4. **Start the development server:**
```bash
npm run dev
```

5. **Open your browser:**
The app will automatically open at `http://localhost:3000`

---

## ⚙️ Configuration

### Environment Variables

Create a `.env.local` file in the root directory with the following variables:

```bash
# API Configuration
VITE_API_BASE_URL=https://unified.fluxeo.net/api/unify/v1
VITE_API_BACKUP_URL=https://your-project.supabase.co/functions/v1/make-server-d751d621

# Supabase Configuration
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here

# Stripe Configuration (for billing)
VITE_STRIPE_PUBLIC_KEY=pk_test_your_stripe_public_key_here

# Development Mode
VITE_USE_MOCK_BACKEND=true  # Set to false for production
VITE_DEBUG_MODE=false
```

### Mock Backend

By default, the app uses a mock backend for development. To use the real API:

1. Set `VITE_USE_MOCK_BACKEND=false` in `.env.local`
2. Ensure your API is running at `VITE_API_BASE_URL`
3. Configure proper authentication tokens

---

## 📁 Project Structure

```
Enterprise-Ready SaaS Upgrade (5)/
├── src/
│   ├── components/          # React components
│   │   ├── ui/             # shadcn/ui components
│   │   ├── Dashboard.tsx   # Main dashboard
│   │   ├── LandingPage.tsx # Landing page
│   │   └── ...             # Other pages
│   ├── contexts/           # React contexts
│   │   ├── UserContext.tsx # User/auth state
│   │   ├── ThemeContext.tsx # Theme management
│   │   └── BrokerContext.tsx # Broker selection
│   ├── utils/              # Utilities
│   │   ├── api-client-enhanced.ts # API client
│   │   ├── mock-backend.ts # Mock API
│   │   └── stripe-helpers.ts # Stripe utilities
│   ├── App.tsx             # Main app component
│   └── main.tsx            # Entry point
├── public/                 # Static assets
├── .env.example            # Environment template
├── .env.local              # Local environment (gitignored)
├── package.json            # Dependencies
├── vite.config.ts          # Vite configuration
└── README.md               # This file
```

---

## 🛠️ Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build

# Code Quality (if configured)
npm run lint         # Run linter
npm run type-check   # TypeScript type checking
```

---

## 🎨 Tech Stack

- **Framework:** React 18.3+ with TypeScript
- **Build Tool:** Vite 6.3+
- **UI Library:** shadcn/ui (Radix UI primitives)
- **Styling:** Tailwind CSS v4
- **Charts:** Recharts
- **Forms:** React Hook Form
- **Notifications:** Sonner
- **Icons:** Lucide React
- **Authentication:** Supabase Auth
- **Backend API:** FastAPI @ unified.fluxeo.net
- **Billing:** Stripe

---

## 📡 API Integration

### Endpoints Covered (27 total)

#### Overview & Trading
- `GET /api/overview` - Dashboard KPIs
- `GET /api/positions` - Open positions
- `GET /api/orders` - Order history
- `POST /api/orders/close` - Close position
- `DELETE /api/orders/{id}` - Cancel order
- `GET /api/reports/pnl` - P&L reports
- `GET /api/analytics/metrics` - Analytics metrics
- `GET /api/analytics/trades` - Trade analytics

#### Broker Management
- `GET /api/user/brokers` - List brokers
- `POST /register/{broker}` - Connect broker
- `POST /api/accounts/switch` - Switch account
- `GET /api/accounts/sync_results` - Sync results
- `POST /api/accounts/sync/{id}` - Retry sync

#### Configuration
- `GET /api/user/config` - User config
- `PUT /api/user/config` - Update config
- `GET /api/user/risk_config` - Risk config
- `PUT /api/user/risk_config` - Update risk config
- `POST /api/user/emergency_stop` - Emergency stop

#### API Keys & Billing
- `GET /api/user/api_keys` - List API keys
- `POST /api/user/api_keys/generate` - Generate key
- `DELETE /api/user/api_keys/{id}` - Delete key
- `GET /api/billing/status` - Billing status
- `GET /api/billing/usage` - Usage metrics
- `POST /api/billing/checkout` - Checkout
