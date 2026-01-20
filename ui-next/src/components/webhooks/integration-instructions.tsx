'use client';

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2 } from 'lucide-react';

export function IntegrationInstructions() {
  return (
    <Accordion type="single" collapsible className="w-full">
      {/* TradingView */}
      <AccordionItem value="tradingview">
        <AccordionTrigger>
          <div className="flex items-center gap-2">
            <span className="font-semibold">TradingView Setup</span>
            <Badge variant="outline">Popular</Badge>
          </div>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-4 text-sm">
            <Alert>
              <AlertDescription>
                First, create a webhook configuration in the Signal Routing page to get your
                webhook key.
              </AlertDescription>
            </Alert>

            <div className="space-y-3">
              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 1: Create Alert</p>
                  <p className="text-muted-foreground">
                    In TradingView, right-click on your chart and select &quot;Add alert&quot;
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 2: Configure Alert</p>
                  <p className="text-muted-foreground">Set your conditions and alert name</p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 3: Enable Webhook</p>
                  <p className="text-muted-foreground">
                    Check &quot;Webhook URL&quot; and paste your webhook URL from above
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 4: Configure Message</p>
                  <p className="text-muted-foreground">
                    Set the message body to JSON format:
                  </p>
                  <pre className="mt-2 rounded-md bg-muted p-3 overflow-x-auto">
                    <code>{`{
  "symbol": "{{ticker}}",
  "action": "buy",
  "price": {{close}},
  "strategy": "My Strategy"
}`}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      {/* TrailHacker */}
      <AccordionItem value="trailhacker">
        <AccordionTrigger>
          <span className="font-semibold">TrailHacker Setup</span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-4 text-sm">
            <Alert>
              <AlertDescription>
                Configure your TrailHacker bot to send signals to your webhook URL.
              </AlertDescription>
            </Alert>

            <div className="space-y-3">
              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 1: Open Bot Settings</p>
                  <p className="text-muted-foreground">
                    Navigate to your bot configuration in TrailHacker
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 2: Add Webhook</p>
                  <p className="text-muted-foreground">
                    Find the webhook configuration section and paste your webhook URL
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 3: Set Payload Format</p>
                  <p className="text-muted-foreground">Ensure payload includes required fields:</p>
                  <pre className="mt-2 rounded-md bg-muted p-3 overflow-x-auto">
                    <code>{`{
  "symbol": "EURUSD",
  "action": "buy",
  "price": 1.0850,
  "strategy": "My Strategy"
}`}</code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      {/* Custom */}
      <AccordionItem value="custom">
        <AccordionTrigger>
          <span className="font-semibold">Custom Webhook Setup</span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-4 text-sm">
            <Alert>
              <AlertDescription>
                Send signals from any custom bot, script, or trading system using HTTP POST.
              </AlertDescription>
            </Alert>

            <div className="space-y-3">
              <div>
                <p className="font-semibold mb-2">Required Payload Fields</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
                  <li>
                    <code className="text-xs">symbol</code> - Trading pair (e.g., EURUSD)
                  </li>
                  <li>
                    <code className="text-xs">action</code> - Trade action (buy, sell, close)
                  </li>
                </ul>
              </div>

              <div>
                <p className="font-semibold mb-2">Optional Fields</p>
                <ul className="list-disc list-inside space-y-1 text-muted-foreground ml-4">
                  <li>
                    <code className="text-xs">price</code> - Current price
                  </li>
                  <li>
                    <code className="text-xs">strategy</code> - Strategy name
                  </li>
                  <li>
                    <code className="text-xs">metadata</code> - Additional data object
                  </li>
                </ul>
              </div>

              <div>
                <p className="font-semibold mb-2">Example: Python</p>
                <pre className="rounded-md bg-muted p-3 overflow-x-auto">
                  <code>{`import requests

url = "YOUR_WEBHOOK_URL_HERE"
payload = {
    "symbol": "EURUSD",
    "action": "buy",
    "price": 1.0850,
    "strategy": "My Bot"
}

response = requests.post(url, json=payload)
print(response.json())`}</code>
                </pre>
              </div>

              <div>
                <p className="font-semibold mb-2">Example: cURL</p>
                <pre className="rounded-md bg-muted p-3 overflow-x-auto">
                  <code>{`curl -X POST YOUR_WEBHOOK_URL_HERE \\
  -H "Content-Type: application/json" \\
  -d '{
    "symbol": "EURUSD",
    "action": "buy",
    "price": 1.0850,
    "strategy": "Manual Test"
  }'`}</code>
                </pre>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>

      {/* Testing */}
      <AccordionItem value="testing">
        <AccordionTrigger>
          <span className="font-semibold">Testing Your Webhook</span>
        </AccordionTrigger>
        <AccordionContent>
          <div className="space-y-4 text-sm">
            <Alert>
              <AlertDescription>
                Test your webhook configuration before sending live signals.
              </AlertDescription>
            </Alert>

            <div className="space-y-3">
              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 1: Use cURL or Postman</p>
                  <p className="text-muted-foreground">
                    Send a test POST request with your webhook URL
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 2: Check Signal Status</p>
                  <p className="text-muted-foreground">
                    Navigate to the Dashboard to see if your signal was received and processed
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 3: Verify Routing</p>
                  <p className="text-muted-foreground">
                    Ensure signals are routed to the correct broker accounts based on your routing
                    rules
                  </p>
                </div>
              </div>

              <div className="flex gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold">Step 4: Monitor Logs</p>
                  <p className="text-muted-foreground">
                    Check the Trade Logs for any errors or execution details
                  </p>
                </div>
              </div>
            </div>
          </div>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
