# 🎯 Account Management System - Complete Guide

## Overview

The Account Management system allows users to:
- ✅ Connect multiple accounts per broker (based on subscription tier)
- ✅ Enable/disable accounts
- ✅ Refresh account data
- ✅ Edit account numbers
- ✅ Delete accounts
- ✅ View real-time account stats (Balance, Equity, P&L, P&L%)

---

## 🎫 Tier Limits

### Account Limits Per Broker

| Plan | Brokers | Accounts Per Broker | Monthly Cost |
|------|---------|---------------------|--------------|
| **Trial** | 1 | 1 | Free (3 days or 100 trades) |
| **Starter** | 1 | 1 | $20 |
| **Pro** | 2 | 2 | $40 |
| **Elite** | 3 | 3 | $60 |

### Examples

**Starter Plan:**
- ✅ TradeLocker Account 1
- ❌ Cannot add TradeLocker Account 2

**Pro Plan:**
- ✅ TradeLocker Account 1
- ✅ TradeLocker Account 2
- ✅ Topstep Account 1
- ✅ Topstep Account 2
- ❌ Cannot add TruForex (limit: 2 brokers)

**Elite Plan:**
- ✅ TradeLocker Account 1, 2, 3
- ✅ Topstep Account 1, 2, 3
- ✅ TruForex Account 1, 2, 3
- ✅ Full flexibility across all 3 brokers

---

## 📋 Account Management UI

### Header Section
```
┌────────────────────────────────────────────────────────────────┐
│  Account Management                         [+ Add Account]     │
│  Connect and configure your TradeLocker accounts                │
└────────────────────────────────────────────────────────────────┘
```

### Tier Info Card
```
┌────────────────────────────────────────────────────────────────┐
│  1 / 2 accounts used for TradeLocker                           │
│  Current plan: PRO                              [Upgrade Plan]  │
└────────────────────────────────────────────────────────────────┘
```

### Individual Account Card
```
┌────────────────────────────────────────────────────────────────┐
│  Main Trading Account   ✓ Connected   ACC-123456 ✏️            │
│  Last synced: 2 minutes ago                                     │
│                                         Enabled [Toggle] 🔄 🗑️  │
│                                                                 │
│  ┌──────────┬──────────┬──────────┬──────────┐                │
│  │ Balance  │ Equity   │  P&L     │  P&L %   │                │
│  │ $52,430  │ $53,677  │ +$1,247  │ +2.38%   │                │
│  └──────────┴──────────┴──────────┴──────────┘                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🎬 Account Operations

### 1. **Add Account**

**Button Location:** Top-right corner of Account Management page

**Flow:**
1. Click "Add Account"
2. If at tier limit → Show upgrade prompt
3. If under limit → Allow adding new account
4. Fill in broker credentials
5. Generate API key
6. Account appears in list

**Tier Enforcement:**
```typescript
const canAddMore = accounts.length < limit.accounts;

