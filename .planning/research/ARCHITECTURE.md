# Architecture Research: v1.1 Integrations

**Researched:** 2026-01-20
**Domain:** Stripe Billing + Broker OAuth Integration
**Confidence:** HIGH (for architecture patterns), MEDIUM (for Tradovate specifics)

## Executive Summary

This research addresses how Stripe billing and broker OAuth should integrate with Tradeflow's existing hexagonal architecture. The v1.0 architecture provides clear boundaries: domain entities, application use cases, and infrastructure adapters wired through a DI container.

**Key architectural decisions:**

1. **Stripe webhooks**: Create a new `PaymentPort` in domain, `StripeAdapter` in infrastructure. Subscription logic lives in application layer as `ManageSubscriptionUseCase`.

2. **Broker OAuth**: Extend existing `CredentialRepository` for OAuth token storage. OAuth callbacks are infrastructure concerns that trigger `LinkBrokerAccountUseCase` in application layer.

3. **Subscription gating**: Enforcement at application layer (use case guards), not domain. Domain knows about `SubscriptionTier` value object, not enforcement rules.

4. **Frontend routing**: Use Next.js route groups: `(marketing)` for landing page, `(dashboard)` for protected app. Middleware checks both auth AND subscription status.

**Primary recommendation:** Stripe and OAuth are infrastructure adapters behind ports. Subscription status is domain state on User entity. Feature gating is application layer policy.

## Stripe Integration Architecture

### New Ports/Adapters

**Domain Layer - New Port:**
```python
# app/domain/ports/payment_port.py
class PaymentPort(ABC):
    """Port for payment provider operations"""

    @abstractmethod
    async def create_checkout_session(
        self,
        user_id: int,
        price_id: str,
        success_url: str,
        cancel_url: str
    ) -> CheckoutSession:
        """Create a checkout session for subscription"""
        pass

    @abstractmethod
    async def create_customer_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> PortalSession:
        """Create customer portal session for self-service"""
        pass

    @abstractmethod
    async def get_subscription(self, subscription_id: str) -> Subscription:
        """Get subscription details"""
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> None:
        """Cancel a subscription"""
        pass
```

**Infrastructure Layer - Stripe Adapter:**
```python
# app/infrastructure/adapters/stripe_adapter.py
class StripeAdapter(PaymentPort):
    """Stripe implementation of PaymentPort"""

    def __init__(self):
        self._stripe = stripe
        self._stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
```

**Webhook Handler (Infrastructure):**
```python
# app/infrastructure/webhooks/stripe_webhook_handler.py
class StripeWebhookHandler:
    """Infrastructure component that receives webhooks and dispatches to use cases"""

    def __init__(
        self,
        manage_subscription_use_case: ManageSubscriptionUseCase,
        event_port: EventPort
    ):
        self._manage_subscription = manage_subscription_use_case
        self._event_port = event_port

    async def handle_webhook(self, payload: bytes, signature: str) -> None:
        """Verify signature, parse event, dispatch to appropriate use case"""
        event = self._verify_and_parse(payload, signature)

        match event.type:
            case "checkout.session.completed":
                await self._handle_checkout_completed(event)
            case "customer.subscription.updated":
                await self._handle_subscription_updated(event)
            case "customer.subscription.deleted":
                await self._handle_subscription_deleted(event)
            case "invoice.payment_failed":
                await self._handle_payment_failed(event)
```

### Data Flow

```
Stripe -> POST /webhooks/stripe -> FastAPI Router
    -> StripeWebhookHandler.handle_webhook()
    -> Signature verification (Stripe SDK)
    -> ManageSubscriptionUseCase.execute()
    -> UserRepository.save(updated_user)
    -> EventPort.publish(SubscriptionEvent)
    -> Response 200 to Stripe
```

