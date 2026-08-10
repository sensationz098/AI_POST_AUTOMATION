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
  Activity,
  ChevronRight,
  Sun,
  Moon
} from 'lucide-react';
import { useTheme } from '@/components/ThemeProvider';

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
    title: 'Workspace',
    items: [
      { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
      { name: 'AI Studio', href: '/studio', icon: Sparkles, badge: 'AI Engine' },
      { name: 'Post Scheduler', href: '/posts', icon: Calendar },
    ],
  },
  {
    title: 'Social & Brands',
    items: [
      { name: 'Brand Profiles', href: '/brands', icon: Layers },
      { name: 'Meta Accounts', href: '/meta-connect', icon: Share2, isMeta: true },
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
    <aside className="w-64 bg-[#090D16] border-r border-slate-800/80 flex flex-col justify-between p-4 min-h-screen select-none">
      <div className="space-y-6">
        {/* Brand Header */}
        <Link href="/dashboard" className="flex items-center space-x-3 px-2 py-3 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-200">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <h1 className="font-extrabold text-sm text-white tracking-tight">SocialAI Pro</h1>
              <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                v2.4
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium mt-0.5">Meta Graph Automation</p>
          </div>
        </Link>

        {/* Grouped Nav links */}
        <div className="space-y-5">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-1">
              <span className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {group.title}
              </span>
              <nav className="space-y-1 pt-1">
                {group.items.map((item) => {
                  const isActive = pathname === item.href;
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center justify-between px-3 py-2 rounded-xl font-medium text-xs transition-all duration-200 group ${
                        isActive
                          ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/30 font-semibold shadow-sm'
                          : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="flex items-center space-x-2.5">
                        <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-200'}`} />
                        <span>{item.name}</span>
                      </div>

                      {item.badge ? (
                        <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-gradient-to-r from-pink-500 to-purple-600 text-white shadow-sm">
                          {item.badge}
                        </span>
                      ) : isActive ? (
                        <ChevronRight className="w-3.5 h-3.5 text-indigo-400" />
                      ) : null}
                    </Link>
                  );
                })}
              </nav>
            </div>
          ))}
        </div>
      </div>

      {/* Theme Toggle & System Status Footer Card */}
      <div className="space-y-3">
        <button
          onClick={toggleTheme}
          className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-indigo-500/40 text-slate-300 hover:text-white transition focus-ring text-xs font-semibold"
        >
          <div className="flex items-center space-x-2">
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-indigo-400" />
            )}
            <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 uppercase tracking-wider">
            {theme}
          </span>
        </button>

        <div className="p-3.5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-[11px] font-bold text-slate-200">Meta Engine Active</span>
            </div>
            <Zap className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            Celery Beat worker active with live Facebook & Instagram Graph API hooks.
          </p>
        </div>
      </div>
    </aside>
  );
};
