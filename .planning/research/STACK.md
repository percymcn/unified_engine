# Stack Research: v1.1 Additions

**Researched:** 2026-01-20
**Domain:** Stripe Billing + Official Broker SDKs
**Confidence:** HIGH (verified via PyPI, npm, official docs)

## Executive Summary

v1.1 adds Stripe billing infrastructure and replaces placeholder broker adapters with official SDKs. The existing hexagonal architecture (BrokerPort interface, adapter pattern) maps perfectly to this integration. Stripe Python SDK 14.2.0 and Stripe.js 8.6.1 provide complete billing lifecycle management. For brokers: TradeLocker has an official Python SDK (0.56.2), TopStep uses project-x-py (3.5.9), MetaAPI provides metaapi-cloud-sdk (29.1.1), and Tradovate requires custom OAuth 2.0 implementation (no official Python SDK exists).

**Critical finding:** All broker SDKs except Tradovate have official Python libraries. Tradovate requires building a custom adapter using httpx + websockets for their REST/WebSocket API with OAuth 2.0 authentication.

---

## Stripe Integration

### Libraries

| Package | Version | Purpose | Confidence |
|---------|---------|---------|------------|
| `stripe` (Python) | 14.2.0 | Backend API operations | HIGH |
| `@stripe/stripe-js` | 8.6.1 | Frontend Stripe.js loader | HIGH |
| `@stripe/react-stripe-js` | 5.4.1 | React components for Elements | HIGH |
| `stripe` (Node.js) | 20.1.0 | Optional: server-side actions | MEDIUM |

**Installation:**
```bash
# Backend (Python)
pip install stripe==14.2.0

# Frontend (Next.js)
npm install @stripe/stripe-js@8.6.1 @stripe/react-stripe-js@5.4.1
```

**Why these versions:**
- stripe 14.2.0: Latest stable, supports Python 3.7-3.12, async support via `[async]` extra
- @stripe/stripe-js 8.6.1: Current stable, auto-loads latest Stripe.js from CDN (PCI compliance)
- @stripe/react-stripe-js 5.4.1: React 16.8+ support, works with existing React 18 setup

**What NOT to use:**
- `stripe-subscriptions` (PyPI): Third-party wrapper, unnecessary abstraction over official SDK
- Self-hosted Stripe.js: Violates PCI compliance (must load from js.stripe.com)
- Older stripe versions (<14.0): Deprecated Python 3.6 support, missing async features

### Environment Variables

```bash
# Backend (.env)
STRIPE_SECRET_KEY=sk_live_...              # Required: API operations
STRIPE_PUBLISHABLE_KEY=pk_live_...         # Required: Frontend config
STRIPE_WEBHOOK_SECRET=whsec_...            # Required: Webhook signature verification
STRIPE_API_VERSION=2025-12-15.clover       # Optional: Pin API version

# Product/Price IDs (create in Stripe Dashboard first)
STRIPE_PRICE_ID_BASIC=price_...            # Basic plan price ID
STRIPE_PRICE_ID_PRO=price_...              # Pro plan price ID
STRIPE_PRICE_ID_ENTERPRISE=price_...       # Enterprise plan price ID
```

### Integration Pattern with Hexagonal Architecture

**New Port Interface:**
```python
# app/domain/ports/billing_port.py
from abc import ABC, abstractmethod
from typing import Optional
from app.domain.entities.subscription import Subscription
from app.domain.value_objects import CustomerId, SubscriptionId

class BillingPort(ABC):
    """Port interface for billing operations."""

    @abstractmethod
    async def create_checkout_session(
        self,
        customer_id: CustomerId,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create checkout session, return session URL."""
        pass

    @abstractmethod
    async def create_portal_session(
        self,
        customer_id: CustomerId,
        return_url: str,
    ) -> str:
        """Create customer portal session, return portal URL."""
        pass

    @abstractmethod
    async def get_subscription(
        self,
        subscription_id: SubscriptionId,
    ) -> Optional[Subscription]:
        """Get subscription details."""
        pass

    @abstractmethod
    async def cancel_subscription(
        self,
        subscription_id: SubscriptionId,
        at_period_end: bool = True,
    ) -> Subscription:
        """Cancel subscription."""
        pass

    @abstractmethod
    async def handle_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> dict:
        """Verify and handle webhook event."""
        pass
```

