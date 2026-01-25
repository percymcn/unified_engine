"use client";

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { AlertTriangle, CheckCircle, XCircle } from "lucide-react";

interface GuardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  modalData: {
    type: string;
    message: string;
    count?: number;
    current_bias?: string;
    opposite_bias?: string;
    options?: string[];
    current_exposure?: number;
    max_exposure?: number;
    // Webhook 202 response fields
    symbol?: string;
    action?: string;
    quantity?: number;
    reason?: string;
    reason_detail?: string;
    warning_type?: string;
  };
  sessionKey?: string;
  signalId?: string;
  onActionComplete?: () => void;
}

export function GuardModal({
  open,
  onOpenChange,
  modalData,
  sessionKey,
  signalId,
  onActionComplete
}: GuardModalProps) {
  const [processing, setProcessing] = useState(false);
  const { toast } = useToast();

  async function handleAction(action: string) {
    setProcessing(true);
    try {
      const res = await fetch("/api/signal-intelligence/modal-action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          signal_id: signalId,
          action: action,
          session_key: sessionKey,
        }),
      });

      if (res.ok) {
        const result = await res.json();
        toast({
          title: "Action completed",
          description: result.message || `Action "${action}" completed successfully`,
        });
        onOpenChange(false);
        if (onActionComplete) {
          onActionComplete();
        }
      } else {
        const error = await res.json().catch(() => ({ detail: "Action failed" }));
        toast({
          title: "Error",
          description: error.detail || "Failed to complete action",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "Error",
        description: "Failed to complete action",
        variant: "destructive",
      });
    } finally {
      setProcessing(false);
    }
  }

  if (!modalData) return null;

  // Check if this is a webhook 202 response (has symbol/action)
  const isWebhookWarning = Boolean(modalData.symbol && modalData.action);

  // Determine title based on type
  const getTitle = () => {
    if (isWebhookWarning) return "Signal Requires Confirmation";
    if (modalData.type === "momentum_warning") return "Momentum Warning";
    return "Exposure Warning";
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            {getTitle()}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {modalData.message || "The Signal Intelligence Guard has flagged this signal for review."}
          </AlertDialogDescription>
        </AlertDialogHeader>

        {/* Webhook Signal Info */}
        {isWebhookWarning && (
          <div className="space-y-3 py-2">
            <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{modalData.symbol}</span>
                  <Badge
                    variant="secondary"
                    className={
                      modalData.action?.toUpperCase() === "BUY"
                        ? "bg-green-100 text-green-700"
                        : "bg-red-100 text-red-700"
                    }
                  >
                    {modalData.action?.toUpperCase()}
                  </Badge>
                  {modalData.quantity && (
                    <span className="text-sm text-muted-foreground">
                      {modalData.quantity} lots
                    </span>
                  )}
                </div>
              </div>
            </div>
            {(modalData.warning_type || modalData.reason) && (
              <Badge variant="outline" className="border-amber-500 text-amber-600">
                {modalData.warning_type || modalData.reason}
              </Badge>
            )}
            {modalData.reason_detail && (
              <p className="text-sm text-muted-foreground">{modalData.reason_detail}</p>
            )}
          </div>
        )}

        <AlertDialogFooter>
          {/* Webhook 202 buttons: execute or discard */}
          {isWebhookWarning ? (
            <>
              <AlertDialogCancel
                onClick={() => handleAction("discard")}
                disabled={processing}
                className="gap-2"
              >
                <XCircle className="h-4 w-4" />
                Discard
              </AlertDialogCancel>
              <AlertDialogAction
                onClick={() => handleAction("execute")}
                disabled={processing}
                className="gap-2"
              >
                <CheckCircle className="h-4 w-4" />
                Execute Anyway
              </AlertDialogAction>
            </>
          ) : (
            <>
              {modalData.options?.includes("breakeven") && (
                <AlertDialogAction
                  onClick={() => handleAction("breakeven")}
                  disabled={processing}
                >
                  Breakeven
                </AlertDialogAction>
              )}
              {modalData.options?.includes("close") && (
                <Button
                  onClick={() => handleAction("close")}
                  disabled={processing}
                  variant="destructive"
                >
                  Close
                </Button>
              )}
              {modalData.options?.includes("ignore") && (
                <AlertDialogCancel
                  onClick={() => handleAction("ignore")}
                  disabled={processing}
                >
                  Ignore
                </AlertDialogCancel>
              )}
              {modalData.options?.includes("pause") && (
                <AlertDialogAction
                  onClick={() => handleAction("pause")}
                  disabled={processing}
                >
                  Pause
                </AlertDialogAction>
              )}
              {modalData.options?.includes("continue") && (
                <AlertDialogAction
                  onClick={() => handleAction("continue")}
                  disabled={processing}
                >
                  Continue
                </AlertDialogAction>
              )}
            </>
          )}
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
