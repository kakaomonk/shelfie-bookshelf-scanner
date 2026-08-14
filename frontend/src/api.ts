import { LibraryEntry, ScanResponse } from './types';

// Points at the Django dev server. Not baked in, because a phone/simulator can't reach
// "localhost" on the dev machine -- see README setup steps for finding your LAN IP.
const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {}

async function fetchWithTimeout(url: string, options: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      throw new ApiError('The server took too long to respond. Please try again.');
    }
    throw new ApiError('Could not reach the server. Is the backend running and is EXPO_PUBLIC_API_URL correct?');
  } finally {
    clearTimeout(timer);
  }
}

async function parseJsonOrThrow(response: Response) {
  const text = await response.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError(`The server sent back something unreadable (status ${response.status}).`);
  }
  if (!response.ok) {
    throw new ApiError(data?.error ?? `Request failed (status ${response.status}).`);
  }
  return data;
}

export async function scanPhoto(uri: string): Promise<ScanResponse> {
  const formData = new FormData();
  // React Native's fetch/FormData accepts this shape for file uploads even though it doesn't
  // match the DOM File type -- hence the `as any`.
  formData.append('photo', { uri, name: 'shelf.jpg', type: 'image/jpeg' } as any);

  const response = await fetchWithTimeout(
    `${API_URL}/api/scan/`,
    { method: 'POST', body: formData, headers: { Accept: 'application/json' } },
    60_000,
  );
  return parseJsonOrThrow(response);
}

export async function confirmBook(payload: {
  title: string;
  author: string;
  catalog_id?: number | null;
  match_confidence?: number | null;
}): Promise<LibraryEntry> {
  const response = await fetchWithTimeout(
    `${API_URL}/api/library/`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    15_000,
  );
  return parseJsonOrThrow(response);
}

export async function fetchLibrary(): Promise<LibraryEntry[]> {
  const response = await fetchWithTimeout(`${API_URL}/api/library/`, {}, 15_000);
  return parseJsonOrThrow(response);
}

export async function deleteLibraryEntry(id: number): Promise<void> {
  const response = await fetchWithTimeout(`${API_URL}/api/library/${id}/`, { method: 'DELETE' }, 15_000);
  if (!response.ok && response.status !== 204) {
    throw new ApiError(`Could not remove that entry (status ${response.status}).`);
  }
}

export function resolveMediaUrl(path: string | null): string | null {
  if (!path) return null;
  return path.startsWith('http') ? path : `${API_URL}${path}`;
}
