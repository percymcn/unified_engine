import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8765';

interface ConversionConfig {
  strategyName: string;
  includeStopLoss: boolean;
  includeTakeProfit: boolean;
  includeTimestamp: boolean;
  includeQuantity: boolean;
  defaultQuantity: string;
  useSymbolFromChart: boolean;
}

interface ConversionResult {
  success: boolean;
  convertedCode: string;
  webhookTemplate: string;
  alertMessage: string;
  warnings: string[];
  summary: string;
}

/**
 * POST /api/ai-suite/convert-script
 * Convert any Pine Script to work with TradeFlow webhooks
 */
export async function POST(request: NextRequest) {
  try {
    const token = await getTokenFromCookies();
    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { code, config } = body;

    if (!code) {
      return NextResponse.json(
        { error: 'Code is required' },
        { status: 400 }
      );
    }

    // Try backend first (if it has this endpoint)
    try {
      const response = await fetch(`${BACKEND_URL}/api/v1/ai-suite/convert-script`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (response.ok) {
        const data = await response.json();
        return NextResponse.json(data);
      }
    } catch {
      // Backend doesn't have this endpoint, use local conversion
    }

    // Local conversion fallback
    const result = convertScriptLocally(code, config);
    return NextResponse.json(result);

  } catch (error) {
    console.error('AI Suite convert-script error:', error);
    return NextResponse.json(
      { error: 'Failed to convert script', detail: String(error) },
      { status: 500 }
    );
  }
}

/**
 * Local conversion function - converts Pine Script to TradeFlow webhook format
 */
function convertScriptLocally(code: string, config: ConversionConfig): ConversionResult {
  const warnings: string[] = [];
  let convertedCode = code;

  // Detect script type
  const isIndicator = code.includes('indicator(') || code.includes('study(');
  const isStrategy = code.includes('strategy(');

  // Detect existing alert conditions
  const hasAlertCondition = code.includes('alertcondition(') || code.includes('alert(');
  const hasStrategyEntry = code.includes('strategy.entry(') || code.includes('strategy.order(');

  // Build webhook JSON
  const webhookJson = {
    webhook_key: 'YOUR_WEBHOOK_KEY',
    action: '{{strategy.order.action}}',
    symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
    ...(config.includeQuantity && { quantity: parseFloat(config.defaultQuantity) || 0.01 }),
    ...(config.includeStopLoss && { sl: '{{strategy.order.stop}}' }),
    ...(config.includeTakeProfit && { tp: '{{strategy.order.take_profit}}' }),
    ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
    strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
    comment: `${config.strategyName} Alert`,
  };

  // Generate alert message for different scenarios
  let alertMessage = '';

  if (isStrategy || hasStrategyEntry) {
    // Strategy - use strategy placeholders
    alertMessage = JSON.stringify({
      webhook_key: 'YOUR_WEBHOOK_KEY',
      action: '{{strategy.order.action}}',
      symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
      quantity: parseFloat(config.defaultQuantity) || 0.01,
      ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
      strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
      comment: '{{strategy.order.comment}}',
    }, null, 2);
  } else {
    // Indicator - generate buy/sell JSON templates
    alertMessage = `// For BUY alerts:
${JSON.stringify({
  webhook_key: 'YOUR_WEBHOOK_KEY',
  action: 'buy',
  symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
  quantity: parseFloat(config.defaultQuantity) || 0.01,
  ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
  strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
  comment: `${config.strategyName} Buy Signal`,
}, null, 2)}

// For SELL alerts:
${JSON.stringify({
  webhook_key: 'YOUR_WEBHOOK_KEY',
  action: 'sell',
  symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
  quantity: parseFloat(config.defaultQuantity) || 0.01,
  ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
  strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
  comment: `${config.strategyName} Sell Signal`,
}, null, 2)}

// For CLOSE alerts:
${JSON.stringify({
  webhook_key: 'YOUR_WEBHOOK_KEY',
  action: 'close',
  symbol: config.useSymbolFromChart ? '{{ticker}}' : 'SYMBOL',
  ...(config.includeTimestamp && { timestamp: '{{timenow}}' }),
  strategy_id: config.strategyName.toLowerCase().replace(/\s+/g, '_'),
  comment: `${config.strategyName} Close Position`,
}, null, 2)}`;
  }

  // Modify code to add alert functions if needed
  if (isIndicator && !hasAlertCondition) {
    // Find entry/exit conditions in the code
    const longConditionMatch = code.match(/(\w+)\s*=.*?(crossover|crossunder|>|<).*?(long|buy|entry)/i) ||
                               code.match(/(longCondition|buyCondition|entryLong)\s*=/i);
    const shortConditionMatch = code.match(/(\w+)\s*=.*?(crossover|crossunder|>|<).*?(short|sell|entry)/i) ||
                                code.match(/(shortCondition|sellCondition|entryShort)\s*=/i);

    // Add alert conditions
    const alertCode = `
// ============ TradeFlow Alert Integration ============
// Add these alert conditions to enable webhook signals

// Long/Buy Alert
alertcondition(${longConditionMatch ? longConditionMatch[1] : 'longCondition'},
    title="${config.strategyName} - Buy Signal",
    message='{"webhook_key":"YOUR_WEBHOOK_KEY","action":"buy","symbol":"{{ticker}}","quantity":${config.defaultQuantity}${config.includeTimestamp ? ',"timestamp":"{{timenow}}"' : ''},"strategy_id":"${config.strategyName.toLowerCase().replace(/\s+/g, '_')}","comment":"${config.strategyName} Buy"}')

// Short/Sell Alert
alertcondition(${shortConditionMatch ? shortConditionMatch[1] : 'shortCondition'},
    title="${config.strategyName} - Sell Signal",
    message='{"webhook_key":"YOUR_WEBHOOK_KEY","action":"sell","symbol":"{{ticker}}","quantity":${config.defaultQuantity}${config.includeTimestamp ? ',"timestamp":"{{timenow}}"' : ''},"strategy_id":"${config.strategyName.toLowerCase().replace(/\s+/g, '_')}","comment":"${config.strategyName} Sell"}')

// Close Position Alert (optional - use with exit condition)
// alertcondition(exitCondition,
//     title="${config.strategyName} - Close Position",
//     message='{"webhook_key":"YOUR_WEBHOOK_KEY","action":"close","symbol":"{{ticker}}"${config.includeTimestamp ? ',"timestamp":"{{timenow}}"' : ''},"strategy_id":"${config.strategyName.toLowerCase().replace(/\s+/g, '_')}","comment":"${config.strategyName} Close"}')

// ============ End TradeFlow Integration ============
`;

    convertedCode = code + '\n' + alertCode;
    warnings.push('Added alert conditions at the end of the script. Make sure longCondition and shortCondition variables exist.');
  } else if (isStrategy) {
    // For strategies, add the webhook URL instruction as a comment
    const webhookComment = `
// ============ TradeFlow Webhook Integration ============
// To connect this strategy to TradeFlow:
//
// 1. Add this strategy to your chart
// 2. Create an alert: Right-click chart > Add Alert
// 3. In Condition, select this strategy
// 4. Enable "Webhook URL" and enter your TradeFlow webhook URL:
//    https://app.mytradeflow.com/api/webhook/execute
//
// 5. In the Message field, use this JSON format:
//    {
//      "webhook_key": "YOUR_WEBHOOK_KEY",
//      "action": "{{strategy.order.action}}",
//      "symbol": "{{ticker}}",
//      "quantity": ${config.defaultQuantity},
//      "timestamp": "{{timenow}}",
//      "strategy_id": "${config.strategyName.toLowerCase().replace(/\s+/g, '_')}",
//      "comment": "{{strategy.order.comment}}"
//    }
//
// Replace YOUR_WEBHOOK_KEY with your actual webhook key from TradeFlow
// ============ End TradeFlow Integration ============

`;

    // Insert the comment after the version declaration
    const versionMatch = code.match(/\/\/@version=\d+\n/);
    if (versionMatch && versionMatch.index !== undefined) {
      const insertPos = versionMatch.index + versionMatch[0].length;
      convertedCode = code.slice(0, insertPos) + webhookComment + code.slice(insertPos);
    } else {
      convertedCode = webhookComment + code;
    }

    warnings.push('Strategy detected. Make sure to enable webhook alerts and use the provided JSON template.');
  }

  // Check for common issues
  if (!code.includes('strategy.') && !code.includes('alertcondition')) {
    warnings.push('No strategy entries or alert conditions found. You may need to manually add entry/exit logic.');
  }

  if (!code.includes('stop') && !code.includes('sl')) {
    warnings.push('No stop loss detected. Consider adding risk management for live trading.');
  }

  const webhookTemplate = `Webhook URL:
https://app.mytradeflow.com/api/webhook/execute

Your Webhook Key:
Get this from TradeFlow Dashboard > Settings > API Keys

Payload Format:
${JSON.stringify(webhookJson, null, 2)}`;

  const summary = isStrategy
    ? `Strategy converted! Added webhook integration comments and generated alert JSON template. Use with TradingView strategy alerts.`
    : `Indicator modified! Added ${hasAlertCondition ? 'enhanced' : 'new'} alert conditions for TradeFlow webhook integration.`;

  return {
    success: true,
    convertedCode,
    webhookTemplate,
    alertMessage,
    warnings,
    summary,
  };
}
