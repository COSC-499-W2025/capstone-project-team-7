import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export default function EncryptionHelpPage() {
  return (
    <div className="p-8 space-y-6">
      <div>
        <Link href="/settings" className="text-sm text-gray-600 hover:text-gray-900 mb-2 inline-block">
          ← Back to Settings
        </Link>
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Encryption Setup</h1>
        <p className="text-gray-600 mt-2">Configure backend encryption to secure stored data.</p>
      </div>

      <Card className="bg-white rounded-xl shadow-sm border border-gray-200">
        <CardHeader className="border-b border-gray-200">
          <CardTitle className="text-xl font-bold text-gray-900">Required Environment Variable</CardTitle>
          <CardDescription className="text-gray-600">
            The backend uses AES-GCM and requires a 32-byte base64-encoded key.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-gray-700">
              Set the `ENCRYPTION_MASTER_KEY` environment variable for the backend process and restart the server.
            </p>
            <pre className="bg-gray-900 text-gray-100 text-xs rounded-lg p-4 overflow-x-auto">
              <code>openssl rand -base64 32</code>
            </pre>
            <p className="text-xs text-gray-500">
              Store the generated value in your backend `.env` file or deployment secrets.
            </p>
          </div>

          <div className="space-y-2">
            <p className="text-sm text-gray-700">Common causes of misconfiguration:</p>
            <ul className="text-xs text-gray-600 list-disc pl-5 space-y-1">
              <li>Missing `ENCRYPTION_MASTER_KEY` in the backend environment.</li>
              <li>Key is not base64 encoded or not 32 bytes after decoding.</li>
              <li>The backend was not restarted after updating environment variables.</li>
            </ul>
          </div>

          <div>
            <Link href="/settings">
              <Button variant="outline" className="border-gray-300 text-gray-900 hover:bg-gray-50">
                Return to Settings
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
