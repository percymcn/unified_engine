'use client';

import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Edit, Trash2, Users, Folder, Briefcase, Building, Star, Shield } from 'lucide-react';
import { AccountGroup } from '@/types/account';

interface AccountGroupCardProps {
  group: AccountGroup;
  onEdit: (group: AccountGroup) => void;
  onDelete: (group: AccountGroup) => void;
  onManageAccounts: (group: AccountGroup) => void;
}

// Icon mapping for group icons
const ICON_MAP: Record<string, React.FC<{ className?: string }>> = {
  folder: Folder,
  briefcase: Briefcase,
  building: Building,
  star: Star,
  shield: Shield,
  users: Users,
};

export function AccountGroupCard({
  group,
  onEdit,
  onDelete,
  onManageAccounts,
}: AccountGroupCardProps) {
  const IconComponent = ICON_MAP[group.icon] || Folder;

  return (
    <Card className="relative overflow-hidden">
      {/* Color strip at top */}
      <div
        className="absolute top-0 left-0 right-0 h-1"
        style={{ backgroundColor: group.color }}
      />

      <CardHeader className="pt-4">
        <div className="flex items-start gap-3">
          <div
            className="p-2 rounded-lg"
            style={{ backgroundColor: `${group.color}20` }}
          >
            <IconComponent
              className="h-5 w-5"
              style={{ color: group.color }}
            />
          </div>
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg truncate">{group.name}</CardTitle>
            <CardDescription className="flex items-center gap-2 mt-1">
              <Users className="h-3.5 w-3.5" />
              {group.accountCount} {group.accountCount === 1 ? 'account' : 'accounts'}
            </CardDescription>
          </div>
          {!group.isActive && (
            <Badge variant="secondary">Inactive</Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {group.description ? (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {group.description}
          </p>
        ) : (
          <p className="text-sm text-muted-foreground italic">
            No description
          </p>
        )}
      </CardContent>

      <CardFooter className="flex justify-between gap-2 pt-0">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onManageAccounts(group)}
          className="flex-1"
        >
          <Users className="h-4 w-4 mr-2" />
          Manage Accounts
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onEdit(group)}
        >
          <Edit className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => onDelete(group)}
          className="text-destructive hover:text-destructive hover:bg-destructive/10"
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </CardFooter>
    </Card>
  );
}
