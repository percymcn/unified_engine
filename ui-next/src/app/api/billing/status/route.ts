import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("token")?.value;

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const backendUrl = process.env.BACKEND_URL || "http://localhost:8765";

  try {
    const response = await fetch(`${backendUrl}/api/billing/status`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Billing status API error:", error);
    return NextResponse.json(
      { error: "Failed to fetch billing status" },
      { status: 500 }
    );
  }
}
