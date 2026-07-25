import { PageSkeleton } from "@/components/feedback/skeletons/page-skeleton";
import { PageContainer } from "@/components/layout/page-container";

/**
 * The authenticated segment's loading boundary. Next.js wraps only
 * `(authenticated)/layout.tsx`'s `{children}` slot in Suspense with this
 * fallback — the Sidebar/Header shell (rendered by the layout itself)
 * stays mounted and visible, so only the content area shows a skeleton
 * while a page resolves. Generic "list" shape by default; an individual
 * route (e.g. a future `/companies/[id]/loading.tsx`) overrides this with
 * the `PageSkeleton` variant matching its own page type.
 */
export default function AuthenticatedLoading() {
  return (
    <PageContainer>
      <PageSkeleton variant="list" />
    </PageContainer>
  );
}
