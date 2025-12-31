# ✅ TradeFlow Testing Checklist

Print this page and check off each item as you test!

---

## 🏠 Landing Page (/)

- [ ] Page loads without errors
- [ ] "Start Free Trial" (Hero) → Goes to signup
- [ ] "Login" button → Goes to login page
- [ ] "Features" nav link → Scrolls to features
- [ ] "Pricing" nav link → Scrolls to pricing
- [ ] "Integrations" nav link → Scrolls to integrations
- [ ] FAQ accordion expands/collapses
- [ ] Chatbot button opens chat widget
- [ ] Chatbot quick replies work
- [ ] "Start Trial" buttons in pricing cards → Signup

**Status:** _____ / 10

---

## 🔐 Login Page (/login)

- [ ] Email input accepts text
- [ ] Password input hides characters
- [ ] "Sign in to your account" submits form
- [ ] Wrong credentials show error
- [ ] Correct credentials → Dashboard
- [ ] "Start free trial" link → Signup
- [ ] "Forgot password?" shows placeholder

**Test Credentials:**
```
Email: demo@tradeflow.com
Password: demo123
```

**Status:** _____ / 7

---

## 📝 Signup Page (/signup)

- [ ] Full Name input accepts text
- [ ] Email input validates format
- [ ] Password input requires 6+ chars
- [ ] Confirm Password validates match
- [ ] Plan selection highlights chosen plan
- [ ] All 3 plans selectable (Starter/Pro/Elite)
- [ ] "Start Free Trial" creates account
- [ ] Success → Auto login → Dashboard
- [ ] "Login" link → Login page

**Status:** _____ / 9

---

## 📊 Dashboard - Navigation

- [ ] Dashboard loads after login
- [ ] Overview tab shows (default)
- [ ] Accounts tab changes content
- [ ] Positions tab changes content
- [ ] Orders tab changes content
- [ ] Risk tab changes content
- [ ] Webhooks tab changes content
- [ ] API Keys tab changes content
- [ ] Logs tab changes content
- [ ] Billing tab changes content
- [ ] Active tab is highlighted
- [ ] User avatar/name shows in header

**Status:** _____ / 12

---

## ⚙️ Dashboard - Settings Dropdown

- [ ] Click avatar → Dropdown opens
- [ ] "Light" theme → UI turns light
- [ ] "Dark" theme → UI turns dark
- [ ] "Auto" theme → Follows system
- [ ] Theme persists after refresh
- [ ] "Logout" → Returns to homepage
- [ ] After logout, /dashboard redirects

**Status:** _____ / 7

---

## 🏦 Accounts Tab

- [ ] Tab loads with 3 mock accounts
- [ ] Each account shows balance/equity
- [ ] "Add Account" button opens dialog
- [ ] TradeLocker form displays
- [ ] Fill TradeLocker form → "Auto Register" works
- [ ] API key displays after registration
- [ ] "Copy" button copies API key
- [ ] "Done" closes dialog
- [ ] Account enable/disable toggle works
- [ ] Refresh (sync) button logs to console
- [ ] Delete button removes account

**Status:** _____ / 11

---

## 📈 Positions Tab

- [ ] Tab shows 4 mock positions
- [ ] Symbol, Size, P&L columns visible
- [ ] P&L is color-coded (green=profit, red=loss)
- [ ] Account filter dropdown shows accounts
- [ ] Select account → Positions filter
- [ ] "All Accounts" shows all positions
- [ ] "Close Position" button appears
- [ ] Click "Close" → Position removed
- [ ] Refresh updates position list

**Status:** _____ / 9

---

## 📋 Orders Tab

- [ ] Tab shows 4 mock orders
- [ ] Status filter dropdown works
- [ ] "Pending" filter shows pending only
- [ ] "Filled" filter shows filled only
- [ ] "All" shows all orders
- [ ] Account filter works
- [ ] "Cancel Order" button appears on pending
- [ ] Click "Cancel" → Order status changes
- [ ] Refresh updates order list

**Status:** _____ / 9

---

## 🎯 Risk Tab

- [ ] Tab loads risk settings form
- [ ] Account select dropdown shows accounts
- [ ] Max Risk slider moves (0.01% steps)
- [ ] Default SL slider moves (0.01% steps)
- [ ] Default TP slider moves (0.01% steps)
- [ ] Max Position Size input accepts numbers
- [ ] Value displays update in real-time
- [ ] "Save Risk Settings" button works
- [ ] Success toast appears after save
- [ ] Position Size Calculator section visible
- [ ] Calculator inputs accept values
- [ ] "Calculate" button shows lot size result

**Status:** _____ / 12

---

## 🔗 Webhooks Tab

- [ ] Tab loads with template dropdown
- [ ] Template dropdown shows options
- [ ] "Long Entry with SL/TP" template loads JSON
- [ ] "Short Entry with SL/TP" template loads JSON
- [ ] "Close All Positions" template loads JSON
- [ ] JSON code is readable in textarea
- [ ] "Copy Webhook URL" button works
- [ ] URL copied to clipboard
- [ ] "Copy Alert JSON" button works
- [ ] JSON copied to clipboard
- [ ] Success toast shows after copy

**Status:** _____ / 11

---

## 🔑 API Keys Tab

- [ ] Tab shows 2 mock API keys
- [ ] Each key shows name, prefix, date
- [ ] "Generate New Key" opens dialog
- [ ] Name input accepts text
- [ ] Permission checkboxes toggle
- [ ] "Generate API Key" creates new key
- [ ] New key appears in list
- [ ] Key starts with "tfk_"
- [ ] "Copy" button on key works
- [ ] "Copy" button on secret works
- [ ] "Revoke" button removes key
- [ ] Webhook URL button shows URL

