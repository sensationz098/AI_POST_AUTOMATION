'use client';

import React from 'react';
import { Bell, UserCheck, Shield, CheckCircle2, Search, Sparkles, Sun, Moon } from 'lucide-react';
import Link from 'next/link';
import { useTheme } from '@/components/ThemeProvider';

interface Props {
  brandName?: string;
  userRole?: string;
}

export const Header: React.FC<Props> = ({
  brandName = 'Apex Innovations',
  userRole = 'Admin'
}) => {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-12 bg-[#0B0F17] border-b border-slate-800/60 px-4 flex items-center justify-between sticky top-0 z-30 select-none text-xs font-sans">
      {/* Left: Breadcrumbs & Active Brand */}
      <div className="flex items-center space-x-3 min-w-0">
        <div className="flex items-center space-x-1.5 text-slate-400 text-[11px] font-medium">
          <span>SocialAI</span>
          <span>/</span>
          <span className="text-slate-200 font-semibold">{brandName}</span>
        </div>

        <div className="h-3.5 w-[1px] bg-slate-800" />

        <div className="flex items-center space-x-1.5 bg-slate-900/60 border border-slate-800 px-2 py-0.5 rounded text-[10px] font-medium text-slate-300">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>Active Persona</span>
        </div>
      </div>

      {/* Right: Actions, Search, Notifications, Profile */}
      <div className="flex items-center space-x-2">
        <Link
          href="/studio"
          className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-[11px] transition shadow-sm"
        >
          <Sparkles className="w-3 h-3" />
          <span>+ New Post</span>
          <kbd className="hidden md:inline-block px-1 py-0.2 rounded bg-indigo-700/60 text-[9px] text-indigo-200 font-mono">⌘K</kbd>
        </Link>

        <Link
          href="/meta-connect"
          className="hidden sm:flex items-center space-x-1 px-2 py-1 rounded bg-slate-900/60 border border-slate-800 hover:border-slate-700 text-slate-300 text-[10px] font-medium transition"
        >
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span>Meta Sync</span>
        </Link>

        <div className="h-3.5 w-[1px] bg-slate-800" />

        {/* Theme Switcher Button */}
        <button
          onClick={toggleTheme}
          className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800/60 transition focus-ring"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {theme === 'dark' ? (
            <Sun className="w-3.5 h-3.5 text-amber-400" />
          ) : (
            <Moon className="w-3.5 h-3.5 text-indigo-400" />
          )}
        </button>

        <button className="relative p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800/60 transition focus-ring">
          <Bell className="w-3.5 h-3.5" />
          <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-pink-500" />
        </button>

        <div className="flex items-center space-x-1.5 bg-slate-900/60 border border-slate-800/80 px-2 py-1 rounded text-[11px]">
          <UserCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-semibold text-slate-200 text-[10px]">{userRole}</span>
        </div>
      </div>
    </header>
  );
};
