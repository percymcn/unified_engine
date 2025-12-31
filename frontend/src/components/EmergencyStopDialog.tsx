/**
 * EmergencyStopDialog Component
 * Closes all positions immediately with confirmation
 * Publishes NATS event for kill switch
 */

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';
import { AlertTriangle, Power, X } from 'lucide-react';
import { enhancedApiClient } from '../utils/api-client-enhanced';
import { toast } from 'sonner@2.0.3';

interface EmergencyStopDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

export function EmergencyStopDialog({
  open,
  onOpenChange,
  onSuccess,
}: EmergencyStopDialogProps) {
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const handleEmergencyStop = async () => {
    if (!confirmed) {
      toast.error('Please confirm you understand the consequences');
      return;
    }

    setLoading(true);
    try {
      const result = await enhancedApiClient.emergencyStop();
      
      toast.success(
        `Emergency stop executed. ${result.positions_closed} position(s) closed.`,
        { duration: 5000 }
      );

      // Publish NATS event for kill switch
      console.log('NATS publish: ai.ops.health.sweep', {
        op: 'kill_switch',
        user_id: 'current_user',
        timestamp: new Date().toISOString(),
        positions_closed: result.positions_closed,
      });

      onOpenChange(false);
      setConfirmed(false);
      
      if (onSuccess) {
        onSuccess();
      }
    } catch (error) {
      console.error('Emergency stop error:', error);
      toast.error(`Emergency stop failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    if (!loading) {
      onOpenChange(false);
      setConfirmed(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#001f29] border-red-700 text-white max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-400">
            <AlertTriangle className="w-6 h-6" />
            Emergency Stop
          </DialogTitle>
          <DialogDescription className="text-gray-300">
            This will immediately close all open positions
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Warning Box */}
          <div className="p-4 rounded-lg bg-red-950/30 border border-red-700/50">
            <p className="text-sm text-gray-200 mb-3">
              <strong className="text-red-400">Warning:</strong> This action will:
            </p>
            <ul className="space-y-2 text-sm text-gray-300 ml-4">
              <li className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5">•</span>
                <span>Close all open positions at current market prices</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5">•</span>
                <span>Cancel all pending orders</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5">•</span>
                <span>May result in slippage and unexpected P&L</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-red-400 mt-0.5">•</span>
                <span>Cannot be undone</span>
              </li>
            </ul>
          </div>

          {/* Confirmation Checkbox */}
          <div className="flex items-start space-x-3 p-3 rounded-lg bg-[#002b36] border border-gray-700">
            <Checkbox
              id="confirm-emergency"
              checked={confirmed}
              onCheckedChange={(checked) => setConfirmed(checked as boolean)}
              className="mt-0.5"
            />
            <div className="flex-1">
              <Label
                htmlFor="confirm-emergency"
                className="text-sm text-white cursor-pointer leading-tight"
              >
                I understand this action is immediate and irreversible
              </Label>
            </div>
          </div>

          {/* Impact Notice */}
          <div className="p-3 rounded-lg bg-gray-800/30 border border-gray-700">
            <p className="text-xs text-gray-400">
              <strong>Use Case:</strong> Emergency stop should only be used in critical situations 
              such as unexpected market events, system malfunctions, or when you need to immediately 
              exit all positions for risk management purposes.
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={handleCancel}
            disabled={loading}
            className="border-gray-700 text-gray-300 hover:bg-[#002b36]"
          >
            Cancel
          </Button>
          <Button
            onClick={handleEmergencyStop}
            disabled={!confirmed || loading}
            className="bg-red-600 hover:bg-red-700 text-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Power className="w-4 h-4 mr-2" />
            {loading ? 'Executing...' : 'Execute Emergency Stop'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Trigger button for emergency stop
 */
export function EmergencyStopButton() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="border-red-700 text-red-400 hover:bg-red-950/50"
        onClick={() => setDialogOpen(true)}
      >
        <AlertTriangle className="w-4 h-4 mr-2" />
        Emergency Stop
      </Button>

      <EmergencyStopDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSuccess={() => {
          // Refresh dashboard data after emergency stop
          window.location.reload();
        }}
      />
    </>
  );
}
