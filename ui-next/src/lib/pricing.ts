/**
 * Pricing configuration for Tradeflow
 * 4-tier pricing structure with feature-based differentiation
 * Matches backend PRICING_TIERS in stripe_service.py
 */

// Price in cents
export interface PricingTier {
  tier_id: string;
  name: string;
  price: number; // cents (2900 = $29)
  brokers: number;
  stripe_price_id: string | null;
  tagline: string;
  signalsPerDay: number; // -1 = unlimited
  webhooks: number; // -1 = unlimited
  features: string[];
}

// 4-tier pricing structure with feature-based differentiation
export const PRICING_TIERS: Record<string, PricingTier> = {
  tier_1: {
    tier_id: "tier_1",
    name: "Starter",
    price: 2900, // $29/month
    brokers: 1,
    stripe_price_id: "price_tier1_monthly",
    tagline: "Get started with automated trading",
    signalsPerDay: 100,
    webhooks: 2,
    features: [
      "1 broker connection",
      "100 signals per day",
      "2 webhooks",
      "Staleness guard protection",
      "Daily trade limits",
      "Fixed lot sizing",
      "Basic dashboard analytics",
      "Email support (48h)",
    ],
  },
  tier_2: {
    tier_id: "tier_2",
    name: "Trader",
    price: 5900, // $59/month
    brokers: 2,
    stripe_price_id: "price_tier2_monthly",
    tagline: "For serious traders who want protection",
    signalsPerDay: -1,
    webhooks: 5,
    features: [
      "2 broker connections",
      "Unlimited signals",
      "5 webhooks",
      "All 5 AI Signal Guards",
      "Full risk management suite",
      "Drawdown protection",
      "% of balance sizing",
      "Symbol mapping",
      "2 account groups",
      "Email support (24h)",
    ],
  },
  tier_3: {
    tier_id: "tier_3",
    name: "Pro",
    price: 9900, // $99/month
    brokers: 4,
    stripe_price_id: "price_tier3_monthly",
    tagline: "Scale your trading across multiple accounts",
    signalsPerDay: -1,
    webhooks: -1,
    features: [
      "4 broker connections",
      "Unlimited signals & webhooks",
      "AI Guards + custom thresholds",
      "Risk-based position sizing",
      "Advanced rule-based routing",
      "Custom symbol aliases",
      "Unlimited account groups",
      "Full analytics suite",
      "AI Strategy Suite access",
      "API access",
      "30-day webhook logs",
      "Priority support (12h)",
    ],
  },
  tier_4: {
    tier_id: "tier_4",
    name: "Enterprise",
    price: 19900, // $199/month
    brokers: 8,
    stripe_price_id: "price_tier4_monthly",
    tagline: "Unlimited power for professional traders",
    signalsPerDay: -1,
    webhooks: -1,
    features: [
      "8 broker connections",
      "Everything in Pro",
      "AI Strategy Suite + AI Coach",
      "Pine Script AI Fixer",
      "Custom risk profiles per account",
      "Strategy-based routing",
      "Bulk symbol import/export",
      "Nested account groups",
      "Analytics export (CSV/JSON)",
      "Higher API rate limits",
      "90-day webhook logs",
      "SMS & push notifications",
      "Priority support + live chat",
    ],
  },
};

// Free tier (not purchasable, for comparison display)
export const FREE_TIER: PricingTier = {
  tier_id: "free",
  name: "Free",
  price: 0,
  brokers: 1,
  stripe_price_id: null,
  tagline: "Try automated trading risk-free",
  signalsPerDay: 50,
  webhooks: 1,
  features: [
    "1 broker connection",
    "50 signals per day",
    "1 webhook",
    "Basic signal routing",
    "Fixed lot sizing",
    "7-day webhook logs",
    "Community support",
  ],
};

/**
 * Format price from cents to display string
 * @param cents - Price in cents (e.g., 1999)
 * @returns Formatted price string (e.g., "$19.99")
 */
