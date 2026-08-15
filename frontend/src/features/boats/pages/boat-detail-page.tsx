"use client";

import { Pencil, Ship, Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { SectionHeader } from "@/components/layout/section-header";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { BoatProfitabilityTab } from "@/features/boats/components/boat-profitability-tab";
import { BOAT_STATUS_BADGE_VARIANT, BOAT_STATUS_LABELS, toBoatStatus } from "@/features/boats/constants/boat-status";
import { useBoat } from "@/features/boats/hooks/use-boat";
import { useDeleteBoat } from "@/features/boats/hooks/use-delete-boat";
import { normalizeApiError } from "@/utils/api-error";
import { formatDate, formatDateTime } from "@/utils/format-date";
import { formatQuantity } from "@/utils/format-number";

/**
 * Read-only Boat record view - no editing, no Activity/Audit/Attachments
 * (Sprint 5 Session 3's explicit scope), mirroring `CompanyDetailPage`/
 * `FishDetailPage`. Delete opens the shared `DeleteConfirmationDialog`; the
 * actual mutation, its toast, and the post-delete navigation all live in
 * `useDeleteBoat` so this page and the List page's row action share
 * identical behavior.
 *
 * No company lookup - a boat is owned by the tenant only. A `Company` is a
 * customer (buyer), never a boat owner (ARCHITECTURE.md's Business Model).
 */
export function BoatDetailPage() {
  const params = useParams<{ id: string }>();
  const boatId = params.id;
  const { hasPermission } = usePermissions();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const boatQuery = useBoat(boatId);
  const deleteBoat = useDeleteBoat();

  if (!hasPermission("boat:view")) {
    return (
      <ErrorState
        title="You don't have permission to view boats"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const boat = boatQuery.data;
  const apiError = boatQuery.isError ? normalizeApiError(boatQuery.error) : null;
  const status = boat ? toBoatStatus(boat.isActive) : null;

  return (
    <DetailPageTemplate
      title={boat?.name ?? "Boat"}
      description={boat?.code}
      icon={Ship}
      badge={status && <Badge variant={BOAT_STATUS_BADGE_VARIANT[status]}>{BOAT_STATUS_LABELS[status]}</Badge>}
      primaryAction={
        boat && hasPermission("boat:edit")
          ? { label: "Edit", icon: Pencil, href: `/boats/${boat.id}/edit` }
          : undefined
      }
      secondaryActions={
        boat && hasPermission("boat:delete")
          ? [{ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }]
          : undefined
      }
      isLoading={boatQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load boat record",
              description: apiError.message,
              onRetry: () => boatQuery.refetch(),
            }
          : null
      }
    >
      {boat && (
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            {hasPermission("reports:view") && (
              <TabsTrigger value="profitability">Profitability</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview">
            <div className="space-y-6">
              <SectionHeader title="Boat Information" />

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <InfoCard title="Details">
                  <DescriptionList
                    items={[
                      { term: "Boat Name", details: boat.name },
                      { term: "Boat Code", details: boat.code },
                      { term: "Registration Number", details: boat.registrationNumber },
                      { term: "Boat Type", details: boat.boatType ?? "—" },
                      {
                        term: "Capacity",
                        details: boat.capacityKg ? `${formatQuantity(boat.capacityKg)} kg` : "—",
                      },
                      { term: "Status", details: status ? BOAT_STATUS_LABELS[status] : "—" },
                      { term: "Created At", details: formatDateTime(boat.createdAt) },
                      { term: "Updated At", details: formatDateTime(boat.updatedAt) },
                    ]}
                  />
                </InfoCard>

                <InfoCard title="Engine & Compliance">
                  <DescriptionList
                    items={[
                      { term: "Engine Number", details: boat.engineNumber ?? "—" },
                      { term: "Engine Power", details: boat.engineHp != null ? `${boat.engineHp} HP` : "—" },
                      { term: "Captain Name", details: boat.captainName ?? "—" },
                      { term: "Captain Phone", details: boat.captainPhone ?? "—" },
                      { term: "License Number", details: boat.licenseNumber ?? "—" },
                      {
                        term: "License Expiry",
                        details: boat.licenseExpiry ? formatDate(boat.licenseExpiry) : "—",
                      },
                      {
                        term: "Insurance Expiry",
                        details: boat.insuranceExpiry ? formatDate(boat.insuranceExpiry) : "—",
                      },
                    ]}
                  />
                </InfoCard>
              </div>

              <InfoCard title="Notes">
                {boat.notes ? (
                  <p className="text-sm whitespace-pre-wrap">{boat.notes}</p>
                ) : (
                  <EmptyState title="No notes added" description="Notes for this boat will appear here." />
                )}
              </InfoCard>
            </div>
          </TabsContent>

          {hasPermission("reports:view") && (
            <TabsContent value="profitability">
              <BoatProfitabilityTab boatId={boat.id} />
            </TabsContent>
          )}
        </Tabs>
      )}

      {boat && (
        <DeleteConfirmationDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
          entityName={boat.name}
          entityLabel="boat"
          isLoading={deleteBoat.isPending}
          onConfirm={() => deleteBoat.mutate(boat.id)}
        />
      )}
    </DetailPageTemplate>
  );
}
