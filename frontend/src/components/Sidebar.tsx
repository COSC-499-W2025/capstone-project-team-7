import React from 'react';
import { NavLink } from 'react-router-dom';
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

interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
}

const NavItem: React.FC<NavItemProps> = ({ to, icon, label }) => {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 ${
          isActive
            ? 'bg-white/15 text-white font-medium'
            : 'text-gray-400 hover:bg-white/10 hover:text-gray-200'
        }`
      }
    >
      <span className="w-5 h-5 flex-shrink-0">{icon}</span>
      <span className="text-sm">{label}</span>
    </NavLink>
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
  return (
    <div className="fixed left-0 top-0 h-screen w-[280px] bg-gradient-to-b from-gray-900 via-gray-950 to-black border-r border-gray-800/50 flex flex-col shadow-2xl">
      {/* Brand Section */}
      <div className="flex-shrink-0 px-6 py-6 border-b border-gray-800/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-gray-700 to-gray-900 flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-base">L</span>
          </div>
          <span className="text-xl font-bold text-white tracking-tight">Lumen</span>
        </div>
      </div>

      {/* Navigation - Scrollable middle section */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6">
        <SectionLabel>Overview</SectionLabel>
        <div className="space-y-1">
          <NavItem
            to="/"
            icon={<LayoutDashboard size={20} />}
            label="Dashboard"
          />
          <NavItem
            to="/portfolio"
            icon={<Folder size={20} />}
            label="Portfolio"
          />
          <NavItem
            to="/projects"
            icon={<Briefcase size={20} />}
            label="Projects"
          />
          <NavItem
            to="/resumes"
            icon={<FileText size={20} />}
            label="Resumes"
          />
          <NavItem
            to="/scanned-results"
            icon={<Scan size={20} />}
            label="Scanned Results"
          />
        </div>
      </div>

      {/* Bottom Section - Fixed at bottom */}
      <div className="flex-shrink-0 border-t border-gray-800/50 px-4 py-5">
        <div className="space-y-1 mb-4">
          <NavItem
            to="/settings"
            icon={<Settings size={20} />}
            label="Settings"
          />
          <NavItem
            to="/help"
            icon={<HelpCircle size={20} />}
            label="Get Help"
          />
          <NavItem
            to="/search"
            icon={<Search size={20} />}
            label="Search"
          />
        </div>

        {/* User Card */}
        <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 rounded-xl p-3.5 border border-gray-700/30 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-600 to-gray-800 flex items-center justify-center flex-shrink-0 shadow-md">
              <span className="text-white font-semibold text-sm">JD</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">Jacob</p>
              <p className="text-xs text-gray-400 truncate">Dameryjac@gmail.com</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
