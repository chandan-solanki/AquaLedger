"use client";

import { Fish as FishIcon, Pencil, Trash2 } from "lucide-react";
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
import { FishSalesAnalyticsTab } from "@/features/fish/components/fish-sales-analytics-tab";
import { FISH_STATUS_BADGE_VARIANT, FISH_STATUS_LABELS, toFishStatus } from "@/features/fish/constants/fish-status";
import { useDeleteFish } from "@/features/fish/hooks/use-delete-fish";
import { useFish } from "@/features/fish/hooks/use-fish";
import { FISH_UNIT_LABELS } from "@/features/fish/types/fish";
import { normalizeApiError } from "@/utils/api-error";
import { formatDateTime } from "@/utils/format-date";
import { formatRate } from "@/utils/format-number";

/**
 * Read-only Fish record view - no editing, no Activity/Audit/Attachments
 * (Sprint 4 Session 3's explicit scope), mirroring `CompanyDetailPage`
 * exactly. Delete opens the shared `DeleteConfirmationDialog`; the actual
 * mutation, its toast, and the post-delete navigation all live in
 * `useDeleteFish` so this page and the List page's row action share
 * identical behavior.
 *
 * The backend's fish permissions are a coarse `fish:view` / `fish:manage`
 * split (app/modules/fish/permissions.py), not separate edit/delete codes
 * like Companies - Edit and Delete are both gated on `fish:manage` here for
 * that reason.
 */
export function FishDetailPage() {
  const params = useParams<{ id: string }>();
  const fishId = params.id;
  const { hasPermission } = usePermissions();
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const fishQuery = useFish(fishId);
  const deleteFish = useDeleteFish();

  if (!hasPermission("fish:view")) {
    return (
      <ErrorState
        title="You don't have permission to view fish records"
        description="Contact an administrator if you believe this is a mistake."
      />
    );
  }

  const fish = fishQuery.data;
  const apiError = fishQuery.isError ? normalizeApiError(fishQuery.error) : null;
  const status = fish ? toFishStatus(fish.isActive) : null;

  return (
    <DetailPageTemplate
      title={fish?.name ?? "Fish"}
      description={fish?.code}
      icon={FishIcon}
      badge={status && <Badge variant={FISH_STATUS_BADGE_VARIANT[status]}>{FISH_STATUS_LABELS[status]}</Badge>}
      primaryAction={
        fish && hasPermission("fish:manage")
          ? { label: "Edit", icon: Pencil, href: `/fish/${fish.id}/edit` }
          : undefined
      }
      secondaryActions={
        fish && hasPermission("fish:manage")
          ? [{ label: "Delete", icon: Trash2, onClick: () => setIsDeleteDialogOpen(true) }]
          : undefined
      }
      isLoading={fishQuery.isLoading}
      error={
        apiError
          ? {
              title: "Failed to load fish record",
              description: apiError.message,
              onRetry: () => fishQuery.refetch(),
            }
          : null
      }
    >
      {fish && (
        <Tabs defaultValue="overview">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            {hasPermission("reports:view") && (
              <TabsTrigger value="sales-analytics">Sales Analytics</TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview">
            <div className="space-y-6">
              <SectionHeader title="Fish Information" />

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <InfoCard title="Details">
                  <DescriptionList
                    items={[
                      { term: "Fish Name", details: fish.name },
                      { term: "Fish Code", details: fish.code },
                      { term: "Local Name", details: fish.localName ?? "—" },
                      { term: "Scientific Name", details: fish.scientificName ?? "—" },
                      { term: "Category", details: fish.category ?? "—" },
                      { term: "Unit", details: FISH_UNIT_LABELS[fish.unit] },
                      { term: "Status", details: status ? FISH_STATUS_LABELS[status] : "—" },
                      { term: "Created At", details: formatDateTime(fish.createdAt) },
                      { term: "Updated At", details: formatDateTime(fish.updatedAt) },
                    ]}
                  />
                </InfoCard>

                <InfoCard title="Pricing & Tax">
                  <DescriptionList
                    items={[
                      { term: "HSN Code", details: fish.hsnCode ?? "—" },
                      {
                        term: "Default Purchase Rate",
                        details: fish.defaultPurchaseRate ? formatRate(fish.defaultPurchaseRate) : "—",
                      },
                      {
                        term: "Default Sale Rate",
                        details: fish.defaultSaleRate ? formatRate(fish.defaultSaleRate) : "—",
                      },
                    ]}
                  />
                </InfoCard>
              </div>

              <InfoCard title="Description">
                {fish.description ? (
                  <p className="text-sm whitespace-pre-wrap">{fish.description}</p>
                ) : (
                  <EmptyState
                    title="No description added"
                    description="A description for this fish will appear here."
                  />
                )}
              </InfoCard>
            </div>
          </TabsContent>

          {hasPermission("reports:view") && (
            <TabsContent value="sales-analytics">
              <FishSalesAnalyticsTab fishId={fish.id} />
            </TabsContent>
          )}
        </Tabs>
      )}

      {fish && (
        <DeleteConfirmationDialog
          open={isDeleteDialogOpen}
          onOpenChange={setIsDeleteDialogOpen}
          entityName={fish.name}
          entityLabel="fish record"
          isLoading={deleteFish.isPending}
          onConfirm={() => deleteFish.mutate(fish.id)}
        />
      )}
    </DetailPageTemplate>
  );
}