**Webhook events to handle:**
| Event | Action | Domain Impact |
|-------|--------|---------------|
| `checkout.session.completed` | Create/activate subscription | User.subscription_tier = PRO |
| `customer.subscription.updated` | Sync subscription state | User.subscription_status updated |
| `customer.subscription.deleted` | Handle cancellation | User.subscription_tier = FREE |
| `invoice.payment_failed` | Handle payment failure | User.subscription_status = PAST_DUE |
| `invoice.paid` | Confirm payment | User.subscription_status = ACTIVE |

### Domain vs Infrastructure Concerns

**Domain Layer (app/domain/):**
- `SubscriptionTier` enum: FREE, PRO
- `SubscriptionStatus` enum: ACTIVE, PAST_DUE, CANCELLED, TRIALING
- `User` entity extended with subscription fields
- `PaymentPort` interface (what payment operations are available)

**Application Layer (app/application/use_cases/):**
- `ManageSubscriptionUseCase`: Orchestrates subscription lifecycle
- `CheckSubscriptionAccessUseCase`: Validates feature access
- Guards on existing use cases (e.g., `CreateAccountUseCase` checks tier limits)

**Infrastructure Layer (app/infrastructure/):**
- `StripeAdapter`: Implements `PaymentPort`
- `StripeWebhookHandler`: Receives and verifies webhooks
- `SQLAlchemyUserRepository`: Persists subscription state

**Key principle:** Stripe-specific details (customer_id, subscription_id, price_id) are stored but domain logic only knows about tier and status.

### New Domain Entities/Value Objects

```python
# app/domain/enums.py (extend)
class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"
    INCOMPLETE = "incomplete"
```

```python
# app/domain/entities/user.py (new or extend existing)
@dataclass
class User:
    id: int
    email: str
    # ... existing fields

    # Subscription fields
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    subscription_status: Optional[SubscriptionStatus] = None
    stripe_customer_id: Optional[str] = None
    subscription_ends_at: Optional[datetime] = None

    @property
    def is_pro(self) -> bool:
        return (
            self.subscription_tier == SubscriptionTier.PRO and
            self.subscription_status == SubscriptionStatus.ACTIVE
        )

    @property
    def max_broker_accounts(self) -> int:
        return 1 if self.subscription_tier == SubscriptionTier.FREE else 99
```

## Broker OAuth Architecture

### Token Exchange Flow

**OAuth 2.0 Authorization Code Flow for Tradovate:**

```
1. User clicks "Connect Tradovate" in dashboard
   Frontend -> GET /api/auth/tradovate/authorize

2. Backend generates OAuth URL with state
   -> Redirect to Tradovate OAuth page

3. User authenticates with Tradovate
   -> Tradovate redirects to /auth/tradovate/callback?code=XXX&state=YYY

4. Frontend callback page extracts code
   -> POST /api/auth/tradovate/exchange { code, state }

5. Backend exchanges code for tokens
   -> POST https://live-api-d.tradovate.com/auth/oauthtoken
   -> Receives access_token (no refresh_token per Tradovate docs)

6. Backend encrypts and stores tokens
   -> CredentialRepository.create() with Fernet encryption

7. Backend creates/updates TradingAccount
   -> LinkBrokerAccountUseCase.execute()

8. Frontend redirects to dashboard
   -> Account appears as connected
```

### Credential Storage (Existing Fernet Pattern)

The existing `CredentialRepository` with Fernet encryption is perfect for OAuth tokens:

```python
# Existing pattern in app/infrastructure/repositories/credential_repository.py
# OAuth tokens stored as:
await credential_repo.create(
    credential_id=str(uuid4()),
    user_id=user.id,
    name=f"Tradovate - {account_name}",
    credential_type="oauth",
    service="tradovate",
    credential_data={
        "access_token": access_token,
        "md_access_token": md_access_token,  # Tradovate-specific
        "token_type": "Bearer",
        "obtained_at": datetime.utcnow().isoformat(),
    },
    expires_at=datetime.utcnow() + timedelta(hours=24),  # Tradovate tokens expire
)
```

**Token Refresh Strategy:**

Tradovate's OAuth is problematic (no refresh token, limited docs). Recommended approach:

