"""
Pine Script AI Fixer Router
Uses Claude/OpenAI to fix and enhance Pine Script code
"""

import os
import logging
from typing import Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Load .env file for API keys
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[3] / ".env"
    load_dotenv(env_path)
except ImportError:
    pass  # dotenv not installed, rely on environment

from app.db.database import get_db
from app.models.models import User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class RiskManagement(BaseModel):
    """Risk management settings for strategy"""
    stopLossType: str = Field(default="atr", description="Type: atr, percent, or fixed")
    stopLossValue: float = Field(default=1.5, description="Stop loss value")
    takeProfitRatio: float = Field(default=2.0, description="Risk:Reward ratio")


class PineFixRequest(BaseModel):
    """Request to fix Pine Script code"""
    code: str = Field(..., description="Pine Script code to fix")
    errors: Optional[str] = Field(None, description="Error messages from TradingView")
    requirements: Optional[str] = Field(None, description="Additional requirements")
    strategyType: Optional[str] = Field("both", description="long_only, short_only, or both")
    riskManagement: Optional[RiskManagement] = None


class WebhookPayload(BaseModel):
    """Generated webhook payload for TradingView alerts"""
    webhook_key: Optional[str] = None
    symbol: str = "{{ticker}}"
    action: str = "buy"
    quantity: Optional[float] = None
    riskPercent: Optional[float] = 1.0
    stopLoss: Optional[str] = None
    takeProfit: Optional[str] = None
    comment: Optional[str] = None


class PineFixResponse(BaseModel):
    """Response with fixed Pine Script"""
    success: bool
    fixedCode: str
    explanation: Optional[str] = None
    warnings: Optional[list[str]] = None
    webhookPayload: Optional[WebhookPayload] = None


def build_pine_fix_prompt(request: PineFixRequest) -> str:
    """Build the prompt for the AI model"""

    strategy_direction = {
        "long_only": "ONLY long entries (no shorts)",
        "short_only": "ONLY short entries (no longs)",
        "both": "both long and short entries"
    }.get(request.strategyType, "both long and short entries")

    sl_type = request.riskManagement.stopLossType if request.riskManagement else "atr"
    sl_value = request.riskManagement.stopLossValue if request.riskManagement else 1.5
    rr_ratio = request.riskManagement.takeProfitRatio if request.riskManagement else 2.0

    sl_description = {
        "atr": f"ATR-based stop loss ({sl_value}x ATR)",
        "percent": f"Percentage-based stop loss ({sl_value}%)",
        "fixed": f"Fixed pip stop loss ({sl_value} pips)"
    }.get(sl_type, f"ATR-based stop loss ({sl_value}x ATR)")

    prompt = f"""You are an expert Pine Script v5 developer. Fix the following Pine Script code and ensure it:

1. Uses proper //@version=5 syntax
2. Has valid strategy() or indicator() declaration
3. Uses correct ta.* function calls (ta.sma, ta.ema, ta.rsi, etc.)
4. Implements {strategy_direction}
5. Includes proper {sl_description}
6. Includes take profit at {rr_ratio}:1 risk-reward ratio
7. Adds alert() calls with JSON payloads for webhook integration
8. Has no syntax errors

The alert() calls MUST output JSON in this exact format:
alert('{{"symbol": "' + syminfo.ticker + '", "action": "buy", "price": ' + str.tostring(close) + ', "sl": ' + str.tostring(stopLoss) + ', "tp": ' + str.tostring(takeProfit) + '}}', alert.freq_once_per_bar_close)

ORIGINAL CODE:
```pinescript
{request.code}
```

"""

    if request.errors:
        prompt += f"""
ERRORS TO FIX:
{request.errors}

"""

    if request.requirements:
        prompt += f"""
ADDITIONAL REQUIREMENTS:
{request.requirements}

"""

    prompt += """
Return ONLY the fixed Pine Script code, no explanations. The code must be complete and ready to use in TradingView.
"""

    return prompt


async def call_anthropic_api(prompt: str) -> str:
    """Call Anthropic Claude API to fix Pine Script"""
    try:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        # Extract text from response
        response_text = ""
        for block in message.content:
            if hasattr(block, 'text'):
                response_text += block.text

        return response_text

    except ImportError:
        logger.warning("Anthropic SDK not installed, falling back to OpenAI")
        return await call_openai_api(prompt)
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        return await call_openai_api(prompt)


