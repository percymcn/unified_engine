import { useState } from 'react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Eye, EyeOff, Copy, RefreshCw, Check, Info } from 'lucide-react';
import { toast } from 'sonner@2.0.3';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from './ui/alert-dialog';

interface ApiKeyDisplayProps {
  apiKey: string;
  accountId: string;
  accountName: string;
  broker: string;
  onRegenerate?: (accountId: string) => Promise<void>;
  showLabel?: boolean;
  compact?: boolean;
}

export function ApiKeyDisplay({
  apiKey,
  accountId,
  accountName,
  broker,
  onRegenerate,
  showLabel = true,
  compact = false,
}: ApiKeyDisplayProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [copied, setCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    toast.success('API Key copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRegenerate = async () => {
    if (!onRegenerate) return;
    
    setRegenerating(true);
    try {
      await onRegenerate(accountId);
      toast.success('API Key regenerated successfully');
    } catch (error) {
      toast.error('Failed to regenerate API Key');
    } finally {
      setRegenerating(false);
    }
  };

  const maskedKey = apiKey.replace(/./g, '•');
  const displayKey = isVisible ? apiKey : maskedKey;

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <code className="text-xs bg-muted px-2 py-1 rounded font-mono flex-1 truncate">
          {displayKey}
        </code>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setIsVisible(!isVisible)}
          className="h-7 w-7 p-0"
        >
          {isVisible ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-7 w-7 p-0"
        >
          {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {showLabel && (
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">API Key</label>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <Info className="h-4 w-4 text-muted-foreground" />
              </TooltipTrigger>
              <TooltipContent className="max-w-xs">
                <p className="text-xs">
                  Use this API Key in TradingView alerts to send trading signals to your {broker} account.
                  Include it in the Authorization header as "Bearer {'{API_KEY}'}"
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      )}

      <div className="flex items-center gap-2 p-3 bg-muted/50 border border-border rounded-lg">
        <code className="text-sm font-mono flex-1 truncate select-all">
          {displayKey}
        </code>

        <div className="flex items-center gap-1">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsVisible(!isVisible)}
                  className="h-8 w-8 p-0"
                >
                  {isVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isVisible ? 'Hide' : 'Show'} API Key</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  className="h-8 w-8 p-0"
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-500" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Copy to clipboard</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {onRegenerate && (
            <TooltipProvider>
              <Tooltip>
                <AlertDialog>
                  <TooltipTrigger asChild>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-8 w-8 p-0"
                        disabled={regenerating}
                      >
                        <RefreshCw className={`h-4 w-4 ${regenerating ? 'animate-spin' : ''}`} />
                      </Button>
                    </AlertDialogTrigger>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Regenerate API Key</p>
                  </TooltipContent>

                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Regenerate API Key?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This will generate a new API Key for "{accountName}". 
                        Your old API Key will stop working immediately and you'll need to update 
                        any TradingView alerts or webhooks that use it.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={handleRegenerate}>
                        Regenerate
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Keep this API Key secure. It allows TradingView to execute trades on your behalf.
      </p>
    </div>
  );
}
