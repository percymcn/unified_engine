'use client';

import { useState } from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Pencil, Trash2, ArrowRight, Sparkles } from 'lucide-react';
import { SymbolAlias, SymbolAliasGroup } from '@/types/symbol-alias';
import { deleteSymbolAlias } from '@/lib/api/symbol-aliases';

interface SymbolAliasListProps {
  groups: SymbolAliasGroup[];
  onEdit: (alias: SymbolAlias) => void;
  onRefresh: () => void;
}

export function SymbolAliasList({ groups, onEdit, onRefresh }: SymbolAliasListProps) {
  const [deleteTarget, setDeleteTarget] = useState<SymbolAlias | null>(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!deleteTarget) return;

    setDeleting(true);
    try {
      await deleteSymbolAlias(deleteTarget.id);
      onRefresh();
    } catch (err) {
      console.error('Failed to delete alias:', err);
    } finally {
      setDeleting(false);
      setDeleteTarget(null);
    }
  };

  if (groups.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">
            No symbol mappings configured yet.
          </p>
          <p className="text-sm text-muted-foreground mt-2">
            Add a mapping to translate TradingView symbols to your broker's format.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-6">
        {groups.map((group) => (
          <Card key={group.brokerType}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">{group.brokerName}</CardTitle>
              <CardDescription>
                {group.aliases.length} symbol mapping{group.aliases.length !== 1 ? 's' : ''}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>TradingView</TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                    <TableHead>Broker Symbol</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {group.aliases.map((alias) => (
                    <TableRow key={alias.id}>
                      <TableCell className="font-mono font-medium">
                        {alias.sourceSymbol}
                      </TableCell>
                      <TableCell>
                        <ArrowRight className="h-4 w-4 text-muted-foreground" />
                      </TableCell>
                      <TableCell className="font-mono">
                        {alias.targetSymbol}
                      </TableCell>
                      <TableCell>
                        {alias.isAutoDetected ? (
                          <Badge variant="secondary" className="gap-1">
                            <Sparkles className="h-3 w-3" />
                            Auto
                          </Badge>
                        ) : (
                          <Badge variant="outline">Custom</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => onEdit(alias)}
                            title="Edit mapping"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => setDeleteTarget(alias)}
                            title="Delete mapping"
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Symbol Mapping</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the mapping from{' '}
              <span className="font-mono font-medium">{deleteTarget?.sourceSymbol}</span> to{' '}
              <span className="font-mono font-medium">{deleteTarget?.targetSymbol}</span>?
              {deleteTarget?.isAutoDetected && (
                <span className="block mt-2 text-sm">
                  This was an auto-detected mapping. You can re-detect it by testing your broker connection.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