async def call_openai_api(prompt: str) -> str:
    """Fallback to OpenAI API if Anthropic fails"""
    try:
        import openai

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Pine Script v5 developer. Fix and improve trading strategy code."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=4096,
            temperature=0.3
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI service unavailable: {str(e)}"
        )


def extract_pine_code(response: str) -> str:
    """Extract Pine Script code from AI response"""
    # Check for code blocks
    if "```pinescript" in response:
        start = response.find("```pinescript") + len("```pinescript")
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()

    if "```pine" in response:
        start = response.find("```pine") + len("```pine")
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()

    if "```" in response:
        start = response.find("```") + 3
        # Skip language identifier if present
        newline = response.find("\n", start)
        if newline > start and newline - start < 20:
            start = newline + 1
        end = response.find("```", start)
        if end > start:
            return response[start:end].strip()

    # Return as-is if no code blocks found
    return response.strip()


def generate_webhook_payload(code: str, webhook_key: Optional[str] = None) -> WebhookPayload:
    """Generate webhook payload from Pine Script code"""
    # Determine if it's a long-only, short-only, or both strategy
    has_long = "strategy.long" in code.lower() or '"long"' in code.lower()
    has_short = "strategy.short" in code.lower() or '"short"' in code.lower()

    action = "buy" if has_long else ("sell" if has_short else "buy")

    return WebhookPayload(
        webhook_key=webhook_key,
        symbol="{{ticker}}",
        action=action,
        riskPercent=1.0,
        stopLoss="{{strategy.order.stop}}",
        takeProfit="{{strategy.order.limit}}",
        comment="AI Strategy Suite"
    )


@router.post("/fix-pine", response_model=PineFixResponse)
async def fix_pine_script(
    request: PineFixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fix Pine Script code using AI

    Sends the code to Claude/OpenAI for fixing and returns the corrected version
    with proper syntax, risk management, and webhook integration.
    """
    try:
        # Build the prompt
        prompt = build_pine_fix_prompt(request)

        # Call AI API
        response = await call_anthropic_api(prompt)

        # Extract code from response
        fixed_code = extract_pine_code(response)

        # Validate the fixed code has basic requirements
        warnings = []
        if "//@version=" not in fixed_code:
            warnings.append("Missing version directive - added //@version=5")
            fixed_code = "//@version=5\n" + fixed_code

        if "strategy(" not in fixed_code and "indicator(" not in fixed_code:
            warnings.append("Missing strategy/indicator declaration")

        if "alert(" not in fixed_code:
            warnings.append("No alert() calls found - webhooks may not work")

        # Get user's webhook key for payload generation
        webhook_key = None
        if hasattr(current_user, 'webhook_key'):
            webhook_key = current_user.webhook_key

        # Generate webhook payload
        webhook_payload = generate_webhook_payload(fixed_code, webhook_key)

        return PineFixResponse(
            success=True,
            fixedCode=fixed_code,
            explanation="Code has been fixed and optimized for TradingView with webhook integration.",
            warnings=warnings if warnings else None,
            webhookPayload=webhook_payload
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pine Script fix error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fix Pine Script: {str(e)}"
        )


@router.post("/analyze-strategy")
async def analyze_strategy(
    request: PineFixRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze a Pine Script strategy for potential issues and improvements
    """
    try:
        analysis_prompt = f"""Analyze this Pine Script strategy and provide:
1. Identified trading biases (time-of-day, trend, etc.)
2. Risk management issues
3. Suggested improvements
4. Expected performance characteristics

CODE:
```pinescript
{request.code}
```

Return analysis in JSON format:
{{
    "biases": [{{"type": "time|day|session|trend", "description": "...", "severity": "low|medium|high"}}],
    "riskIssues": [{{"type": "no_sl|large_position|etc", "description": "...", "severity": "low|medium|high|critical", "recommendation": "..."}}],
    "suggestions": [{{"type": "parameter|logic|filter|exit", "description": "...", "expectedImpact": "...", "codeSnippet": "..."}}],
    "summary": "Brief overall assessment"
}}
"""

        response = await call_anthropic_api(analysis_prompt)

        # Try to parse as JSON
        import json
        try:
            # Extract JSON from response
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
            else:
                json_str = response.strip()

            analysis = json.loads(json_str)
            return {"success": True, "analysis": analysis}
        except json.JSONDecodeError:
            return {"success": True, "analysis": {"summary": response}}

    except Exception as e:
        logger.error(f"Strategy analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze strategy: {str(e)}"
        )
