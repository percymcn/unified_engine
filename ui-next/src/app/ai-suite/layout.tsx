'use client';

import { UserProvider } from '@/providers/user-provider';

export default function AISuiteLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <UserProvider>{children}</UserProvider>;
}
