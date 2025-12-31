# 📦 Migration Guide: v5.0 → v6.0

Guide for upgrading your TradeFlow installation from v5.0 to v6.0.

---

## 🎯 Overview

**v6.0 adds:**
- ✅ Onboarding flow (Plan Selection → Broker Connection)
- ✅ Analytics dashboard with charts
- ✅ Connect Broker page
- ✅ Stripe billing integration
- ✅ Enhanced user context
- ✅ New routing system

**Breaking changes:**
- ⚠️ App.tsx routing structure changed
- ⚠️ UserContext interface expanded
- ⚠️ Dashboard navigation updated
- ⚠️ BillingPortal props changed

---

## ⏱️ Migration Time

**Estimated time:** 30-60 minutes

**Difficulty:** Medium

**Requires:**
- Code changes
- Configuration updates
- Testing

---

## 📋 Pre-Migration Checklist

Before starting:

- [ ] Backup your current code
- [ ] Review [V6_UPGRADE_SUMMARY.md](V6_UPGRADE_SUMMARY.md)
- [ ] Ensure git working tree is clean
- [ ] Note your current customizations
- [ ] Have Stripe account ready (for billing features)

---

## 🔄 Step-by-Step Migration

### Step 1: Update Dependencies

```bash
# Pull latest changes (if using git)
git pull origin main

# Or manually update files
# See file list below

# Install new dependencies (if any)
npm install
```

**New files to add:**
```
/components/OnboardingPlanSelection.tsx
/components/ConnectBrokerPage.tsx
/components/AnalyticsPage.tsx
/utils/stripe-helpers.ts
/V6_UPGRADE_SUMMARY.md
/BACKEND_INTEGRATION_GUIDE.md
/USER_JOURNEY_MAP.md
/README_V6.md
/QUICK_START_V6.md
/MIGRATION_V5_TO_V6.md (this file)
```

**Files to update:**
```
/App.tsx
/components/Dashboard.tsx
/components/BillingPortal.tsx
/contexts/UserContext.tsx (minor changes)
```

---

### Step 2: Update App.tsx

**Old routing (v5.0):**
```typescript
type AppView = 'landing' | 'login' | 'signup' | 'dashboard';

// Simple routing
if (user) {
  return <Dashboard />;
}
```

**New routing (v6.0):**
```typescript
type AppView = 'landing' | 'login' | 'signup' | 'onboarding' | 'connect-broker' | 'dashboard';

// Add onboarding flow
const [onboardingComplete, setOnboardingComplete] = useState(false);

// Check if user needs onboarding
useEffect(() => {
  if (!loading && user) {
    const needsOnboarding = !user.plan || user.plan === 'trial';
    if (needsOnboarding && !onboardingComplete) {
      setView('onboarding');
    } else {
      setView('dashboard');
    }
  }
}, [user, loading, onboardingComplete]);
```

**Action:** Replace your App.tsx with the new version or merge changes.

---

### Step 3: Update Dashboard.tsx

**Changes:**
1. Added Analytics page
2. Added Connect Broker page
3. New imports

**Old navigation:**
```typescript
const sections = [
  { id: 'dashboard', name: 'Dashboard', icon: Activity },
  { id: 'accounts', name: 'Accounts', icon: Users },
  // ... other sections
];
```

**New navigation (v6.0):**
```typescript
const sections = [
  { id: 'dashboard', name: 'Dashboard', icon: Activity },
  { id: 'analytics', name: 'Analytics', icon: BarChart3 },     // NEW
  { id: 'connect', name: 'Connect Broker', icon: Users },      // NEW
  { id: 'accounts', name: 'Accounts', icon: Users },
  // ... other sections
];
```

**Add to renderSection():**
```typescript
case 'analytics':
  return <AnalyticsPage broker={activeBroker} />;
case 'connect':
  return <ConnectBrokerPage standalone={false} />;
```

**Add imports:**
```typescript
import { AnalyticsPage } from './AnalyticsPage';
import { ConnectBrokerPage } from './ConnectBrokerPage';
```

**Action:** Update your Dashboard.tsx with these additions.

---

### Step 4: Update BillingPortal.tsx