1. Store token obtained_at timestamp
2. Before broker operations, check if token is old (>12 hours)
3. If old, prompt user to re-authenticate
4. Consider background job to check token validity

```python
# app/application/use_cases/check_broker_connection.py
class CheckBrokerConnectionUseCase:
    async def execute(self, account_id: str) -> ConnectionStatus:
        account = await self.account_repo.get_by_id(account_id)
        credential = await self.credential_repo.get_by_id(account.credential_id)

        if self._is_token_expired(credential):
            return ConnectionStatus.TOKEN_EXPIRED

        # Try a lightweight API call
        try:
            await self.broker_adapter.get_account_info()
            return ConnectionStatus.CONNECTED
        except AuthenticationError:
            return ConnectionStatus.AUTHENTICATION_FAILED
```

### Callback Handling

**Backend Routes (FastAPI):**
```python
# app/routers/oauth.py
router = APIRouter(prefix="/auth", tags=["oauth"])

@router.get("/{broker}/authorize")
async def initiate_oauth(broker: str, user: User = Depends(get_current_user)):
    """Generate OAuth URL and redirect"""
    state = generate_secure_state(user.id)
    store_state_temporarily(state, user.id)  # Redis with 10min TTL

    oauth_url = build_oauth_url(broker, state)
    return RedirectResponse(oauth_url)

@router.post("/{broker}/exchange")
async def exchange_code(
    broker: str,
    code: str,
    state: str,
    user: User = Depends(get_current_user),
    link_account_use_case: LinkBrokerAccountUseCase = Depends()
):
    """Exchange authorization code for tokens"""
    # Verify state
    stored_user_id = get_and_delete_state(state)
    if stored_user_id != user.id:
        raise HTTPException(400, "Invalid state")

    # Exchange and link
    account = await link_account_use_case.execute(
        user_id=user.id,
        broker=broker,
        authorization_code=code
    )

    return {"account_id": account.id, "status": "connected"}
```

**Frontend Callback Page (Next.js):**
```typescript
// ui-next/src/app/auth/tradovate/callback/page.tsx
export default function TradovateCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');

    if (code && state) {
      exchangeToken(code, state)
        .then(() => router.push('/dashboard/accounts?connected=true'))
        .catch((error) => router.push('/dashboard/accounts?error=' + error.message));
    }
  }, [searchParams, router]);

  return <div>Connecting your Tradovate account...</div>;
}
```

### New Use Cases for OAuth

```python
# app/application/use_cases/link_broker_account.py
class LinkBrokerAccountUseCase:
    """Exchange OAuth code and create linked account"""

    def __init__(
        self,
        account_repository: AccountRepository,
        credential_repository: CredentialRepository,
        oauth_service: OAuthService,  # Infrastructure service for token exchange
        event_port: EventPort,
    ):
        ...

    async def execute(
        self,
        user_id: int,
        broker: BrokerType,
        authorization_code: str,
    ) -> Account:
        # Exchange code for tokens
        tokens = await self.oauth_service.exchange_code(broker, authorization_code)

        # Store encrypted credentials
        credential = await self.credential_repository.create(
            credential_id=str(uuid4()),
            user_id=user_id,
            credential_type="oauth",
            service=broker.value,
            credential_data=tokens,
        )

        # Create account linked to credential
        account = Account(
            id=AccountId(str(uuid4())),
            user_id=user_id,
            broker=broker,
            credential_id=credential.id,
            ...
        )

        await self.account_repository.save(account)
        await self.event_port.publish(DomainEvent.create(
            EventType.ACCOUNT_CONNECTED,
            {"account_id": account.id.value, "broker": broker.value}
        ))

        return account
```

## Subscription Gating

### Where Enforcement Lives

**NOT in Domain Layer:** Domain defines WHAT subscription tiers mean (limits, features), not HOW enforcement happens.

**Application Layer (Use Case Guards):** Feature gating happens in use cases. This keeps domain pure while centralizing enforcement.

