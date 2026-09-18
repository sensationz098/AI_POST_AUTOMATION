'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  TrendingUp,
  Sparkles, 
  Layers, 
  Calendar, 
  Share2, 
  MessageSquare,
  Megaphone,
  ShieldCheck, 
  Bot,
  Zap,
  Activity,
  ChevronRight,
  Sun,
  Moon,
  Youtube,
  X
} from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

export interface SidebarProps {
  isMobileOpen?: boolean;
  onMobileClose?: () => void;
}

interface NavItem {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
  isMeta?: boolean;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    title: 'Overview',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'Social Analytics', href: '/analytics', icon: TrendingUp },
    ],
  },
  {
    title: 'Publish',
    items: [
      { name: 'Studio', href: '/studio', icon: Sparkles },
      { name: 'YouTube Videos', href: '/youtube/videos', icon: Youtube },
      { name: 'Post Scheduler', href: '/posts', icon: Calendar },
    ],
  },
  {
    title: 'Engage',
    items: [
      { name: 'Comment Inbox', href: '/comments', icon: MessageSquare },
      { name: 'Comment Automations', href: '/automations', icon: Bot, badge: 'V1' },
      { name: 'Organic Posts', href: '/comments/posts', icon: Sparkles },
      { name: 'Ad Comments', href: '/comments/ads', icon: Megaphone },
    ],
  },
  {
    title: 'Brand & Accounts',
    items: [
      { name: 'Brand Profiles', href: '/brands', icon: Layers },
      { name: 'Meta Accounts', href: '/meta-connect', icon: Share2, isMeta: true },
      { name: 'Audit Logs', href: '/audit', icon: ShieldCheck },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({ isMobileOpen, onMobileClose }) => {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-[#0B0F17] border-r border-slate-200 dark:border-slate-800/70 flex flex-col justify-between p-3.5 select-none font-sans transition-transform duration-200 ease-in-out md:static md:translate-x-0 ${
        isMobileOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'
      }`}
    >
      <div className="space-y-4 overflow-y-auto pr-1">
        {/* Workspace Brand Header */}
        <div className="flex items-center justify-between px-1">
          <Link
            href="/dashboard"
            onClick={onMobileClose}
            className="flex items-center space-x-3 px-2 py-2 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800/50 transition-colors duration-150 group flex-1 min-w-0"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center text-white font-bold shadow-sm group-hover:opacity-95 transition-opacity flex-shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="font-bold text-sm text-slate-900 dark:text-slate-100 truncate tracking-tight">
                SocialAI
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">
                Sensationz Enterprise
              </p>
            </div>
          </Link>

          {/* Close button on mobile view */}
          {onMobileClose && (
            <button
              onClick={onMobileClose}
              className="md:hidden p-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition focus-ring"
              aria-label="Close navigation sidebar"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Navigation Groups */}
        <div className="space-y-4 pt-1">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-1">
              <div className="px-3 py-1 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                {group.title}
              </div>
              <nav className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive =
                    pathname === item.href ||
                    (item.href !== '/' && pathname.startsWith(item.href + '/'));
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      onClick={onMobileClose}
                      className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150 group relative ${
                        isActive
                          ? 'bg-indigo-50/90 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300 font-semibold border-l-2 border-indigo-600 dark:border-indigo-500 pl-2.5'
                          : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100/80 dark:hover:bg-slate-800/60'
                      }`}
                    >
                      <div className="flex items-center space-x-3 truncate">
                        <Icon
                          className={`w-4 h-4 flex-shrink-0 transition-colors ${
                            isActive
                              ? 'text-indigo-600 dark:text-indigo-400'
                              : 'text-slate-400 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-200'
                          }`}
                        />
                        <span className="truncate">{item.name}</span>
                      </div>

                      {item.badge ? (
                        <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30">
                          {item.badge}
                        </span>
                      ) : isActive ? (
                        <ChevronRight className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                      ) : null}
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </div>

      {/* Footer Controls: Theme Toggle & Engine Telemetry */}
      <div className="space-y-2 pt-3 border-t border-slate-200 dark:border-slate-800/70">
        <button
          onClick={toggleTheme}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-700 dark:text-slate-300 transition-colors text-xs font-medium focus-ring"
        >
          <div className="flex items-center space-x-2.5">
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-600" />
            )}
            <span>{theme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>
          </div>
          <span className="text-xs font-mono uppercase text-slate-400 dark:text-slate-400">
            {theme}
          </span>
        </button>

        <div className="px-3 py-2 rounded-lg bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse" />
            <span className="text-xs font-medium text-slate-600 dark:text-slate-400">
              Celery Engine Active
            </span>
          </div>
          <Zap className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
        </div>
      </div>
    </aside>
  );
};
