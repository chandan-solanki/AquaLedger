"use client";

import { KeyRound } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { DataTable, DataTableEmpty, DataTableNoResults, DataTableToolbar, useDataTable } from "@/components/data-table";
import { ErrorState } from "@/components/feedback/error-state";
import { SearchBar } from "@/components/filters";
import { ListPageTemplate } from "@/components/templates/list-page-template";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { getRoleColumns } from "@/features/roles/components/role-columns";
import { useRoles } from "@/features/roles/hooks/use-roles";
import { normalizeApiError } from "@/utils/api-error";

const USER_MANAGE_PERMISSION = "user:manage";

/**
 * The Administration -> Roles & Permissions list page: search plus a fully
 * client-side-sorted table of Role / Users / Permissions counts, per this
 * session's mockup. No pagination (the backend never paginates this list -
 * a tenant's role count is small by design) and no "New Role" action - role
 * creation isn't supported by this read-only module (see
 * app/modules/roles/router.py's docstring).
 */
export function RoleListPage() {
  const router = useRouter();
  const { hasPermission } = usePermissions();
  const [search, setSearch] = useState("");

  const rolesQuery = useRoles();
  const apiError = rolesQuery.isError ? normalizeApiError(rolesQuery.error) : null;

  const allRoles = rolesQuery.data ?? [];
  const trimmedSearch = search.trim().toLowerCase();
  const roles = trimmedSearch
    ? allRoles.filter((role) => role.name.toLowerCase().includes(trimmedSearch))
    : allRoles;

  const isGenuinelyEmpty = !rolesQuery.isLoading && !apiError && allRoles.length === 0;
  const isNoResults = !rolesQuery.isLoading && !apiError && allRoles.length > 0 && roles.length === 0;

  // Every hook above must run unconditionally on every render - this check
  // comes after all of them, not before, so it can safely early-return.
  const columns = useMemo(() => getRoleColumns(), []);
  const table = useDataTable({
    data: roles,
    columns,
    manualSorting: false,
    manualPagination: false,
  });

  if (!hasPermission(USER_MANAGE_PERMISSION)) {
    return (
      <ErrorState
        title="You don't have permission to view roles"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  return (
    <ListPageTemplate
      title="Roles & Permissions"
      description="What each role in your organization can do, and who holds it."
      icon={KeyRound}
      isLoading={rolesQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load roles",
              description: apiError.message,
              onRetry: () => rolesQuery.refetch(),
            }
          : null
      }
      isEmpty={isGenuinelyEmpty}
      emptyState={<DataTableEmpty title="No roles yet" description="Roles for your organization will appear here." />}
    >
      <DataTable
        table={table}
        toolbar={
          <DataTableToolbar
            search={
              <SearchBar
                defaultValue={search}
                onSearch={setSearch}
                placeholder="Search roles…"
                aria-label="Search roles"
                className="min-w-56 flex-1"
              />
            }
          />
        }
        isLoading={rolesQuery.isLoading}
        isNoResults={isNoResults}
        noResultsState={
          <DataTableNoResults
            description={`No roles match "${search.trim()}".`}
            onClearFilters={() => setSearch("")}
          />
        }
        onRowClick={(role) => router.push(`/roles/${role.id}`)}
        aria-label="Roles"
      />
    </ListPageTemplate>
  );
}
