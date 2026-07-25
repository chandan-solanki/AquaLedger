import { toast as sonnerToast } from "sonner";

type ToastOptions = Parameters<typeof sonnerToast.success>[1];

/**
 * A thin, standardized wrapper over Sonner (`providers/toast-provider.tsx`
 * mounts the one `<Toaster>` these render into) so every call site in the
 * app reaches for one of these five verbs instead of calling `sonner`
 * directly with ad hoc styling — the Toast category default in
 * `06_COMPONENT_LIBRARY.md` §7.
 */
export function toastSuccess(message: string, options?: ToastOptions) {
  return sonnerToast.success(message, options);
}

export function toastError(message: string, options?: ToastOptions) {
  return sonnerToast.error(message, options);
}

export function toastWarning(message: string, options?: ToastOptions) {
  return sonnerToast.warning(message, options);
}

export function toastInfo(message: string, options?: ToastOptions) {
  return sonnerToast.info(message, options);
}

/** Returns a toast id — pass it to `dismissToast()` or update it via `sonner`'s own `toast.loading` id-reuse pattern once the async work resolves. */
export function toastLoading(message: string, options?: ToastOptions) {
  return sonnerToast.loading(message, options);
}

export function dismissToast(id: string | number) {
  sonnerToast.dismiss(id);
}

/** Wires a promise straight to a loading → success/error toast sequence, for the common "fire an async action, show its outcome" case. */
export function toastPromise<T>(
  promise: Promise<T>,
  messages: { loading: string; success: string | ((data: T) => string); error: string | ((error: unknown) => string) }
) {
  return sonnerToast.promise(promise, messages);
}
