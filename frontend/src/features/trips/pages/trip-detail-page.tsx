"use client";

import { Pencil, Plus, Route, Trash2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { DescriptionList } from "@/components/data-display/description-list";
import { InfoCard } from "@/components/data-display/info-card";
import { DeleteConfirmationDialog } from "@/components/feedback/dialogs/delete-confirmation-dialog";
import { EmptyState } from "@/components/feedback/empty-state";
import { ErrorState } from "@/components/feedback/error-state";
import { ContentSection } from "@/components/layout/content-section";
import { DetailPageTemplate } from "@/components/templates/detail-page-template";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useBoat } from "@/features/boats";
import { usePermissions } from "@/features/auth/hooks/use-permissions";
import { TripCatchTable } from "@/features/trips/components/trip-catch-table";
import { TripExpenseTable } from "@/features/trips/components/trip-expense-table";
import { TRIP_STATUS_BADGE_VARIANT, TRIP_STATUS_LABELS } from "@/features/trips/constants/trip-status";
import { TRIP_TYPE_LABELS } from "@/features/trips/constants/trip-type";
import { useDeleteTrip } from "@/features/trips/hooks/use-delete-trip";
import { useTrip } from "@/features/trips/hooks/use-trip";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";

/**
 * Read-only Trip record view - no Timeline/Attachments/Audit/Depart-Return/
 * Profitability/Invoice generation (out of scope through Sprint 6),
 * mirroring `BoatDetailPage`. Delete opens the shared
 * `DeleteConfirmationDialog`; the actual mutation, its toast, and the
 * post-delete navigation all live in `useDeleteTrip` so this page and the
 * List page's row action share identical behavior.
 *
 * `TripResponse` carries only `boat_id` (app/modules/trips/schemas.py), so
 * the Boat's display name is resolved via the Boats feature's own public
 * `useBoat` hook (`@/features/boats`), not invented/joined here.
 *
 * The Catch/Expenses sections (`TripCatchTable`/`TripExpenseTable`) are each
 * gated on their own `trip_catch:view`/`trip_expense:view` permission,
 * distinct from `trip:view` - a role could see a trip's own record without
 * seeing its catch or expense detail. Each section's "Add Catch"/
 * "Add Expense" button (gated on `trip_catch:create`/`trip_expense:create`)
 * links to `/trips/{id}/catches/new` / `/trips/{id}/expenses/new` - the
 * trip id always comes from this page's own route param, never a field the
 * user fills in (Sprint 6 Session 6's Navigation rule). Row-level Create/
 * Edit/Delete for both tables live in `TripCatchTable`/`TripExpenseTable`
 * themselves.
 */
export function TripDetailPage() {
  const params = useParams<{ id: string }>();
  const tripId = params.id;
  const { hasPermission } = usePermissions();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const tripQuery = useTrip(tripId);
  const deleteTrip = useDeleteTrip();
  // Called unconditionally (before the permission early-return below) per
  // the Rules of Hooks - depends on `tripQuery.data` rather than the `trip`
  // const derived after the guard.
  const boatQuery = useBoat(tripQuery.data?.boatId);

  if (!hasPermission("trip:view")) {
    return (
      <ErrorState
        title="You don't have permission to view trips"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const trip = tripQuery.data;
  const apiError = tripQuery.isError ? normalizeApiError(tripQuery.error) : null;

  return (
    <DetailPageTemplate
      title={trip?.tripNumber ?? "Trip"}
      description={boatQuery.data?.name}
      icon={Route}
      badge={
        trip && <Badge variant={TRIP_STATUS_BADGE_VARIANT[trip.status]}>{TRIP_STATUS_LABELS[trip.status]}</Badge>
      }
      primaryAction={
        trip && hasPermission("trip:edit")
          ? { label: "Edit", icon: Pencil, href: `/trips/${trip.id}/edit` }
          : undefined
      }
      secondaryActions={
        trip && hasPermission("trip:delete")
          ? [{ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }]
          : undefined
      }
      isLoading={tripQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load trip record",
              description: apiError.message,
              onRetry: () => tripQuery.refetch(),
            }
          : null
      }
    >
      {trip && (
        <div className="space-y-6">
          <ContentSection title="Trip Information">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <InfoCard title="Details">
                <DescriptionList
                  items={[
                    { term: "Trip Number", details: trip.tripNumber },
                    { term: "Boat", details: boatQuery.data?.name ?? "—" },
                    { term: "Trip Type", details: TRIP_TYPE_LABELS[trip.tripType] },
                    { term: "Status", details: TRIP_STATUS_LABELS[trip.status] },
                    { term: "Captain Name", details: trip.captainName ?? "—" },
                    { term: "Created At", details: formatDateTime(trip.createdAt) },
                    { term: "Updated At", details: formatDateTime(trip.updatedAt) },
                  ]}
                />
              </InfoCard>

              <InfoCard title="Schedule">
                <DescriptionList
                  items={[
                    { term: "Departure", details: formatDateTime(trip.departureDatetime) },
                    {
                      term: "Expected Return",
                      details: trip.expectedReturnDatetime ? formatDateTime(trip.expectedReturnDatetime) : "—",
                    },
                    {
                      term: "Actual Return",
                      details: trip.actualReturnDatetime ? formatDateTime(trip.actualReturnDatetime) : "—",
                    },
                    { term: "Departure Port", details: trip.departurePort ?? "—" },
                    { term: "Arrival Port", details: trip.arrivalPort ?? "—" },
                  ]}
                />
              </InfoCard>
            </div>
          </ContentSection>

          <InfoCard title="Notes">
            {trip.notes ? (
              <p className="text-sm whitespace-pre-wrap">{trip.notes}</p>
            ) : (
              <EmptyState title="No notes added" description="Notes for this trip will appear here." />
            )}
          </InfoCard>

          {hasPermission("trip_catch:view") && (
            <ContentSection
              title="Trip Catch"
              actions={
                hasPermission("trip_catch:create") ? (
                  <Button asChild size="sm">
                    <Link href={`/trips/${trip.id}/catches/new`}>
                      <Plus aria-hidden />
                      Add Catch
                    </Link>
                  </Button>
                ) : undefined
              }
            >
              <TripCatchTable tripId={trip.id} />
            </ContentSection>
          )}

          {hasPermission("trip_expense:view") && (
            <ContentSection
              title="Trip Expenses"
              actions={
                hasPermission("trip_expense:create") ? (
                  <Button asChild size="sm">
                    <Link href={`/trips/${trip.id}/expenses/new`}>
                      <Plus aria-hidden />
                      Add Expense
                    </Link>
                  </Button>
                ) : undefined
              }
            >
              <TripExpenseTable tripId={trip.id} />
            </ContentSection>
          )}
        </div>
      )}

      {trip && (
        <DeleteConfirmationDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
          entityName={trip.tripNumber}
          entityLabel="trip"
          isLoading={deleteTrip.isPending}
          onConfirm={() => deleteTrip.mutate(trip.id)}
        />
      )}
    </DetailPageTemplate>
  );
}
