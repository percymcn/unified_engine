# Empire Trading Hub V5 - Implementation Priority Guide

## 🚀 CRITICAL PATH (SPRINT 1 - Week 1-2)

### P0: Database & Auth Foundation
**Estimated: 3-4 days**

1. **Supabase Setup**
   ```bash
   # Run schema
   psql $SUPABASE_DB_URL < supabase_schema_v5.sql
   
   # Enable Realtime
   ALTER PUBLICATION supabase_realtime ADD TABLE positions;
   ALTER PUBLICATION supabase_realtime ADD TABLE orders;
   ALTER PUBLICATION supabase_realtime ADD TABLE logs;
   ```

2. **Row-Level Security Testing**
   - Create test users (admin, user, viewer)
   - Verify RLS policies block unauthorized access
   - Test admin bypass with JWT role claim

3. **Credential Encryption**
   ```typescript
   // /utils/encryption.ts
   import crypto from 'crypto';
   
   const ENCRYPTION_KEY = process.env.ENCRYPTION_KEY!;
   
   export function encrypt(text: string): string {
     const iv = crypto.randomBytes(16);
     const cipher = crypto.createCipheriv('aes-256-gcm', Buffer.from(ENCRYPTION_KEY, 'hex'), iv);
     let encrypted = cipher.update(text, 'utf8', 'hex');
     encrypted += cipher.final('hex');
     const authTag = cipher.getAuthTag().toString('hex');
     return iv.toString('hex') + ':' + authTag + ':' + encrypted;
   }
   
   export function decrypt(encrypted: string): string {
     const parts = encrypted.split(':');
     const iv = Buffer.from(parts[0], 'hex');
     const authTag = Buffer.from(parts[1], 'hex');
     const encryptedText = parts[2];
     const decipher = crypto.createDecipheriv('aes-256-gcm', Buffer.from(ENCRYPTION_KEY, 'hex'), iv);
     decipher.setAuthTag(authTag);
     let decrypted = decipher.update(encryptedText, 'hex', 'utf8');
     decrypted += decipher.final('utf8');
     return decrypted;
   }
   ```

### P0: Realtime Integration
**Estimated: 2-3 days**

1. **Create Supabase Client Hook**
   ```typescript
   // /hooks/useSupabase.ts
   import { createClient } from '@supabase/supabase-js';
   import { useEffect, useState } from 'react';
   
   const supabase = createClient(
     process.env.NEXT_PUBLIC_SUPABASE_URL!,
     process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
   );
   
   export function useRealtimePositions(userId: string) {
     const [positions, setPositions] = useState([]);
     
     useEffect(() => {
       const channel = supabase
         .channel(`positions:${userId}`)
         .on('postgres_changes', {
           event: '*',
           schema: 'public',
           table: 'positions',
           filter: `user_id=eq.${userId}`
         }, (payload) => {
           // Update positions state
           console.log('Position update:', payload);
         })
         .subscribe();
         
       return () => { supabase.removeChannel(channel); };
     }, [userId]);
     
     return positions;
   }
   ```

2. **Update PositionsMonitor Component**
   - Replace mock data with `useRealtimePositions` hook
   - Display live P&L updates (green flash on increase, red on decrease)
   - Add toast notifications for new positions

### P0: HMAC Webhook Signing
**Estimated: 1-2 days**

1. **Generate Signed Webhook URLs**
   ```typescript
   // /utils/webhook.ts
   import crypto from 'crypto';
   
   export function generateWebhookSecret(): string {
     return 'whsec_' + crypto.randomBytes(32).toString('base64url');
   }
   
   export function signWebhookPayload(payload: any, secret: string): string {
     const timestamp = Math.floor(Date.now() / 1000);
     const signedPayload = `${timestamp}.${JSON.stringify(payload)}`;
     const signature = crypto
       .createHmac('sha256', secret)
       .update(signedPayload)
       .digest('hex');
     return `t=${timestamp},v1=${signature}`;
   }
   
   export function verifyWebhookSignature(
     payload: string,
     signature: string,
     secret: string,
     tolerance = 300
   ): boolean {
     const parts = signature.split(',');
     const timestamp = parseInt(parts[0].split('=')[1]);
     const receivedSig = parts[1].split('=')[1];
     
     // Check timestamp tolerance (5 min)
     const now = Math.floor(Date.now() / 1000);
     if (Math.abs(now - timestamp) > tolerance) return false;
     
     const signedPayload = `${timestamp}.${payload}`;
     const expectedSig = crypto
       .createHmac('sha256', secret)
       .update(signedPayload)
       .digest('hex');
       
     return crypto.timingSafeEqual(
       Buffer.from(receivedSig, 'hex'),
       Buffer.from(expectedSig, 'hex')
     );
   }
   ```

