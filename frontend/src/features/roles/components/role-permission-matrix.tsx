"use client";

import { Checkbox } from "@/components/ui/checkbox";
import type { PermissionSummary } from "@/features/roles/types/role";

/**
 * Title-cases a `resource` value (e.g. `purchase_order` -> `Purchase Order`)
 * without pluralizing - several resources are already irregular (`fish`,
 * `settings`, `audit_log`) and a naive `+s` would misrender them. This is a
 * deliberately plain transform of the backend's own naming
 * (Permission.resource, app/modules/auth/models.py), not an invented
 * category - per this session's "group by existing module/resource naming"
 * scope.
 */
function humanizeResource(resource: string): string {
  return resource
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function groupByResource(permissions: PermissionSummary[]): Map<string, PermissionSummary[]> {
  const groups = new Map<string, PermissionSummary[]>();
  for (const permission of permissions) {
    const group = groups.get(permission.resource);
    if (group) {
      group.push(permission);
    } else {
      groups.set(permission.resource, [permission]);
    }
  }
  return groups;
}

export interface RolePermissionMatrixProps {
  /** The full, global permission catalog - every module/resource is shown, whether or not this role holds anything in it. */
  allPermissions: PermissionSummary[];
  /** The codes this specific role currently grants. */
  assignedCodes: ReadonlySet<string>;
}

/**
 * A read-only, grouped-by-resource permission checklist - per this
 * session's Phase 4/backend design, there is no assignment mutation
 * endpoint yet (app/modules/roles/router.py's module docstring explains
 * why), so every checkbox here is permanently disabled. It exists to make
 * a role's exact grants legible at a glance, which is also the
 * prerequisite for building an edit flow safely later.
 */
export function RolePermissionMatrix({ allPermissions, assignedCodes }: RolePermissionMatrixProps) {
  const groups = groupByResource(allPermissions);
  const resources = [...groups.keys()].sort();

  return (
    <div className="space-y-6">
      {resources.map((resource) => (
        <div key={resource} className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">{humanizeResource(resource)}</h3>
          <div className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
            {groups.get(resource)?.map((permission) => {
              const isAssigned = assignedCodes.has(permission.code);
              return (
                <div key={permission.id} className="flex items-start gap-2">
                  <Checkbox checked={isAssigned} disabled aria-label={permission.code} className="mt-0.5" />
                  <div className="min-w-0">
                    <p className={isAssigned ? "text-sm font-medium text-foreground" : "text-sm text-muted-foreground"}>
                      {permission.code}
                    </p>
                    {permission.description && (
                      <p className="text-xs text-muted-foreground">{permission.description}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
