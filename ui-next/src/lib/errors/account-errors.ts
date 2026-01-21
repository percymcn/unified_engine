/**
 * Account-related error handling utilities
 *
 * Maps technical errors to user-friendly messages with suggested actions.
 */

export interface UserFriendlyError {
  title: string;
  message: string;
  suggestion?: string;
  isRetryable: boolean;
}

/**
 * Error types for categorization
 */
export type AccountErrorType =
  | 'auth'          // Authentication/authorization errors
  | 'network'       // Network connectivity issues
  | 'broker'        // Broker-specific errors
  | 'validation'    // Input validation errors
  | 'rate_limit'    // Too many requests
  | 'server'        // Server-side errors
  | 'unknown';      // Unexpected errors

/**
 * Parse error from API response and return user-friendly error
 */
export function parseAccountError(
  error: unknown,
  context: 'create' | 'update' | 'delete' | 'sync' | 'fetch' | 'test'
): UserFriendlyError {
  // Handle Error objects
  if (error instanceof Error) {
    return mapErrorMessage(error.message, context);
  }

  // Handle API response errors
  if (typeof error === 'object' && error !== null) {
    const errorObj = error as Record<string, unknown>;

    // Check for detail field (FastAPI style)
    if (typeof errorObj.detail === 'string') {
      return mapErrorMessage(errorObj.detail, context);
    }

    // Check for error field
    if (typeof errorObj.error === 'string') {
      return mapErrorMessage(errorObj.error, context);
    }

    // Check for message field
    if (typeof errorObj.message === 'string') {
      return mapErrorMessage(errorObj.message, context);
    }
  }

  // Handle string errors
  if (typeof error === 'string') {
    return mapErrorMessage(error, context);
  }

  // Fallback for unknown error types
  return getGenericError(context);
}

/**
 * Map error message to user-friendly error based on patterns
 */
