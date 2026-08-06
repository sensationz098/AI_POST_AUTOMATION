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
  Zap
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'AI Studio', href: '/studio', icon: Sparkles, badge: 'AI Powered' },
  { name: 'Post Scheduler', href: '/posts', icon: Calendar },
  { name: 'Brand Profiles', href: '/brands', icon: Layers },
  { name: 'Meta Accounts', href: '/meta-connect', icon: Share2 },
  { name: 'Audit Logs', href: '/audit', icon: ShieldCheck },
];

export const Sidebar = () => {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-[#0B0F17] border-r border-slate-800 flex flex-col justify-between p-4 min-h-screen">
      <div>
        {/* Brand Header */}
        <div className="flex items-center space-x-3 px-3 py-4 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base text-white tracking-wide">SocialAI Pro</h1>
            <p className="text-[10px] text-indigo-400 font-medium">Meta Automation Platform</p>
          </div>
        </div>

        {/* Nav links */}
        <nav className="space-y-1.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-200 ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30 shadow-md'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-5 h-5 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span className="text-[9px] font-bold px-2 py-0.5 rounded-full bg-gradient-to-r from-pink-500 to-purple-600 text-white">
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Plan & Upgrade Card */}
      <div className="p-4 rounded-2xl bg-gradient-to-b from-indigo-950/40 to-purple-950/40 border border-indigo-500/20 text-center space-y-2">
        <div className="w-8 h-8 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
          <Zap className="w-4 h-4" />
        </div>
        <h4 className="font-semibold text-xs text-white">Meta Enterprise Engine</h4>
        <p className="text-[11px] text-slate-400">FB Pages & IG Business connected with Celery worker beat active.</p>
      </div>
    </aside>
  );
};
