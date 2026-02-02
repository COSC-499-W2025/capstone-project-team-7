"use client";

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Folder,
  Briefcase,
  FileText,
  Scan,
  Settings,
  HelpCircle,
  Search,
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
  const isActive = pathname === href;

  return (
    <Link
      href={href as any}
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
        isActive
          ? 'bg-white/15 text-white font-medium'
          : 'text-gray-400 hover:bg-white/10 hover:text-gray-200'
      }`}
    >
      <span className="w-5 h-5 flex-shrink-0">{icon}</span>
      <span className="text-sm">{label}</span>
    </Link>
  );
};

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="px-3 mb-3 mt-1 first:mt-0">
      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        {children}
      </span>
    </div>
  );
};

export const Sidebar: React.FC = () => {
  const { user, isAuthenticated } = useAuth();
  const [profile, setProfile] = useState<SidebarProfile>({
    displayName: "Guest",
    email: "",
    avatarUrl: null,
  });

  const initials = useMemo(() => {
    const source = profile.displayName || profile.email || "?";
    return source.trim().charAt(0).toUpperCase() || "?";
  }, [profile.displayName, profile.email]);

  useEffect(() => {
    if (user?.email) {
      setProfile((prev) => ({
        ...prev,
        displayName: prev.displayName === "Guest" ? user.email.split("@")[0] : prev.displayName,
        email: user.email ?? prev.email,
      }));
    }
  }, [user?.email]);

  useEffect(() => {
    if (!isAuthenticated) {
      setProfile({ displayName: "Guest", email: "", avatarUrl: null });
      return;
    }

    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (!token) return;

    let cancelled = false;
    const fetchProfile = () => {
      api.profile.get(token).then((res) => {
        if (!res.ok || cancelled) return;
        setProfile({
          displayName: res.data.display_name || res.data.email || "User",
          email: res.data.email || "",
          avatarUrl: res.data.avatar_url || null,
        });
      });
    };

    fetchProfile();
    const handleProfileUpdated = () => fetchProfile();
    window.addEventListener("profile:updated", handleProfileUpdated);

    return () => {
      window.removeEventListener("profile:updated", handleProfileUpdated);
      cancelled = true;
    };
  }, [isAuthenticated]);

  return (
    <div className="fixed left-0 top-0 h-screen w-[280px] bg-gradient-to-b from-gray-900 via-gray-950 to-black border-r border-gray-800/50 flex flex-col shadow-2xl">
      <div className="flex-shrink-0 px-6 py-6 border-b border-gray-800/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-base">L</span>
          </div>
          <span className="text-xl font-bold text-white tracking-tight">Lumen</span>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6">
        <SectionLabel>Overview</SectionLabel>
        <div className="space-y-1">
          <NavItem
            href="/"
            icon={<LayoutDashboard size={20} />}
            label="Dashboard"
          />
          <NavItem
            href="/portfolio"
            icon={<Folder size={20} />}
            label="Portfolio"
          />
          <NavItem
            href="/projects"
            icon={<Briefcase size={20} />}
            label="Projects"
          />
          <NavItem
            href="/resumes"
            icon={<FileText size={20} />}
            label="Resumes"
          />
          <NavItem
            href="/scanned-results"
            icon={<Scan size={20} />}
            label="Scanned Results"
          />
        </div>
      </div>

      <div className="flex-shrink-0 border-t border-gray-800/50 px-4 py-5">
        <div className="space-y-1 mb-4">
          <NavItem
            href="/settings"
            icon={<Settings size={20} />}
            label="Settings"
          />
          <NavItem
            href="/help"
            icon={<HelpCircle size={20} />}
            label="Get Help"
          />
          <NavItem
            href="/search"
            icon={<Search size={20} />}
            label="Search"
          />
        </div>

        <Link
          href="/profile"
          className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 rounded-xl p-3.5 border border-gray-700/30 backdrop-blur-sm block transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/20"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-600 to-gray-800 flex items-center justify-center flex-shrink-0 shadow-md">
              {profile.avatarUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={profile.avatarUrl}
                  alt={`${profile.displayName} avatar`}
                  className="h-full w-full rounded-full object-cover"
                />
              ) : (
                <span className="text-white font-semibold text-sm">{initials}</span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">{profile.displayName}</p>
              {profile.email ? (
                <p className="text-xs text-gray-400 truncate">{profile.email}</p>
              ) : (
                <p className="text-xs text-gray-400 truncate">Sign in to view profile</p>
              )}
            </div>
          </div>
        </Link>
      </div>
    </div>
  );
};
