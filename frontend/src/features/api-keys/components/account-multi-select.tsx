import { memo, useCallback, useMemo, useState } from "react";
import { ChevronsUpDown, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useAccounts } from "@/features/accounts/hooks/use-accounts";
import { cn } from "@/lib/utils";

export type AccountMultiSelectProps = {
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  triggerId?: string;
  ariaInvalid?: boolean;
  ariaDescribedBy?: string;
  triggerClassName?: string;
};

export const AccountMultiSelect = memo(function AccountMultiSelect({
  value,
  onChange,
  placeholder = "All accounts",
  triggerId,
  ariaInvalid = false,
  ariaDescribedBy,
  triggerClassName,
}: AccountMultiSelectProps) {
  const { accountsQuery } = useAccounts();
  const accounts = useMemo(() => accountsQuery.data ?? [], [accountsQuery.data]);
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return accounts;
    const query = search.toLowerCase();
    return accounts.filter(
      (account) =>
        account.accountId.toLowerCase().includes(query) ||
        account.email.toLowerCase().includes(query) ||
        account.displayName.toLowerCase().includes(query),
    );
  }, [accounts, search]);

  const selectedSet = useMemo(() => new Set(value), [value]);
  const selectedAccounts = useMemo(
    () =>
      value
        .map((accountId) => accounts.find((account) => account.accountId === accountId))
        .filter((account): account is (typeof accounts)[number] => account !== undefined),
    [accounts, value],
  );

  const toggle = useCallback(
    (accountId: string) => {
      if (selectedSet.has(accountId)) {
        onChange(value.filter((current) => current !== accountId));
        return;
      }
      onChange([...value, accountId]);
    },
    [onChange, selectedSet, value],
  );

  const remove = useCallback(
    (accountId: string) => {
      onChange(value.filter((current) => current !== accountId));
    },
    [onChange, value],
  );

  const selectAll = useCallback(() => {
    onChange([]);
  }, [onChange]);

  const label =
    value.length === 0 ? placeholder : `${value.length} account${value.length > 1 ? "s" : ""} selected`;

  return (
    <div className="space-y-1.5">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            type="button"
            variant="outline"
            id={triggerId}
            aria-invalid={ariaInvalid}
            aria-describedby={ariaDescribedBy}
            className={cn("w-full justify-between font-normal", triggerClassName)}
            disabled={accountsQuery.isLoading}
          >
            <span className="truncate text-left">
              {accountsQuery.isLoading ? "Loading accounts..." : label}
            </span>
            <ChevronsUpDown className="ml-1 size-4 shrink-0 opacity-50" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[var(--radix-dropdown-menu-trigger-width)] max-h-64">
          <div className="px-2 py-1.5">
            <Input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search accounts..."
              className="h-7 text-xs"
              onClick={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
            />
          </div>
          <DropdownMenuSeparator />
          <DropdownMenuCheckboxItem
            checked={value.length === 0}
            onCheckedChange={selectAll}
            onSelect={(event) => event.preventDefault()}
          >
            All accounts
          </DropdownMenuCheckboxItem>
          <DropdownMenuSeparator />
          {filtered.map((account) => (
            <DropdownMenuCheckboxItem
              key={account.accountId}
              checked={selectedSet.has(account.accountId)}
              onCheckedChange={() => toggle(account.accountId)}
              onSelect={(event) => event.preventDefault()}
            >
              {account.email}
            </DropdownMenuCheckboxItem>
          ))}
          {filtered.length === 0 ? (
            <div className="px-2 py-1.5 text-xs text-muted-foreground">No accounts found</div>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>

      {selectedAccounts.length > 0 ? (
        <div className="flex flex-wrap gap-1">
          {selectedAccounts.map((account) => (
            <Badge key={account.accountId} variant="secondary" className="gap-1 text-xs">
              {account.email}
              <button
                type="button"
                className="ml-0.5 hover:text-foreground"
                onClick={() => remove(account.accountId)}
              >
                <X className="size-3" />
              </button>
            </Badge>
          ))}
        </div>
      ) : null}
    </div>
  );
});
