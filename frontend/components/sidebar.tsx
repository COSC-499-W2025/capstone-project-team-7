"use client";

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard,
  Folder,
  Briefcase,
  FileEdit,
  Settings,
  Search,
  Sparkles,
  LogOut,
  Target,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useAuth } from '@/hooks/use-auth';

type SidebarProfile = {
  displayName: string;
  email: string;
  avatarUrl: string | null;
};

interface NavItemProps {
  href: string;
  icon: React.ReactNode;
  label: string;
}

const NavItem: React.FC<NavItemProps> = ({ href, icon, label }) => {
  const pathname = usePathname();
  const isActive = href === "/" ? pathname === "/" : pathname.startsWith(href);

  return (
    <Link
      href={href as any}
      className={`sidebar-link text-sm font-medium ${isActive ? 'sidebar-link-active' : ''}`}
    >
      <span className="w-5 h-5 flex-shrink-0">{icon}</span>
      <span>{label}</span>
    </Link>
  );
};

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="mb-2 mt-4 first:mt-0 px-1">
      <span className="sidebar-group-label">
        {children}
      </span>
    </div>
  );
};

export const Sidebar: React.FC = () => {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuth();
  const [profile, setProfile] = useState<SidebarProfile>({
    displayName: "Guest",
    email: "",
    avatarUrl: null,
  });
  const [avatarLoadError, setAvatarLoadError] = useState(false);

  const initials = useMemo(() => {
    const source = profile.displayName || profile.email || "?";
    return source.trim().charAt(0).toUpperCase() || "?";
  }, [profile.displayName, profile.email]);

  useEffect(() => {
    if (!isAuthenticated) {
      setProfile({ displayName: "Guest", email: "", avatarUrl: null });
      return;
    }

    const fallbackEmail = user?.email ?? "";
    setProfile((prev) => ({
      ...prev,
      displayName:
        prev.displayName === "Guest" && fallbackEmail
          ? fallbackEmail.split("@")[0]
          : prev.displayName,
      email: fallbackEmail || prev.email,
    }));

    let cancelled = false;
    const fetchProfile = () => {
      api.profile
        .get()
        .then((res) => {
          if (!res.ok) {
            throw new Error(res.error || `Failed to fetch profile (${res.status ?? "unknown"})`);
          }
          if (cancelled) return;
          setProfile({
            displayName: res.data.display_name || res.data.email || "User",
            email: res.data.email || "",
            avatarUrl: res.data.avatar_url || null,
          });
        })
        .catch((error) => {
          console.error("Failed to fetch profile:", error);
        });
    };

    fetchProfile();
    const handleProfileUpdated = () => fetchProfile();
    window.addEventListener("profile:updated", handleProfileUpdated);

    return () => {
      window.removeEventListener("profile:updated", handleProfileUpdated);
      cancelled = true;
    };
  }, [isAuthenticated, user?.email]);

  useEffect(() => {
    setAvatarLoadError(false);
  }, [profile.avatarUrl]);

  return (
    <aside className="sidebar-shell">
      <div className="sidebar-rail flex-1 min-h-0">
        <div className="sidebar-brand">
          <div className="sidebar-brand-mark">D</div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-neutral-400">
              Workspace
            </p>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-xl font-semibold tracking-tight text-white">DevFolio</span>
            </div>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto">
          <SectionLabel>Overview</SectionLabel>
          <div className="space-y-1">
            <NavItem
              href="/"
              icon={<LayoutDashboard size={18} />}
              label="Dashboard"
            />
            <NavItem
              href="/portfolio"
              icon={<Folder size={18} />}
              label="Portfolio"
            />
            <NavItem
              href="/projects"
              icon={<Briefcase size={18} />}
              label="Projects"
            />
            <NavItem
              href="/ai-analysis"
              icon={<Sparkles size={18} />}
              label="AI Analysis"
            />
            <NavItem
              href="/resume-builder"
              icon={<FileEdit size={18} />}
              label="Resume Builder"
            />
            <NavItem
              href="/job-match"
              icon={<Target size={18} />}
              label="Job Match"
            />
          </div>
          <SectionLabel>Utilities</SectionLabel>
          <div className="space-y-1">
            <NavItem
              href="/settings"
              icon={<Settings size={18} />}
              label="Settings"
            />
            <NavItem
              href="/search"
              icon={<Search size={18} />}
              label="Search"
            />
            {isAuthenticated && (
              <button
                type="button"
                onClick={() => {
                  logout();
                  router.push('/auth/login');
                }}
                className="flex w-full items-center gap-3 rounded-2xl border border-transparent px-[14px] py-[13px] text-sm font-medium text-neutral-400 transition-all duration-200 hover:border-red-500/20 hover:bg-red-500/10 hover:text-red-300"
              >
                <span className="flex h-5 w-5 flex-shrink-0 items-center justify-center">
                  <LogOut size={18} />
                </span>
                <span>Logout</span>
              </button>
            )}
          </div>
        </div>

        <Link
          href="/profile"
          className="sidebar-profile mt-auto block"
        >
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full border border-white/12 bg-white/10">
              {profile.avatarUrl && !avatarLoadError ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile.avatarUrl}
                  alt={`${profile.displayName} avatar`}
                  className="h-full w-full rounded-full object-cover"
                  onError={() => setAvatarLoadError(true)}
                />
              ) : (
                <span className="text-sm font-semibold text-white">{initials}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-semibold text-white">{profile.displayName}</p>
              {profile.email ? (
                <p className="truncate text-xs text-neutral-400">{profile.email}</p>
              ) : (
                <p className="truncate text-xs text-neutral-400">Sign in to view profile</p>
              )}
            </div>
          </div>
        </Link>
      </div>
    </aside>
  );
};
