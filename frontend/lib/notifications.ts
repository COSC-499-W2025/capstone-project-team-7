"use client";

type ToastOptions = {
  id?: string;
  duration?: number;
};

type ToastApi = {
  error: (message: string, options?: ToastOptions) => void;
};

export const toast: ToastApi = {
  error: (message: string, _options?: ToastOptions) => {
    if (process.env.NODE_ENV !== "test") {
      console.error(message);
    }
  },
};

export function Toaster(_props?: { position?: string }): null {
  return null;
}
