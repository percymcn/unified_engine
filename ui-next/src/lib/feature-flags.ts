/**
 * Feature Flags System for Tradeflow
 * Tier-gated features for subscription management
 */

export type SubscriptionTier = 'free' | 'starter' | 'trader' | 'pro' | 'enterprise';

export interface FeatureDefinition {
  id: string;
  name: string;
  description: string;
  minTier: SubscriptionTier;
  category: 'execution' | 'compliance' | 'analytics' | 'security' | 'integration';
}

// Feature definitions with tier requirements
export const FEATURES: Record<string, FeatureDefinition> = {
  // Execution features
  ULTRA_LOW_LATENCY: {
    id: 'ultra_low_latency',
    name: 'Ultra-Low Latency Mode',
    description: 'Sub-5ms execution with optimized routing',
    minTier: 'pro',
    category: 'execution',
  },
  STEALTH_MODE: {
    id: 'stealth_mode',
    name: 'Stealth Mode',
    description: 'Mask bot behavior patterns for prop firm compliance',
    minTier: 'trader',
    category: 'execution',
  },
  AUTO_FLATTEN: {
    id: 'auto_flatten',
    name: 'Auto-Flatten',
    description: 'Automatic position flattening on disconnect or drawdown',
    minTier: 'trader',
    category: 'execution',
  },
  GHOST_MODE: {
    id: 'ghost_mode',
    name: 'Ghost Mode',
    description: 'Background resilience - trades protected even when UI offline',
    minTier: 'pro',
    category: 'execution',
  },

  // Compliance features
  PROP_FIRM_DASHBOARD: {
    id: 'prop_firm_dashboard',
    name: 'Prop Firm Dashboard',
    description: 'Real-time drawdown tracking and compliance monitoring',
    minTier: 'trader',
    category: 'compliance',
  },
  RULE_SYNC: {
    id: 'rule_sync',
    name: 'Broker Rule Sync',
    description: 'Automatic sync and alerts for prop firm rule changes',
    minTier: 'trader',
    category: 'compliance',
  },
  PAYOUT_TRACKER: {
    id: 'payout_tracker',
    name: 'Payout Tracker',
    description: 'Track payout eligibility and history',
    minTier: 'trader',
    category: 'compliance',
  },

  // Analytics features
  AI_SUITE: {
    id: 'ai_suite',
    name: 'AI Strategy Suite',
    description: 'Pine Script AI fixer, backtest preview, and AI trading coach',
    minTier: 'pro',
    category: 'analytics',
  },
  BACKTEST_PREVIEW: {
    id: 'backtest_preview',
    name: 'Backtest Preview',
    description: 'One-click backtest preview from TradingView webhooks',
    minTier: 'pro',
    category: 'analytics',
  },
  WEBHOOK_LOGS: {
    id: 'webhook_logs',
    name: 'Webhook Logs',
    description: '30-day webhook execution history and debugging',
    minTier: 'pro',
    category: 'analytics',
  },
  TAX_EXPORT: {
    id: 'tax_export',
    name: 'Tax Export',
    description: 'Export trades with tax-ready formatting',
    minTier: 'trader',
    category: 'analytics',
  },
  ADVANCED_EXPORT: {
    id: 'advanced_export',
    name: 'Advanced Export',
    description: 'Custom export profiles and batch processing',
    minTier: 'enterprise',
    category: 'analytics',
  },

  // Security features
  API_KEYS: {
    id: 'api_keys',
    name: 'API Keys',
    description: 'Programmatic access to trading API with custom permissions',
    minTier: 'pro',
    category: 'security',
  },
  KILL_SWITCH: {
    id: 'kill_switch',
    name: 'Emergency Kill Switch',
    description: 'One-click flatten all positions across all accounts',
    minTier: 'enterprise',
    category: 'security',
  },
  ENCRYPTED_LOGS: {
    id: 'encrypted_logs',
    name: 'Encrypted Webhook Logs',
    description: 'End-to-end encrypted audit logs',
    minTier: 'pro',
    category: 'security',
  },
  QUIET_MODE: {
    id: 'quiet_mode',
    name: 'Quiet Mode',
    description: 'Mute non-critical notifications',
    minTier: 'pro',
    category: 'security',
  },

  // Integration features
  MOBILE_PUSH: {
    id: 'mobile_push',
    name: 'Mobile Push Notifications',
    description: 'Real-time mobile alerts with one-tap actions',
    minTier: 'trader',
    category: 'integration',
  },
  HEARTBEAT_MONITORING: {
    id: 'heartbeat_monitoring',
    name: 'Heartbeat Monitoring',
    description: 'Per-broker connection monitoring and auto-reconnect',
    minTier: 'starter',
    category: 'integration',
  },
};

// Tier hierarchy for comparison
const TIER_LEVELS: Record<SubscriptionTier, number> = {
  free: 0,
  starter: 1,
  trader: 2,
  pro: 3,
  enterprise: 4,
};

/**
 * Check if a user's tier has access to a feature
 */
export function hasFeatureAccess(userTier: SubscriptionTier, featureId: string): boolean {
  const feature = FEATURES[featureId];
  if (!feature) return false;
  return TIER_LEVELS[userTier] >= TIER_LEVELS[feature.minTier];
}

/**
 * Get all features available for a tier
 */
export function getFeaturesForTier(tier: SubscriptionTier): FeatureDefinition[] {
  return Object.values(FEATURES).filter(
    (feature) => TIER_LEVELS[tier] >= TIER_LEVELS[feature.minTier]
  );
}

/**
 * Get features by category
 */
export function getFeaturesByCategory(category: FeatureDefinition['category']): FeatureDefinition[] {
  return Object.values(FEATURES).filter((feature) => feature.category === category);
}

/**
 * Get the minimum tier needed for a feature
 */
export function getMinTierForFeature(featureId: string): SubscriptionTier | null {
  const feature = FEATURES[featureId];
  return feature?.minTier || null;
}

/**
 * Check if user needs upgrade for a feature
 */
export function needsUpgradeFor(userTier: SubscriptionTier, featureId: string): boolean {
  return !hasFeatureAccess(userTier, featureId);
}

/**
 * Get upgrade message for a feature
 */
export function getUpgradeMessage(featureId: string): string {
  const feature = FEATURES[featureId];
  if (!feature) return 'Upgrade required';
  return `Upgrade to ${feature.minTier.charAt(0).toUpperCase() + feature.minTier.slice(1)} to unlock ${feature.name}`;
}
