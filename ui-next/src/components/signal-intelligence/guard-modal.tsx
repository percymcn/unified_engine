"use client";

import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";

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
    } catch (error) {
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

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            {modalData.type === "momentum_warning" ? "Momentum Warning" : "Exposure Warning"}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {modalData.message}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
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
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