**Changes:**
1. Added Stripe integration
2. New imports
3. Button handlers

**Add imports:**
```typescript
import { useState } from 'react';
import { ExternalLink } from 'lucide-react';
import { 
  getStripeCheckoutUrl, 
  getStripePortalUrl, 
  updateSubscription, 
  cancelSubscription 
} from '../utils/stripe-helpers';
import { toast } from 'sonner@2.0.3';
```

**Add state:**
```typescript
const [loading, setLoading] = useState(false);
```

**Update buttons:**
See [BillingPortal.tsx](components/BillingPortal.tsx) for full implementation.

**Action:** Update button onClick handlers to use Stripe functions.

---

### Step 5: Add New Components

Copy these files to your project:

1. **OnboardingPlanSelection.tsx**
   - Location: `/components/`
   - Purpose: Plan selection page
   - Dependencies: Motion, Shadcn UI

2. **ConnectBrokerPage.tsx**
   - Location: `/components/`
   - Purpose: Broker connection wizard
   - Dependencies: Tabs, Forms, API client

3. **AnalyticsPage.tsx**
   - Location: `/components/`
   - Purpose: Analytics dashboard
   - Dependencies: Recharts

**Action:** Copy files from new codebase to your project.

---

### Step 6: Add Stripe Helpers

Create `/utils/stripe-helpers.ts`:

```typescript
export const STRIPE_PRICE_IDS = {
  starter: 'price_YOUR_ID',  // Replace with your IDs
  pro: 'price_YOUR_ID',
  elite: 'price_YOUR_ID'
};

// ... rest of file
```

**Action:** Copy stripe-helpers.ts and configure your Price IDs.

---

### Step 7: Update UserContext (Optional)

**Minor changes in v6.0:**

Added `setUser` export (already existed, just now used):
```typescript
export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  
  return (
    <UserContext.Provider value={{ 
      user, 
      setUser,  // Make sure this is exported
      // ... other values
    }}>
      {children}
    </UserContext.Provider>
  );
}
```

**Action:** Ensure `setUser` is in your UserContext value.

---

## 🔧 Configuration Updates

### 1. API Client

No changes needed if you're already using v5.0 api-client.

**Optional:** Review new broker endpoints in ConnectBrokerPage.

### 2. Stripe Configuration

**New in v6.0:**

Create Stripe products:
1. Go to Stripe Dashboard
2. Create 3 products
3. Get Price IDs
4. Update stripe-helpers.ts

### 3. Environment Variables

**Add (if deploying):**
```bash
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

**Existing (no changes):**
```bash
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
```

---

## 🧪 Testing After Migration

### Critical Paths to Test

#### 1. Existing Functionality (Should Still Work)
- [ ] Login/Logout
- [ ] Dashboard loads
- [ ] Orders page works
- [ ] Positions display
- [ ] Risk controls function
- [ ] API keys generate
- [ ] Admin panel (if admin)

#### 2. New Functionality (Should Now Work)
- [ ] Signup → Onboarding flow
- [ ] Plan selection page appears
- [ ] Broker connection wizard
- [ ] Analytics page renders
- [ ] Charts display data
- [ ] Billing upgrade redirects
- [ ] Stripe portal opens

#### 3. Regressions to Check
- [ ] No console errors
- [ ] Navigation works
- [ ] Mobile responsive
- [ ] Forms validate
- [ ] API calls succeed

---

## 🐛 Common Migration Issues

### Issue 1: "Cannot find module './AnalyticsPage'"

**Cause:** New component not added

**Solution:**
```bash
# Ensure file exists
ls components/AnalyticsPage.tsx

# If not, copy from new codebase
```

### Issue 2: "Property 'setUser' does not exist"

**Cause:** UserContext not updated

**Solution:** Add `setUser` to UserContext value object

### Issue 3: Onboarding shows every time

**Cause:** User always has plan set

**Solution:** Update onboarding logic or remove check temporarily

### Issue 4: Stripe checkout doesn't redirect

**Cause:** Placeholder URLs still in use

**Solution:** Update `STRIPE_PRICE_IDS` in stripe-helpers.ts

### Issue 5: Charts not rendering

**Cause:** Recharts not installed

**Solution:**
```bash
npm install recharts
```

---

## 🔄 Rollback Plan

If migration fails:

### Quick Rollback

```bash
# If using git
git checkout HEAD~1  # Go back one commit

