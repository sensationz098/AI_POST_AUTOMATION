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
    <header className="h-16 bg-[#090D16]/90 backdrop-blur-xl border-b border-slate-800/80 px-6 flex items-center justify-between sticky top-0 z-30 select-none">
      {/* Left: Active Brand & Search Bar */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2.5 bg-slate-900/90 border border-slate-800 px-3.5 py-1.5 rounded-xl shadow-inner">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-bold text-white tracking-wide">{brandName}</span>
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Active Brand
          </span>
        </div>

        <Link
          href="/studio"
          className="hidden md:flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 hover:text-slate-200 transition text-xs"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Quick Create Post...</span>
          <kbd className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 font-mono">⌘K</kbd>
        </Link>
      </div>

      {/* Right: Actions & User Info */}
      <div className="flex items-center space-x-3.5">
        <Link
          href="/meta-connect"
          className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold hover:bg-emerald-500/20 transition"
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Meta API Connected</span>
        </Link>

        {/* Sun/Moon Dark & Light Mode Toggle Button */}
        <button
          onClick={toggleTheme}
          className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/60 transition focus-ring flex items-center justify-center"
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
        >
          {theme === 'dark' ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-indigo-400" />
          )}
        </button>

        <button className="relative p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800/60 transition focus-ring">
          <Bell className="w-4 h-4" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-pink-500" />
        </button>

        <div className="h-5 w-[1px] bg-slate-800/80" />

        <div className="flex items-center space-x-2.5 bg-slate-900/90 border border-slate-800 px-3 py-1.5 rounded-xl shadow-sm">
          <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-indigo-400 text-xs font-bold">
            <UserCheck className="w-3.5 h-3.5" />
          </div>
          <div>
            <p className="text-xs font-bold text-white leading-none">Software Architect</p>
            <div className="flex items-center space-x-1 mt-0.5">
              <Shield className="w-2.5 h-2.5 text-indigo-400" />
              <span className="text-[9px] text-indigo-300 font-semibold">{userRole}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
