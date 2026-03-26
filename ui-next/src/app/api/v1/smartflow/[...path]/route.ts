import { NextRequest, NextResponse } from 'next/server';
import { getTokenFromCookies } from '@/lib/auth';

const BACKEND_URL = process.env.BACKEND_URL || 'http://api:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return forwardRequest(request, params.path, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return forwardRequest(request, params.path, 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return forwardRequest(request, params.path, 'PUT');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return forwardRequest(request, params.path, 'DELETE');
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return forwardRequest(request, params.path, 'PATCH');
}

async function forwardRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
) {
  try {
    // Get auth token from httpOnly cookie
    const token = await getTokenFromCookies();

    if (!token) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }

    // Build the target URL
    const path = pathSegments.join('/');
    const url = `${BACKEND_URL}/api/v1/smartflow/${path}`;
    const searchParams = request.nextUrl.searchParams.toString();
    const targetUrl = searchParams ? `${url}?${searchParams}` : url;

    // Forward headers
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };

    // Get request body if present
    let body: string | undefined;
    if (method !== 'GET' && method !== 'DELETE') {
      try {
        body = await request.text();
      } catch (error) {
        // No body or body already consumed
      }
    }

    // Forward the request to the backend
    const response = await fetch(targetUrl, {
      method,
      headers,
      body,
    });

    // Get response data
    const data = await response.json();

    // Return the response
    return NextResponse.json(data, {
      status: response.status,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    console.error('SmartFlow API proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