function mapErrorMessage(
  message: string,
  context: 'create' | 'update' | 'delete' | 'sync' | 'fetch' | 'test'
): UserFriendlyError {
  const lowerMessage = message.toLowerCase();

  // Authentication errors
  if (
    lowerMessage.includes('unauthorized') ||
    lowerMessage.includes('401') ||
    lowerMessage.includes('invalid api key') ||
    lowerMessage.includes('invalid credentials') ||
    lowerMessage.includes('authentication failed')
  ) {
    return {
      title: 'Authentication Failed',
      message: 'Your API credentials are invalid or have expired.',
      suggestion: 'Check your API key and secret, or generate new credentials from your broker dashboard.',
      isRetryable: false,
    };
  }

  // Authorization/permission errors
  if (
    lowerMessage.includes('forbidden') ||
    lowerMessage.includes('403') ||
    lowerMessage.includes('access denied') ||
    lowerMessage.includes('permission')
  ) {
    return {
      title: 'Access Denied',
      message: 'Your account does not have permission for this operation.',
      suggestion: 'Ensure API access is enabled on your broker account and your plan includes API access.',
      isRetryable: false,
    };
  }

  // Network/connectivity errors
  if (
    lowerMessage.includes('network') ||
    lowerMessage.includes('fetch') ||
    lowerMessage.includes('econnrefused') ||
    lowerMessage.includes('dns') ||
    lowerMessage.includes('socket')
  ) {
    return {
      title: 'Connection Error',
      message: 'Unable to reach the broker server.',
      suggestion: 'Check your internet connection and try again.',
      isRetryable: true,
    };
  }

  // Timeout errors
  if (
    lowerMessage.includes('timeout') ||
    lowerMessage.includes('timed out') ||
    lowerMessage.includes('408')
  ) {
    return {
      title: 'Request Timeout',
      message: 'The broker server took too long to respond.',
      suggestion: 'The server may be busy. Please wait a moment and try again.',
      isRetryable: true,
    };
  }

  // Server not found
  if (
    lowerMessage.includes('not found') ||
    lowerMessage.includes('404') ||
    lowerMessage.includes('server')
  ) {
    if (context === 'sync' || context === 'test') {
      return {
        title: 'Server Not Found',
        message: 'The broker server address could not be found.',
        suggestion: 'Verify the server address is correct.',
        isRetryable: false,
      };
    }
  }

  // Rate limiting
  if (
    lowerMessage.includes('rate limit') ||
    lowerMessage.includes('too many requests') ||
    lowerMessage.includes('429')
  ) {
    return {
      title: 'Rate Limited',
      message: 'Too many requests. The broker has temporarily limited access.',
      suggestion: 'Wait a few minutes before trying again.',
      isRetryable: true,
    };
  }

  // Broker slot limit (billing)
  if (
    lowerMessage.includes('broker slot') ||
    lowerMessage.includes('broker limit') ||
    lowerMessage.includes('upgrade')
  ) {
    return {
      title: 'Broker Limit Reached',
      message: 'You have reached the maximum number of broker connections for your plan.',
      suggestion: 'Upgrade to Pro for unlimited broker connections.',
      isRetryable: false,
    };
  }

  // Duplicate account
  if (
    lowerMessage.includes('duplicate') ||
    lowerMessage.includes('already exists') ||
    lowerMessage.includes('unique')
  ) {
    return {
      title: 'Account Already Exists',
      message: 'An account with this ID is already connected.',
      suggestion: 'Use a different account ID or edit the existing account.',
      isRetryable: false,
    };
  }

  // Validation errors
  if (
    lowerMessage.includes('invalid') ||
    lowerMessage.includes('validation') ||
    lowerMessage.includes('required')
  ) {
    return {
      title: 'Invalid Input',
      message: message,
      suggestion: 'Please check your input and try again.',
      isRetryable: false,
    };
  }

  // Server errors
  if (
    lowerMessage.includes('500') ||
    lowerMessage.includes('502') ||
    lowerMessage.includes('503') ||
    lowerMessage.includes('internal server') ||
    lowerMessage.includes('service unavailable')
  ) {
    return {
      title: 'Service Temporarily Unavailable',
      message: 'The broker service is experiencing issues.',
      suggestion: 'Please try again in a few minutes.',
      isRetryable: true,
    };
  }

  // Broker offline
  if (
    lowerMessage.includes('offline') ||
    lowerMessage.includes('unavailable') ||
    lowerMessage.includes('maintenance')
  ) {
    return {
      title: 'Broker Unavailable',
      message: 'The broker API is currently offline or under maintenance.',
      suggestion: 'Check the broker status page and try again later.',
      isRetryable: true,
    };
  }

  // If we can't match, return a context-specific generic error
  return getGenericError(context);
}

/**
 * Get generic error for context when specific error is unknown
 */
function getGenericError(
  context: 'create' | 'update' | 'delete' | 'sync' | 'fetch' | 'test'
): UserFriendlyError {
  switch (context) {
    case 'create':
      return {
        title: 'Failed to Create Account',
        message: 'Unable to connect your broker account.',
        suggestion: 'Verify your credentials and try again.',
        isRetryable: true,
      };
    case 'update':
      return {
        title: 'Failed to Update Account',
        message: 'Unable to save your changes.',
        suggestion: 'Try again or refresh the page.',
        isRetryable: true,
      };
    case 'delete':
      return {
        title: 'Failed to Delete Account',
        message: 'Unable to remove the account.',
        suggestion: 'Try again or refresh the page.',
        isRetryable: true,
      };
    case 'sync':
      return {
        title: 'Sync Failed',
        message: 'Unable to fetch account data from broker.',
        suggestion: 'Check your connection and try again.',
        isRetryable: true,
      };
    case 'fetch':
      return {
        title: 'Failed to Load Accounts',
        message: 'Unable to retrieve your account list.',
        suggestion: 'Check your connection and refresh the page.',
        isRetryable: true,
      };
    case 'test':
      return {
        title: 'Connection Test Failed',
        message: 'Unable to verify broker connection.',
        suggestion: 'Check your credentials and try again.',
        isRetryable: true,
      };
  }
}

/**
 * Format error for toast notification
 */
export function formatErrorForToast(error: UserFriendlyError): {
  title: string;
  description: string;
  variant: 'destructive';
} {
  const description = error.suggestion
    ? `${error.message} ${error.suggestion}`
    : error.message;

  return {
    title: error.title,
    description,
    variant: 'destructive',
  };
}
