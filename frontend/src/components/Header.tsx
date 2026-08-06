'use client';

import React from 'react';
import { Bell, UserCheck, Shield } from 'lucide-react';

interface Props {
  brandName?: string;
  userRole?: string;
}

export const Header: React.FC<Props> = ({
  brandName = 'Apex Innovations',
  userRole = 'Admin'
}) => {
  return (
    <header className="h-16 bg-[#0B0F17]/90 backdrop-blur-md border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center space-x-3">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Brand:</span>
        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-700/60 px-3 py-1.5 rounded-lg">
          <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-bold text-white">{brandName}</span>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <button className="relative p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60 transition">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-pink-500" />
        </button>

        <div className="h-6 w-[1px] bg-slate-800" />

        <div className="flex items-center space-x-2.5 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl">
          <div className="w-7 h-7 rounded-full bg-indigo-600/30 border border-indigo-500/50 flex items-center justify-center text-indigo-400 text-xs font-bold">
            <UserCheck className="w-4 h-4" />
          </div>
          <div>
            <p className="text-xs font-semibold text-white">Software Architect</p>
            <div className="flex items-center space-x-1">
              <Shield className="w-3 h-3 text-indigo-400" />
              <span className="text-[10px] text-indigo-300 font-medium">{userRole}</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
