export type ConfirmDialogOptions = { title?: string; message: string; confirmText?: string; cancelText?: string; danger?: boolean };

export function confirmDialog(options: ConfirmDialogOptions | string): Promise<boolean> {
  if (typeof window === "undefined") return Promise.resolve(false);
  const normalized = typeof options === "string" ? { message: options } : options;
  return new Promise((resolve) => {
    window.dispatchEvent(new CustomEvent("bonyan-confirm-dialog", { detail: { ...normalized, resolve } }));
  });
}