```python
# Pattern: Use case guard decorator or check
class CreateAccountUseCase:
    async def execute(self, request: CreateAccountRequest) -> Account:
        # Check subscription limits
        user = await self.user_repository.get_by_id(request.user_id)
        existing_accounts = await self.account_repository.get_by_user(request.user_id)

        if len(existing_accounts) >= user.max_broker_accounts:
            raise SubscriptionLimitError(
                f"Your {user.subscription_tier.value} plan allows {user.max_broker_accounts} broker accounts. "
                f"Upgrade to Pro for unlimited accounts."
            )

        # ... proceed with account creation
```

**Alternative: Subscription Guard Decorator:**
```python
# app/application/decorators.py
def requires_subscription(min_tier: SubscriptionTier = SubscriptionTier.FREE):
    def decorator(use_case_method):
        async def wrapper(self, request, *args, **kwargs):
            user = await self.user_repository.get_by_id(request.user_id)

            if not user.has_tier_or_higher(min_tier):
                raise SubscriptionRequired(min_tier)

            if user.subscription_status != SubscriptionStatus.ACTIVE:
                raise SubscriptionInactive(user.subscription_status)

            return await use_case_method(self, request, *args, **kwargs)
        return wrapper
    return decorator

# Usage
class SomeProFeatureUseCase:
    @requires_subscription(SubscriptionTier.PRO)
    async def execute(self, request):
        ...
```

### Middleware vs Use Case Level

| Layer | What to Check | Why |
|-------|---------------|-----|
| **Middleware** | Authentication + basic subscription status | Fast rejection, consistent |
| **Use Case** | Feature-specific limits and rules | Business logic, contextual |

**Middleware checks:**
- Is user authenticated?
- Is subscription active (not past_due, not cancelled)?
- Redirect to billing page if subscription inactive

**Use Case checks:**
- Specific feature limits (max accounts, max signals)
- Tier-specific feature access
- Contextual business rules

```typescript
// ui-next/src/middleware.ts (extended)
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  const subscriptionStatus = request.cookies.get('subscription-status')?.value;

  // Protected dashboard routes require active subscription
  if (isProtectedRoute(pathname)) {
    if (!token) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    // Allow access to billing page even with inactive subscription
    if (pathname.startsWith('/dashboard/billing')) {
      return NextResponse.next();
    }

    if (subscriptionStatus === 'past_due' || subscriptionStatus === 'cancelled') {
      return NextResponse.redirect(new URL('/dashboard/billing', request.url));
    }
  }

  return NextResponse.next();
}
```

### Subscription Feature Matrix

| Feature | Free | Pro |
|---------|------|-----|
| Broker accounts | 1 | Unlimited |
| Signal processing | Yes | Yes |
| Real-time dashboard | Yes | Yes |
| Webhook endpoints | 1 | Unlimited |
| Priority support | No | Yes |
| API rate limit | 100/hour | 1000/hour |

## Frontend Architecture

### Landing Page Routing

Use Next.js **route groups** to separate marketing and dashboard:

```
ui-next/src/app/
├── (marketing)/           # Public marketing site
│   ├── layout.tsx         # Marketing layout (different header)
│   ├── page.tsx           # Landing page at "/"
│   ├── pricing/
│   │   └── page.tsx       # Pricing page at "/pricing"
│   └── features/
│       └── page.tsx       # Features page at "/features"
│
├── (dashboard)/           # Protected app
│   ├── layout.tsx         # Dashboard layout (sidebar, etc.)
│   └── dashboard/
│       ├── page.tsx       # Dashboard at "/dashboard"
│       ├── accounts/
│       ├── signals/
│       ├── settings/
│       └── billing/       # Subscription management
│           └── page.tsx
│
├── login/                 # Auth pages (outside groups)
│   └── page.tsx
├── auth/                  # OAuth callbacks
│   ├── tradovate/
│   │   └── callback/
│   │       └── page.tsx
│   └── callback/          # Generic OAuth callback
│       └── page.tsx
│
└── api/                   # BFF API routes
    ├── auth/
    ├── stripe/
    │   └── webhook/
    │       └── route.ts   # Stripe webhook endpoint
    └── ...
```

