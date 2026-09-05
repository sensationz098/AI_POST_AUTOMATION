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
  MessageSquare,
  Megaphone,
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
      { name: 'Studio', href: '/studio', icon: Sparkles },
      { name: 'Post Scheduler', href: '/posts', icon: Calendar },
    ],
  },
  {
    title: 'Social & Brands',
    items: [
      { name: 'Organic Comments', href: '/comments/posts', icon: MessageSquare },
      { name: 'Ad Comments', href: '/comments/ads', icon: Megaphone },
      { name: 'Brand Profiles', href: '/brands', icon: Layers },
      { name: 'Meta Accounts', href: '/meta-connect', icon: Share2, isMeta: true },
    ],
  },
];

export const Sidebar = () => {
  const pathname = usePathname();
  const { theme, toggleTheme } = useTheme();

  return (
    <aside className="w-60 bg-[#0B0F17] border-r border-slate-800/60 flex flex-col justify-between p-3 select-none text-xs font-sans">
      <div className="space-y-5">
        {/* Workspace Brand Header */}
        <Link href="/dashboard" className="flex items-center space-x-2.5 px-2 py-2.5 rounded-lg hover:bg-slate-800/40 transition group">
          <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center text-white font-bold shadow-sm group-hover:bg-indigo-500 transition">
            <Bot className="w-4 h-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h1 className="font-bold text-xs text-slate-100 truncate tracking-tight">SocialAI Workspace</h1>
            </div>
            <p className="text-[10px] text-slate-400 truncate">Enterprise Meta Suite</p>
          </div>
        </Link>

        {/* Navigation Group Tree */}
        <div className="space-y-4">
          {navGroups.map((group) => (
            <div key={group.title} className="space-y-0.5">
              <div className="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                {group.title}
              </div>
              <nav className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href + '/'));
                  const Icon = item.icon;
                  return (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={`flex items-center justify-between px-2.5 py-1.5 rounded-md font-medium transition-colors duration-150 group ${
                        isActive
                          ? 'bg-indigo-500/10 text-indigo-400 font-semibold border-l-2 border-indigo-500 pl-2'
                          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                      }`}
                    >
                      <div className="flex items-center space-x-2 truncate">
                        <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${isActive ? 'text-indigo-400' : 'text-slate-400 group-hover:text-slate-300'}`} />
                        <span className="truncate">{item.name}</span>
                      </div>

                      {item.badge ? (
                        <span className="text-[9px] font-mono font-bold px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {item.badge}
                        </span>
                      ) : isActive ? (
                        <ChevronRight className="w-3 h-3 text-indigo-400" />
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
      <div className="space-y-2 pt-3 border-t border-slate-800/60">
        <button
          onClick={toggleTheme}
          className="w-full flex items-center justify-between px-2.5 py-1.5 rounded-md bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 text-slate-300 transition text-[11px] font-medium"
        >
          <div className="flex items-center space-x-2">
            {theme === 'dark' ? (
              <Sun className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <Moon className="w-3.5 h-3.5 text-indigo-400" />
            )}
            <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
          </div>
          <span className="text-[9px] font-mono uppercase text-slate-400">
            {theme}
          </span>
        </button>

        <div className="px-2.5 py-2 rounded-md bg-slate-900/40 border border-slate-800/60 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-medium text-slate-300">Celery Beat Active</span>
          </div>
          <Zap className="w-3 h-3 text-amber-400" />
        </div>
      </div>
    </aside>
  );
};
