import Link from "next/link";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">Reset password</CardTitle>
          <CardDescription className="text-center">
            Password reset is not available yet. Please contact your admin for access.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-center">
          <Link href="/auth/login" className="text-primary hover:underline text-sm">
            Back to login
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
