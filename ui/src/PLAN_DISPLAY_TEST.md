# 🧪 Plan Display Testing Guide

## Quick Test: Verify Dynamic Plan Display

---

## ✅ What to Check

The Billing Portal should now show the **user's actual selected plan**, not a hardcoded "Pro" plan.

---

## 🚀 Quick Test (2 Minutes)

### Test Setup:
```bash
npm run dev
# Open http://localhost:5173
```

### Test Cases:

#### Test 1: Default User (Pro Plan)
1. **Login:**
   ```
   Email: demo@tradeflow.com
   Password: demo123
   ```

2. **Navigate:** Dashboard → Billing tab

3. **Verify:**
   - ✅ **Pro** card has green border (#00ffc2)
   - ✅ Pro card shows "Current Plan" button (grayed out)
   - ✅ Subscription details show "Plan: Pro"
   - ✅ Subscription details show "Amount: $40.00"
   - ❌ Starter card should NOT have green border
   - ❌ Elite card should NOT have green border

---

#### Test 2: New User - Starter Plan
1. **Signup:**
   - Click "Start Free Trial" on homepage
   - Fill form:
     ```
     Name: Test Starter
     Email: starter@test.com
     Password: test123
     ```
   - Select: **○ Starter** plan
   - Click "Start Free Trial"

2. **Verify Signup:**
   - Should auto-login and go to dashboard

3. **Navigate:** Billing tab

4. **Verify:**
   - ✅ **Starter** card has green border
   - ✅ Starter card shows "Current Plan" button
   - ✅ Subscription shows "Plan: Starter"
   - ✅ Subscription shows "Amount: $20.00"
   - ❌ Pro card should show "Upgrade" button
   - ❌ Elite card should show "Upgrade" button

---

#### Test 3: New User - Elite Plan
1. **Logout** (Settings → Logout)

2. **Signup:**
   - Click "Start Free Trial"
   - Fill form:
     ```
     Name: Test Elite
     Email: elite@test.com
     Password: test123
     ```
   - Select: **○ Elite** plan
   - Click "Start Free Trial"

3. **Navigate:** Billing tab

4. **Verify:**
   - ✅ **Elite** card has green border
   - ✅ Elite card shows "Current Plan" button
   - ✅ Subscription shows "Plan: Elite"
   - ✅ Subscription shows "Amount: $60.00"
   - ❌ Starter card should show "Start Trial" button
   - ❌ Pro card should show "Upgrade" button

---

## 📊 Visual Checklist

### Current Plan Card Should Have:

```
┌─────────────────────────────────┐
│ ← GREEN BORDER (#00ffc2) →     │
│                                 │
│  Plan Name        [Popular]?   │
│  $XX / month                    │
│  [Trial]                        │
│                                 │
│  ✓ Feature 1                    │
│  ✓ Feature 2                    │
│  ✓ Feature 3                    │
│  ...                            │
│                                 │
│  ┌─────────────────────────┐   │
│  │   Current Plan          │   │  ← Gray, disabled
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

### Other Plan Cards Should Have:

```
┌─────────────────────────────────┐
│ ← GRAY BORDER (default) →       │
│                                 │
│  Plan Name                      │
│  $XX / month                    │
│  [Trial]                        │
│                                 │
│  ✓ Feature 1                    │
│  ✓ Feature 2                    │
│  ...                            │
│                                 │
│  ┌─────────────────────────┐   │
│  │   Upgrade / Start Trial │   │  ← Teal, clickable
│  └─────────────────────────┘   │
│                                 │
└─────────────────────────────────┘
```

---

## 🔍 Subscription Details Check

### For Starter Plan User:
```
┌─────────────────────────────────────┐
│  Current Subscription               │
├─────────────────────────────────────┤
│  Plan              Billing Cycle    │
│  Starter           Monthly          │  ← Should say "Starter"
│                                     │
│  Next Billing      Amount           │
│  Nov 14, 2025      $20.00           │  ← Should be $20.00
└─────────────────────────────────────┘
```

### For Pro Plan User:
```
┌─────────────────────────────────────┐
│  Current Subscription               │
├─────────────────────────────────────┤
│  Plan              Billing Cycle    │
│  Pro               Monthly          │  ← Should say "Pro"
│                                     │
│  Next Billing      Amount           │
│  Nov 14, 2025      $40.00           │  ← Should be $40.00
└─────────────────────────────────────┘
```

### For Elite Plan User:
```
┌─────────────────────────────────────┐
│  Current Subscription               │
├─────────────────────────────────────┤
│  Plan              Billing Cycle    │
│  Elite             Monthly          │  ← Should say "Elite"
│                                     │
│  Next Billing      Amount           │
│  Nov 14, 2025      $60.00           │  ← Should be $60.00
└─────────────────────────────────────┘
```

---

## 🐛 Common Issues

### Issue 1: All cards show green border
**Cause:** currentPlan logic error  
**Fix:** Check `BillingPortal.tsx` line ~20-60

### Issue 2: Shows "Pro" for all users
**Cause:** Not reading from UserContext  
**Fix:** Verify `const { user } = useUser()` is present

### Issue 3: Amount always $40.00
**Cause:** Not using dynamic price  
**Fix:** Check line ~174 uses `plans.find(p => p.id === currentPlan)?.price`

### Issue 4: No green border at all
**Cause:** CSS class not applied  
**Fix:** Check line ~77 `plan.current ? 'border-[#00ffc2] border-2'`

---

## 🎯 Expected Results Summary

| User Plan | Green Border On | Subscription Shows | Amount Shows |
|-----------|----------------|-------------------|--------------|
| Starter   | Starter card   | "Starter"         | "$20.00"     |
| Pro       | Pro card       | "Pro"             | "$40.00"     |
| Elite     | Elite card     | "Elite"           | "$60.00"     |

---

## 🔧 Developer Console Check

Open DevTools (F12) and check:

```javascript
// In Console, run:
// (After logging in)

// Check user object
console.log(user); 
// Should show: { plan: 'starter' | 'pro' | 'elite', ... }

// Check current plan
console.log(currentPlan);
// Should match user's selected plan
```

---

## ✅ Pass Criteria

**Test PASSES if:**
- ✅ Correct plan card has green border
- ✅ Correct plan shows "Current Plan" button
- ✅ Subscription details show correct plan name
- ✅ Subscription amount matches plan price
- ✅ Other plans show "Upgrade" or "Start Trial"
- ✅ No console errors

**Test FAILS if:**
- ❌ Wrong plan highlighted
- ❌ Multiple plans highlighted
- ❌ No plans highlighted
- ❌ Subscription shows wrong plan
- ❌ Amount doesn't match plan
- ❌ Console shows errors

---

## 📸 Screenshot Comparison

### ❌ BEFORE (Wrong):
```
Billing Portal showing:
- Pro card: GREEN BORDER ✓ (even for Starter users!)
- Subscription: "Plan: Pro" (hardcoded)
- Amount: "$40.00" (hardcoded)
```

### ✅ AFTER (Correct):
```
For Starter user:
- Starter card: GREEN BORDER ✓
- Pro card: Gray border
- Elite card: Gray border
- Subscription: "Plan: Starter" (dynamic)
- Amount: "$20.00" (dynamic)
```

---

## 🚀 Quick Verification (30 seconds)

**Fastest way to verify fix:**

1. Login as existing user
2. Go to Billing tab
3. Look for green border on plan card
4. Check if plan name matches in subscription details
5. ✅ Done!

**Expected:** Green border appears on the plan you selected during signup (or Pro for demo users)

---

## 📞 Troubleshooting

### If test fails:

1. **Clear browser cache:**
   ```
   Ctrl+Shift+Delete → Clear cached files
   ```

2. **Hard reload:**
   ```
   Ctrl+Shift+R (or Cmd+Shift+R on Mac)
   ```

3. **Check console for errors:**
   ```
   F12 → Console tab
   Look for red errors
   ```

4. **Verify file was updated:**
   ```bash
   # Check if BillingPortal.tsx has useUser import
   grep -n "useUser" components/BillingPortal.tsx
   ```

5. **Restart dev server:**
   ```bash
   # Stop current server (Ctrl+C)
   npm run dev
   ```

---

## 📝 Test Results Template

```
Date: ________________
Tester: ______________
Browser: _____________

Test 1 - Pro User (Default):
[ ] Green border on Pro card
[ ] Subscription shows "Pro"
[ ] Amount shows "$40.00"

Test 2 - Starter User:
[ ] Green border on Starter card
[ ] Subscription shows "Starter"
[ ] Amount shows "$20.00"

Test 3 - Elite User:
[ ] Green border on Elite card
[ ] Subscription shows "Elite"
[ ] Amount shows "$60.00"

Overall Result: [ ] PASS  [ ] FAIL

Notes:
_________________________________
_________________________________
```

---

**Test Created:** October 16, 2025  
**Version:** 5.0  
**Status:** Ready for Testing  
**Estimated Time:** 2-5 minutes
