/**
 * Webhook Endpoint Types
 */

export interface WebhookEndpoint {
  source: 'tradingview' | 'trailhacker' | 'custom';
  name: string;
  description: string;
  url_template: string;
  example_payload: Record<string, unknown>;
  required_fields: string[];
}
