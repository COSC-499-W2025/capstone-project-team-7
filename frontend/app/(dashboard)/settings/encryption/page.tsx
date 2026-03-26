import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function EncryptionHelpPage() {
  return (
    <div className="p-8 space-y-6 min-h-screen">
      <div>
        <Link href="/settings" className="text-sm text-muted-foreground hover:text-foreground mb-2 inline-block">
          &larr; Back to Settings
        </Link>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Encryption Setup</h1>
        <p className="text-muted-foreground mt-2">Configure backend encryption to secure stored data.</p>
      </div>

      <Card>
        <CardHeader className="border-b-2 border-border">
          <CardTitle>Required Environment Variable</CardTitle>
          <CardDescription>
            The backend uses AES-GCM and requires a 32-byte base64-encoded key.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-foreground">
              Set the `ENCRYPTION_MASTER_KEY` environment variable for the backend process and restart the server.
            </p>
            <pre className="bg-primary text-primary-foreground text-xs rounded-md p-4 overflow-x-auto">
              <code>openssl rand -base64 32</code>
            </pre>
            <p className="text-xs text-muted-foreground">
              Store the generated value in your backend `.env` file or deployment secrets.
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-sm text-foreground">Common causes of misconfiguration:</p>
            <ul className="text-xs text-muted-foreground list-disc pl-5 space-y-1">
              <li>Missing `ENCRYPTION_MASTER_KEY` in the backend environment.</li>
              <li>Key is not base64 encoded or not 32 bytes after decoding.</li>
              <li>The backend was not restarted after updating environment variables.</li>
            </ul>
          </div>

          <div>
            <Link href="/settings">
              <Button variant="outline">
                Return to Settings
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
