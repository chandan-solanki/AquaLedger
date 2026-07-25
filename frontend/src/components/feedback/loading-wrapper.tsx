"use client";

import { Suspense, type ReactNode } from "react";

import { PageSkeleton } from "@/components/feedback/skeletons/page-skeleton";

interface LoadingWrapperProps {
  children: ReactNode;
  fallback?: ReactNode;
}

/**
 * A section-level Suspense boundary for content within an already-rendered
 * page — distinct from route `loading.tsx` files, which cover whole-segment
 * navigation transitions. Defaults to the generic `PageSkeleton`; pass a
 * more specific skeleton (`TableSkeleton`, `CardSkeleton`, ...) as
 * `fallback` once a page has a part that loads independently of the rest.
 */
export function LoadingWrapper({ children, fallback }: LoadingWrapperProps) {
  return <Suspense fallback={fallback ?? <PageSkeleton />}>{children}</Suspense>;
}
