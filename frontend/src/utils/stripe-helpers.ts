// Stripe integration helpers for TradeFlow

export const STRIPE_PRICE_IDS = {
  starter: 'price_starter_monthly', // Replace with actual Stripe Price ID
  pro: 'price_pro_monthly',         // Replace with actual Stripe Price ID
  elite: 'price_elite_monthly'      // Replace with actual Stripe Price ID
};

export const STRIPE_CHECKOUT_BASE = 'https://checkout.stripe.com'; // Replace with your Stripe checkout URL

/**
 * Create a Stripe Checkout session URL
 * @param plan - The plan to checkout (starter, pro, elite)
 * @param userEmail - User's email address
 * @returns Stripe checkout URL
 */
export function getStripeCheckoutUrl(plan: 'starter' | 'pro' | 'elite', userEmail?: string): string {
  const priceId = STRIPE_PRICE_IDS[plan];
  
  // In production, you would call your backend to create a Stripe Checkout session
  // For now, return a placeholder URL
  const params = new URLSearchParams({
    price_id: priceId,
    ...(userEmail && { prefilled_email: userEmail }),
    success_url: `${window.location.origin}/?checkout=success`,
    cancel_url: `${window.location.origin}/?checkout=cancel`
  });

  return `${STRIPE_CHECKOUT_BASE}?${params.toString()}`;
}

/**
 * Create a Stripe Customer Portal session URL
 * For managing subscriptions, payment methods, and billing history
 */
export async function getStripePortalUrl(): Promise<string> {
  // In production, call your backend to create a Customer Portal session
  // const response = await fetch('/api/create-portal-session', { method: 'POST' });
  // const { url } = await response.json();
  // return url;
  
  return 'https://billing.stripe.com/p/login/test'; // Placeholder
}

/**
 * Handle subscription upgrade/downgrade
 */
export async function updateSubscription(newPlan: 'starter' | 'pro' | 'elite'): Promise<boolean> {
  try {
    // In production, call your backend to update the subscription
    // const response = await fetch('/api/update-subscription', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ plan: newPlan })
    // });
    // return response.ok;
    
    console.log(`Updating subscription to ${newPlan}`);
    return true;
  } catch (error) {
    console.error('Failed to update subscription:', error);
    return false;
  }
}

/**
 * Cancel subscription
 */
export async function cancelSubscription(): Promise<boolean> {
  try {
    // In production, call your backend to cancel the subscription
    // const response = await fetch('/api/cancel-subscription', {
    //   method: 'POST'
    // });
    // return response.ok;
    
    console.log('Canceling subscription');
    return true;
  } catch (error) {
    console.error('Failed to cancel subscription:', error);
    return false;
  }
}
