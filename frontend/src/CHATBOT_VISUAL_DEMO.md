# 💬 Support Chatbot - Visual Demo & Examples

## 🎨 UI Components Breakdown

### **Sidebar Button (Default State)**

```
┌─────────────────────────────────────┐
│  📋 Logs                            │
├─────────────────────────────────────┤  ← Separator line
│  💬 Support Chat            🟢      │  ← Chatbot button with pulse
└─────────────────────────────────────┘
     ↑                          ↑
   Icon                   Online indicator
                         (animated pulse)
```

**States:**
- **Default**: Gray text, transparent background
- **Hover**: White text, dark blue background (#002b36)
- **Active**: Conversation window opens

---

### **Chat Window - Full Layout**

```
┌──────────────────────────────────────────┐
│  🤖 TradeFlow Support     🟢 Online   ✕  │  ← Header (Blue Gradient)
│                                          │
├──────────────────────────────────────────┤
│                                          │
│  🤖  Hi! I'm the TradeFlow assistant.   │  ← Bot Message
│      How can I help you today?          │
│      10:30 AM                            │
│                                          │
│                     Hi, I need help! 👤  │  ← User Message
│                               10:31 AM   │
│                                          │
│  🤖  I'm here to help! Ask me about     │  ← Bot Response
│      MT4/MT5 EA setup, pricing,         │
│      brokers, trials, or contact...     │
│      10:31 AM                            │
│                                          │
├──────────────────────────────────────────┤
│  Quick replies:                          │  ← Quick Actions
│  ┌──────────────┐ ┌──────────────┐      │
│  │ MT4/MT5 EA   │ │ Pricing Plans│      │
│  └──────────────┘ └──────────────┘      │
│  ┌──────────────┐ ┌──────────────┐      │
│  │   Brokers    │ │    Trial     │      │
│  └──────────────┘ └──────────────┘      │
│  ┌──────────────┐                       │
│  │   Support    │                       │
│  └──────────────┘                       │
├──────────────────────────────────────────┤
│  ┌────────────────────────────┐  ┌───┐  │  ← Input Area
│  │ Type your message...       │  │ → │  │
│  └────────────────────────────┘  └───┘  │
│  Or email us at support@fluxeo.net      │
└──────────────────────────────────────────┘
```

---

## 💬 Conversation Examples

### **Example 1: MT4/MT5 Setup Help**

```
┌──────────────────────────────────────────┐
│  🤖 TradeFlow Support     🟢 Online   ✕  │
├──────────────────────────────────────────┤
│                                          │
│  🤖  Hi! I'm the TradeFlow assistant.   │
│      How can I help you today?          │
│      10:30 AM                            │
│                                          │
│                How do I set up MT4?  👤  │
│                               10:31 AM   │
│                                          │
│  🤖  MT4 and MT5 require the TradeFlow  │
│      EA (Expert Advisor) installation.  │
│      Download it from your dashboard    │
│      after signup, install it in your   │
│      MetaTrader platform, and configure │
│      your API credentials. Need help?   │
│      Email support@fluxeo.net           │
│      10:31 AM                            │
│                                          │
│              Thanks, that helps! 👤      │
│                               10:32 AM   │
│                                          │
└──────────────────────────────────────────┘
```

---

### **Example 2: Pricing Inquiry**

```
┌──────────────────────────────────────────┐
│  🤖 TradeFlow Support     🟢 Online   ✕  │
├──────────────────────────────────────────┤
│                                          │
│  🤖  Hi! I'm the TradeFlow assistant.   │
│      How can I help you today?          │
│      09:15 AM                            │
│                                          │
│      User clicked "Pricing Plans"        │
│                                          │
│  🤖  We offer 3 plans:                  │
│      • Starter ($20/mo, 1 broker)       │
│      • Pro ($40/mo, 2 brokers +         │
│        1 Fluxeo strategy)               │
│      • Elite ($60/mo, 3 brokers +       │
│        3 strategies)                    │
│                                          │
│      All plans include a 3-day or       │
│      100-trade trial. Contact           │
│      support@fluxeo.net for custom      │
│      plans.                             │
│      09:15 AM                            │
│                                          │
│           What about the trial? 👤       │
│                               09:16 AM   │
│                                          │
│  🤖  Your trial lasts 3 days OR 100     │
│      trades, whichever comes first.     │
│      No credit card required to start!  │
│      After the trial, choose a plan     │
│      to continue.                       │
│      Support: support@fluxeo.net        │
│      09:16 AM                            │
│                                          │
└──────────────────────────────────────────┘
```

---

### **Example 3: Using Quick Replies**

```
┌──────────────────────────────────────────┐
│  🤖 TradeFlow Support     🟢 Online   ✕  │
├──────────────────────────────────────────┤
│                                          │
│  🤖  Hi! I'm the TradeFlow assistant.   │
│      How can I help you today?          │
│      14:20 AM                            │
│                                          │
├──────────────────────────────────────────┤
│  Quick replies:                          │
│  ┌──────────────┐ ┌──────────────┐      │
│  │ MT4/MT5 EA   │ │ Pricing Plans│ ← Click
│  └──────────────┘ └──────────────┘      │
│                     ↓                    │
├──────────────────────────────────────────┤
│                                          │
│                    Pricing Plans 👤      │
│                               14:20 AM   │
│                                          │
│  🤖  We offer 3 plans: Starter ($20/mo, │
│      1 broker), Pro ($40/mo, 2 brokers  │
│      + 1 Fluxeo strategy)...            │
│      14:20 AM                            │
│                                          │
│  (Quick replies disappear after use)    │
│                                          │
└──────────────────────────────────────────┘
```

---

## 🎨 Color Scheme Details

### **Header Gradient**

```css
background: linear-gradient(to right, #0EA5E9, #0284c7);
```

**Visual:**
```
┌────────────────────────────────┐
│  #0EA5E9 ──────────► #0284c7  │  ← Smooth gradient
│  (Sky Blue)        (Ocean Blue)│
└────────────────────────────────┘
```

---

### **Message Bubbles**

#### **Bot Messages**
```
┌─────────────────────────────────┐
│  Background: #002b36            │  ← Dark teal
│  Border: 1px solid #6b7280      │  ← Gray border
│  Text: #e5e7eb                  │  ← Light gray
│  Timestamp: #9ca3af             │  ← Muted gray
└─────────────────────────────────┘
```

#### **User Messages**
```
┌─────────────────────────────────┐
│  Background: #0EA5E9            │  ← Primary blue
│  Border: none                   │
│  Text: white                    │
│  Timestamp: rgba(255,255,255,0.6) │  ← Translucent white
└─────────────────────────────────┘
```

---

### **Online Indicator Animation**

```
🟢 = Two overlapping circles:

Outer (pulsing):
  - Size: 8px (h-2 w-2)
  - Color: #00ffc2 (neon green)
  - Opacity: 75%
  - Animation: ping (expand & fade)

Inner (static):
  - Size: 8px (h-2 w-2)
  - Color: #00ffc2
  - Opacity: 100%
  - Position: centered on outer

Result: Pulsing green dot effect
```

**Animation Timeline:**
```
0ms    ●          (both circles same size)
200ms   ◉ ●       (outer expands)
400ms    ◉  ●     (outer expands more, fades)
600ms       ●     (outer disappears, cycle repeats)
```

---

## 📐 Sizing & Spacing

### **Desktop Layout**

```
Window Dimensions:
┌─────────────────────────────────┐
│  Width: 384px (sm:w-96)         │
│  Height: 600px                  │
│  Max Height: 80vh               │
│  Position: fixed bottom-6 right-6│
└─────────────────────────────────┘

Component Spacing:
┌─────────────────────────────────┐
│  Header: p-4 (16px padding)     │
├─────────────────────────────────┤
│  Messages: p-4 space-y-4        │
│    - 16px padding all sides     │
│    - 16px gap between messages  │
├─────────────────────────────────┤
│  Quick Replies: px-4 pb-2       │
│    - 8px bottom padding         │
├─────────────────────────────────┤
│  Input: p-4                     │
│    - 16px padding all sides     │
└─────────────────────────────────┘
```

---

### **Mobile Layout**

```
Window Dimensions:
┌─────────────────────────────────┐
│  Width: 90vw (90% of viewport) │
│  Height: 600px                  │
│  Max Height: 80vh               │
│  Position: fixed bottom-6 right-6│
└─────────────────────────────────┘

Touch Targets:
┌─────────────────────────────────┐
│  Min Height: 44px               │
│  Min Width: 44px                │
│  Ensures easy tapping           │
└─────────────────────────────────┘
```

---

## 🎭 States & Interactions

### **Sidebar Button States**

```
DEFAULT:
┌────────────────────────────────┐
│  💬 Support Chat         🟢    │  ← Gray text (#9ca3af)
└────────────────────────────────┘

HOVER:
┌────────────────────────────────┐
│  💬 Support Chat         🟢    │  ← White text, dark bg
└────────────────────────────────┘
    Background: #002b36

CLICKED:
┌────────────────────────────────┐
│  💬 Support Chat         🟢    │  ← Chat window opens →
└────────────────────────────────┘
```

---

### **Chat Window States**

```
OPENING:
- Opacity: 0 → 1
- Y position: +20px → 0
- Scale: 0.95 → 1
- Duration: 300ms

CLOSING:
- Opacity: 1 → 0
- Y position: 0 → +20px
- Scale: 1 → 0.95
- Duration: 300ms
```

---

### **Message Sending Flow**

```
STEP 1: User types
┌────────────────────────────┐
│ How do I set up MT4?  |    │  ← Text in input
└────────────────────────────┘

STEP 2: User presses Enter or clicks Send
┌────────────────────────────┐
│                       |    │  ← Input cleared
└────────────────────────────┘

STEP 3: User message appears (instant)
             How do I set up MT4? 👤
                          10:31 AM

STEP 4: Bot "typing" indicator (600ms delay)
  🤖 ...

STEP 5: Bot response appears
  🤖  MT4 and MT5 require the TradeFlow
      EA installation. Download...
      10:31 AM
```

---

## 🎯 Avatar Display

### **Bot Avatar**

```
┌────────┐
│   🤖   │  ← Blue circle (#0EA5E9)
│        │     White robot icon (Bot)
└────────┘     Size: 32px (w-8 h-8)
```

Position: Left side of bot messages

---

### **User Avatar**

```
┌────────┐
│   👤   │  ← Green circle (#00ffc2)
│        │     Dark user icon
└────────┘     Size: 32px (w-8 h-8)
```

Position: Right side of user messages

---

## 📱 Responsive Breakpoints

### **Desktop (≥768px)**
```
Sidebar:
- Always visible
- Left side navigation
- Chatbot at bottom

Chat Window:
- 384px width (sm:w-96)
- Fixed right position
- Full feature set
```

### **Mobile (<768px)**
```
Sidebar:
- Hidden by default
- Hamburger menu (☰)
- Slide-in drawer

Chat Window:
- 90vw width (most of screen)
- Centered on screen
- Optimized touch targets
```

---

## 🎬 Animation Timeline

### **Chat Opening Animation**

```
Time    Opacity    Y Position    Scale
─────────────────────────────────────
0ms     0          +20px         0.95
100ms   0.3        +15px         0.97
200ms   0.6        +8px          0.99
300ms   1.0        0px           1.0

Result: Smooth slide-up with slight zoom
```

### **Online Indicator Pulse**

```
Time    Size    Opacity    
──────────────────────────
0ms     8px     75%        ●
300ms   12px    50%         ◉
600ms   16px    25%          ◉
900ms   20px    0%            ○
1000ms  8px     75%        ●  (restart)

Result: Expanding ripple effect
```

---

## ✨ Interactive Elements

### **Quick Reply Buttons**

```
DEFAULT:
┌─────────────────┐
│  Pricing Plans  │  ← Dark bg, blue text, blue border
└─────────────────┘

HOVER:
┌─────────────────┐
│  Pricing Plans  │  ← Blue/10% bg, blue text
└─────────────────┘

CLICKED:
(Quick reply disappears, message sent as user)
```

**Styling:**
```css
background: #002b36
color: #0EA5E9
border: 1px solid rgba(14, 165, 233, 0.3)
border-radius: 9999px (fully rounded)
padding: 6px 12px
```

---

### **Send Button**

```
DEFAULT:
┌─────┐
│  →  │  ← Blue bg (#0EA5E9), white icon
└─────┘

HOVER:
┌─────┐
│  →  │  ← Darker blue (#0284c7)
└─────┘

DISABLED (empty input):
┌─────┐
│  →  │  ← Muted, can't click
└─────┘
```

---

## 🔤 Typography

### **Message Text**
```
Font Size: 14px (text-sm)
Line Height: 1.5 (leading-relaxed)
Font Weight: 400 (normal)
Color: white (user), #e5e7eb (bot)
```

### **Timestamps**
```
Font Size: 12px (text-xs)
Opacity: 60%
Color: inherited from message
Margin Top: 4px (mt-1)
```

### **Header Title**
```
Font Size: 16px (base)
Font Weight: 600 (semibold)
Color: white
```

### **Online Status**
```
Font Size: 12px (text-xs)
Color: rgba(255, 255, 255, 0.8)
```

---

## 🎨 Complete Color Reference

| Element | CSS Class | Hex Value | RGB |
|---------|-----------|-----------|-----|
| Primary Blue | bg-[#0EA5E9] | #0EA5E9 | rgb(14, 165, 233) |
| Dark Blue | bg-[#0284c7] | #0284c7 | rgb(2, 132, 199) |
| Success Green | bg-[#00ffc2] | #00ffc2 | rgb(0, 255, 194) |
| Dark Teal | bg-[#001f29] | #001f29 | rgb(0, 31, 41) |
| Message Bg | bg-[#002b36] | #002b36 | rgb(0, 43, 54) |
| Border Gray | border-gray-700 | #374151 | rgb(55, 65, 81) |
| Border Gray-800 | border-gray-800 | #1f2937 | rgb(31, 41, 55) |
| Text White | text-white | #ffffff | rgb(255, 255, 255) |
| Text Gray-200 | text-gray-200 | #e5e7eb | rgb(229, 231, 235) |
| Text Gray-400 | text-gray-400 | #9ca3af | rgb(156, 163, 175) |
| Text Gray-500 | text-gray-500 | #6b7280 | rgb(107, 114, 128) |

---

## 📏 Component Measurements

```
Chat Window:
├─ Width: 384px (desktop), 90vw (mobile)
├─ Height: 600px (preferred)
├─ Max Height: 80vh
├─ Border Radius: 16px (rounded-2xl)
├─ Box Shadow: 0 25px 50px -12px rgba(0,0,0,0.5)
└─ Z-Index: 50

Header:
├─ Height: auto (content-based)
├─ Padding: 16px all sides
└─ Gradient: linear-gradient(90deg, #0EA5E9, #0284c7)

Message Bubble:
├─ Max Width: 85%
├─ Padding: 10px 16px
├─ Border Radius: 16px
├─ User: rounded-br-none (sharp bottom-right)
└─ Bot: rounded-bl-none (sharp bottom-left)

Avatar:
├─ Size: 32px × 32px
├─ Border Radius: 50% (circle)
└─ Margin: 0 8px

Input:
├─ Height: 40px
├─ Padding: 8px 12px
├─ Border Radius: 8px
└─ Border: 1px solid #374151

Send Button:
├─ Size: 40px × 40px
└─ Border Radius: 8px
```

---

## 🎉 Complete Example: Full Conversation

```
┌──────────────────────────────────────────────────────────┐
│  🤖 TradeFlow Support              🟢 Online         ✕   │
│────────────────────────────────────────────────────────  │
│                                                          │
│  🤖  Hi! I'm the TradeFlow assistant.                   │
│      How can I help you today?                          │
│      09:00 AM                                            │
│                                                          │
│                    Which brokers do you support? 👤      │
│                                            09:01 AM      │
│                                                          │
│  🤖  TradeFlow supports TradeLocker, Topstep            │
│      (ProjectX), and TruForex. MT4/MT5 require our      │
│      EA installation. TradeLocker, Topstep, and         │
│      TruForex work via API. Questions? Email            │
│      support@fluxeo.net                                 │
│      09:01 AM                                            │
│                                                          │
│                            How much does it cost? 👤     │
│                                            09:02 AM      │
│                                                          │
│  🤖  We offer 3 plans: Starter ($20/mo, 1 broker),      │
│      Pro ($40/mo, 2 brokers + 1 Fluxeo strategy),       │
│      and Elite ($60/mo, 3 brokers + 3 strategies).      │
│      All plans include a 3-day or 100-trade trial.      │
│      Contact support@fluxeo.net for custom plans.       │
│      09:02 AM                                            │
│                                                          │
│                                 Perfect, thanks! 👤      │
│                                            09:03 AM      │
│                                                          │
│────────────────────────────────────────────────────────  │
│  ┌───────────────────────────────────────────┐  ┌────┐  │
│  │  Type your message...                     │  │ →  │  │
│  └───────────────────────────────────────────┘  └────┘  │
│  Or email us at support@fluxeo.net                      │
└──────────────────────────────────────────────────────────┘
```

This visual guide shows exactly how the chatbot looks and behaves! 🎨✨
