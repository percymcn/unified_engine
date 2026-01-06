# 🔐 Public SaaS vs Internal Admin - Complete Guide

TradeFlow v6.0 now features a **complete separation** between PUBLIC SaaS (end-users) and INTERNAL ADMIN (platform management).

---

## 🎯 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    TradeFlow Platform                    │
├──────────────────────────┬──────────────────────────────┤
│      PUBLIC SaaS         │      INTERNAL ADMIN          │
│   (End User Layer)       │    (Management Layer)        │
├──────────────────────────┼──────────────────────────────┤
│ • Landing Page           │ • Admin Login (/admin/login) │
│ • User Signup/Login      │ • Admin Dashboard            │
│ • User Dashboard         │ • User Management            │
│ • Broker Connections     │ • Webhook Logs (All)         │
│ • Personal Analytics     │ • System Health              │
│ • Billing Management     │ • Trade Logs (All Users)     │
│ • Risk Controls          │ • Configuration              │
│ • Personal Logs          │ • Data Export                │
└──────────────────────────┴──────────────────────────────┘
         ↓                            ↓
┌──────────────────────────┬──────────────────────────────┐
│    Supabase Auth         │    Admin Auth                │
│  (Public Users)          │  (Hardcoded/Secure)          │
└──────────────────────────┴──────────────────────────────┘
         ↓                            ↓