2. **Update WebhookTemplates Component**
   - Generate unique signing secret per broker account
   - Store in `broker_accounts.credentials_encrypted`
   - Display in UI with copy button

---

## 📊 HIGH PRIORITY (SPRINT 2 - Week 3-4)

### P1: Risk Heatmap Component
**Estimated: 3-4 days**

```typescript
// /components/RiskHeatmap.tsx
import { Treemap, ResponsiveContainer } from 'recharts';
import { useRealtimePositions } from '../hooks/useSupabase';

export function RiskHeatmap({ userId, broker }: Props) {
  const positions = useRealtimePositions(userId);
  
  const data = positions.map(pos => ({
    name: pos.symbol,
    size: pos.qty * pos.current_price,
    pnl: pos.unrealized_pnl,
    color: pos.unrealized_pnl >= 0 ? '#00ffc2' : '#ff4444'
  }));
  
  return (
    <ResponsiveContainer width="100%" height={400}>
      <Treemap
        data={data}
        dataKey="size"
        stroke="#002b36"
        fill="#001f29"
      >
        <Tooltip content={<CustomTooltip />} />
      </Treemap>
    </ResponsiveContainer>
  );
}
```

### P1: Equity Curve Chart
**Estimated: 2-3 days**

```typescript
// /components/EquityCurveChart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useEffect, useState } from 'react';
import { supabase } from '../utils/supabase';

export function EquityCurveChart({ userId, broker }: Props) {
  const [data, setData] = useState([]);
  
  useEffect(() => {
    async function fetchEquityHistory() {
      const { data: history } = await supabase
        .from('equity_history')
        .select('*')
        .eq('user_id', userId)
        .eq('broker', broker)
        .order('timestamp', { ascending: true });
        
      setData(history || []);
    }
    
    fetchEquityHistory();
    
    // Subscribe to realtime updates
    const channel = supabase
      .channel(`equity:${userId}:${broker}`)
      .on('postgres_changes', {
        event: 'INSERT',
        schema: 'public',
        table: 'equity_history',
        filter: `user_id=eq.${userId}`
      }, (payload) => {
        setData(prev => [...prev, payload.new]);
      })
      .subscribe();
      
    return () => { supabase.removeChannel(channel); };
  }, [userId, broker]);
  
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="timestamp" 
          tickFormatter={(ts) => new Date(ts).toLocaleDateString()}
          stroke="#94a3b8"
        />
        <YAxis stroke="#94a3b8" />
        <Tooltip 
          contentStyle={{ backgroundColor: '#001f29', border: '1px solid #334155' }}
          labelFormatter={(ts) => new Date(ts).toLocaleString()}
        />
        <Line 
          type="monotone" 
          dataKey="equity" 
          stroke="#00ffc2" 
          strokeWidth={2}
          dot={false}
        />
        <Line 
          type="monotone" 
          dataKey="balance" 
          stroke="#3b82f6" 
          strokeWidth={1}
          strokeDasharray="5 5"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

### P1: Test Alert Playground
**Estimated: 2-3 days**

```typescript
// /components/TestAlertPlayground.tsx
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Textarea } from './ui/textarea';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export function TestAlertPlayground({ broker }: Props) {
  const [jsonInput, setJsonInput] = useState('');
  const [parsed, setParsed] = useState<any>(null);
  const [errors, setErrors] = useState<string[]>([]);
  
  const handleTest = () => {
    try {
      const payload = JSON.parse(jsonInput);
      
      // Validate schema
      const validationErrors = validateOrderIntent(payload.intent);
      
      if (validationErrors.length > 0) {
        setErrors(validationErrors);
        setParsed(null);
      } else {
        setErrors([]);
        setParsed(payload);
      }
    } catch (e) {
      setErrors(['Invalid JSON format']);
      setParsed(null);
    }
  };
  
  return (
    <Card className="bg-[#001f29] border-gray-800">
      <CardHeader>
        <CardTitle className="text-white">Test Alert Playground</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label className="text-gray-300 mb-2 block">TradingView Alert JSON</Label>
          <Textarea
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
            placeholder='{"version": "unify.v1", "source": "tradingview", ...}'
            className="bg-[#002b36] border-gray-700 text-white font-mono h-64"
          />
        </div>
        
        <Button 
          onClick={handleTest}
          className="w-full bg-[#00ffc2] text-[#002b36]"
        >
          Test & Validate
        </Button>
        
        {errors.length > 0 && (
          <div className="p-4 bg-red-950 border border-red-800 rounded">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-5 h-5 text-red-400" />
              <h4 className="text-red-300">Validation Errors</h4>
            </div>
            <ul className="list-disc list-inside text-sm text-red-200 space-y-1">
              {errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          </div>
        )}
        
        {parsed && (
          <div className="space-y-3">
            <div className="p-4 bg-green-950 border border-green-800 rounded">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-5 h-5 text-green-400" />
                <h4 className="text-green-300">Valid Alert - Ready to Send</h4>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-[#002b36] rounded">
                <p className="text-xs text-gray-400 mb-1">Symbol</p>
                <p className="text-white">{parsed.intent.symbol}</p>
              </div>
              <div className="p-3 bg-[#002b36] rounded">
                <p className="text-xs text-gray-400 mb-1">Side</p>
                <Badge className={parsed.intent.side === 'buy' ? 'bg-green-600' : 'bg-red-600'}>
                  {parsed.intent.side.toUpperCase()}
                </Badge>
              </div>
              <div className="p-3 bg-[#002b36] rounded">
                <p className="text-xs text-gray-400 mb-1">Quantity</p>
                <p className="text-white">{parsed.intent.qty} ({parsed.intent.qty_mode})</p>
              </div>
              <div className="p-3 bg-[#002b36] rounded">
                <p className="text-xs text-gray-400 mb-1">Type</p>
                <p className="text-white">{parsed.intent.type.toUpperCase()}</p>
              </div>
            </div>
            
            {/* Order Visualization (mini chart) */}
            <OrderPreview order={parsed.intent} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function validateOrderIntent(intent: any): string[] {
  const errors: string[] = [];
  
  if (!intent.broker) errors.push('Missing broker');
  if (!intent.side || !['buy', 'sell'].includes(intent.side)) errors.push('Invalid side');
  if (!intent.type || !['market', 'limit', 'stop'].includes(intent.type)) errors.push('Invalid type');
  if (!intent.symbol) errors.push('Missing symbol');
  if (!intent.qty || intent.qty < 0.01) errors.push('Quantity must be >= 0.01');
  if (intent.type !== 'market' && !intent.price) errors.push('Price required for limit/stop orders');
  
  return errors;
}
```

---

## 🔐 SECURITY (SPRINT 3 - Week 5-6)

### P1: 2FA/TOTP Implementation
**Estimated: 3-4 days**

```typescript
// /utils/totp.ts
import * as speakeasy from 'speakeasy';
import * as QRCode from 'qrcode';

export function generateTOTPSecret(email: string) {
  return speakeasy.generateSecret({
    name: `Empire Trading (${email})`,
    issuer: 'Empire Trading Hub'
  });
}

export async function generateQRCode(secret: string): Promise<string> {
  return await QRCode.toDataURL(secret.otpauth_url);
}

export function verifyTOTP(token: string, secret: string): boolean {
  return speakeasy.totp.verify({
    secret,
    encoding: 'base32',
    token,
    window: 2 // Allow 1 step before/after for clock skew
  });
}

// /components/Enable2FA.tsx
export function Enable2FA() {
  const [secret, setSecret] = useState('');
  const [qrCode, setQrCode] = useState('');
  const [token, setToken] = useState('');
  
  const handleGenerate = async () => {
    const newSecret = generateTOTPSecret(user.email);
    const qr = await generateQRCode(newSecret.otpauth_url);
    setSecret(newSecret.base32);
    setQrCode(qr);
  };
  
  const handleVerify = async () => {
    const isValid = verifyTOTP(token, secret);
    if (isValid) {
      // Save to Supabase
      await supabase
        .from('profiles')
        .update({ totp_secret: secret, totp_enabled: true })
        .eq('id', user.id);
    }
  };
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Enable Two-Factor Authentication</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button onClick={handleGenerate}>Generate QR Code</Button>
        
        {qrCode && (
          <div className="flex flex-col items-center gap-4">
            <img src={qrCode} alt="QR Code" className="w-64 h-64" />
            <p className="text-sm text-gray-400">
              Scan with Google Authenticator or Authy
            </p>
            <Input 
              placeholder="Enter 6-digit code"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              maxLength={6}
            />
            <Button onClick={handleVerify}>Verify & Enable</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### P1: Stripe Webhooks
**Estimated: 2-3 days**

```typescript
// /api/webhooks/stripe.ts
import Stripe from 'stripe';
import { supabase } from '../../utils/supabase';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get('stripe-signature')!;
  
  let event: Stripe.Event;
  
  try {
    event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch (err) {
    return new Response('Webhook signature verification failed', { status: 400 });
  }
  
  switch (event.type) {
    case 'customer.subscription.created':
    case 'customer.subscription.updated':
      const subscription = event.data.object as Stripe.Subscription;
      
      // Update subscriptions table
      await supabase
        .from('subscriptions')
        .upsert({
          stripe_subscription_id: subscription.id,
          stripe_customer_id: subscription.customer as string,
          plan: subscription.items.data[0].price.lookup_key, // 'starter' | 'pro' | 'elite'
          status: subscription.status,
          current_period_start: new Date(subscription.current_period_start * 1000),
          current_period_end: new Date(subscription.current_period_end * 1000),
          trial_end: subscription.trial_end ? new Date(subscription.trial_end * 1000) : null
        });
      
      // Update user profile plan_tier
      await supabase
        .from('profiles')
        .update({ plan_tier: subscription.items.data[0].price.lookup_key })
        .eq('id', subscription.metadata.user_id);
      
      // Publish NATS event
      publishNATS('ai.user.billing.status', {
        user_id: subscription.metadata.user_id,
        plan: subscription.items.data[0].price.lookup_key,
        status: subscription.status
      });
      break;
      
    case 'customer.subscription.deleted':
      // Downgrade to free tier or suspend
      break;
      
    case 'invoice.payment_failed':
      // Send dunning email
      break;
  }
  
  return new Response(JSON.stringify({ received: true }), { status: 200 });
}
```

---

## 🎨 UX ENHANCEMENTS (SPRINT 4 - Week 7-8)

### P2: Theme Toggle
**Estimated: 1 day**

```typescript
// /components/ThemeToggle.tsx
import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';
import { Button } from './ui/button';

export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');
  
  useEffect(() => {
    const stored = localStorage.getItem('theme') as 'light' | 'dark';
    if (stored) {
      setTheme(stored);
      document.documentElement.classList.toggle('dark', stored === 'dark');
    }
  }, []);
  
  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
  };
  
  return (
    <Button variant="ghost" size="sm" onClick={toggleTheme}>
      {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </Button>
  );
}
```

### P2: Health Status Banner
**Estimated: 1-2 days**

```typescript
// /components/HealthStatusBanner.tsx
import { useEffect, useState } from 'react';
import { Alert, AlertDescription } from './ui/alert';
import { CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { supabase } from '../utils/supabase';

export function HealthStatusBanner() {
  const [status, setStatus] = useState<'healthy' | 'degraded' | 'down'>('healthy');
  const [brokers, setBrokers] = useState<any>({});
  
  useEffect(() => {
    // Fetch initial health
    fetch('/api/unify/v1/health')
      .then(res => res.json())
      .then(data => {
        setStatus(data.status);
        setBrokers(data.brokers);
      });
    
    // Subscribe to realtime health updates via NATS → Supabase
    const channel = supabase
      .channel('health:system')
      .on('broadcast', { event: 'health_update' }, (payload) => {
        setStatus(payload.status);
        setBrokers(payload.brokers);
      })
      .subscribe();
      
    return () => { supabase.removeChannel(channel); };
  }, []);
  
  if (status === 'healthy') return null;
  
  const icon = status === 'degraded' ? <AlertCircle /> : <XCircle />;
  const bgColor = status === 'degraded' ? 'bg-yellow-950' : 'bg-red-950';
  const borderColor = status === 'degraded' ? 'border-yellow-800' : 'border-red-800';
  const textColor = status === 'degraded' ? 'text-yellow-200' : 'text-red-200';
  
  return (
    <Alert className={`${bgColor} ${borderColor} mb-4`}>
      {icon}
      <AlertDescription className={textColor}>
        System Status: {status.toUpperCase()} - 
        {Object.entries(brokers).map(([broker, brokerStatus]) => (
          <span key={broker}> {broker}: {brokerStatus}</span>
        ))}
      </AlertDescription>
    </Alert>
  );
}
```

---

## 📱 MOBILE RESPONSIVE
**Estimated: 2-3 days**

```typescript
// Update App.tsx layout for mobile
<div className="min-h-screen bg-[#002b36] text-white">
  {/* Mobile: drawer sidebar */}
  <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
    <SheetTrigger asChild>
      <Button variant="ghost" size="sm" className="md:hidden">
        <Menu className="w-6 h-6" />
      </Button>
    </SheetTrigger>
    <SheetContent side="left" className="bg-[#001f29] w-64">
      {/* Sidebar nav */}
    </SheetContent>
  </Sheet>
  
  {/* Desktop: fixed sidebar */}
  <aside className="hidden md:block fixed left-0 top-16 h-[calc(100vh-4rem)] w-64">
    {/* Sidebar nav */}
  </aside>
  
  <main className="md:ml-64 p-4 md:p-6">
    {/* Content */}
  </main>
</div>
```

---

## 🔍 TESTING CHECKLIST

- [ ] RLS policies block unauthorized access
- [ ] Realtime updates reflect in UI < 1s
- [ ] HMAC signatures verify correctly
- [ ] Encrypted credentials decrypt properly
- [ ] 2FA codes validate within 60s window
- [ ] Stripe webhooks update subscriptions
- [ ] Rate limits block excessive requests
- [ ] Mobile layout responsive on 375px width
- [ ] Charts render without lag (< 100ms)
- [ ] Test alert playground catches invalid JSON

---

## 📦 DEPLOYMENT CHECKLIST

- [ ] Run `supabase_schema_v5.sql`
- [ ] Create Docker secrets (JWT, Stripe, encryption)
- [ ] Deploy `stack_v5.yml` to Swarm
- [ ] Configure DNS (app.*, api.*, metrics.*)
- [ ] Enable SSL with Let's Encrypt
- [ ] Configure NATS cluster (3 nodes)
- [ ] Test health monitor (/health returns 200)
- [ ] Set up Prometheus scraping
- [ ] Configure log retention (90 days)
- [ ] Test failover (kill 1 replica, verify recovery)

---

## 📈 SUCCESS METRICS

- **Performance**: P95 latency < 500ms for API calls
- **Uptime**: 99.9% availability (8.76h downtime/year)
- **Conversion**: 22% trial → paid (vs 15% baseline)
- **Revenue**: $19.58/day per 100 signups (vs $7.35)
- **Engagement**: 80% DAU/MAU ratio
- **Support**: < 4h response time for Pro/Elite

---

**READY TO SHIP!** 🚀