**Status:** _____ / 12

---

## 📜 Logs Tab

- [ ] Tab shows 5 mock log entries
- [ ] Entries have timestamps
- [ ] Level filter dropdown works
- [ ] "Info" filter shows info logs only
- [ ] "Warning" filter shows warnings only
- [ ] "Error" filter shows errors only
- [ ] "All" shows all logs
- [ ] Logs are color-coded by level
- [ ] Refresh button reloads logs
- [ ] Newest logs appear first

**Status:** _____ / 10

---

## 💳 Billing Tab

- [ ] Tab loads billing information
- [ ] Current plan is displayed
- [ ] Trial status shows (if active)
- [ ] Days remaining visible
- [ ] Trades used / limit visible
- [ ] "Upgrade Plan" button present
- [ ] Click "Upgrade" → Console logs URL
- [ ] "Cancel Subscription" button present
- [ ] Confirm cancel dialog appears
- [ ] Subscription cancels successfully

**Status:** _____ / 10

---

## 👤 Admin Panel (Admin Only)

⚠️ **Note:** Only visible if logged in as admin

- [ ] Admin tab appears in sidebar
- [ ] Tab shows user list
- [ ] 2 mock users displayed
- [ ] User columns: Email, Name, Role, Plan
- [ ] Role dropdown on each user
- [ ] Change role → Updates immediately
- [ ] Platform stats cards visible
- [ ] Total Users stat shows
- [ ] Active Trades stat shows
- [ ] Revenue stat shows

**Status:** _____ / 10

---

## 💬 Chatbot Widget

- [ ] Chatbot button visible (bottom-right)
- [ ] Click button → Chat opens
- [ ] Welcome message appears
- [ ] Quick reply buttons visible
- [ ] Click "MT4/MT5 EA Setup" → Response
- [ ] Click "Pricing Plans" → Response
- [ ] Type custom message → Response
- [ ] "Send" button works
- [ ] Enter key sends message
- [ ] support@fluxeo.net mentioned in responses
- [ ] Close button closes chat

**Status:** _____ / 11

---

## 📱 Mobile Responsiveness

**Test on Mobile (or DevTools mobile view):**

- [ ] Homepage is readable on mobile
- [ ] Navigation menu works
- [ ] Login form fits screen
- [ ] Signup form fits screen
- [ ] Dashboard sidebar adapts
- [ ] Tables scroll horizontally
- [ ] Cards stack vertically
- [ ] Buttons are touch-friendly
- [ ] Inputs are full-width
- [ ] No horizontal scroll issues

**Status:** _____ / 10

---

## 🐛 Error Handling

- [ ] Invalid login shows error alert
- [ ] Empty form shows validation
- [ ] Mismatched passwords show error
- [ ] Network errors handled gracefully
- [ ] Success toasts appear
- [ ] Error toasts appear
- [ ] Console logs errors
- [ ] No app crashes

**Status:** _____ / 8

---

## 🎨 Visual Polish

- [ ] Logo displays correctly
- [ ] Colors match brand (Navy/Teal/Lime)
- [ ] Fonts load properly
- [ ] Icons render correctly
- [ ] Hover states work
- [ ] Loading spinners appear
- [ ] Animations are smooth
- [ ] No layout shifts

**Status:** _____ / 8

---

## 🔧 Developer Console

Open DevTools (F12) and check:

- [ ] No red errors in console
- [ ] No 404 errors in Network tab
- [ ] API calls show in Network tab
- [ ] Mock backend responds
- [ ] React DevTools shows components
- [ ] localStorage has theme setting
- [ ] sessionStorage has auth token (if logged in)

**Status:** _____ / 7

---

## 🎯 Overall Test Summary

| Section | Items | Passed | Percentage |
|---------|-------|--------|------------|
| Landing Page | 10 | _____ | _____ % |
| Login Page | 7 | _____ | _____ % |
| Signup Page | 9 | _____ | _____ % |
| Dashboard Nav | 12 | _____ | _____ % |
| Settings Dropdown | 7 | _____ | _____ % |
| Accounts Tab | 11 | _____ | _____ % |
| Positions Tab | 9 | _____ | _____ % |
| Orders Tab | 9 | _____ | _____ % |
| Risk Tab | 12 | _____ | _____ % |
| Webhooks Tab | 11 | _____ | _____ % |
| API Keys Tab | 12 | _____ | _____ % |
| Logs Tab | 10 | _____ | _____ % |
| Billing Tab | 10 | _____ | _____ % |
| Admin Panel | 10 | _____ | _____ % |
| Chatbot | 11 | _____ | _____ % |
| Mobile | 10 | _____ | _____ % |
| Error Handling | 8 | _____ | _____ % |
| Visual Polish | 8 | _____ | _____ % |
| Dev Console | 7 | _____ | _____ % |
| **TOTAL** | **183** | **_____** | **_____ %** |

---

## ✅ Sign-Off

**Tested By:** _______________________  
**Date:** _______________________  
**Environment:** _______________________  
**Browser:** _______________________  
**Pass Rate:** _____ / 183 (_____ %)  

**Notes:**
_______________________________________________
_______________________________________________
_______________________________________________

---

## 🎉 Acceptance Criteria

- [ ] **Pass Rate ≥ 95%** (174+ / 183)
- [ ] **No critical bugs**
- [ ] **All core functions work**
- [ ] **Mobile responsive**
- [ ] **Error handling works**

**Status:** ☐ PASS  ☐ FAIL  ☐ NEEDS REVIEW

---

**Version:** 5.0  
**Last Updated:** October 16, 2025  
**Status:** Ready for Testing
