"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

const MAX_AUTO_PROGRESS = 90;
const AUTO_TICK_MS = 120;
const AUTO_TICK_STEP = 0.3;
const COMPLETE_HOLD_MS = 100;
const TRANSITION_MS = 150;

/**
 * A thin top-of-viewport progress bar shown for genuine route changes —
 * Create/Edit/Detail pages, "New X"/row-click navigation, Back/Forward, and
 * switching between modules (Dashboard/Companies/Fish/...) — across the
 * whole app, mounted once here rather than each page wiring its own
 * indicator.
 *
 * **Why this doesn't patch `history.pushState`** (an earlier version of
 * this component did, and it was unreliable): Next's own `HistoryUpdater`
 * (`next/dist/client/components/app-router.js`) only calls
 * `history.pushState`/`replaceState` *after* the destination route's data
 * has already arrived and the router's internal state has already updated
 * — it's how the address bar reflects a finished navigation, not how one
 * starts. By the time it fires, `usePathname()`/`useSearchParams()` may
 * already reflect the new route in the very same commit, so there's no
 * reliable gap left to show a bar in. (It's also called from inside a
 * `useInsertionEffect`, where React forbids scheduling updates at all —
 * "useInsertionEffect must not schedule updates".)
 *
 * **What actually signals a navigation *starting*:** `useRouter()` returns
 * one stable, module-level singleton object (Next's `publicAppRouterInstance`)
 * — every component's `useRouter()` call gets the exact same object, and
 * `next/link`'s click handler calls `.push()`/`.replace()` on it internally
 * too. Patching `.push`/`.replace` on that one shared instance here is
 * therefore visible to every `<Link>` click and every `router.push()` call
 * anywhere in the app, and fires synchronously the instant navigation is
 * requested — before Next's async fetch/transition machinery even begins.
 * Browser Back/Forward doesn't go through this object at all, so `popstate`
 * (which only ever fires for real history traversal, never for a same-page
 * `pushState` like nuqs's filter/sort/page URL updates) covers that case
 * separately.
 *
 * Completion is still simply "the route Next resolved to actually changed":
 * `usePathname()`/`useSearchParams()` updating is what snaps the bar to
 * 100% and fades it out.
 */
export function RouteProgressBar() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    function begin() {
      if (tickRef.current) clearInterval(tickRef.current);
      setVisible(true);
      setProgress(15);
      tickRef.current = setInterval(() => {
        setProgress((current) =>
          current >= MAX_AUTO_PROGRESS ? current : current + (MAX_AUTO_PROGRESS - current) * AUTO_TICK_STEP
        );
      }, AUTO_TICK_MS);
    }

    const originalPush = router.push.bind(router);
    const originalReplace = router.replace.bind(router);

    router.push = (href, options) => {
      begin();
      originalPush(href, options);
    };
    router.replace = (href, options) => {
      begin();
      originalReplace(href, options);
    };

    window.addEventListener("popstate", begin);

    return () => {
      router.push = originalPush;
      router.replace = originalReplace;
      window.removeEventListener("popstate", begin);
      if (tickRef.current) clearInterval(tickRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Runs whenever the resolved route actually changes - the completion
  // signal for whatever navigation was in flight.
  useEffect(() => {
    if (tickRef.current) {
      clearInterval(tickRef.current);
      tickRef.current = null;
    }
    if (!visible) return;
    setProgress(100);
    const timeout = setTimeout(() => {
      setVisible(false);
      setProgress(0);
    }, COMPLETE_HOLD_MS);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, searchParams]);

  if (!visible) return null;

  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-50" aria-hidden>
      <div
        className="h-0.75 bg-primary transition-[width,opacity] ease-out motion-reduce:transition-none"
        style={{ width: `${progress}%`, opacity: progress >= 100 ? 0 : 1, transitionDuration: `${TRANSITION_MS}ms` }}
      />
    </div>
  );
}