### Protected Routes

**Middleware Strategy:**

```typescript
// ui-next/src/middleware.ts
const AUTH_COOKIE_NAME = 'auth-token';

// Routes with different requirements
const publicRoutes = ['/', '/pricing', '/features', '/login', '/api/stripe/webhook'];
const authRoutes = ['/login', '/signup'];
const protectedRoutes = ['/dashboard'];
const billingRoutes = ['/dashboard/billing'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Public routes - always allow
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }

  // Check authentication
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  const isAuthenticated = !!token;

  // Auth routes - redirect to dashboard if logged in
  if (isAuthRoute(pathname) && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Protected routes - require auth
  if (isProtectedRoute(pathname)) {
    if (!isAuthenticated) {
      return NextResponse.redirect(new URL('/login', request.url));
    }

    // Billing routes always accessible (to fix payment issues)
    if (isBillingRoute(pathname)) {
      return NextResponse.next();
    }

    // Check subscription status for other protected routes
    // (subscription check done server-side, this is just a hint)
  }

  return NextResponse.next();
}
```

### OAuth Callback Pages

```typescript
// ui-next/src/app/auth/tradovate/callback/page.tsx
'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function TradovateCallbackPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error');

    if (errorParam) {
      setStatus('error');
      setError(errorParam);
      return;
    }

    if (!code || !state) {
      setStatus('error');
      setError('Missing authorization code');
      return;
    }

    // Exchange code for tokens via BFF
    fetch('/api/auth/tradovate/exchange', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, state }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to connect account');
        return res.json();
      })
      .then(() => {
        setStatus('success');
        setTimeout(() => router.push('/dashboard/accounts'), 1500);
      })
      .catch((err) => {
        setStatus('error');
        setError(err.message);
      });
  }, [searchParams, router]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        {status === 'loading' && (
          <>
            <Loader2 className="mx-auto h-8 w-8 animate-spin" />
            <p className="mt-4">Connecting your Tradovate account...</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="text-green-500 text-4xl">Connected</div>
            <p className="mt-4">Redirecting to dashboard...</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-red-500 text-4xl">Connection Failed</div>
            <p className="mt-4">{error}</p>
            <button
              onClick={() => router.push('/dashboard/accounts')}
              className="mt-4 btn btn-primary"
            >
              Return to Accounts
            </button>
          </>
        )}
      </div>
    </div>
  );
}
```

## Suggested Build Order

Based on dependencies between components:

### Phase 1: Domain Extensions
**No external dependencies - build first**

1. Add `SubscriptionTier`, `SubscriptionStatus` enums to domain
2. Extend User entity with subscription fields
3. Create `PaymentPort` interface in domain/ports
4. Add subscription-related domain exceptions

### Phase 2: Stripe Infrastructure
**Depends on Phase 1**

1. Create `StripeAdapter` implementing `PaymentPort`
2. Create `StripeWebhookHandler` in infrastructure
3. Add Stripe webhook router in FastAPI
4. Wire into DI container

### Phase 3: Subscription Use Cases
**Depends on Phases 1 & 2**

1. Create `ManageSubscriptionUseCase`
2. Create `CreateCheckoutSessionUseCase`
3. Create `GetSubscriptionStatusUseCase`
4. Add subscription guards to existing use cases (e.g., `CreateAccountUseCase`)

### Phase 4: Broker OAuth Backend
**Depends on Phase 1 (uses existing CredentialRepository)**

1. Create OAuth service for token exchange per broker
2. Create `LinkBrokerAccountUseCase`
3. Add OAuth routes (authorize, exchange)
4. Store state in Redis with TTL

### Phase 5: Frontend - Landing Page
**Independent of backend phases**

