# 💬 Support Chatbot - Complete Guide

## Overview

TradeFlow includes an intelligent support chatbot that provides instant help to users directly from the sidebar. The chatbot can answer common questions about MT4/MT5 setup, pricing plans, supported brokers, trial information, and provide contact details.

---

## 🎯 Features

### ✅ **Smart Response System**
- **Keyword Detection**: Automatically detects topic from user messages
- **Instant Responses**: No waiting for support team during common questions
- **Context-Aware**: Understands variations of questions

### ✅ **Two Display Modes**
1. **Sidebar Integration** (Desktop Dashboard)
   - Always visible in navigation menu
   - Quick access without leaving current page
   - Online indicator shows availability
   
2. **Floating Button** (Optional)
   - Can be used on landing pages
   - Bottom-right corner placement
   - Animated notification badge

### ✅ **Quick Reply Buttons**
- MT4/MT5 EA Setup
- Pricing Plans
- Supported Brokers
- Trial Information
- Contact Support

### ✅ **Professional UI**
- Matches TradeFlow color scheme (#0EA5E9)
- Animated message bubbles
- Timestamp on each message
- Online/offline status indicator
- User and bot avatars

---

## 📍 Location & Access

### **Desktop Dashboard**
```
┌─────────────────────────────┐
│  Navigation Sidebar         │
├─────────────────────────────┤
│  📊 Dashboard               │
│  📈 Analytics               │
│  👥 Accounts                │
│  🔗 Webhooks                │
│  ⚙️  Trading Config          │
│  📋 Orders                  │
│  📊 Positions               │
│  🛡️  Risk                    │
│  🔑 API Keys                │
│  💳 Billing                 │
│  📋 Logs                    │
├─────────────────────────────┤
│  💬 Support Chat    🟢      │  ← Chatbot here
└─────────────────────────────┘
```

### **Mobile Dashboard**
- Access via hamburger menu (☰)
- Same position at bottom of navigation drawer
- Touch-optimized interface

---

## 🤖 How It Works

### **User Flow**

1. **Opening the Chat**
   ```
   User clicks "Support Chat" in sidebar
       ↓
   Chat window opens on right side
       ↓
   Bot greeting appears: "Hi! I'm the TradeFlow assistant..."
       ↓
   Quick reply buttons shown
   ```

2. **Asking a Question**
   ```
   User types question OR clicks quick reply
       ↓
   Message sent (appears on right, blue bubble)
       ↓
   Bot processes (600ms delay for natural feel)
       ↓
   Bot response appears (left, dark bubble with avatar)
       ↓
   Timestamp shown under each message
   ```

3. **Getting Help**
   ```
   Bot provides answer
       ↓
   If more help needed → Email link to support@fluxeo.net
       ↓
   User can continue conversation or close
   ```

---

## 📚 Knowledge Base

### **Topic Detection & Responses**

#### 1️⃣ **MT4/MT5 Setup**
**Triggers:** "mt4", "mt5", "ea", "expert advisor"

**Response:**
> MT4 and MT5 require the TradeFlow EA (Expert Advisor) installation. Download it from your dashboard after signup, install it in your MetaTrader platform, and configure your API credentials. Need help? Email support@fluxeo.net

**Example Questions:**
- "How do I set up MT4?"
- "Where do I install the EA?"
- "MT5 configuration help"

---

#### 2️⃣ **Pricing Plans**
**Triggers:** "price", "pricing", "plan", "cost"

**Response:**
> We offer 3 plans: Starter ($20/mo, 1 broker), Pro ($40/mo, 2 brokers + 1 Fluxeo strategy), and Elite ($60/mo, 3 brokers + 3 strategies). All plans include a 3-day or 100-trade trial. Contact support@fluxeo.net for custom plans.

**Example Questions:**
- "How much does it cost?"
- "What are your pricing plans?"
- "Show me plan options"

---

#### 3️⃣ **Supported Brokers**
**Triggers:** "broker", "tradelocker", "topstep", "truforex"

**Response:**
> TradeFlow supports TradeLocker, Topstep (ProjectX), and TruForex. MT4/MT5 require our EA installation. TradeLocker, Topstep, and TruForex work via API. Questions? Email support@fluxeo.net

**Example Questions:**
- "Which brokers do you support?"
- "Can I use TradeLocker?"
- "Does this work with Topstep?"

---

#### 4️⃣ **Trial Information**
**Triggers:** "trial", "free"

**Response:**
> Your trial lasts 3 days OR 100 trades, whichever comes first. No credit card required to start! After the trial, choose a plan to continue. Support: support@fluxeo.net

**Example Questions:**
- "How long is the trial?"
- "Is there a free trial?"
- "Do I need a credit card?"

---

#### 5️⃣ **Contact Support**
**Triggers:** "support", "help", "contact"

**Response:**
> You can reach our support team at support@fluxeo.net. We typically respond within 24 hours for all plans, with priority support for Pro and Elite members.

**Example Questions:**
- "How do I contact support?"
- "I need help with something"
- "Support email?"

---

#### 6️⃣ **Default Response**
**No specific triggers matched**

**Response:**
> I'm here to help! Ask me about MT4/MT5 EA setup, pricing, brokers, trials, or contact support@fluxeo.net directly.

---

## 🎨 Visual Design

### **Color Scheme**

| Element | Color | Usage |
|---------|-------|-------|
| Primary | `#0EA5E9` | Header gradient, user messages, buttons |
| Secondary | `#0284c7` | Header gradient end, hover states |
| Success | `#00ffc2` | Online indicator, active states |
| Background | `#001f29` | Chat window background |
| Message Bg | `#002b36` | Bot message background |
| Border | `#0EA5E9/30` | Window border, input border |
| Text | `white` | Primary text |
| Muted | `gray-400` | Timestamps, placeholders |

### **Chat Window Structure**

```
┌───────────────────────────────────┐
│  🤖 TradeFlow Support      🟢 ✕   │  ← Header (blue gradient)
├───────────────────────────────────┤
│                                   │
│  🤖 Hi! I'm the TradeFlow...      │  ← Bot message (left)
│     10:30 AM                      │
│                                   │
│              Hi, I need help! 👤  │  ← User message (right)
│                        10:31 AM   │
│                                   │
│  🤖 I'm here to help!...          │  ← Bot response (left)
│     10:31 AM                      │
│                                   │
├───────────────────────────────────┤
│  Quick replies:                   │  ← Quick replies (first 2 msgs)
│  [MT4/MT5] [Pricing] [Brokers]    │
│  [Trial] [Support]                │
├───────────────────────────────────┤
│  [Type your message...    ] [📤]  │  ← Input area
│  Or email support@fluxeo.net      │
└───────────────────────────────────┘
```

---

## 💻 Technical Implementation

### **Component Props**

```typescript
interface ChatbotProps {
  /** If true, renders as sidebar button. If false, floating button */
  inSidebar?: boolean;
  /** Optional CSS classes */
  className?: string;
}
```

### **Usage Examples**

#### **In Sidebar (Current Implementation)**
```tsx
import { Chatbot } from './components/Chatbot';

// Inside NavigationMenu component
<Chatbot inSidebar={true} />
```

#### **As Floating Button (Landing Pages)**
```tsx
import { Chatbot } from './components/Chatbot';

// Renders floating button in bottom-right
<Chatbot inSidebar={false} />
// or simply
<Chatbot />
```

### **Message State Management**

```typescript
interface Message {
  id: string;              // Unique identifier (timestamp)
  text: string;            // Message content
  sender: 'bot' | 'user';  // Who sent it
  timestamp: Date;         // When it was sent
}

const [messages, setMessages] = useState<Message[]>([
  // Initial bot greeting
  {
    id: '1',
    text: "Hi! I'm the TradeFlow assistant...",
    sender: 'bot',
    timestamp: new Date()
  }
]);
```

### **Response Logic**

```typescript
const getBotResponse = (userMessage: string): string => {
  const lower = userMessage.toLowerCase();
  
  // Check for keywords and return appropriate response
  if (lower.includes('mt4') || lower.includes('mt5')) {
    return botResponses.mt4;
  }
  // ... other checks
  
  return botResponses.default;
};
```

### **Send Message Flow**

```typescript
const handleSend = (text?: string) => {
  const messageText = text || inputValue.trim();
  if (!messageText) return;

  // 1. Add user message immediately
  const userMessage = {
    id: Date.now().toString(),
    text: messageText,
    sender: 'user',
    timestamp: new Date()
  };
  setMessages(prev => [...prev, userMessage]);
  setInputValue('');

  // 2. Add bot response after 600ms delay (natural feel)
  setTimeout(() => {
    const botMessage = {
      id: (Date.now() + 1).toString(),
      text: getBotResponse(messageText),
      sender: 'bot',
      timestamp: new Date()
    };
    setMessages(prev => [...prev, botMessage]);
  }, 600);
};
```

---

## 📱 Responsive Design

### **Desktop (>768px)**
- Chat window: 384px (sm:w-96)
- Fixed position: bottom-6 right-6
- Max height: 80vh (600px preferred)
- Full feature set

### **Mobile (<768px)**
- Chat window: 90vw
- Covers most of screen
- Touch-optimized buttons (44px min)
- Swipe-friendly message bubbles

### **Accessibility**
- ✅ Keyboard navigation (Enter to send)
- ✅ Screen reader labels (sr-only)
- ✅ Focus states on all interactive elements
- ✅ ARIA labels on icon buttons
- ✅ Color contrast meets WCAG AA

---

## 🎯 User Experience Features

### **1. Online Indicator**
```tsx
<span className="flex h-2 w-2">
  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ffc2] opacity-75"></span>
  <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00ffc2]"></span>
</span>
```
- Green pulsing dot shows bot is "online"
- Always active (24/7 availability)
- Visible on both sidebar button and chat header

### **2. Quick Replies**
- Only shown for first 2 messages
- Disappears after conversation starts
- One-click common questions
- Saves typing time

### **3. Timestamps**
```tsx
{message.timestamp.toLocaleTimeString([], { 
  hour: '2-digit', 
  minute: '2-digit' 
})}
```
- Shows when each message was sent
- Formatted to user's locale
- Positioned below message text

### **4. Smooth Animations**
```tsx
<motion.div
  initial={{ opacity: 0, y: 20, scale: 0.95 }}
  animate={{ opacity: 1, y: 0, scale: 1 }}
  exit={{ opacity: 0, y: 20, scale: 0.95 }}
>
```
- Chat window slides in from bottom
- Messages appear smoothly
- Button hover/tap animations

---

## 🔧 Customization

### **Adding New Responses**

1. **Add to botResponses object:**
```typescript
const botResponses = {
  // ... existing responses
  'newTopic': 'Your new response here. Contact support@fluxeo.net for more.',
};
```

2. **Add detection logic:**
```typescript
const getBotResponse = (userMessage: string): string => {
  const lower = userMessage.toLowerCase();
  
  // ... existing checks
  
  if (lower.includes('keyword1') || lower.includes('keyword2')) {
    return botResponses.newTopic;
  }
  
  return botResponses.default;
};
```

3. **Add quick reply (optional):**
```typescript
const quickReplies = [
  // ... existing replies
  'New Topic Name'
];
```

### **Changing Colors**

Update these Tailwind classes:

```typescript
// Primary blue → Change to your color
'bg-[#0EA5E9]'        // Replace with your primary color
'text-[#0EA5E9]'
'border-[#0EA5E9]/30'
'hover:bg-[#0284c7]'  // Replace with darker shade

// Success green → Keep or change
'bg-[#00ffc2]'
'text-[#00ffc2]'
```

### **Adjusting Response Delay**

```typescript
// Current: 600ms (natural conversation feel)
setTimeout(() => {
  // bot response
}, 600);

// Faster: 300ms (more instant)
// Slower: 1000ms (more thoughtful)
```

---

## 📊 Analytics & Tracking

### **Potential Metrics to Track**

```typescript
// Add tracking to handleSend:
const handleSend = (text?: string) => {
  const messageText = text || inputValue.trim();
  if (!messageText) return;
  
  // Track user message
  analytics.track('chatbot_message_sent', {
    message: messageText,
    topic: detectTopic(messageText),
    timestamp: new Date()
  });
  
  // ... rest of function
};
```

**Useful Metrics:**
- Total messages sent
- Most common topics
- Quick reply usage vs typed messages
- Time of day patterns
- User satisfaction (could add thumbs up/down)

---

## 🚀 Future Enhancements

### **Potential Features**

1. **AI Integration**
   - Connect to OpenAI API
   - More intelligent responses
   - Context-aware conversation

2. **Live Chat Handoff**
   - Button to connect to human agent
   - Escalation for complex issues
   - Business hours availability

3. **Multi-Language Support**
   - Detect user language
   - Translate responses
   - Localized quick replies

4. **Conversation History**
   - Save to localStorage
   - Resume previous conversations
   - Export chat transcript

5. **Rich Media**
   - Send images/videos
   - Tutorial links
   - Interactive guides

6. **Sentiment Analysis**
   - Detect frustration
   - Prioritize urgent requests
   - Offer human assistance

---

## 🔗 Integration Points

### **Where Chatbot Appears**

✅ **Dashboard** - Sidebar (always visible)
✅ **All Dashboard Pages** - Accessible from navigation
✅ **Mobile Menu** - Bottom of drawer

**Not Currently Used (But Available):**
- Landing Page (floating button)
- Login/Signup Pages (floating button)
- Admin Dashboard (could add)

### **To Add to Other Pages**

```tsx
import { Chatbot } from './components/Chatbot';

// At end of component, before closing tags
return (
  <div>
    {/* Your page content */}
    
    {/* Floating chatbot button */}
    <Chatbot />
  </div>
);
```

---

## 📧 Support Email Integration

The chatbot prominently displays support@fluxeo.net in:

1. **Chat footer** (always visible)
2. **All bot responses** (included in text)
3. **Quick reply button** ("Contact Support")

**Email Link:**
```tsx
<a href="mailto:support@fluxeo.net" className="text-[#0EA5E9] hover:underline">
  support@fluxeo.net
</a>
```

Clicking opens user's default email client with:
- **To:** support@fluxeo.net
- **Subject:** (empty, user fills in)
- **Body:** (empty, user fills in)

---

## ✅ Testing Checklist

### **Functionality**
- [ ] Sidebar button opens chat window
- [ ] Quick reply buttons send messages
- [ ] Typing and pressing Enter sends message
- [ ] Bot responds within 600ms
- [ ] Responses match keywords correctly
- [ ] Email link opens mail client
- [ ] Close button closes window
- [ ] Online indicator pulses

### **Responsiveness**
- [ ] Desktop: 384px width, positioned right
- [ ] Mobile: 90vw width, fits screen
- [ ] Messages wrap properly
- [ ] Scroll works with many messages
- [ ] Touch targets ≥44px on mobile

### **Design**
- [ ] Colors match TradeFlow theme
- [ ] Animations smooth
- [ ] Timestamps formatted correctly
- [ ] User messages right-aligned
- [ ] Bot messages left-aligned
- [ ] Avatars display correctly

---

## 🎉 Summary

The TradeFlow Support Chatbot provides:

✅ **Instant Help** - Answers common questions immediately
✅ **Always Accessible** - Sidebar placement, always visible
✅ **Professional Design** - Matches brand, smooth animations
✅ **Smart Responses** - Keyword detection, relevant answers
✅ **Easy Escalation** - Support email always available
✅ **Mobile Optimized** - Works great on all devices
✅ **No External Dependencies** - Fully self-contained
✅ **Extensible** - Easy to add new responses

Perfect for reducing support tickets while maintaining excellent user experience! 💬✨
