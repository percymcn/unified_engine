"""
OpenClaw Client for SmartFlow Integration
==========================================

Connects SmartFlow to OpenClaw for AI-powered signal analysis and position monitoring.
"""

import asyncio
import logging
from typing import Dict, Optional, Any
import aiohttp
import json

logger = logging.getLogger(__name__)


class OpenClawClient:
    """Client for communicating with OpenClaw AI agent system"""

    def __init__(self, gateway_url: str = "http://127.0.0.1:18789"):
        self.gateway_url = gateway_url
        self.ws_url = f"ws://127.0.0.1:18789"
        self.session: Optional[aiohttp.ClientSession] = None
        self.connected = False

    async def ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close the session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def analyze_signal(
        self,
        symbol: str,
        direction: str,
        flow_score: float,
        rsi: float,
        price: float,
        volume: float,
        flow_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyzes SmartFlow signal quality using OpenClaw AI.

        Returns:
        {
            "should_trade": bool,
            "quality_score": 0-100,
            "reasoning": str,
            "entry_suggestion": "immediate" | "wait_pullback" | "skip",
            "confidence": 0-1,
            "risk_reward_ratio": float,
            "optimal_entry_price": float,
            "stop_loss": float,
            "take_profit": float
        }
        """
        try:
            await self.ensure_session()

            # Build analysis prompt for OpenClaw
            prompt = f"""Analyze this SmartFlow trading signal for quality and timing:

SIGNAL DETAILS:
Symbol: {symbol}
Direction: {direction.upper()}
Current Price: ${price:.2f}
RSI: {rsi:.1f}
Volume: {volume:,.0f}

FLOW ANALYSIS:
Flow Score: {flow_score:.2f}
Sources: {flow_data.get('sources', [])}
Bullish Flows: {flow_data.get('bullish_count', 0)}
Bearish Flows: {flow_data.get('bearish_count', 0)}
Golden Sweeps: {flow_data.get('golden_sweeps', 0)}
Institutional Activity: {flow_data.get('institutional', False)}

ANALYSIS REQUIRED:

1. RSI EVALUATION (30 points):
   - For LONG: Is RSI in 30-50 range (oversold bounce)? Score high.
   - For SHORT: Is RSI in 50-70 range (overbought reversal)? Score high.
   - Extreme RSI (>70 or <30): Consider waiting for pullback.

2. FLOW ALIGNMENT (40 points):
   - Does flow direction match signal direction?
   - Is there institutional confirmation (golden sweeps)?
   - Are multiple sources agreeing?

3. VOLUME CONFIRMATION (20 points):
   - Is volume above average? (confidence boost)
   - Low volume? (proceed with caution)

4. ENTRY TIMING (10 points):
   - RSI extreme + strong flow → "wait_pullback"
   - RSI moderate + strong flow → "immediate"
   - Weak flow or divergence → "skip"

Provide a JSON response with:
{{
    "quality_score": <0-100 integer>,
    "should_trade": <true/false based on score >= 60>,
    "reasoning": "<detailed explanation>",
    "entry_suggestion": "<immediate|wait_pullback|skip>",
    "confidence": <0.0-1.0>,
    "risk_reward_ratio": <estimated R:R ratio>,
    "optimal_entry_price": <suggested entry price>,
    "stop_loss": <suggested stop loss price>,
    "take_profit": <suggested take profit price>
}}
"""

            # Send to OpenClaw (placeholder - adapt to actual OpenClaw API)
            # For now, return a mock response based on simple logic
            # TODO: Replace with actual OpenClaw WebSocket communication

            quality_score = self._calculate_quality_score(
                direction, rsi, flow_score, flow_data
            )

            should_trade = quality_score >= 60

            if direction.lower() == "long":
                entry_suggestion = "immediate" if 30 <= rsi <= 50 else "wait_pullback" if rsi < 30 else "skip"
            else:
                entry_suggestion = "immediate" if 50 <= rsi <= 70 else "wait_pullback" if rsi > 70 else "skip"

            reasoning = self._generate_reasoning(
                symbol, direction, rsi, flow_score, flow_data, quality_score
            )

            return {
                "should_trade": should_trade,
                "quality_score": quality_score,
                "reasoning": reasoning,
                "entry_suggestion": entry_suggestion,
                "confidence": quality_score / 100.0,
                "risk_reward_ratio": 2.0,  # Default 2:1
                "optimal_entry_price": price,
                "stop_loss": price * 0.99 if direction == "long" else price * 1.01,
                "take_profit": price * 1.02 if direction == "long" else price * 0.98
            }

        except Exception as e:
            logger.error(f"OpenClaw signal analysis error: {e}")
            # Fail open - return neutral result
            return {
                "should_trade": True,
                "quality_score": 50,
                "reasoning": f"OpenClaw error: {str(e)}. Proceeding with caution.",
                "entry_suggestion": "immediate",
                "confidence": 0.5,
                "risk_reward_ratio": 1.5,
                "optimal_entry_price": price,
                "stop_loss": price * 0.99 if direction == "long" else price * 1.01,
                "take_profit": price * 1.02 if direction == "long" else price * 0.98
            }

    def _calculate_quality_score(
        self,
        direction: str,
        rsi: float,
        flow_score: float,
        flow_data: Dict[str, Any]
    ) -> int:
        """Calculate signal quality score 0-100"""
        score = 0

        # RSI scoring (30 points)
        if direction.lower() == "long":
            if 30 <= rsi <= 50:
                score += 30
            elif 50 < rsi <= 60:
                score += 20
            elif rsi < 30:
                score += 15  # Oversold but wait for bounce
        else:  # short
            if 50 <= rsi <= 70:
                score += 30
            elif 40 <= rsi < 50:
                score += 20
            elif rsi > 70:
                score += 15  # Overbought but wait for rejection

        # Flow alignment (40 points)
        bullish = flow_data.get('bullish_count', 0)
        bearish = flow_data.get('bearish_count', 0)
        total_flows = bullish + bearish

        if total_flows > 0:
            if direction.lower() == "long":
                flow_alignment = bullish / total_flows
            else:
                flow_alignment = bearish / total_flows

            score += int(flow_alignment * 40)

        # Golden sweeps bonus (10 points)
        if flow_data.get('golden_sweeps', 0) > 0:
            score += 10

        # Institutional activity bonus (10 points)
        if flow_data.get('institutional', False):
            score += 10

        # Multiple sources bonus (10 points)
        sources = flow_data.get('sources', [])
        if len(sources) >= 2:
            score += 10

        return min(score, 100)

    def _generate_reasoning(
        self,
        symbol: str,
        direction: str,
        rsi: float,
        flow_score: float,
        flow_data: Dict[str, Any],
        quality_score: int
    ) -> str:
        """Generate human-readable reasoning"""
        reasons = []

        # RSI analysis
        if direction.lower() == "long":
            if 30 <= rsi <= 50:
                reasons.append(f"✓ RSI {rsi:.1f} in favorable oversold bounce zone (30-50)")
            elif rsi < 30:
                reasons.append(f"⚠ RSI {rsi:.1f} deeply oversold - consider waiting for bounce")
            else:
                reasons.append(f"✗ RSI {rsi:.1f} not ideal for LONG (prefer 30-50)")
        else:
            if 50 <= rsi <= 70:
                reasons.append(f"✓ RSI {rsi:.1f} in favorable overbought reversal zone (50-70)")
            elif rsi > 70:
                reasons.append(f"⚠ RSI {rsi:.1f} extremely overbought - consider waiting for rejection")
            else:
                reasons.append(f"✗ RSI {rsi:.1f} not ideal for SHORT (prefer 50-70)")

        # Flow analysis
        bullish = flow_data.get('bullish_count', 0)
        bearish = flow_data.get('bearish_count', 0)
        total = bullish + bearish

        if total > 0:
            if direction.lower() == "long" and bullish > bearish:
                reasons.append(f"✓ Bullish flow ({bullish}/{total}) aligns with LONG")
            elif direction.lower() == "short" and bearish > bullish:
                reasons.append(f"✓ Bearish flow ({bearish}/{total}) aligns with SHORT")
            else:
                reasons.append(f"✗ Flow direction conflicts with signal")

        # Golden sweeps
        if flow_data.get('golden_sweeps', 0) > 0:
            reasons.append(f"✓ {flow_data['golden_sweeps']} golden sweep(s) detected")

        # Institutional
        if flow_data.get('institutional', False):
            reasons.append("✓ Institutional activity confirmed")

        # Sources
        sources = flow_data.get('sources', [])
        if len(sources) >= 2:
            reasons.append(f"✓ Multiple sources agree ({', '.join(sources)})")

        verdict = "APPROVED" if quality_score >= 60 else "REJECTED"
        return f"{verdict} (Score: {quality_score}/100). " + " | ".join(reasons)

    async def monitor_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        current_price: float,
        rsi: float,
        flow_sentiment: str
    ) -> Dict[str, Any]:
        """
        Monitors open position and suggests exit actions.

        Returns:
        {
            "action": "hold" | "take_profit" | "exit" | "trail_stop",
            "reasoning": str,
            "urgency": "low" | "medium" | "high"
        }
        """
        try:
            # Calculate P&L
            if direction.lower() == "long":
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

            # Decision logic
            action = "hold"
            urgency = "low"
            reasoning = ""

            # Profit taking rules
            if pnl_pct >= 2.0 and (rsi > 70 or rsi < 30):
                action = "take_profit"
                urgency = "high"
                reasoning = f"P&L at {pnl_pct:.2f}% with RSI extreme ({rsi:.1f}) - take profit"

            elif pnl_pct >= 1.0 and flow_sentiment != direction.lower():
                action = "exit"
                urgency = "medium"
                reasoning = f"Flow flipped to {flow_sentiment} against our {direction} - exit"

            elif pnl_pct >= 1.0:
                action = "trail_stop"
                urgency = "low"
                reasoning = f"P&L at {pnl_pct:.2f}% - trail stop to lock profit"

            # Loss cutting rules
            elif pnl_pct <= -1.0 and flow_sentiment != direction.lower():
                action = "exit"
                urgency = "high"
                reasoning = f"Losing {abs(pnl_pct):.2f}% with flow against us - cut loss"

            return {
                "action": action,
                "reasoning": reasoning,
                "urgency": urgency,
                "pnl_pct": pnl_pct
            }

        except Exception as e:
            logger.error(f"OpenClaw position monitor error: {e}")
            return {
                "action": "hold",
                "reasoning": f"Monitor error: {str(e)}",
                "urgency": "low",
                "pnl_pct": 0.0
            }


# Singleton instance
_openclaw_client: Optional[OpenClawClient] = None


def get_openclaw_client() -> OpenClawClient:
    """Get or create OpenClaw client singleton"""
    global _openclaw_client
    if _openclaw_client is None:
        _openclaw_client = OpenClawClient()
    return _openclaw_client
