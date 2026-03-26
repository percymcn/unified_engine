"""
LuxAlgo Indicators — Python Port
==================================
5 LuxAlgo TradingView indicators ported to pure Python using pandas + numpy + pandas_ta.

Indicators:
    A. Smart Money Concepts (SMC)
    B. Oscillator Matrix
    C. Evasive SuperTrend
    D. Price Action Concepts (PAC)
    E. Daily Polynomial Regressions

Usage:
    from app.services.luxalgo_indicators import (
        smart_money_concepts, oscillator_matrix,
        evasive_supertrend, price_action_concepts,
        daily_poly_regression
    )
    result = smart_money_concepts(df)
"""

import logging
from typing import Dict, Any, Optional, List

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    ta = None

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_cols(df: pd.DataFrame, cols: List[str], name: str) -> bool:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        logger.warning(f"{name}: missing columns {missing}")
        return False
    return True


def _swing_highs(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """Rolling swing high — centre bar is higher than ±lookback neighbours."""
    highs = df['high']
    # A swing high: the bar at position i is the max of the window centred on i
    roll_max = highs.rolling(window=2 * lookback + 1, center=True).max()
    return (highs == roll_max)


def _swing_lows(df: pd.DataFrame, lookback: int = 5) -> pd.Series:
    """Rolling swing low."""
    lows = df['low']
    roll_min = lows.rolling(window=2 * lookback + 1, center=True).min()
    return (lows == roll_min)


def _empty_signal(indicator: str) -> Dict[str, Any]:
    return {'indicator': indicator, 'signal': 'none', 'error': 'insufficient_data'}


# ---------------------------------------------------------------------------
# A. Smart Money Concepts (SMC)
# ---------------------------------------------------------------------------

def smart_money_concepts(df: pd.DataFrame, lookback: int = 5) -> Dict[str, Any]:
    """
    Smart Money Concepts (SMC)

    Returns:
        signal: 'buy' | 'sell' | 'none'
        signal_type: 'choch+' | 'choch' | 'bos' | None
        confidence: float 0–1
        order_block: bool
        fvg: bool
    """
    required = ['open', 'high', 'low', 'close']
    if not _require_cols(df, required, 'SMC') or len(df) < lookback * 3:
        return _empty_signal('smc')

    try:
        df = df.copy().reset_index(drop=True)
        close = df['close']
        high = df['high']
        low = df['low']

        swing_h = _swing_highs(df, lookback)
        swing_l = _swing_lows(df, lookback)

        # Get the most recent confirmed swing high and low (excluding last lookback bars)
        valid_up_to = len(df) - lookback - 1
        sh_indices = [i for i in range(valid_up_to) if swing_h.iloc[i]]
        sl_indices = [i for i in range(valid_up_to) if swing_l.iloc[i]]

        if not sh_indices or not sl_indices:
            return _empty_signal('smc')

        last_sh_idx = sh_indices[-1]
        last_sl_idx = sl_indices[-1]
        last_sh = high.iloc[last_sh_idx]
        last_sl = low.iloc[last_sl_idx]

        last_close = close.iloc[-1]

        # Determine current trend (which swing came last)
        if last_sh_idx > last_sl_idx:
            current_trend = 'bullish'    # Last swing was a high → trend is up
        else:
            current_trend = 'bearish'   # Last swing was a low → trend is down

        # ── BOS / CHoCH detection ──────────────────────────────────────────
        signal = 'none'
        signal_type = None
        confidence = 0.0

        bos_buy  = last_close > last_sh   # Price breaks above last swing high
        bos_sell = last_close < last_sl   # Price breaks below last swing low

        if bos_buy:
            if current_trend == 'bearish':
                # BOS in opposite direction of trend → CHoCH (reversal)
                signal = 'buy'
                # Check CHoCH+: was there a previous close above last_sh on a prior bar?
                prev_closes_above = close.iloc[last_sh_idx:-1] > last_sh
                if prev_closes_above.any():
                    signal_type = 'choch+'
                    confidence = 0.90
                else:
                    signal_type = 'choch'
                    confidence = 0.75
            else:
                signal = 'buy'
                signal_type = 'bos'
                confidence = 0.65

        elif bos_sell:
            if current_trend == 'bullish':
                signal = 'sell'
                prev_closes_below = close.iloc[last_sl_idx:-1] < last_sl
                if prev_closes_below.any():
                    signal_type = 'choch+'
                    confidence = 0.90
                else:
                    signal_type = 'choch'
                    confidence = 0.75
            else:
                signal = 'sell'
                signal_type = 'bos'
                confidence = 0.65

        # ── Order Blocks ───────────────────────────────────────────────────
        # Bullish OB: last bearish candle (open > close) before a bullish BOS
        # Bearish OB: last bullish candle (open < close) before a bearish BOS
        order_block = False
        if signal == 'buy' and bos_buy:
            for i in range(last_sh_idx, 0, -1):
                if df['open'].iloc[i] > df['close'].iloc[i]:   # bearish candle
                    order_block = True
                    confidence = min(1.0, confidence + 0.10)
                    break
        elif signal == 'sell' and bos_sell:
            for i in range(last_sl_idx, 0, -1):
                if df['open'].iloc[i] < df['close'].iloc[i]:   # bullish candle
                    order_block = True
                    confidence = min(1.0, confidence + 0.10)
                    break

        # ── Fair Value Gaps (FVG) ──────────────────────────────────────────
        # Need at least 3 bars
        fvg = False
        if len(df) >= 3:
            c0 = df.iloc[-3]   # oldest of the 3
            c2 = df.iloc[-1]   # newest
            # Bullish FVG: gap between c0 high and c2 low (price leaves a gap up)
            if c0['high'] < c2['low']:
                fvg = True
                if signal == 'buy':
                    confidence = min(1.0, confidence + 0.05)
            # Bearish FVG: gap between c0 low and c2 high (price leaves a gap down)
            elif c0['low'] > c2['high']:
                fvg = True
                if signal == 'sell':
                    confidence = min(1.0, confidence + 0.05)

        return {
            'indicator': 'smc',
            'signal': signal,
            'signal_type': signal_type,
            'confidence': round(confidence, 3),
            'order_block': order_block,
            'fvg': fvg,
            'current_trend': current_trend,
            'last_swing_high': float(last_sh),
            'last_swing_low': float(last_sl),
        }

    except Exception as e:
        logger.error(f"SMC error: {e}", exc_info=True)
        return _empty_signal('smc')


# ---------------------------------------------------------------------------
# B. Oscillator Matrix
# ---------------------------------------------------------------------------

def oscillator_matrix(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Oscillator Matrix — 6 confluent oscillator components.

    Returns:
        signal: 'buy' | 'sell' | 'none'
        confluence_count: int (0–6)
        strength: 'strong' | 'normal'
        overbought: bool
        oversold: bool
    """
    required = ['high', 'low', 'close', 'volume']
    if not _require_cols(df, required, 'OscMatrix') or len(df) < 35:
        return _empty_signal('oscillator_matrix')

    if not PANDAS_TA_AVAILABLE:
        return {**_empty_signal('oscillator_matrix'), 'error': 'pandas_ta not available'}

    try:
        df = df.copy().reset_index(drop=True)
        bullish_count = 0

        # 1. RSI(14)
        rsi_series = ta.rsi(df['close'], length=14)
        rsi = float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else 50.0
        if rsi > 55:
            bullish_count += 1
        overbought = rsi > 70
        oversold = rsi < 30

        # 2. MACD histogram rising and > 0
        macd_df = ta.macd(df['close'], fast=12, slow=26, signal=9)
        if macd_df is not None and not macd_df.empty:
            hist_col = [c for c in macd_df.columns if 'h' in c.lower() or 'hist' in c.lower()]
            if hist_col:
                hist = macd_df[hist_col[0]]
                if float(hist.iloc[-1]) > 0 and float(hist.iloc[-1]) > float(hist.iloc[-2]):
                    bullish_count += 1

        # 3. Stochastic(14,3,3): K > D and K < 80
        stoch_df = ta.stoch(df['high'], df['low'], df['close'], k=14, d=3, smooth_k=3)
        if stoch_df is not None and not stoch_df.empty:
            k_col = [c for c in stoch_df.columns if 'K' in c or 'k' in c.lower()]
            d_col = [c for c in stoch_df.columns if 'D' in c or 'd' in c.lower()]
            if k_col and d_col:
                k_val = float(stoch_df[k_col[0]].iloc[-1])
                d_val = float(stoch_df[d_col[0]].iloc[-1])
                if k_val > d_val and k_val < 80:
                    bullish_count += 1

        # 4. CCI(20) > 0
        cci_series = ta.cci(df['high'], df['low'], df['close'], length=20)
        if cci_series is not None and not cci_series.empty:
            if float(cci_series.iloc[-1]) > 0:
                bullish_count += 1

        # 5. Williams %R(14) > -50
        willr_series = ta.willr(df['high'], df['low'], df['close'], length=14)
        if willr_series is not None and not willr_series.empty:
            if float(willr_series.iloc[-1]) > -50:
                bullish_count += 1

        # 6. MFI(14) > 50
        mfi_series = ta.mfi(df['high'], df['low'], df['close'], df['volume'], length=14)
        if mfi_series is not None and not mfi_series.empty:
            if float(mfi_series.iloc[-1]) > 50:
                bullish_count += 1

        # Signal
        if bullish_count >= 4:
            signal = 'buy'
        elif bullish_count <= 2:
            signal = 'sell'
        else:
            signal = 'none'

        strength = 'strong' if bullish_count >= 5 or bullish_count <= 1 else 'normal'

        return {
            'indicator': 'oscillator_matrix',
            'signal': signal,
            'confluence_count': bullish_count,
            'strength': strength,
            'overbought': overbought,
            'oversold': oversold,
            'rsi': round(rsi, 2),
        }

    except Exception as e:
        logger.error(f"OscMatrix error: {e}", exc_info=True)
        return _empty_signal('oscillator_matrix')


# ---------------------------------------------------------------------------
# C. Evasive SuperTrend
# ---------------------------------------------------------------------------

def evasive_supertrend(
    df: pd.DataFrame,
    atr_period: int = 10,
    multiplier: float = 3.0,
    evasion_threshold: float = 0.5,
    evasion_push: float = 1.0,
) -> Dict[str, Any]:
    """
    Evasive SuperTrend.

    Returns:
        signal: 'buy' | 'sell' | 'none'
        flip: bool — direction changed this bar
        evasion_event: bool — band was pushed this bar
        band_level: float — current band value
    """
    required = ['high', 'low', 'close']
    if not _require_cols(df, required, 'EST') or len(df) < atr_period + 5:
        return _empty_signal('evasive_supertrend')

    try:
        df = df.copy().reset_index(drop=True)

        # True Range and ATR
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift(1)).abs(),
            (df['low'] - df['close'].shift(1)).abs(),
        ], axis=1).max(axis=1)
        atr = tr.rolling(atr_period).mean()

        hl2 = (df['high'] + df['low']) / 2.0
        close = df['close']

        # Build SuperTrend iteratively (needed for evasion logic)
        upper_band = np.full(len(df), np.nan)
        lower_band = np.full(len(df), np.nan)
        direction  = np.full(len(df), 1, dtype=int)   # 1=bullish, -1=bearish
        band_arr   = np.full(len(df), np.nan)          # active band
        evasion    = np.zeros(len(df), dtype=bool)

        for i in range(atr_period, len(df)):
            atr_i = atr.iloc[i]
            if np.isnan(atr_i):
                continue

            basic_upper = float(hl2.iloc[i]) + multiplier * atr_i
            basic_lower = float(hl2.iloc[i]) - multiplier * atr_i

            # Ratchet bands
            if i == atr_period:
                upper_band[i] = basic_upper
                lower_band[i] = basic_lower
                direction[i] = 1
                band_arr[i] = lower_band[i]
                continue

            prev_upper = upper_band[i - 1]
            prev_lower = lower_band[i - 1]
            prev_dir   = direction[i - 1]
            c = float(close.iloc[i])

            # Standard ratchet
            if not np.isnan(prev_lower) and basic_lower > prev_lower:
                upper_band[i] = basic_upper
                lower_band[i] = basic_lower
            else:
                upper_band[i] = min(basic_upper, prev_upper) if not np.isnan(prev_upper) else basic_upper
                lower_band[i] = max(basic_lower, prev_lower) if not np.isnan(prev_lower) else basic_lower

            # Evasion: price within 0.5*ATR of the active band → push band away
            if prev_dir == 1:
                active_band = lower_band[i]
                if (c - active_band) < evasion_threshold * atr_i:
                    lower_band[i] -= evasion_push * atr_i
                    evasion[i] = True
            else:
                active_band = upper_band[i]
                if (active_band - c) < evasion_threshold * atr_i:
                    upper_band[i] += evasion_push * atr_i
                    evasion[i] = True

            # Direction flip
            if prev_dir == 1 and c < lower_band[i]:
                direction[i] = -1
            elif prev_dir == -1 and c > upper_band[i]:
                direction[i] = 1
            else:
                direction[i] = prev_dir

            band_arr[i] = lower_band[i] if direction[i] == 1 else upper_band[i]

        last_dir  = int(direction[-1])
        prev_dir  = int(direction[-2]) if len(direction) > 1 else last_dir
        flip      = bool(last_dir != prev_dir)
        evasion_e = bool(evasion[-1])
        band_val  = float(band_arr[-1]) if not np.isnan(band_arr[-1]) else 0.0

        signal = 'buy' if last_dir == 1 else 'sell'

        return {
            'indicator': 'evasive_supertrend',
            'signal': signal,
            'flip': flip,
            'evasion_event': evasion_e,
            'band_level': round(band_val, 4),
            'direction': last_dir,
        }

    except Exception as e:
        logger.error(f"EST error: {e}", exc_info=True)
        return _empty_signal('evasive_supertrend')


# ---------------------------------------------------------------------------
# D. Price Action Concepts (PAC)
# ---------------------------------------------------------------------------

def price_action_concepts(df: pd.DataFrame, lookback: int = 5, equal_range: float = 0.001) -> Dict[str, Any]:
    """
    Price Action Concepts (PAC).

    Returns:
        signal: 'buy' | 'sell' | 'none'
        type: 'choch+' | 'choch' | 'liquidity_grab' | 'bos' | None
        order_block: bool
        confidence: float
    """
    required = ['open', 'high', 'low', 'close']
    if not _require_cols(df, required, 'PAC') or len(df) < lookback * 3:
        return _empty_signal('pac')

    try:
        df = df.copy().reset_index(drop=True)
        close = df['close']
        high = df['high']
        low = df['low']

        swing_h = _swing_highs(df, lookback)
        swing_l = _swing_lows(df, lookback)

        valid_up_to = len(df) - lookback - 1
        sh_indices = [i for i in range(valid_up_to) if swing_h.iloc[i]]
        sl_indices = [i for i in range(valid_up_to) if swing_l.iloc[i]]

        if not sh_indices or not sl_indices:
            return _empty_signal('pac')

        last_sh_idx = sh_indices[-1]
        last_sl_idx = sl_indices[-1]
        last_sh = float(high.iloc[last_sh_idx])
        last_sl = float(low.iloc[last_sl_idx])
        last_close = float(close.iloc[-1])

        current_trend = 'bullish' if last_sh_idx > last_sl_idx else 'bearish'

        # ── CHoCH / BOS ────────────────────────────────────────────────────
        signal = 'none'
        sig_type = None
        confidence = 0.0

        if last_close > last_sh:
            signal = 'buy'
            if current_trend == 'bearish':
                # CHoCH
                prev_closes_above = close.iloc[last_sh_idx:-1] > last_sh
                if prev_closes_above.any():
                    sig_type = 'choch+'
                    confidence = 0.90
                else:
                    sig_type = 'choch'
                    confidence = 0.78
            else:
                sig_type = 'bos'
                confidence = 0.65

        elif last_close < last_sl:
            signal = 'sell'
            if current_trend == 'bullish':
                prev_closes_below = close.iloc[last_sl_idx:-1] < last_sl
                if prev_closes_below.any():
                    sig_type = 'choch+'
                    confidence = 0.90
                else:
                    sig_type = 'choch'
                    confidence = 0.78
            else:
                sig_type = 'bos'
                confidence = 0.65

        # ── Equal Highs/Lows (last 20 bars) ───────────────────────────────
        recent = df.iloc[-20:]
        recent_highs = recent['high'].values
        recent_lows  = recent['low'].values
        # Equal highs: any pair within 0.1%
        # Vectorized equal highs/lows check (O(n) not O(n^2))
        if len(recent_highs) > 1:
            rh = recent_highs
            eq_high = bool(np.any(
                np.abs(rh[:, None] - rh[None, :]) / np.where(rh[:, None] > 0, rh[:, None], 1) < equal_range
            ) if len(rh) < 50 else False)
        else:
            eq_high = False
        if len(recent_lows) > 1:
            rl = recent_lows
            rl_safe = np.where(rl > 0, rl, 1e-9)
            eq_low = bool(np.any(
                np.abs(rl[:, None] - rl[None, :]) / rl_safe[:, None] < equal_range
            ) if len(rl) < 50 else False)
        else:
            eq_low = False

        # ── Liquidity Grab detection ───────────────────────────────────────
        liq_grab = False
        last_bar = df.iloc[-1]
        # Bullish liq grab: wick below equal lows then closes above them
        if eq_low and last_bar['low'] < recent_lows.min() and last_bar['close'] > recent_lows.min():
            liq_grab = True
            if signal == 'none':
                signal = 'buy'
                sig_type = 'liquidity_grab'
                confidence = 0.78

        # Bearish liq grab: wick above equal highs then closes below them
        if eq_high and last_bar['high'] > recent_highs.max() and last_bar['close'] < recent_highs.max():
            liq_grab = True
            if signal == 'none':
                signal = 'sell'
                sig_type = 'liquidity_grab'
                confidence = 0.78

        # ── Order Block ────────────────────────────────────────────────────
        order_block = False
        if signal == 'buy':
            for i in range(last_sh_idx, 0, -1):
                if df['open'].iloc[i] > df['close'].iloc[i]:
                    order_block = True
                    confidence = min(1.0, confidence + 0.10)
                    break
        elif signal == 'sell':
            for i in range(last_sl_idx, 0, -1):
                if df['open'].iloc[i] < df['close'].iloc[i]:
                    order_block = True
                    confidence = min(1.0, confidence + 0.10)
                    break

        return {
            'indicator': 'pac',
            'signal': signal,
            'type': sig_type,
            'order_block': order_block,
            'confidence': round(confidence, 3),
            'liquidity_grab': liq_grab,
            'equal_highs': eq_high,
            'equal_lows': eq_low,
        }

    except Exception as e:
        logger.error(f"PAC error: {e}", exc_info=True)
        return _empty_signal('pac')


# ---------------------------------------------------------------------------
# E. Daily Polynomial Regressions
# ---------------------------------------------------------------------------

def daily_poly_regression(df: pd.DataFrame, deviation_mult: float = 1.5) -> Dict[str, Any]:
    """
    Daily Polynomial Regressions.
    Resets at each new trading day. Fits degrees 1-4, picks best R².

    Returns:
        signal: 'buy' | 'sell' | 'none'
        r_squared: float
        degree: int
        type: 'trend' | 'mean_reversion'
        deviation_stddev: float
    """
    required = ['close']
    if not _require_cols(df, required, 'PolyReg') or len(df) < 5:
        return _empty_signal('poly_regression')

    try:
        df = df.copy().reset_index(drop=True)

        # Identify today's bars (reset at new day if datetime index available)
        if hasattr(df.index, 'date') or 'timestamp' in df.columns or 'datetime' in df.columns:
            dt_col = 'datetime' if 'datetime' in df.columns else 'timestamp'
            if dt_col in df.columns:
                df['_date'] = pd.to_datetime(df[dt_col]).dt.date
                today = df['_date'].iloc[-1]
                day_df = df[df['_date'] == today].copy()
            else:
                day_df = df.copy()
        else:
            # No date info — use all bars (or last 78 bars ≈ 1 trading day of 5m bars)
            day_df = df.iloc[-78:].copy() if len(df) > 78 else df.copy()

        if len(day_df) < 4:
            return _empty_signal('poly_regression')

        closes = day_df['close'].values.astype(float)
        x = np.arange(len(closes), dtype=float)

        best_degree = 1
        best_r2 = -np.inf
        best_coeffs = None
        best_fitted = None
        best_residuals = None

        for deg in range(1, 5):
            if len(closes) < deg + 2:
                continue
            try:
                coeffs = np.polyfit(x, closes, deg)
                fitted = np.polyval(coeffs, x)
                ss_res = np.sum((closes - fitted) ** 2)
                ss_tot = np.sum((closes - closes.mean()) ** 2)
                r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
                if r2 > best_r2:
                    best_r2 = r2
                    best_degree = deg
                    best_coeffs = coeffs
                    best_fitted = fitted
                    best_residuals = closes - fitted
            except Exception:
                continue

        if best_fitted is None:
            return _empty_signal('poly_regression')

        # Endpoint direction
        is_bullish = float(best_fitted[-1]) > float(best_fitted[0])

        # Mean reversion: current price deviates > 1.5 * std(residuals)
        std_res = float(np.std(best_residuals))
        last_dev = float(closes[-1] - best_fitted[-1])
        dev_sigma = abs(last_dev) / std_res if std_res > 0 else 0.0
        mean_reversion = dev_sigma > deviation_mult

        if mean_reversion:
            # Fade the deviation
            signal = 'sell' if last_dev > 0 else 'buy'
            sig_type = 'mean_reversion'
        else:
            # Follow the trend direction
            signal = 'buy' if is_bullish else 'sell'
            sig_type = 'trend'

        return {
            'indicator': 'poly_regression',
            'signal': signal,
            'r_squared': round(float(best_r2), 4),
            'degree': best_degree,
            'type': sig_type,
            'deviation_stddev': round(dev_sigma, 3),
            'is_bullish_trend': is_bullish,
        }

    except Exception as e:
        logger.error(f"PolyReg error: {e}", exc_info=True)
        return _empty_signal('poly_regression')


# ---------------------------------------------------------------------------
# Convenience: run all 5
# ---------------------------------------------------------------------------

def run_all(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Run all 5 LuxAlgo indicators and return a dict of results."""
    return {
        'smc':               smart_money_concepts(df),
        'oscillator_matrix': oscillator_matrix(df),
        'evasive_supertrend': evasive_supertrend(df),
        'pac':               price_action_concepts(df),
        'poly_regression':   daily_poly_regression(df),
    }
