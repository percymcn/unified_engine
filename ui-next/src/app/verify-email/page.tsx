"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, XCircle, Loader2, Mail } from "lucide-react";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error" | "already_verified">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("No verification token provided");
      return;
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch("/api/auth/verify-email", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        const data = await response.json();

        if (response.ok) {
          if (data.already_verified) {
            setStatus("already_verified");
            setMessage("Your email has already been verified.");
          } else {
            setStatus("success");
            setMessage("Your email has been verified successfully!");
          }
        } else {
          setStatus("error");
          setMessage(data.error || "Verification failed. The link may have expired.");
        }
      } catch {
        setStatus("error");
        setMessage("Something went wrong. Please try again.");
      }
    };

    verifyEmail();
  }, [token]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/30 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4">
            {status === "loading" && (
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                <Loader2 className="h-8 w-8 text-primary animate-spin" />
              </div>
            )}
            {status === "success" && (
              <div className="h-16 w-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            )}
            {status === "already_verified" && (
              <div className="h-16 w-16 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                <Mail className="h-8 w-8 text-blue-600" />
              </div>
            )}
            {status === "error" && (
              <div className="h-16 w-16 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                <XCircle className="h-8 w-8 text-red-600" />
              </div>
            )}
          </div>
          <CardTitle>
            {status === "loading" && "Verifying Email..."}
            {status === "success" && "Email Verified!"}
            {status === "already_verified" && "Already Verified"}
            {status === "error" && "Verification Failed"}
          </CardTitle>
          <CardDescription>{message}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {(status === "success" || status === "already_verified") && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground text-center">
                You can now log in and start using Tradeflow.
              </p>
              <Button className="w-full" onClick={() => router.push("/login")}>
                Go to Login
              </Button>
            </div>
          )}
          {status === "error" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground text-center">
                The verification link may have expired. You can request a new one.
              </p>
              <Link href="/resend-verification">
                <Button variant="outline" className="w-full">
                  Resend Verification Email
                </Button>
              </Link>
              <Link href="/login">
                <Button variant="ghost" className="w-full">
                  Back to Login
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/30 p-4">
          <Card className="w-full max-w-md">
            <CardHeader className="text-center">
              <div className="mx-auto mb-4">
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <Loader2 className="h-8 w-8 text-primary animate-spin" />
                </div>
              </div>
              <CardTitle>Loading...</CardTitle>
            </CardHeader>
          </Card>
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
