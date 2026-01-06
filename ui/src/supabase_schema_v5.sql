-- =====================================================
-- Empire Trading Hub - Supabase Schema V5
-- Enterprise-Grade Multi-Broker Trading Platform
-- =====================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =====================================================
-- PROFILES TABLE
-- =====================================================
CREATE TABLE profiles (
  id UUID PRIMARY KEY DEFAULT auth.uid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'user' CHECK (role IN ('admin', 'user', 'viewer')),
  plan_tier TEXT DEFAULT 'starter' CHECK (plan_tier IN ('starter', 'pro', 'elite')),
  trial_end TIMESTAMPTZ,
  totp_secret TEXT,
  totp_enabled BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_role ON profiles(role);
CREATE INDEX idx_profiles_plan_tier ON profiles(plan_tier);

-- RLS Policies for profiles
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Admins can view all profiles"
  ON profiles FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

CREATE POLICY "Admins can update all profiles"
  ON profiles FOR UPDATE
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- BROKER ACCOUNTS TABLE
-- =====================================================
CREATE TABLE broker_accounts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  broker TEXT NOT NULL CHECK (broker IN ('tradelocker', 'topstep', 'truforex')),
  account_name TEXT,
  account_id TEXT,
  api_key TEXT UNIQUE NOT NULL,
  api_key_hash TEXT NOT NULL,
  credentials_encrypted TEXT,
  status TEXT DEFAULT 'connected' CHECK (status IN ('connected', 'disconnected', 'error')),
  last_sync TIMESTAMPTZ,
  balance NUMERIC(15,2),
  equity NUMERIC(15,2),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_broker_accounts_user_id ON broker_accounts(user_id);
CREATE INDEX idx_broker_accounts_broker ON broker_accounts(broker);
CREATE INDEX idx_broker_accounts_api_key_hash ON broker_accounts(api_key_hash);

ALTER TABLE broker_accounts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own broker accounts"
  ON broker_accounts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own broker accounts"
  ON broker_accounts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own broker accounts"
  ON broker_accounts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all broker accounts"
  ON broker_accounts FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- RISK SETTINGS TABLE
-- =====================================================
CREATE TABLE risk_settings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  broker TEXT NOT NULL,
  enabled BOOLEAN DEFAULT TRUE,
  max_daily_loss_usd NUMERIC(10,2) DEFAULT 500,
  max_daily_loss_pct NUMERIC(5,2) DEFAULT 2.0,
  max_trades_per_day INTEGER DEFAULT 10,
  max_open_trades INTEGER DEFAULT 5,
  max_concurrent_positions INTEGER DEFAULT 3,
  max_risk_per_trade_usd NUMERIC(10,2) DEFAULT 100,
  max_risk_per_trade_pct NUMERIC(5,2) DEFAULT 1.0,
  leverage_cap NUMERIC(5,2) DEFAULT 10.0,
  allowed_instruments TEXT[],
  denied_instruments TEXT[],
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, broker)
);

CREATE INDEX idx_risk_settings_user_id ON risk_settings(user_id);
CREATE INDEX idx_risk_settings_broker ON risk_settings(broker);

ALTER TABLE risk_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own risk settings"
  ON risk_settings FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all risk settings"
  ON risk_settings FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- TRADING CONFIG TABLE
-- =====================================================
CREATE TABLE trading_config (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  broker TEXT NOT NULL,
  lot_size_mode TEXT DEFAULT 'fixed',
  fixed_lot_size NUMERIC(10,2) DEFAULT 0.01,
  percentage_lot_size NUMERIC(5,2) DEFAULT 1.0,
  sl_mode TEXT DEFAULT 'percentage',
  sl_percentage NUMERIC(5,2) DEFAULT 2.0,
  sl_pips NUMERIC(10,1) DEFAULT 20,
  use_trailing_sl BOOLEAN DEFAULT FALSE,
  trailing_sl_distance NUMERIC(5,2) DEFAULT 1.0,
  tp_mode TEXT DEFAULT 'percentage',
  tp_percentage NUMERIC(5,2) DEFAULT 4.0,
  tp_pips NUMERIC(10,1) DEFAULT 40,
  risk_reward_ratio NUMERIC(5,2) DEFAULT 2.0,
  use_partial_tp BOOLEAN DEFAULT FALSE,
  partial_tp_percent INTEGER DEFAULT 50,
  partial_tp_level NUMERIC(5,2) DEFAULT 1.5,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, broker)
);

