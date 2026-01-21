import { Suspense } from 'react';
import { AccountList } from '@/components/accounts/account-list';
import { BrokerHealthGrid } from '@/components/brokers/broker-health-grid';

function AccountListSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-24 bg-muted animate-pulse rounded-lg" />
      <div className="h-24 bg-muted animate-pulse rounded-lg" />
    </div>
  );
}

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

      {/* Account Management */}
      <div>
        <h2 className="text-lg font-semibold tracking-tight mb-4">
          Broker Accounts
        </h2>
        <Suspense fallback={<AccountListSkeleton />}>
          <AccountList />
        </Suspense>
      </div>

      {/* Broker Health Grid */}
      <div>
        <h2 className="text-lg font-semibold tracking-tight mb-4">
          Broker Connections
        </h2>
        <BrokerHealthGrid />
      </div>
    </div>
  );
}