# Or restore from backup
cp -r backup/v5/* .
```

### Selective Rollback

Keep new features but revert breaking changes:

1. Keep new components
2. Revert App.tsx to v5 routing
3. Remove Analytics/Connect from Dashboard nav
4. Remove Stripe helpers

This lets you keep code for later while staying on v5 behavior.

---

## 📊 Migration Checklist

Use this to track your progress:

**Code Changes:**
- [ ] App.tsx updated
- [ ] Dashboard.tsx updated
- [ ] BillingPortal.tsx updated
- [ ] UserContext checked
- [ ] New components added
- [ ] Stripe helpers added

**Configuration:**
- [ ] Stripe Price IDs set
- [ ] Environment variables added
- [ ] API endpoints configured

**Testing:**
- [ ] All v5 features work
- [ ] New onboarding works
- [ ] Analytics renders
- [ ] Broker connection works
- [ ] Billing integration works
- [ ] Mobile responsive
- [ ] No console errors

**Deployment:**
- [ ] Build successful
- [ ] Preview deployed
- [ ] Production tested
- [ ] Monitoring active

---

## 🚀 Post-Migration Tasks

After successful migration:

### 1. Update Documentation

- [ ] Update internal wiki
- [ ] Notify team of changes
- [ ] Update training materials

### 2. Monitor

- [ ] Watch error rates
- [ ] Check analytics
- [ ] Monitor user feedback
- [ ] Track new feature usage

### 3. Optimize

- [ ] Review bundle size
- [ ] Optimize images
- [ ] Enable caching
- [ ] Set up CDN

---

## 🎓 Learning the New Features

### For Developers

**Read:**
- [V6_UPGRADE_SUMMARY.md](V6_UPGRADE_SUMMARY.md) - Feature overview
- [BACKEND_INTEGRATION_GUIDE.md](BACKEND_INTEGRATION_GUIDE.md) - API integration
- Component source code - Inline comments

**Try:**
- Modify plan pricing
- Add a new broker
- Customize analytics charts
- Test Stripe checkout

### For Users

**Share:**
- [USER_JOURNEY_MAP.md](USER_JOURNEY_MAP.md) - User flow
- Updated user manual
- Demo video (if available)

---

## 💡 Migration Tips

### Tip 1: Incremental Migration

Don't do everything at once:

**Phase 1 (Day 1):**
- Add new components (no breaking changes)
- Test in isolation

**Phase 2 (Day 2):**
- Update routing
- Add to navigation
- Test flows

**Phase 3 (Day 3):**
- Configure Stripe
- Test billing
- Deploy

### Tip 2: Feature Flags

Add flags to control new features:

```typescript
const ENABLE_ONBOARDING = true;
const ENABLE_ANALYTICS = true;
const ENABLE_STRIPE = false;  // Enable later

if (ENABLE_ONBOARDING && needsOnboarding) {
  setView('onboarding');
}
```

### Tip 3: Keep Old Code

Comment out rather than delete:

```typescript
// Old routing (v5)
// if (user) {
//   return <Dashboard />;
// }

// New routing (v6)
if (user && view === 'dashboard') {
  return <Dashboard />;
}
```

---

## 📞 Need Help?

**Stuck on migration?**

1. Check [Troubleshooting](#common-migration-issues)
2. Review component source code
3. Check console for errors
4. Email: support@fluxeo.net

**Include in support request:**
- Current version (v5.0)
- Migration step you're on
- Error messages
- Browser console logs

---

## ✅ Migration Complete!

Congratulations! You've successfully upgraded to TradeFlow v6.0.

**Next steps:**
1. Explore new features
2. Gather user feedback
3. Plan customizations
4. Optimize performance

**Enjoy the new features! 🎉**

---

**Document Version:** 1.0  
**Last Updated:** October 17, 2025  
**TradeFlow Version:** v5.0 → v6.0
