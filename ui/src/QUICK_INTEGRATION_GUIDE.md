# 🚀 Quick Integration Guide - Backend HTML to TradeFlow

## 30-Second Overview
All ProjectX/Topstep backend HTML pages have been integrated into TradeFlow v6.0 as modern React components.

---

## 🎯 What Was Added

### New Pages (6)
1. **AccountSelectionPage** - Select synced accounts after broker connection
2. **ChangeAccountPage** - Switch between broker accounts
3. **SyncResultsPage** - View account sync status
4. **PasswordResetPage** - Reset password flow
5. **NotFoundPage** - 404 error page
6. **Success Toasts** - Integrated throughout app

---

## 🔗 How to Use New Features

### From Dashboard
```typescript
// Navigate to new pages
import { AccountSelectionPage } from './components/AccountSelectionPage';
import { ChangeAccountPage } from './components/ChangeAccountPage';
import { SyncResultsPage } from './components/SyncResultsPage';

// In your component
<Button onClick={() => setView('account-selection')}>
  Select Accounts
</Button>
```

### From Login Page
```typescript
// Password reset link already added
<LoginPage 
  onNavigateToPasswordReset={() => setView('password-reset')}
/>
```

---

## 📋 API Endpoints to Implement

```bash
# Account Management
POST   /api/accounts/activate          # Activate selected accounts
POST   /api/accounts/switch            # Switch active account
GET    /api/accounts/sync_results      # Get sync results
POST   /api/accounts/sync/{id}         # Retry sync

# Authentication
POST   /api/auth/reset-password        # Send reset email
```

---

## 🎨 Component Props

### AccountSelectionPage
```typescript
<AccountSelectionPage
  onComplete={() => navigate('dashboard')}
  onBack={() => navigate('accounts')}
/>
```

### ChangeAccountPage
```typescript
<ChangeAccountPage
  onComplete={() => navigate('dashboard')}
  onBack={() => navigate('accounts')}
/>
```

### SyncResultsPage
```typescript
<SyncResultsPage
  onBack={() => navigate('accounts')}
  onRetry={(id) => handleRetry(id)}
/>
```

### PasswordResetPage
```typescript
<PasswordResetPage
  onBack={() => navigate('login')}
  onSuccess={() => navigate('login')}
/>
```

---

## 🔄 User Flows

### Connect Broker → Select Accounts
```
ConnectBrokerPage
  ↓ (multiple accounts detected)
AccountSelectionPage
  ↓ (accounts activated)
Dashboard
```

### Switch Active Account
```
Dashboard
  ↓ (click "Change Account")
ChangeAccountPage
  ↓ (confirm switch)
Dashboard (refreshed)
```

### Password Reset
```
LoginPage
  ↓ (click "Forgot password?")
PasswordResetPage
  ↓ (email sent)
LoginPage
```

---

## 🎨 Design Tokens Used

```css
/* All components use existing design system */
--primary: #0EA5E9;        /* Sky blue */
--success: #10b981;        /* Green */
--warning: #f59e0b;        /* Amber */
--destructive: #ef4444;    /* Red */
```

---

## 📱 Mobile Support

All components are fully responsive:
- ✅ Touch-friendly buttons (44px min)
- ✅ Sticky action bars on mobile
- ✅ Full-screen modals on small screens
- ✅ Horizontal scroll tables
- ✅ Safe area padding for notched devices

---

## 🧪 Quick Test

```typescript
// Test account selection
navigate('account-selection');
// → Should show synced accounts with checkboxes

// Test account switching
navigate('change-account');
// → Should show radio buttons for account selection

// Test sync results
navigate('sync-results');
// → Should show success/failure summary

// Test password reset
navigate('password-reset');
// → Should show email input form

// Test 404
navigate('invalid-route');
// → Should show 404 page
```

---

## ✅ Checklist for Developers

### Frontend
- [ ] Import new components in App.tsx ✅ (Already done)
- [ ] Add navigation buttons in Dashboard
- [ ] Replace mock data with real API calls
- [ ] Test all user flows
- [ ] Test on mobile devices

### Backend
- [ ] Implement `/api/accounts/activate`
- [ ] Implement `/api/accounts/switch`
- [ ] Implement `/api/accounts/sync_results`
- [ ] Implement `/api/auth/reset-password`
- [ ] Set up email service for password reset

### Testing
- [ ] Unit tests for components
- [ ] E2E tests for user flows
- [ ] Accessibility testing
- [ ] Mobile responsive testing

---

## 🎯 Quick Commands

```bash
# View all new components
ls components/*Page.tsx

# Search for component usage
grep -r "AccountSelectionPage" .

# Test routing
# Navigate to: http://localhost:5173/account-selection
```

---

## 📞 Support

- **Documentation**: See `BACKEND_HTML_INTEGRATION_COMPLETE.md`
- **API Contract**: See `ui_contract.json`
- **Complete Guide**: See `PUBLIC_VS_ADMIN_GUIDE.md`

---

**Status**: ✅ Ready to use  
**Version**: 6.0.0  
**Updated**: October 18, 2025