**Stripe Adapter Implementation:**
```python
# app/infrastructure/adapters/stripe_adapter.py
import stripe
from app.domain.ports.billing_port import BillingPort
from app.config import settings

class StripeAdapter(BillingPort):
    """Stripe adapter implementing BillingPort."""

    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY

    async def create_checkout_session(
        self,
        customer_id: CustomerId,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        session = stripe.checkout.Session.create(
            customer=customer_id.value,
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    async def create_portal_session(
        self,
        customer_id: CustomerId,
        return_url: str,
    ) -> str:
        session = stripe.billing_portal.Session.create(
            customer=customer_id.value,
            return_url=return_url,
        )
        return session.url

    async def handle_webhook_event(
        self,
        payload: bytes,
        signature: str,
    ) -> dict:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
        return {"type": event.type, "data": event.data.object}
```

**Webhook Endpoint (FastAPI):**
```python
# app/api/routes/billing.py
from fastapi import APIRouter, Request, HTTPException, Depends
from app.domain.ports.billing_port import BillingPort

router = APIRouter(prefix="/billing", tags=["billing"])

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    billing: BillingPort = Depends(get_billing_port),
):
    payload = await request.body()  # Raw bytes required
    signature = request.headers.get("stripe-signature")

    try:
        event = await billing.handle_webhook_event(payload, signature)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    # Handle event types
    match event["type"]:
        case "checkout.session.completed":
            await handle_checkout_complete(event["data"])
        case "customer.subscription.updated":
            await handle_subscription_updated(event["data"])
        case "customer.subscription.deleted":
            await handle_subscription_deleted(event["data"])
        case "invoice.payment_failed":
            await handle_payment_failed(event["data"])

    return {"status": "ok"}
```

**Frontend (Next.js) Pattern:**
```typescript
// src/lib/stripe.ts
import { loadStripe } from '@stripe/stripe-js';

export const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
);

// src/app/pricing/page.tsx
'use client';
import { stripePromise } from '@/lib/stripe';

async function handleCheckout(priceId: string) {
  const response = await fetch('/api/checkout', {
    method: 'POST',
    body: JSON.stringify({ priceId }),
  });
  const { url } = await response.json();
  window.location.href = url;  // Redirect to Stripe Checkout
}
```

---

## Broker SDKs

### TradeLocker (tradelocker)

