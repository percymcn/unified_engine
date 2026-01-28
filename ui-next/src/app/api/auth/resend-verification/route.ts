import { NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8765";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email) {
      return NextResponse.json(
        { error: "Email is required" },
        { status: 400 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/v1/auth/resend-verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    const data = await response.json();

    // Always return success to not reveal if email exists
    return NextResponse.json(data);
  } catch (error) {
    console.error("Resend verification error:", error);
    return NextResponse.json(
      { message: "If the email exists, a verification link has been sent" },
      { status: 200 }
    );
  }
}
