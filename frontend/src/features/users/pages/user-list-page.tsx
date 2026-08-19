"use client";

import { Plus, Users as UsersIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";
import type { SortingState } from "@tanstack/react-table";

import {
  DataTable,
  DataTableEmpty,
  DataTableNoResults,
  DataTablePagination,
  DataTableToolbar,
  useDataTable,
} from "@/components/data-table";
import { ConfirmationDialog } from "@/components/feedback/dialogs/confirmation-dialog";
import { AdvancedFilter, AppliedFilters, SearchBar, StatusFilter } from "@/components/filters";
import type { AppliedFilter } from "@/components/filters";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { Button } from "@/components/ui/button";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getUserColumns } from "@/features/users/components/user-columns";
import { useUserRowActions } from "@/features/users/components/user-row-actions";
import { USER_STATUS_FILTER_OPTIONS, USER_STATUS_LABELS } from "@/features/users/constants/user-status";
import { useRoleOptions } from "@/features/users/hooks/use-role-options";
import { useUpdateUserStatus } from "@/features/users/hooks/use-update-user-status";
import { useUserFilters } from "@/features/users/hooks/use-user-filters";
import { useUsers } from "@/features/users/hooks/use-users";
import type { UserFilters } from "@/features/users/schemas/user-filters";
import type { ManagedUser } from "@/features/users/types/user";
import { normalizeApiError } from "@/utils/api-error";

const USER_MANAGE_PERMISSION = "user:manage";

/**
 * The Administration -> Users list page: search, Role/Status filters,
 * sorting, pagination, and row-level Activate/Deactivate via a shared
 * confirmation dialog. Mirrors CompanyListPage's structure; the notable
 * difference is there is no hard Delete here - Users are deactivated
 * (AccountStatus.INACTIVE), never removed, per ARCHITECTURE.md §38.
 */
