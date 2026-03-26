import { writable } from 'svelte/store';

export const currentUser = writable(null);
export const theme = writable('light');
export const toastMessage = writable(null);

export function showToast(message, type = 'success') {
  toastMessage.set({ message, type });
  setTimeout(() => toastMessage.set(null), 3500);
}