export function formatPrice(cents: number): string {
  if (cents === 0) {
    return "Free";
  }
  const dollars = cents / 100;
  return `$${dollars.toFixed(2)}`;
}

/**
 * Format price with period
 * @param cents - Price in cents
 * @param period - Billing period (default: "/month")
 * @returns Formatted price with period (e.g., "$19.99/month")
 */
export function formatPriceWithPeriod(
  cents: number,
  period: string = "/month"
): string {
  if (cents === 0) {
    return "Free";
  }
  return `${formatPrice(cents)}${period}`;
}

/**
 * Get features for a tier
 * @param tier_id - Tier identifier (e.g., "tier_1", "free")
 * @returns Array of feature strings
 */
export function getTierFeatures(tier_id: string): string[] {
  if (tier_id === "free") {
    return FREE_TIER.features;
  }
  return PRICING_TIERS[tier_id]?.features || FREE_TIER.features;
}

/**
 * Get tier info by ID
 * @param tier_id - Tier identifier
 * @returns Full tier information
 */
export function getTierInfo(tier_id: string): PricingTier {
  if (tier_id === "free") {
    return FREE_TIER;
  }
  return PRICING_TIERS[tier_id] || FREE_TIER;
}

/**
 * Get broker limit for a tier
 * @param tier_id - Tier identifier
 * @returns Maximum brokers allowed
 */
export function getBrokerLimit(tier_id: string): number {
  if (tier_id === "free") {
    return FREE_TIER.brokers;
  }
  // Handle legacy "pro" tier
  if (tier_id === "pro") {
    return PRICING_TIERS.tier_4.brokers;
  }
  return PRICING_TIERS[tier_id]?.brokers || FREE_TIER.brokers;
}

/**
 * Get all tiers for pricing display (including free)
 * @returns Array of all tiers in order
 */
export function getAllTiers(): PricingTier[] {
  return [
    FREE_TIER,
    PRICING_TIERS.tier_1,
    PRICING_TIERS.tier_2,
    PRICING_TIERS.tier_3,
    PRICING_TIERS.tier_4,
  ];
}

/**
 * Get all paid tiers (excluding free)
 * @returns Array of paid tiers
 */
export function getPaidTiers(): PricingTier[] {
  return [
    PRICING_TIERS.tier_1,
    PRICING_TIERS.tier_2,
    PRICING_TIERS.tier_3,
    PRICING_TIERS.tier_4,
  ];
}

/**
 * Get minimum tier required for a given broker count
 * @param brokerCount - Number of brokers needed
 * @returns Tier ID or null if no tier supports that many
 */
export function getTierByBrokerCount(brokerCount: number): string | null {
  const tiers = ["tier_1", "tier_2", "tier_3", "tier_4"];
  for (const tierId of tiers) {
    if (PRICING_TIERS[tierId].brokers >= brokerCount) {
      return tierId;
    }
  }
  return null; // More than 4 brokers not supported
}

/**
 * Check if a tier is higher than another
 * @param tier1 - First tier ID
 * @param tier2 - Second tier ID
 * @returns true if tier1 is higher than tier2
 */
export function isTierHigher(tier1: string, tier2: string): boolean {
  const tierOrder = ["free", "tier_1", "tier_2", "tier_3", "tier_4"];
  const index1 = tierOrder.indexOf(tier1);
  const index2 = tierOrder.indexOf(tier2);
  return index1 > index2;
}

/**
 * Get upgrade options from a given tier
 * @param currentTier - Current tier ID
 * @returns Array of tiers that are upgrades
 */
export function getUpgradeTiers(currentTier: string): PricingTier[] {
  const tierOrder = ["free", "tier_1", "tier_2", "tier_3", "tier_4"];
  const currentIndex = tierOrder.indexOf(currentTier);

  if (currentIndex === -1 || currentIndex >= tierOrder.length - 1) {
    return []; // Unknown tier or already at highest
  }

  return tierOrder
    .slice(currentIndex + 1)
    .map((tierId) => getTierInfo(tierId));
}