if (!canAddMore) {
  toast.error(`Upgrade to add more accounts. Current plan allows ${limit.accounts} account(s).`);
}
```

---

### 2. **Enable/Disable Account**

**Control:** Toggle switch on right side of account card

**Purpose:** Control which accounts receive trading signals

**Behavior:**
- ✅ **Enabled (Green):** Account receives all trading signals from webhooks
- ⏸️ **Disabled (Gray):** Account is paused, no trades executed
- 💾 **State Persisted:** Setting saved across sessions

**Use Case:**
```
User has 2 accounts:
- Main Account: ENABLED ← Receives trades
- Demo Account: DISABLED ← No trades, but still connected
```

**Code:**
```typescript
const handleToggle = async (accountId: string) => {
  setAccounts(accounts.map(acc => 
    acc.id === accountId ? { ...acc, enabled: !acc.enabled } : acc
  ));
  
  toast.success(`${account.accountName} ${!account.enabled ? 'enabled' : 'disabled'}`);
};
```

---

### 3. **Refresh Account Data**

**Button:** Circular arrow icon (🔄)

**Purpose:** Manually sync account data with broker

**Behavior:**
- Shows spinning animation while syncing
- Updates: Balance, Equity, P&L, Last Sync time
- Typically takes 2-5 seconds

**Visual Feedback:**
```typescript
<RefreshCw className={cn("w-4 h-4", isRefreshing === account.id && "animate-spin")} />
```

**API Call:**
```typescript
const handleRefresh = async (accountId: string) => {
  setIsRefreshing(accountId);
  try {
    await refreshBrokerData();
    
    setAccounts(accounts.map(acc =>
      acc.id === accountId ? { ...acc, lastSync: 'Just now' } : acc
    ));
    
    toast.success('Account data refreshed');
  } finally {
    setIsRefreshing(null);
  }
};
```

---

### 4. **Edit Account Number**

**Control:** Click the account number badge

**Purpose:** Update the account ID/number

**Flow:**
1. Click account number badge (e.g., "ACC-123456 ✏️")
2. Prompt appears: "Enter new account number:"
3. Type new number
4. Account ID updates immediately

**Code:**
```typescript
const handleEditAccountNumber = (accountId: string) => {
  const newNumber = prompt('Enter new account number:');
  if (newNumber) {
    setAccounts(accounts.map(acc =>
      acc.id === accountId ? { ...acc, accountId: newNumber } : acc
    ));
    toast.success('Account number updated');
  }
};
```

**Use Case:**
- User switches from demo account to live account
- Account number changes from DEMO-789012 → LIVE-456123
- Click edit, enter new number, done!

---

### 5. **Delete Account**

**Button:** Trash icon (🗑️) on far right

**Purpose:** Permanently remove account from platform

**Safety:**
- ⚠️ Shows confirmation dialog
- ⚠️ Action cannot be undone
- ✅ Removed from all systems (context, localStorage)

**Flow:**
```typescript
const handleDelete = async (accountId: string) => {
  const account = accounts.find(a => a.id === accountId);
  
  if (confirm(`Are you sure you want to delete ${account.accountName}?`)) {
    removeBrokerAccount(broker, accountId);
    setAccounts(accounts.filter(acc => acc.id !== accountId));
    toast.success(`${account.accountName} deleted`);
  }
};
```

---

## 🔗 Connect Broker Page Integration

### Multi-Account Support

**Before (Old Behavior):**
```
┌──────────────────────────────┐
│  TradeLocker                 │
│  [Already Connected] ✓       │  ← Disabled after 1 account
└──────────────────────────────┘
```

**After (New Behavior):**
```
┌──────────────────────────────┐
│  TradeLocker                 │
│  [+ Add Account (1/2)] ✓     │  ← Can add more!
└──────────────────────────────┘