CREATE INDEX idx_trading_config_user_id ON trading_config(user_id);

ALTER TABLE trading_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own trading config"
  ON trading_config FOR ALL
  USING (auth.uid() = user_id);

-- =====================================================
-- ORDERS TABLE
-- =====================================================
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  broker_account_id UUID REFERENCES broker_accounts(id),
  broker TEXT NOT NULL,
  broker_order_id TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
  type TEXT NOT NULL CHECK (type IN ('MARKET', 'LIMIT', 'STOP')),
  qty NUMERIC(15,4) NOT NULL,
  price NUMERIC(15,4),
  filled_qty NUMERIC(15,4) DEFAULT 0,
  avg_fill_price NUMERIC(15,4),
  status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'FILLED', 'REJECTED', 'CANCELLED')),
  reject_reason TEXT,
  tag TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  filled_at TIMESTAMPTZ
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_broker ON orders(broker);
CREATE INDEX idx_orders_symbol ON orders(symbol);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_timestamp ON orders(timestamp DESC);

ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own orders"
  ON orders FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own orders"
  ON orders FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Admins can view all orders"
  ON orders FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- POSITIONS TABLE
-- =====================================================
CREATE TABLE positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  broker_account_id UUID REFERENCES broker_accounts(id),
  broker TEXT NOT NULL,
  broker_position_id TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('LONG', 'SHORT')),
  qty NUMERIC(15,4) NOT NULL,
  entry_price NUMERIC(15,4) NOT NULL,
  current_price NUMERIC(15,4),
  unrealized_pnl NUMERIC(15,2) DEFAULT 0,
  unrealized_pnl_pct NUMERIC(10,4) DEFAULT 0,
  stop_loss NUMERIC(15,4),
  take_profit NUMERIC(15,4),
  tag TEXT,
  open_time TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_positions_broker ON positions(broker);
CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_open_time ON positions(open_time DESC);

ALTER TABLE positions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own positions"
  ON positions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can modify own positions"
  ON positions FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all positions"
  ON positions FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- LOGS TABLE
-- =====================================================
CREATE TABLE logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
  broker TEXT,
  level TEXT NOT NULL CHECK (level IN ('success', 'info', 'warning', 'error')),
  type TEXT NOT NULL CHECK (type IN ('order', 'position', 'webhook', 'risk', 'sync', 'auth')),
  message TEXT NOT NULL,
  details JSONB,
  correlation_id TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_user_id ON logs(user_id);
CREATE INDEX idx_logs_level ON logs(level);
CREATE INDEX idx_logs_type ON logs(type);
CREATE INDEX idx_logs_timestamp ON logs(timestamp DESC);
CREATE INDEX idx_logs_correlation_id ON logs(correlation_id);

ALTER TABLE logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own logs"
  ON logs FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "System can insert logs"
  ON logs FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Admins can view all logs"
  ON logs FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- WEBHOOK EVENTS TABLE
-- =====================================================
CREATE TABLE webhook_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  broker TEXT,
  source TEXT DEFAULT 'tradingview',
  payload JSONB NOT NULL,
  signature TEXT,
  signature_valid BOOLEAN,
  processed BOOLEAN DEFAULT FALSE,
  processing_error TEXT,
  order_id UUID REFERENCES orders(id),
  received_at TIMESTAMPTZ DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);

CREATE INDEX idx_webhook_events_user_id ON webhook_events(user_id);
CREATE INDEX idx_webhook_events_broker ON webhook_events(broker);
CREATE INDEX idx_webhook_events_processed ON webhook_events(processed);
CREATE INDEX idx_webhook_events_received_at ON webhook_events(received_at DESC);

ALTER TABLE webhook_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own webhook events"
  ON webhook_events FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "System can insert webhook events"
  ON webhook_events FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Admins can view all webhook events"
  ON webhook_events FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- SUBSCRIPTIONS TABLE
-- =====================================================
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE UNIQUE NOT NULL,
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT UNIQUE,
  plan TEXT NOT NULL CHECK (plan IN ('starter', 'pro', 'elite')),
  status TEXT NOT NULL CHECK (status IN ('active', 'trialing', 'past_due', 'canceled')),
  trial_end TIMESTAMPTZ,
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer_id ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own subscription"
  ON subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Admins can view all subscriptions"
  ON subscriptions FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

