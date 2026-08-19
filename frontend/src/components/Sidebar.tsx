'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Sparkles, 
  Layers, 
  Calendar, 
  Share2, 
  ShieldCheck, 
  Bot,
  Zap,
  Sun,
  Moon,
  ChevronRight
} from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    title: 'Workspace',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Studio', href: '/studio', icon: Sparkles },
      { name: 'Post Scheduler', href: '/posts', icon: Calendar },
    ],
  },
  {
    title: 'Social & Brands',
    items: [
      { name: 'Brand Studio', href: '/brands', icon: Layers },
      { name: 'Meta Accounts', href: '/meta-connect', icon: Share2 },
    ],
  },
  {
    title: 'Management',
    items: [
      { name: 'Audit Logs', href: '/audit', icon: ShieldCheck },
    ],
  },
];

export const Sidebar = () => {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <aside className="w-60 bg-[var(--bg-secondary)] border-r border-[var(--border-color)] flex flex-col justify-between p-3 select-none text-xs font-sans transition-colors duration-150">
      <div className="space-y-6">
        {/* Sensationz App Brand Header */}
        <Link href="/dashboard" className="flex items-center space-x-3 px-3 py-3 rounded-lg hover:bg-[var(--bg-tertiary)] transition group">
          <div className="w-8 h-8 rounded-md bg-[var(--accent-color)] flex items-center justify-center text-white font-bold shadow-sm flex-shrink-0">
            <Bot className="w-4.5 h-4.5 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="font-bold text-sm text-[var(--text-primary)] truncate tracking-tight">Sensationz</h1>
            <p className="text-[11px] text-[var(--text-secondary)] truncate">Publishing Platform</p>
          </div>
        </Link>

        {/* Navigation Group Tree */}
        <div className="space-y-5">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-1">
              <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-tertiary)]">
                {group.title}
              </div>
              <nav className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center justify-between px-3 py-2 rounded-md font-medium transition-colors duration-150 ${
                        isActive
                          ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] font-semibold border-l-2 border-[var(--accent-color)] pl-2.5'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-tertiary)]'
                      }`}
                    >
                      <div className="flex items-center space-x-2.5 truncate">
                        <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-[var(--accent-color)]' : 'text-[var(--text-tertiary)]'}`} />
                        <span className="truncate text-xs">{item.name}</span>
                      </div>

                      {item.badge ? (
                        <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-[var(--bg-tertiary)] text-[var(--accent-color)] border border-[var(--border-color)]">
                          {item.badge}
                        </span>
                      ) : isActive ? (
                        <ChevronRight className="w-3.5 h-3.5 text-[var(--accent-color)]" />
                      ) : null}
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Controls: Theme Toggle & Engine Status */}
      <div className="space-y-2 pt-3 border-t border-[var(--border-color)]">
        <button
          onClick={toggleTheme}
          className="w-full flex items-center justify-between px-3 py-2 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] hover:border-[var(--text-tertiary)] text-[var(--text-primary)] transition text-xs font-medium"
        >
          <div className="flex items-center space-x-2">
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-[var(--warning-color)]" />
            ) : (
              <Moon className="w-4 h-4 text-[var(--accent-color)]" />
            )}
            <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
          </div>
          <span className="text-[10px] font-mono uppercase text-[var(--text-tertiary)]">
            {theme}
          </span>
        </button>

        <div className="px-3 py-2 rounded-md bg-[var(--bg-tertiary)] border border-[var(--border-color)] flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-[var(--success-color)]" />
            <span className="text-[11px] font-medium text-[var(--text-secondary)]">Meta Engine Active</span>
          </div>
          <Zap className="w-3.5 h-3.5 text-[var(--warning-color)]" />
        </div>
      </div>
    </aside>
  );
};