1. Create `(marketing)` route group
2. Build landing page at `/`
3. Build pricing page at `/pricing`
4. Add marketing layout (different from dashboard)

### Phase 6: Frontend - Subscription Flow
**Depends on Phases 2, 3**

1. Create billing page at `/dashboard/billing`
2. Integrate Stripe Checkout (redirect to hosted page)
3. Add subscription status display
4. Update middleware for subscription checks

### Phase 7: Frontend - OAuth Callbacks
**Depends on Phase 4**

1. Create `/auth/tradovate/callback` page
2. Create `/auth/callback` generic page
3. Add "Connect [Broker]" buttons to accounts page
4. Handle OAuth error states

### Phase 8: Integration Testing
**Depends on all phases**

1. Test Stripe webhook signature verification
2. Test subscription state transitions
3. Test OAuth flow end-to-end
4. Test subscription gating

## Integration Points with v1.0 Architecture

### What Gets Extended

| v1.0 Component | Extension |
|----------------|-----------|
| `User` (models.py) | Add subscription fields |
| `CredentialRepository` | Already handles OAuth tokens |
| `EventType` enum | Add SUBSCRIPTION_* events |
| `Container` | Wire PaymentPort, new use cases |
| Middleware (Next.js) | Add subscription checks |
| DI Container | Add StripeAdapter, new use cases |

### What Gets Added

| New Component | Location |
|---------------|----------|
| `PaymentPort` | app/domain/ports/ |
| `StripeAdapter` | app/infrastructure/adapters/ |
| `StripeWebhookHandler` | app/infrastructure/webhooks/ |
| `ManageSubscriptionUseCase` | app/application/use_cases/ |
| `LinkBrokerAccountUseCase` | app/application/use_cases/ |
| OAuth routes | app/routers/oauth.py |
| Stripe webhook route | app/routers/webhooks.py |
| Landing page | ui-next/src/app/(marketing)/ |
| OAuth callback pages | ui-next/src/app/auth/ |
| Billing page | ui-next/src/app/dashboard/billing/ |

### What Stays Unchanged

- Domain entities (Signal, Trade, Order, Position, Account structure)
- Existing use cases (just add guards)
- Broker adapters (TradeLocker, TopStep, etc.)
- Event infrastructure (NATS, Redis)
- API key authentication
- Webhook signal processing

## Sources

### Primary (HIGH confidence)
- Existing codebase: `/home/pharma5/unified_engine/app/` structure
- Existing middleware: `/home/pharma5/unified_engine/ui-next/src/middleware.ts`
- Existing credential repository: `/home/pharma5/unified_engine/app/infrastructure/repositories/credential_repository.py`

### Secondary (MEDIUM confidence)
- [RFC 9700 - OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/rfc9700/) - January 2025 IETF standard
- [FastAPI Stripe Integration Tutorial](https://www.fast-saas.com/blog/fastapi-stripe-integration/) - FastSaaS 2025
- [Next.js Layouts and Pages](https://nextjs.org/docs/app/getting-started/layouts-and-pages) - Official docs on route groups
- [Clean Architecture Domain Layer](https://wojciechowski.app/en/articles/clean-architecture-domain-driven-design-2025) - 2025 best practices
- [Stripe Subscriptions Next.js](https://www.pedroalonso.net/blog/stripe-subscriptions-nextjs/) - Pedro Alonso

### Tertiary (LOW confidence - needs validation)
- [Tradovate OAuth Example](https://github.com/tradovate/example-api-oauth) - GitHub repo (reported issues in 2024)
- Tradovate token refresh behavior (conflicting community reports)

## Metadata

**Confidence breakdown:**
- Hexagonal architecture patterns: HIGH - based on existing codebase
- Stripe integration: MEDIUM - based on official docs + community patterns
- Broker OAuth: MEDIUM for general patterns, LOW for Tradovate specifics
- Frontend routing: HIGH - based on official Next.js docs

**Research date:** 2026-01-20
**Valid until:** 2026-02-20 (30 days - architecture patterns stable)
