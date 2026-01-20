import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BrokerHealthGrid } from '@/components/brokers/broker-health-grid';

export default function AccountsPage() {
  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Accounts</h1>
        <p className="text-muted-foreground">
          Manage your broker accounts and monitor connection status.
        </p>
      </div>

      {/* Broker Health Grid */}
      <div>
        <h2 className="text-lg font-semibold tracking-tight mb-4">Broker Connections</h2>
        <BrokerHealthGrid />
      </div>

      {/* Accounts list placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Connected Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Account management will be available in Phase 9.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