┌─────────────────────────────────────────────────────────┐
│           Unified API Gateway (FastAPI)                  │
│  • User-scoped endpoints (tenant_id + api_key)          │
│  • Admin endpoints (/admin/*)                           │
│  • Broker proxies (/register/*)                         │
└─────────────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────────────┐
│         Backend Services                                 │
│  TradeLocker | Topstep | MT4/MT5 | TruForex            │
└─────────────────────────────────────────────────────────┘
```

---

## 📱 PUBLIC SaaS LAYER

### Purpose
Serve end-users who want to automate their trading.

### User Flow

```
1. Discovery (Landing Page)
   ↓
2. Signup (Supabase Auth)
   ↓
3. Plan Selection (Onboarding)
   ↓
4. Connect Broker(s)
   ↓
5. Dashboard (Main App)
```

### Key Features

#### 1. **Landing Page** (`/`)
- Modern hero section
- Feature showcase
- Pricing cards ($20, $40, $60)
- FAQ section
- CTA: "Start Free" or "Login"

**Access:** Public (no auth required)

#### 2. **Signup/Login** (`/signup`, `/login`)
- Supabase email + password auth
- Google OAuth (future)
- Email confirmation
- Password requirements

**Access:** Public (no auth required)

#### 3. **User Dashboard** (`/dashboard`)
Sidebar Navigation:
- **Dashboard** - Overview (PnL, Trades, Positions)
- **Analytics** - Charts and KPIs (personal)
- **Connect Broker** - Add/manage broker connections
- **Accounts** - View connected accounts
- **Webhooks** - TradingView webhook templates
- **Trading Config** - Risk settings
- **Orders** - Order history (personal)
- **Positions** - Open positions (personal)
- **Risk** - Risk controls
- **API Keys** - Generate webhook keys
- **Billing** - Subscription management
- **Logs** - Personal activity logs

**Access:** Requires user authentication (Supabase)

#### 4. **Connect Broker Modal/Page**
- Dropdown: TradeLocker / Topstep / MT4 / MT5
- Form fields: Email, Password, Server, Mode
- Submit → `POST /register/<broker>`
- Backend auto-generates API key (hidden)
- Shows connected brokers with Sync/Edit/Delete

**Access:** Logged-in users only

#### 5. **Billing Page**
- Current plan display
- Usage quotas
- Upgrade/downgrade (→ Stripe)
- Cancel subscription
- Payment method management

**Access:** Logged-in users only

### Public API Endpoints

All endpoints require user authentication token (Supabase):

```
GET  /user/profile          - Get user profile
GET  /user/brokers          - Get connected brokers (user's only)
POST /register/tradelocker  - Register broker (user-scoped)
POST /register/projectx     - Register broker (user-scoped)
POST /register/mtx          - Register MT4/MT5 (user-scoped)
GET  /orders                - Get orders (user's only)
GET  /positions             - Get positions (user's only)
GET  /reports/pnl           - Get P&L (user's only)
GET  /alerts                - Get alerts (user's only)
POST /alerts                - Create alert
GET  /metrics               - Get analytics (user's only)
POST /copilot/query         - AI assistant
GET  /billing/usage         - Usage stats
POST /billing/checkout      - Stripe checkout
```

**Authentication:** Bearer token from Supabase
**Scope:** User can only see/modify their own data

---

## 🔒 INTERNAL ADMIN LAYER

### Purpose
Platform management, user oversight, system monitoring.

### Admin Flow

```
1. Navigate to /admin/login (footer link)
   ↓
2. Admin Login (hardcoded credentials)
   ↓
3. Admin Dashboard (full system access)
```

### Key Features

#### 1. **Admin Login** (`/admin/login`)
- Dedicated admin login page
- Username + Password (hardcoded or secure vault)
- Security warning
- Purple shield icon
- Back to public site button

**Current Credentials (DEV ONLY):**
```
Username: admin
Password: admin123
```

⚠️ **IMPORTANT:** Change these in production!

**Access:** Public URL but requires admin credentials

#### 2. **Admin Dashboard** (`/admin/dashboard`)

**Tabs:**

##### **Overview Tab**
- System stats (4 KPI cards):
  - Total Users (1,247)
  - Total Trades (45,230)
  - MRR ($49,680)
  - Active Connections (2,341)
- Charts:
  - Daily Trades (Area chart)
  - Broker Distribution (Pie chart)
- Quick Actions:
  - Add User
  - Sync Accounts
  - Export Data
  - System Config

##### **Users Tab**
- Search and filter all users
- User cards showing:
  - Name, Email
  - Plan (Starter/Pro/Elite)
  - Status (Active/Trial/Suspended)
  - Connected brokers count
  - Join date
- Actions per user:
  - Edit (→ `/admin/edit_accounts/{id}`)
  - Delete (→ `/admin/delete/{id}`)

##### **Webhook Logs Tab**
- Real-time webhook activity
- All users (not scoped)
- Columns:
  - Timestamp
  - User email
  - Symbol
  - Action (BUY/SELL)
  - Broker
  - Status (Success/Error)
- Filter by broker, status, date

##### **System Tab**
- System health indicators:
  - API Status
  - Database Status
  - Webhook Status
  - Cache Usage
- Admin actions:
  - Sync All Accounts (→ `/admin/sync_accounts`)
  - Export System Logs
  - Configure Instruments (→ `/admin/enable/{symbol}`)
  - Clear Cache

**Access:** Requires admin login

### Admin API Endpoints

All endpoints require admin authentication:

```
POST /admin/login               - Admin authentication
GET  /admin/users               - List all users
POST /admin/register/manual     - Manually add user
PUT  /admin/edit_accounts/{id}  - Edit user account
DELETE /admin/delete/{id}       - Delete user
POST /admin/sync_accounts       - Sync all accounts
GET  /admin/select_accounts     - View all accounts
POST /admin/enable/{symbol}     - Enable instrument
GET  /admin/webhook_log         - All webhook logs
GET  /admin/trade_log           - All trade logs
GET  /admin/metrics             - System-wide metrics
GET  /admin/health              - System health
```

**Authentication:** Admin session (separate from user auth)
**Scope:** Full system access (all users, all data)

---

## 🎨 Design Differences

### Public SaaS Design

**Color Scheme:**
- Primary: `#0EA5E9` (Sky Blue)
- Background: White / `#f8fafc` (Light Gray)
- Cards: White with subtle shadows
- Borders: `#e2e8f0` (Light Gray)
- Success: `#10b981` (Green)
- Error: `#ef4444` (Red)

**Style:**
- Clean, minimal, modern
- Robinhood/Revolut aesthetic
- Rounded corners (12px)
- Soft shadows
- Gradient buttons

**Layout:**
- Sidebar navigation
- Card-based content
- Responsive grid
- Mobile-first

### Admin Portal Design

**Color Scheme:**
- Primary: `#0EA5E9` (Same blue)
- Admin Accent: `#8b5cf6` (Purple)
- Background: `#f8fafc` → `#fafbfc` (Slightly different)
- Borders: `#e2e8f0`
- Warning: Purple badges

**Style:**
- Professional, data-dense
- Table/list heavy
- More compact
- Purple accents for admin elements

**Layout:**
- Tab-based navigation
- List/table views
- Dense information display
- Desktop-optimized

---

## 🔐 Security Considerations

### Public Layer Security

1. **Supabase Auth**
   - Row-level security (RLS)
   - Email confirmation
   - Password hashing
   - Session management

2. **API Scoping**
   - Every request includes user ID
   - Backend filters by `tenant_id`
   - Users can't access other users' data

3. **API Keys**
   - Generated by backend
   - Hashed before storage
   - Never exposed in full
   - Scoped to user

### Admin Layer Security

1. **Admin Authentication**
   - Separate login flow
   - Hardcoded credentials (dev)
   - Use secure vault in production
   - Session timeout

2. **Admin Access Control**
   - Admin flag in user context
   - Route protection
   - Action logging
   - Audit trail

3. **Production Recommendations**
   ```typescript
   // DO NOT use hardcoded credentials in production!
   
   // Option 1: Environment variable
   if (username === process.env.ADMIN_USERNAME && 
       password === process.env.ADMIN_PASSWORD) {
     // ...
   }
   
   // Option 2: Database check
   const adminUser = await db.getAdmin(username);
   const valid = await bcrypt.compare(password, adminUser.hashedPassword);
   
   // Option 3: SSO/OAuth for admins
   const adminSession = await verifyAdminOAuth(token);
   ```

4. **Additional Security**
   - IP whitelist for `/admin/*` routes
   - 2FA for admin login
   - Rate limiting on admin endpoints
   - Comprehensive audit logging
   - Regular security reviews

---

## 🚀 Routing Structure

### Public Routes

```
/                    → Landing Page
/login               → User Login
/signup              → User Signup
/dashboard           → User Dashboard
/onboarding          → Plan Selection (new users)
/connect-broker      → Broker Connection (onboarding)
```

### Admin Routes

```
/admin/login         → Admin Login
/admin/dashboard     → Admin Dashboard
```

**Route Protection:**
- Public routes: Open or require Supabase auth
- Admin routes: Require admin session

---

## 📊 Data Separation

### User Data (Scoped)
```sql
SELECT * FROM trades 
WHERE user_id = current_user_id;
```

**Users see:**
- Their own trades
- Their own P&L
- Their own brokers
- Their own logs

### Admin Data (Global)
```sql
SELECT * FROM trades;
-- No user_id filter
```

**Admins see:**
- All trades
- All users
- All brokers
- System metrics
- All logs

---

## 🔄 API Gateway Flow

### Public Request Flow

```
User Browser
  → Supabase Auth (get token)
  → Frontend (attach token to request)
  → API Gateway (validate token)
  → Extract user_id from token
  → Query database (WHERE user_id = ?)
  → Return user-scoped data
```

### Admin Request Flow

```
Admin Browser
  → Admin Login (get admin session)
  → Frontend (attach admin session)
  → API Gateway (validate admin)
  → Query database (no user filter)
  → Return all data
```

---

## 🧪 Testing

### Test Public Flow

1. Go to `/`
2. Click "Start Free Trial"
3. Sign up with email
4. Select a plan
5. Connect a broker
6. View dashboard (only your data)

### Test Admin Flow

1. Go to `/` (footer)
2. Click "Admin" link
3. Login with `admin` / `admin123`
4. View admin dashboard (all data)
5. Manage users
6. View system logs

---

## 📝 Implementation Checklist

### Frontend

- [x] Public landing page
- [x] User signup/login (Supabase)
- [x] User dashboard
- [x] Broker connection page
- [x] Analytics (user-scoped)
- [x] Billing portal
- [x] Admin login page
- [x] Admin dashboard
- [x] Route separation
- [x] Design system (#0EA5E9)

### Backend

- [ ] User authentication endpoints
- [ ] User-scoped API endpoints
- [ ] Admin authentication
- [ ] Admin management endpoints
- [ ] Webhook logging (all users)
- [ ] System health monitoring
- [ ] Broker registration
- [ ] API key generation

### Security

- [ ] Change admin credentials
- [ ] Implement proper admin auth
- [ ] Add IP whitelist for admin
- [ ] Enable audit logging
- [ ] Set up 2FA (optional)
- [ ] Rate limiting
- [ ] CORS configuration

### Deployment

- [ ] Separate admin subdomain (optional)
- [ ] Environment variables
- [ ] SSL certificates
- [ ] Monitoring setup
- [ ] Backup strategy

---

## 🎯 Key Differences Summary

| Feature | Public SaaS | Internal Admin |
|---------|-------------|----------------|
| **Access** | Public signup | Hardcoded login |
| **Auth** | Supabase | Admin session |
| **Data Scope** | User's only | All users |
| **Navigation** | Sidebar | Tabs |
| **Design** | Consumer | Professional |
| **Color Accent** | Blue | Purple |
| **Primary Goal** | Trading automation | Platform management |
| **Users** | Traders | Platform staff |
| **Routes** | `/dashboard` | `/admin/dashboard` |

---

## 💡 Best Practices

### For Public SaaS

1. **Never expose other users' data**
2. **Always validate user ID from token**
3. **Implement rate limiting**
4. **Cache user-specific data**
5. **Show helpful error messages**

### For Admin Portal

1. **Secure admin credentials**
2. **Log all admin actions**
3. **Use separate subdomain (optional)**
4. **Implement IP whitelist**
5. **Regular security audits**

---

## 📞 Access URLs

### Development

**Public:**
- Landing: `http://localhost:5173/`
- Login: `http://localhost:5173/login`
- Signup: `http://localhost:5173/signup`
- Dashboard: `http://localhost:5173/dashboard`

**Admin:**
- Admin Login: `http://localhost:5173/admin/login`
- Admin Dashboard: `http://localhost:5173/admin/dashboard`

### Production

**Public:**
- Landing: `https://tradeflow.fluxeo.net/`
- Dashboard: `https://tradeflow.fluxeo.net/dashboard`

**Admin (Option 1 - Same domain):**
- Admin: `https://tradeflow.fluxeo.net/admin/login`

**Admin (Option 2 - Subdomain - Recommended):**
- Admin: `https://admin.tradeflow.fluxeo.net/`

---

## 🔮 Future Enhancements

### Public SaaS
- Social auth (Google, GitHub)
- Mobile app
- Team accounts
- Advanced AI features
- White-label options

### Admin Portal
- Advanced analytics dashboard
- User impersonation (for support)
- Automated reports
- Alert triggers
- Cost analysis
- Performance monitoring

---

**Last Updated:** October 17, 2025  
**Version:** 6.0.0  
**Status:** Production Ready (Update admin credentials!)
