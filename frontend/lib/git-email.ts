/** Utilities for formatting git contributor emails. */

const NOREPLY_PATTERN =
  /^(\d+\+)?(.+)@users\.noreply\.github\.com$/i;

/** Check whether an email is a GitHub noreply address. */
export function isGitHubNoreply(email: string | null | undefined): boolean {
  if (!email) return false;
  return NOREPLY_PATTERN.test(email);
}

/**
 * Format a contributor email for display.
 *
 * - GitHub noreply → `"username (GitHub)"`
 * - Regular email → returned as-is
 * - null/undefined → em dash `"—"`
 */
export function formatContributorEmail(
  email: string | null | undefined
): string {
  if (!email) return "—";

  const match = email.match(NOREPLY_PATTERN);
  if (match) {
    return `${match[2]} (GitHub)`;
  }

  return email;
}
