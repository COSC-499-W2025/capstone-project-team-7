"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Check,
  Copy,
  ExternalLink,
  Linkedin,
  Loader2,
  Send,
  Unplug,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getStoredToken } from "@/lib/auth";
import {
  generateLinkedInPost,
  getLinkedInStatus,
  getLinkedInAuthUrl,
  postToLinkedIn,
  disconnectLinkedIn,
} from "@/lib/api/portfolio";
import type {
  LinkedInPostRequest,
  LinkedInConnectionStatus,
} from "@/types/portfolio";

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

  // LinkedIn connection state
  const [connection, setConnection] = useState<LinkedInConnectionStatus | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);
  const [posting, setPosting] = useState(false);
  const [posted, setPosted] = useState(false);
  const [postError, setPostError] = useState<string | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);

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

  const checkStatus = useCallback(async () => {
    const token = getStoredToken();
    if (!token) return;
    setStatusLoading(true);
    try {
      const res = await getLinkedInStatus(token);
      setConnection(res);
    } catch {
      // LinkedIn not configured — leave connection null
      setConnection(null);
    } finally {
      setStatusLoading(false);
    }
  }, []);

  // Fetch post text + connection status on dialog open
  useEffect(() => {
    if (open) {
      generate();
      checkStatus();
      setCopied(false);
      setPosted(false);
      setPostError(null);
    }
  }, [open, generate, checkStatus]);

  // Poll for connection status after OAuth popup opens (works in Electron
  // where the system browser handles the callback and can't postMessage back).
  // Automatically stops after ~2 minutes to avoid running indefinitely.
  const POLL_TIMEOUT_MS = 120_000;
  const [polling, setPolling] = useState(false);
  useEffect(() => {
    if (!polling) return;
    const start = Date.now();
    const interval = setInterval(async () => {
      if (Date.now() - start > POLL_TIMEOUT_MS) {
        setPolling(false);
        return;
      }
      const token = getStoredToken();
      if (!token) return;
      try {
        const res = await getLinkedInStatus(token);
        if (res.connected) {
          setConnection(res);
          setPolling(false);
        }
      } catch { /* keep polling */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [polling]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(postText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setError("Failed to copy to clipboard");
    }
  };

  const handleConnect = async () => {
    const token = getStoredToken();
    if (!token) return;
    try {
      const res = await getLinkedInAuthUrl(token);
      // Opens in system browser in Electron, popup in regular browser
      window.open(
        res.auth_url,
        "linkedin-oauth",
        "width=600,height=700,left=200,top=100",
      );
      // Start polling for connection status (needed for Electron where
      // the system browser can't communicate back via postMessage)
      setPolling(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start LinkedIn connection");
    }
  };

  const handlePost = async () => {
    const token = getStoredToken();
    if (!token || !postText.trim()) return;
    setPosting(true);
    setPostError(null);
    try {
      const res = await postToLinkedIn(token, { post_text: postText });
      if (res.success) {
        setPosted(true);
        setTimeout(() => setPosted(false), 3000);
      } else {
        setPostError(res.error ?? "Failed to post");
      }
    } catch (err) {
      setPostError(err instanceof Error ? err.message : "Failed to post");
    } finally {
      setPosting(false);
    }
  };

  const handleDisconnect = async () => {
    const token = getStoredToken();
    if (!token) return;
    setDisconnecting(true);
    try {
      await disconnectLinkedIn(token);
      setConnection({ connected: false });
    } catch {
      // silently fail
    } finally {
      setDisconnecting(false);
    }
  };

  const handleOpenLinkedIn = () => {
    window.open("https://www.linkedin.com/feed/", "_blank");
  };

  const charCount = postText.length;
  const overLimit = charCount > LINKEDIN_CHAR_LIMIT;
  const isConnected = connection?.connected === true;

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
            <Loader2 size={20} className="animate-spin text-muted-foreground" />
          </div>
        )}

        {error && !loading && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-sm text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400">{error}</div>
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
              <span className={overLimit ? "text-red-600 font-medium" : "text-muted-foreground"}>
                {charCount.toLocaleString()} / {LINKEDIN_CHAR_LIMIT.toLocaleString()} characters
              </span>
              <Button variant="ghost" size="sm" onClick={generate} className="text-xs h-7">
                Regenerate
              </Button>
            </div>

            {/* Post error */}
            {postError && (
              <div className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/10 dark:text-red-400">
                {postError}
              </div>
            )}

            {/* Connection status */}
            {isConnected && (
              <div className="flex items-center justify-between rounded-lg border border-emerald-200/60 bg-emerald-50/50 px-3 py-2 dark:border-emerald-500/20 dark:bg-emerald-500/10">
                <span className="text-xs text-emerald-700 dark:text-emerald-400">
                  Connected as <strong>{connection?.linkedin_name || "LinkedIn user"}</strong>
                </span>
                <button
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                  className="inline-flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  <Unplug size={10} />
                  {disconnecting ? "..." : "Disconnect"}
                </button>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex flex-wrap items-center gap-2">
              {/* Direct post button (when connected) */}
              {isConnected && (
                <Button
                  onClick={handlePost}
                  disabled={!postText || posting || overLimit}
                  className="flex-1 bg-[#0A66C2] text-white hover:bg-[#004182]"
                >
                  {posted ? (
                    <>
                      <Check size={14} className="mr-1.5 text-emerald-300" />
                      Posted!
                    </>
                  ) : posting ? (
                    <>
                      <Loader2 size={14} className="mr-1.5 animate-spin" />
                      Posting...
                    </>
                  ) : (
                    <>
                      <Send size={14} className="mr-1.5" />
                      Post to LinkedIn
                    </>
                  )}
                </Button>
              )}

              {/* Connect button (when not connected) */}
              {!isConnected && !statusLoading && connection !== null && (
                <Button
                  onClick={handleConnect}
                  className="flex-1 bg-[#0A66C2] text-white hover:bg-[#004182]"
                >
                  <Linkedin size={14} className="mr-1.5" />
                  Connect LinkedIn
                </Button>
              )}

              {/* Copy button */}
              <Button
                onClick={handleCopy}
                disabled={!postText}
                variant={isConnected ? "outline" : "default"}
                className={isConnected ? "flex-1" : "flex-1 bg-foreground text-background hover:bg-foreground/90"}
              >
                {copied ? (
                  <>
                    <Check size={14} className="mr-1.5 text-emerald-500" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy size={14} className="mr-1.5" />
                    Copy
                  </>
                )}
              </Button>

              {/* Open LinkedIn button (only when not connected) */}
              {!isConnected && (
                <Button
                  variant="outline"
                  onClick={handleOpenLinkedIn}
                  className="flex-1 border-[#0A66C2] text-[#0A66C2] hover:bg-[#0A66C2]/5"
                >
                  <ExternalLink size={14} className="mr-1.5" />
                  Open LinkedIn
                </Button>
              )}
            </div>

            {/* Help text */}
            <p className="text-[10px] text-muted-foreground text-center leading-relaxed">
              {isConnected
                ? "Click 'Post to LinkedIn' to publish directly, or copy and paste manually."
                : "Copy your post text and paste it into LinkedIn, or connect your account for direct posting."}
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
