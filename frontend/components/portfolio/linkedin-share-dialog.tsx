"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, ExternalLink, Linkedin, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getStoredToken } from "@/lib/auth";
import { generateLinkedInPost } from "@/lib/api/portfolio";
import type { LinkedInPostRequest } from "@/types/portfolio";

const LINKEDIN_CHAR_LIMIT = 3000;

interface LinkedInShareDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scope?: "portfolio" | "project";
  projectId?: string;
}

export function LinkedInShareDialog({
  open,
  onOpenChange,
  scope = "portfolio",
  projectId,
}: LinkedInShareDialogProps) {
  const [postText, setPostText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const generate = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setError("Not authenticated");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const body: LinkedInPostRequest = { scope };
      if (projectId) body.project_id = projectId;
      const res = await generateLinkedInPost(token, body);
      // Replace bare share token with full URL if present
      let text = res.post_text;
      if (res.share_url && !res.share_url.startsWith("http")) {
        const fullUrl = `${window.location.origin}/p?token=${res.share_url}`;
        text = text.replace(res.share_url, fullUrl);
      }
      setPostText(text);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate post");
    } finally {
      setLoading(false);
    }
  }, [scope, projectId]);

  // Generate when dialog opens
  useEffect(() => {
    if (open) {
      generate();
      setCopied(false);
    }
  }, [open, generate]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(postText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setError("Failed to copy to clipboard");
    }
  };

  const handleOpenLinkedIn = () => {
    window.open("https://www.linkedin.com/feed/", "_blank");
  };

  const charCount = postText.length;
  const overLimit = charCount > LINKEDIN_CHAR_LIMIT;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-base">
            <Linkedin size={18} className="text-[#0A66C2]" />
            Share on LinkedIn
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={20} className="animate-spin text-gray-400" />
          </div>
        )}

        {error && !loading && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && (
          <div className="space-y-4">
            <Textarea
              value={postText}
              onChange={(e) => setPostText(e.target.value)}
              rows={12}
              className="text-sm font-mono leading-relaxed"
              placeholder="Your LinkedIn post will appear here..."
            />

            <div className="flex items-center justify-between text-xs">
              <span className={overLimit ? "text-red-600 font-medium" : "text-gray-400"}>
                {charCount.toLocaleString()} / {LINKEDIN_CHAR_LIMIT.toLocaleString()} characters
              </span>
              <Button variant="ghost" size="sm" onClick={generate} className="text-xs h-7">
                Regenerate
              </Button>
            </div>

            <div className="flex items-center gap-3">
              <Button
                onClick={handleCopy}
                disabled={!postText}
                className="flex-1 bg-gray-900 text-white hover:bg-gray-800"
              >
                {copied ? (
                  <>
                    <Check size={14} className="mr-1.5 text-emerald-400" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy size={14} className="mr-1.5" />
                    Copy to Clipboard
                  </>
                )}
              </Button>
              <Button
                variant="outline"
                onClick={handleOpenLinkedIn}
                className="flex-1 border-[#0A66C2] text-[#0A66C2] hover:bg-[#0A66C2]/5"
              >
                <ExternalLink size={14} className="mr-1.5" />
                Open LinkedIn
              </Button>
            </div>

            <p className="text-[10px] text-gray-400 text-center leading-relaxed">
              Copy your post text, then paste it into the LinkedIn compose box.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
