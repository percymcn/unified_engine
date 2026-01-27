/**
 * Fetch utilities with timeout and error handling
 * Provides resilient fetch operations for BFF routes
 */

export const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * Fetch with timeout to prevent hanging requests
 * @param url - URL to fetch
 * @param options - Fetch options
 * @param timeout - Timeout in milliseconds (default: 30s)
 * @returns Response or throws error
 */
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout = DEFAULT_TIMEOUT
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

/**
 * Check if an error is a timeout error
 */
export function isTimeoutError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError';
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(error: unknown, defaultMessage: string): string {
  if (isTimeoutError(error)) {
    return 'Request timed out. The server is taking too long to respond.';
  }
  if (error instanceof Error) {
    return error.message || defaultMessage;
  }
  return defaultMessage;
}