| Attribute | Value |
|-----------|-------|
| Package | `tradelocker` |
| Version | 0.56.2 |
| Python | >=3.11 |
| Confidence | HIGH |
| Source | [PyPI](https://pypi.org/project/tradelocker/), [GitHub](https://github.com/TradeLocker/tradelocker-python) |

**Installation:**
```bash
pip install tradelocker==0.56.2
```

**Environment Variables:**
```bash
TRADELOCKER_ENV_URL=https://api.tradelocker.com    # API environment
TRADELOCKER_USERNAME=your_username                  # Account username
TRADELOCKER_PASSWORD=your_password                  # Account password
TRADELOCKER_SERVER=server_id                        # Server identifier
```

**Why official SDK:**
- Direct mapping to existing `TradeLockerAdapter` pattern
- Officially maintained by TradeLocker
- Healthy release cadence (new version in past 3 months)
- Simplifies authentication flow (handles token refresh)

**Key API Methods:**
```python
from tradelocker import TLAPI

tl = TLAPI(
    environment_url=settings.TRADELOCKER_ENV_URL,
    username=settings.TRADELOCKER_USERNAME,
    password=settings.TRADELOCKER_PASSWORD,
    server=settings.TRADELOCKER_SERVER,
)

# Get instruments
instruments = tl.get_all_instruments()
instrument_id = tl.get_instrument_id_from_symbol_name("BTCUSD")

# Get price data
history = tl.get_price_history(instrument_id, "1h", start_ts, end_ts)
price = tl.get_latest_asking_price(instrument_id)

# Order management
order = tl.create_order(instrument_id, quantity=1.0, side="buy", type_="market")
tl.close_position(order_id)
```

**Adapter Integration:**
The existing `TradeLockerAdapter` wraps a `TradeLockerExecutor`. Replace the executor internals with official SDK calls while maintaining the same port interface.

### TopStep/ProjectX (project-x-py)

| Attribute | Value |
|-----------|-------|
| Package | `project-x-py` |
| Version | 3.5.9 |
| Python | >=3.8 (async-native) |
| Confidence | HIGH |
| Source | [PyPI](https://pypi.org/project/project-x-py/), [ReadTheDocs](https://project-x-py.readthedocs.io/) |

**Installation:**
```bash
pip install project-x-py==3.5.9
```

**Environment Variables:**
```bash
# Configuration via JSON file or environment
PROJECTX_API_KEY=your_api_key
PROJECTX_USERNAME=your_username
PROJECTX_API_URL=https://api.topstepx.com/api
PROJECTX_WEBSOCKET_URL=wss://api.topstepx.com
PROJECTX_TIMEZONE=US/Central
```

**Why this SDK:**
- High-performance async SDK for ProjectX Trading Platform
- 58+ TA-Lib compatible indicators
- Real-time WebSocket streaming
- Level 2 orderbook analysis

**Key Features:**
- Async session management
- Multi-account support
- Real-time position P&L
- Historical market data
- Pattern recognition (58+ indicators)

**Important Restrictions:**
- API Access: $29/month (50% off for Topstep traders)
- All trading must originate from personal device
- VPS/VPN/remote servers prohibited by Topstep ToS

**Adapter Pattern:**
```python
# app/infrastructure/adapters/topstep_adapter.py
from project_x_py import ProjectXClient
from app.domain.ports.broker_port import BrokerPort

class TopStepAdapter(BrokerPort):
    def __init__(self):
        self._client = None

    async def connect(self) -> bool:
        self._client = ProjectXClient(config_path="projectx_config.json")
        await self._client.connect()
        return True

    async def place_order(self, symbol, order_type, volume, **kwargs):
        return await self._client.orders.place(
            symbol=symbol.value,
            side=self._map_order_type(order_type),
            quantity=float(volume.value),
        )
```

### MetaAPI (metaapi-cloud-sdk)

| Attribute | Value |
|-----------|-------|
| Package | `metaapi-cloud-sdk` |
| Version | 29.1.1 |
| Python | >=3.8 |
| Confidence | HIGH |
| Source | [PyPI](https://pypi.org/project/metaapi-cloud-sdk/), [GitHub](https://github.com/metaapi/metaapi-python-sdk) |

**Installation:**
```bash
pip install metaapi-cloud-sdk==29.1.1
```

**Environment Variables:**
```bash
METAAPI_TOKEN=your_metaapi_token                   # MetaApi API token
METAAPI_ACCOUNT_ID=your_account_id                 # MT4/MT5 account ID
```

**Why MetaAPI (not direct MT4/MT5):**
- Cloud-based bridge to MT4/MT5 (no local terminal required)
- REST + WebSocket API
- Supports both MT4 and MT5
- Real-time synchronization
- CopyFactory trade copying included
- Free usage tier available

**Key Features:**
- Terminal state synchronization (positions, orders, quotes)
- Streaming quote updates
- Custom history storage (MongoDB, etc.)
- Connection health monitoring
- Quote streaming (G1: 1 tick/2.5s limit)

**Adapter Pattern:**
```python
# app/infrastructure/adapters/metaapi_adapter.py
from metaapi_cloud_sdk import MetaApi
from app.domain.ports.broker_port import BrokerPort

class MetaApiAdapter(BrokerPort):
    def __init__(self):
        self._api = None
        self._connection = None

    async def connect(self) -> bool:
        self._api = MetaApi(token=settings.METAAPI_TOKEN)
        account = await self._api.metatrader_account_api.get_account(
            settings.METAAPI_ACCOUNT_ID
        )
        self._connection = account.get_streaming_connection()
        await self._connection.connect()
        await self._connection.wait_synchronized()
        return True

    async def get_positions(self):
        terminal_state = self._connection.terminal_state
        return [
            self._to_domain_position(p)
            for p in terminal_state.positions
        ]

    async def get_quote(self, symbol):
        price = self._connection.terminal_state.price(symbol.value)
        return {"bid": price.bid, "ask": price.ask}
```

**Streaming Listener:**
```python
from metaapi_cloud_sdk import SynchronizationListener

class QuoteListener(SynchronizationListener):
    async def on_symbol_price_updated(self, instance_index, price):
        # Handle real-time quote update
        await self._publish_quote(price)

    async def on_position_updated(self, instance_index, position):
        # Handle position update
        await self._publish_position_update(position)
```

### Tradovate OAuth

| Attribute | Value |
|-----------|-------|
| Package | None (custom implementation) |
| Auth | OAuth 2.0 |
| API | REST + WebSocket |
| Confidence | MEDIUM |
| Source | [API Docs](https://api.tradovate.com/), [Community Python Client](https://github.com/cullen-b/Tradovate-Python-Client) |

**No Official Python SDK:** Tradovate does not provide an official Python library. Must build custom adapter using:
- `httpx` for REST API calls
- `websockets` for real-time data
- Custom OAuth 2.0 flow implementation

**Environment Variables:**
```bash
TRADOVATE_API_URL=https://live.tradovateapi.com/v1  # Live API
TRADOVATE_DEMO_URL=https://demo.tradovateapi.com/v1 # Demo API
TRADOVATE_WS_URL=wss://live.tradovateapi.com/v1     # WebSocket
TRADOVATE_CLIENT_ID=your_client_id                   # OAuth client ID
TRADOVATE_CLIENT_SECRET=your_client_secret           # OAuth client secret
TRADOVATE_DEVICE_ID=your_device_id                   # Device identifier
TRADOVATE_USERNAME=your_username                     # Account username
TRADOVATE_PASSWORD=your_password                     # Account password
```

**OAuth 2.0 Flow:**
```python
# 1. Get access token
POST /auth/accesstokenrequest
{
    "name": username,
    "password": password,
    "appId": client_id,
    "appVersion": "1.0",
    "deviceId": device_id,
    "cid": client_id,
    "sec": client_secret
}

# Response
{
    "accessToken": "...",
    "mdAccessToken": "...",
    "expirationTime": "2026-01-20T20:00:00Z",  # 1 hour limit
    "userId": 12345,
    "name": "username"
}

# 2. Renew before expiry (must renew within 1 hour)
POST /auth/renewaccesstoken
Authorization: Bearer <accessToken>
```

**Custom Adapter Pattern:**
```python
# app/infrastructure/adapters/tradovate_adapter.py
import httpx
from datetime import datetime, timedelta
from app.domain.ports.broker_port import BrokerPort

class TradovateAdapter(BrokerPort):
    def __init__(self):
        self._client = httpx.AsyncClient()
        self._access_token = None
        self._token_expiry = None

    async def connect(self) -> bool:
        await self._authenticate()
        return True

    async def _authenticate(self):
        response = await self._client.post(
            f"{settings.TRADOVATE_API_URL}/auth/accesstokenrequest",
            json={
                "name": settings.TRADOVATE_USERNAME,
                "password": settings.TRADOVATE_PASSWORD,
                "appId": settings.TRADOVATE_CLIENT_ID,
                "appVersion": "1.0",
                "deviceId": settings.TRADOVATE_DEVICE_ID,
                "cid": settings.TRADOVATE_CLIENT_ID,
                "sec": settings.TRADOVATE_CLIENT_SECRET,
            }
        )
        data = response.json()
        self._access_token = data["accessToken"]
        self._token_expiry = datetime.fromisoformat(
            data["expirationTime"].replace("Z", "+00:00")
        )

    async def _ensure_token_valid(self):
        if datetime.utcnow() >= self._token_expiry - timedelta(minutes=5):
            await self._renew_token()

    async def _renew_token(self):
        response = await self._client.post(
            f"{settings.TRADOVATE_API_URL}/auth/renewaccesstoken",
            headers={"Authorization": f"Bearer {self._access_token}"}
        )
        data = response.json()
        self._access_token = data["accessToken"]

    async def place_order(self, symbol, order_type, volume, **kwargs):
        await self._ensure_token_valid()
        response = await self._client.post(
            f"{settings.TRADOVATE_API_URL}/order/placeOrder",
            headers={"Authorization": f"Bearer {self._access_token}"},
            json={
                "accountId": self._account_id,
                "action": self._map_order_type(order_type),
                "symbol": symbol.value,
                "orderQty": int(volume.value),
                "orderType": "Market",
            }
        )
        return self._to_domain_order(response.json())
```

**Known Issues:**
- Token has 1-hour limit (must implement proactive renewal)
- Rate limits return 429 (implement exponential backoff)
- Only one WebSocket per user
- OAuth errors common with incorrect client setup

---

## Dependency Compatibility Matrix

| Component | Python Version | Notes |
|-----------|----------------|-------|
| Existing stack | 3.13 | Project uses Python 3.13 |
| stripe | >=3.7 | Compatible |
| tradelocker | >=3.11 | Compatible |
| project-x-py | >=3.8 | Compatible |
| metaapi-cloud-sdk | >=3.8 | Compatible |
| Tradovate (httpx) | >=3.8 | Compatible (httpx 0.25.2 already installed) |

**All SDKs are compatible with Python 3.13.**

---

## Updated requirements.txt Additions

```txt
# Billing
stripe==14.2.0

# Broker SDKs (Official)
tradelocker==0.56.2
project-x-py==3.5.9
metaapi-cloud-sdk==29.1.1

# Tradovate (using existing httpx + websockets)
# httpx==0.25.2 (already installed)
# websockets==12.0 (already installed)
```

---

## Updated package.json Additions

```json
{
  "dependencies": {
    "@stripe/stripe-js": "^8.6.1",
    "@stripe/react-stripe-js": "^5.4.1"
  }
}
```

---

## Confidence Assessment

| Component | Confidence | Notes |
|-----------|------------|-------|
| Stripe Python SDK | HIGH | Verified via PyPI (14.2.0), official docs |
| Stripe.js / React | HIGH | Verified via npm (8.6.1 / 5.4.1) |
| TradeLocker SDK | HIGH | Official SDK, PyPI verified (0.56.2) |
| project-x-py | HIGH | PyPI verified (3.5.9), active maintenance |
| MetaAPI SDK | HIGH | Official SDK, PyPI verified (29.1.1) |
| Tradovate OAuth | MEDIUM | No official SDK; based on API docs + community client |

---

## Architecture Integration Summary

The existing hexagonal architecture supports clean integration:

1. **New Port:** `BillingPort` for Stripe operations
2. **Existing Port:** `BrokerPort` already defines the interface for broker adapters
3. **New Adapters:**
   - `StripeAdapter` implements `BillingPort`
   - Update `TradeLockerAdapter` to use official `tradelocker` SDK
   - Create `TopStepAdapter` using `project-x-py`
   - Update `MetaApiAdapter` to use `metaapi-cloud-sdk`
   - Update `TradovateAdapter` with proper OAuth 2.0 flow

4. **Dependency Injection:** Register adapters in DI container based on configuration
5. **Event Integration:** Webhook events flow through existing `EventPort` for domain events

---

## Open Questions

1. **Stripe Pricing Model:** Need to decide on subscription tiers (Basic/Pro/Enterprise) and corresponding feature gates
2. **MetaAPI Tier:** Free tier has quote streaming limits (1 tick/2.5s); may need paid tier for real-time
3. **TopStep API Cost:** $29/month API access cost - include in SaaS pricing or pass through?
4. **Tradovate WebSocket:** Single connection limit may require connection pooling strategy

---

## Sources

### Primary (HIGH confidence)
- [stripe PyPI](https://pypi.org/project/stripe/) - Version 14.2.0 verified
- [tradelocker PyPI](https://pypi.org/project/tradelocker/) - Version 0.56.2 verified
- [project-x-py PyPI](https://pypi.org/project/project-x-py/) - Version 3.5.9 verified
- [metaapi-cloud-sdk PyPI](https://pypi.org/project/metaapi-cloud-sdk/) - Version 29.1.1 verified
- [Stripe API Docs](https://docs.stripe.com/api) - Customer Portal, Subscriptions, Webhooks
- [TradeLocker API](https://public-api.tradelocker.com/) - Official API documentation
- [ProjectX SDK Docs](https://project-x-py.readthedocs.io/) - SDK documentation

### Secondary (MEDIUM confidence)
- [Tradovate API](https://api.tradovate.com/) - Official API docs (no Python SDK)
- [MetaAPI Docs](https://metaapi.cloud/docs/client/) - Streaming API documentation
- [FastAPI Stripe Integration](https://www.fast-saas.com/blog/fastapi-stripe-integration/) - Integration patterns

### Tertiary (LOW confidence)
- [Tradovate Python Client](https://github.com/cullen-b/Tradovate-Python-Client) - Community client (reference only)