-- =====================================================
-- ADMIN ACTIONS TABLE (Audit Trail)
-- =====================================================
CREATE TABLE admin_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_user_id UUID REFERENCES profiles(id),
  action TEXT NOT NULL,
  target_user_id UUID REFERENCES profiles(id),
  target_resource TEXT,
  details JSONB,
  ip_address INET,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_admin_actions_admin_user_id ON admin_actions(admin_user_id);
CREATE INDEX idx_admin_actions_target_user_id ON admin_actions(target_user_id);
CREATE INDEX idx_admin_actions_timestamp ON admin_actions(timestamp DESC);

ALTER TABLE admin_actions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Only admins can view audit log"
  ON admin_actions FOR SELECT
  USING ((auth.jwt() ->> 'role')::text = 'admin');

CREATE POLICY "System can insert admin actions"
  ON admin_actions FOR INSERT
  WITH CHECK (true);

-- =====================================================
-- EQUITY HISTORY TABLE (For charting)
-- =====================================================
CREATE TABLE equity_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id) ON DELETE CASCADE NOT NULL,
  broker TEXT NOT NULL,
  equity NUMERIC(15,2) NOT NULL,
  balance NUMERIC(15,2) NOT NULL,
  unrealized_pnl NUMERIC(15,2) DEFAULT 0,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_equity_history_user_id ON equity_history(user_id);
CREATE INDEX idx_equity_history_broker ON equity_history(broker);
CREATE INDEX idx_equity_history_timestamp ON equity_history(timestamp DESC);

ALTER TABLE equity_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own equity history"
  ON equity_history FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "System can insert equity history"
  ON equity_history FOR INSERT
  WITH CHECK (true);

-- =====================================================
-- FUNCTIONS
-- =====================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Hash API key with SHA-256
CREATE OR REPLACE FUNCTION hash_api_key(plaintext TEXT)
RETURNS TEXT AS $$
BEGIN
  RETURN encode(digest(plaintext, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Verify API key against hash
CREATE OR REPLACE FUNCTION verify_api_key(plaintext TEXT, hash TEXT)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN encode(digest(plaintext, 'sha256'), 'hex') = hash;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- TRIGGERS
-- =====================================================

-- Profiles updated_at trigger
CREATE TRIGGER update_profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Broker accounts updated_at trigger
CREATE TRIGGER update_broker_accounts_updated_at
  BEFORE UPDATE ON broker_accounts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Risk settings updated_at trigger
CREATE TRIGGER update_risk_settings_updated_at
  BEFORE UPDATE ON risk_settings
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Trading config updated_at trigger
CREATE TRIGGER update_trading_config_updated_at
  BEFORE UPDATE ON trading_config
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Positions updated_at trigger
CREATE TRIGGER update_positions_updated_at
  BEFORE UPDATE ON positions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- Subscriptions updated_at trigger
CREATE TRIGGER update_subscriptions_updated_at
  BEFORE UPDATE ON subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at();

-- =====================================================
-- REALTIME PUBLICATION (Enable Realtime)
-- =====================================================

-- Enable Realtime for positions (live P&L updates)
ALTER PUBLICATION supabase_realtime ADD TABLE positions;

-- Enable Realtime for orders (status changes)
ALTER PUBLICATION supabase_realtime ADD TABLE orders;

-- Enable Realtime for logs (live tail mode)
ALTER PUBLICATION supabase_realtime ADD TABLE logs;

-- =====================================================
-- INITIAL DATA (Optional: Seed admin user)
-- =====================================================

-- Insert default admin user (replace with actual values)
-- INSERT INTO profiles (id, email, name, role, plan_tier)
-- VALUES (
--   'admin-uuid-here',
--   'admin@empiretrading.io',
--   'System Admin',
--   'admin',
--   'elite'
-- );

-- =====================================================
-- CLEANUP / RETENTION POLICIES
-- =====================================================

-- Function to clean old logs (90 days retention)
CREATE OR REPLACE FUNCTION cleanup_old_logs()
RETURNS void AS $$
BEGIN
  DELETE FROM logs WHERE timestamp < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Function to clean old webhook events (30 days retention)
CREATE OR REPLACE FUNCTION cleanup_old_webhook_events()
RETURNS void AS $$
BEGIN
  DELETE FROM webhook_events WHERE received_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Schedule with pg_cron (if available) or external cron job
-- SELECT cron.schedule('cleanup-logs', '0 2 * * *', 'SELECT cleanup_old_logs()');
-- SELECT cron.schedule('cleanup-webhooks', '0 3 * * *', 'SELECT cleanup_old_webhook_events()');

-- =====================================================
-- END OF SCHEMA
-- =====================================================