┌──────────────────────────────┐
│  TradeLocker                 │
│  [🔒 Limit Reached (2/2)]    │  ← Upgrade needed
└──────────────────────────────┘
```

### Tier Limits Display

Shows at top of Connect Broker page:
```
┌────────────────────────────────────────────────┐
│  PRO  2 account(s) per broker • 2 broker(s) total│
└────────────────────────────────────────────────┘
```

### Add Account Flow

1. **Check Limit:**
   ```typescript
   const brokerAccountCount = connectedBrokers.filter(b => b.broker === brokerId).length;
   
   if (brokerAccountCount >= limits.accountsPerBroker) {
     toast.error(`You can only have ${limits.accountsPerBroker} account(s) per broker on ${currentTier} plan.`);
     return;
   }
   ```

2. **Allow Connection:**
   - If under limit → Show connection dialog
   - User fills credentials
   - Account added to context
   - Appears in "Connected Brokers" list

3. **Button States:**
   ```tsx
   {!canAdd ? (
     <>
       <Lock className="w-4 h-4 mr-2" />
       Limit Reached ({accountCount}/{limits.accountsPerBroker})
     </>
   ) : accountCount > 0 ? (
     <>
       <Plus className="w-4 h-4 mr-2" />
       Add Account ({accountCount}/{limits.accountsPerBroker})
     </>
   ) : (
     <>
       <Plus className="w-4 h-4 mr-2" />
       Connect Account
     </>
   )}
   ```

---

## 📊 Account Stats Display

### Real-Time Data

Each account card shows 4 key metrics:

| Metric | Description | Color Logic |
|--------|-------------|-------------|
| **Balance** | Total account balance | White |
| **Equity** | Current equity (balance + floating P&L) | White |
| **P&L** | Profit/Loss ($) | Green if positive, Red if negative |
| **P&L %** | Profit/Loss (%) | Green if positive, Red if negative |

### Calculation

```typescript
account.pnl = account.equity - account.balance;
account.pnlPercent = (account.pnl / account.balance) * 100;
```

### Example

```
Account Balance: $52,430
Account Equity:  $53,677
─────────────────────────
P&L: $53,677 - $52,430 = +$1,247 (Green)
P&L %: ($1,247 / $52,430) × 100 = +2.38% (Green)
```

---

## 🎯 BrokerContext Integration

### Adding Accounts

```typescript
addBrokerAccount({
  broker: 'tradelocker',
  accountId: 'acc-123456',
  accountName: 'Main Trading Account',
  connected: true,
  lastSync: new Date().toISOString()
});
```

### Removing Accounts

```typescript
removeBrokerAccount('tradelocker', 'acc-123456');
```

### Account State

All accounts stored in:
- **BrokerContext state:** `connectedBrokers` array
- **LocalStorage:** Persisted across sessions
- **Key:** `connectedBrokers`

### Data Structure

```json
[
  {
    "broker": "tradelocker",
    "accountId": "acc-123456",
    "accountName": "Main Trading Account",
    "connected": true,
    "lastSync": "2025-10-19T10:30:00.000Z"
  },
  {
    "broker": "tradelocker",
    "accountId": "demo-789012",
    "accountName": "Demo Account",
    "connected": false,
    "lastSync": "2025-10-19T09:15:00.000Z"
  }
]
```

---

## 💡 User Experience Flow

### Scenario: Pro User Adding Second TradeLocker Account

1. **Navigate to Accounts Tab**
   - See existing "Main Trading Account"
   - Tier info shows: "1 / 2 accounts used"

2. **Click "Add Account"**
   - Button enabled (not at limit)
   - Dialog opens with connection form

3. **Fill Credentials**
   - Account Name: "Scalping Account"
   - TL Username: scalper@email.com
   - TL Password: ********
   - Server: TOPFX-Live

4. **Register Account**
   - API key generated
   - Account added to list
   - Toast: "TradeLocker account connected!"

5. **Manage Accounts**
   - Main Account: ENABLED
   - Scalping Account: ENABLED
   - Both show real-time stats
   - Can toggle, refresh, edit, or delete either

6. **Try Adding Third Account**
   - Button shows: "🔒 Limit Reached (2/2)"
   - Click → Toast: "Upgrade to Elite to add more accounts"

---

## 🚀 Upgrade Prompts

### When Limit Reached

**Location 1: Account Management Page**
```
┌────────────────────────────────────────────────┐
│  2 / 2 accounts used for TradeLocker           │
│  Current plan: PRO              [Upgrade Plan] │
└────────────────────────────────────────────────┘
```

**Location 2: Connect Broker Page**
```
[🔒 Limit Reached (2/2)]  ← Button disabled
```

**Location 3: Add Account Click**
```
❌ Toast: "You can only have 2 account(s) per broker on PRO plan. Upgrade to add more."
```

### Upgrade Path

1. Click "Upgrade Plan" button
2. Redirected to Billing Portal
3. Select Elite plan ($60/mo)
4. Payment processed
5. Plan updated instantly
6. Can now add up to 3 accounts per broker

---

## 🔧 Technical Implementation

### AccountsManager Component

**Location:** `/components/AccountsManager.tsx`

**Key Features:**
- Reads from BrokerContext
- Filters accounts by active broker
- Enforces tier limits
- Handles CRUD operations (Create, Read, Update, Delete)
- Shows real-time stats
- Responsive design

### ConnectBrokerPage Component

**Location:** `/components/ConnectBrokerPage.tsx`

**Key Features:**
- Shows tier limits at top
- Displays account count per broker
- Allows adding multiple accounts
- Enforces tier limits
- Shows "Limit Reached" when at max
- Lists all connected accounts

### BrokerContext

**Location:** `/contexts/BrokerContext.tsx`

**Key Methods:**
- `addBrokerAccount(account)` - Add new account
- `removeBrokerAccount(broker, accountId)` - Delete account
- `switchBroker(broker, accountId)` - Switch active account
- `refreshBrokerData()` - Sync account data

---

## 📱 Mobile Responsive

All account management features work on mobile:
- ✅ Touch-friendly buttons (44px minimum)
- ✅ Stacked layouts on small screens
- ✅ Swipe-friendly cards
- ✅ Large tap targets for toggle switches
- ✅ Bottom sheet dialogs

---

## 🎉 Summary

The Account Management system provides:

✅ **Multi-Account Support** - Add multiple accounts per broker
✅ **Tier-Based Limits** - Enforce subscription plan restrictions
✅ **Full CRUD Operations** - Create, Read, Update, Delete accounts
✅ **Real-Time Stats** - Live balance, equity, P&L display
✅ **Enable/Disable** - Control which accounts receive signals
✅ **Manual Refresh** - Sync data on demand
✅ **Edit Account Numbers** - Update IDs easily
✅ **Safe Deletion** - Confirmation before removing
✅ **Upgrade Prompts** - Clear path to higher tiers
✅ **Visual Feedback** - Loading states, toasts, animations

**Result:** Users have complete control over their trading accounts with clear tier-based limitations and upgrade paths. 🚀