export function UserListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [filters, setFilters] = useUserFilters();
  const [pendingStatusChange, setPendingStatusChange] = useState<ManagedUser | null>(null);

  const listQuery = useUsers(filters);
  const roleOptionsQuery = useRoleOptions();
  const updateUserStatus = useUpdateUserStatus();
  const users = listQuery.data?.data ?? [];
  const totalCount = listQuery.data?.meta.total_records ?? 0;
  const apiError = listQuery.isError ? normalizeApiError(listQuery.error) : null;

  const hasActiveFilters = Boolean(filters.search.trim() || filters.roleId || filters.status);
  const isGenuinelyEmpty = !listQuery.isLoading && !apiError && totalCount === 0 && !hasActiveFilters;
  const isNoResults = !listQuery.isLoading && !apiError && totalCount === 0 && hasActiveFilters;

  const applyFilterChange = useCallback(
    (patch: Partial<Omit<UserFilters, "page">>) => {
      setFilters({ ...patch, page: 1 });
    },
    [setFilters]
  );

  const goToPage = useCallback((page: number) => setFilters({ page }), [setFilters]);
  const setPageSize = useCallback((pageSize: number) => setFilters({ pageSize, page: 1 }), [setFilters]);
  const clearAllFilters = useCallback(() => setFilters(null), [setFilters]);

  const onStatusChangeRequest = useCallback((user: ManagedUser) => setPendingStatusChange(user), []);
  const rowActionsFor = useUserRowActions(onStatusChangeRequest);
  const columns = useMemo(() => getUserColumns(rowActionsFor), [rowActionsFor]);

  const sorting = useMemo<SortingState>(
    () => [{ id: filters.sort, desc: filters.direction === "desc" }],
    [filters.sort, filters.direction]
  );

  const table = useDataTable({
    data: users,
    columns,
    sorting,
    onSortingChange: (updater) => {
      const [next] = typeof updater === "function" ? updater(sorting) : updater;
      if (next) {
        applyFilterChange({ sort: next.id as UserFilters["sort"], direction: next.desc ? "desc" : "asc" });
        return;
      }
      applyFilterChange({ direction: filters.direction === "desc" ? "asc" : "desc" });
    },
    enableMultiSort: false,
    pageCount: Math.max(1, Math.ceil(totalCount / filters.pageSize)),
  });

  const roleName = (roleId: string | null) =>
    roleOptionsQuery.data?.find((role) => role.id === roleId)?.name ?? roleId ?? "";

  const appliedFilters: AppliedFilter[] = [
    filters.search.trim() ? { key: "search", label: `Search: "${filters.search.trim()}"` } : null,
    filters.roleId ? { key: "roleId", label: `Role: ${roleName(filters.roleId)}` } : null,
    filters.status ? { key: "status", label: `Status: ${USER_STATUS_LABELS[filters.status]}` } : null,
  ].filter((filter): filter is AppliedFilter => filter !== null);

  function removeAppliedFilter(key: string) {
    if (key === "search") applyFilterChange({ search: "" });
    if (key === "roleId") applyFilterChange({ roleId: null });
    if (key === "status") applyFilterChange({ status: null });
  }

  const isDeactivating = pendingStatusChange?.status !== "inactive";
  const nextStatus = isDeactivating ? "inactive" : "active";

  return (
    <>
      <ListPageTemplate
        title="Users"
        description="Administrators and staff with access to this organization."
        icon={UsersIcon}
        primaryAction={
          hasPermission(USER_MANAGE_PERMISSION)
            ? { label: "New User", icon: Plus, href: "/users/new" }
            : undefined
        }
        isLoading={listQuery.isLoading}
        error={
          apiError
            ? {
                title: "Failed to load users",
                description: apiError.message,
                onRetry: () => listQuery.refetch(),
              }
            : null
        }
        isEmpty={isGenuinelyEmpty}
        emptyState={
          <DataTableEmpty
            title="No users yet"
            description="Users you add will appear here."
            action={
              hasPermission(USER_MANAGE_PERMISSION) ? (
                <Button asChild size="sm">
                  <Link href="/users/new">
                    <Plus aria-hidden />
                    New User
                  </Link>
                </Button>
              ) : undefined
            }
          />
        }
      >
        <DataTable
          table={table}
          toolbar={
            <div className="flex flex-col gap-3">
              <DataTableToolbar
                search={
                  <SearchBar
                    defaultValue={filters.search}
                    onSearch={(value) => applyFilterChange({ search: value })}
                    placeholder="Search by name, email or username…"
                    isLoading={listQuery.isFetching}
                    aria-label="Search users"
                    className="min-w-56 flex-1"
                  />
                }
                filters={
                  <AdvancedFilter
                    triggerLabel="Filters"
                    activeCount={appliedFilters.length}
                    onReset={hasActiveFilters ? clearAllFilters : undefined}
                    resetLabel="Clear all"
                  >
                    <StatusFilter
                      label="Status"
                      options={USER_STATUS_FILTER_OPTIONS}
                      value={filters.status ?? undefined}
                      onChange={(value) => applyFilterChange({ status: value ?? null })}
                    />
                    <StatusFilter
                      label="Role"
                      options={(roleOptionsQuery.data ?? []).map((role) => ({
                        value: role.id,
                        label: role.name,
                      }))}
                      value={filters.roleId ?? undefined}
                      onChange={(value) => applyFilterChange({ roleId: value ?? null })}
                    />
                  </AdvancedFilter>
                }
              />

              <AppliedFilters
                filters={appliedFilters}
                onRemove={removeAppliedFilter}
                onClearAll={hasActiveFilters ? clearAllFilters : undefined}
              />
            </div>
          }
          pagination={
            <DataTablePagination
              pageIndex={filters.page - 1}
              pageSize={filters.pageSize}
              totalCount={totalCount}
              onPageChange={(pageIndex) => goToPage(pageIndex + 1)}
              onPageSizeChange={setPageSize}
            />
          }
          isLoading={listQuery.isFetching}
          loadingRowCount={Math.min(filters.pageSize, 10)}
          isNoResults={isNoResults}
          noResultsState={
            <DataTableNoResults
              description={
                filters.search.trim()
                  ? `No users match "${filters.search.trim()}". Try a different search or clear your filters.`
                  : "Try adjusting your search or filters."
              }
              onClearFilters={clearAllFilters}
            />
          }
          onRowClick={
            hasPermission(USER_MANAGE_PERMISSION) ? (user) => router.push(`/users/${user.id}`) : undefined
          }
          stickyActionColumn
          aria-label="Users"
        />
      </ListPageTemplate>

      {pendingStatusChange && (
        <ConfirmationDialog
          open={Boolean(pendingStatusChange)}
          onOpenChange={(open) => !open && setPendingStatusChange(null)}
          title={isDeactivating ? `Deactivate ${pendingStatusChange.fullName}?` : `Activate ${pendingStatusChange.fullName}?`}
          description={
            isDeactivating
              ? "They will be signed out everywhere and unable to log in until reactivated."
              : "They will be able to log in again."
          }
          variant={isDeactivating ? "destructive" : "default"}
          confirmLabel={isDeactivating ? "Deactivate" : "Activate"}
          isLoading={updateUserStatus.isPending}
          onConfirm={() =>
            updateUserStatus.mutate(
              { id: pendingStatusChange.id, status: nextStatus },
              { onSuccess: () => setPendingStatusChange(null) }
            )
          }
        />
      )}
    </>
  );
}
