"use client";

import { toast as sonnerToast, Toaster as SonnerToaster } from "sonner";

type ToastOptions = {
  id?: string;
  duration?: number;
};

type ToastApi = {
  error: (message: string, options?: ToastOptions) => void;
  success: (message: string, options?: ToastOptions) => void;
  info: (message: string, options?: ToastOptions) => void;
};

export const toast: ToastApi = {
  error: (message: string, options?: ToastOptions) => {
    sonnerToast.error(message, options);
  },
  success: (message: string, options?: ToastOptions) => {
    sonnerToast.success(message, options);
  },
  info: (message: string, options?: ToastOptions) => {
    sonnerToast.info(message, options);
  },
};

export { SonnerToaster as Toaster };
