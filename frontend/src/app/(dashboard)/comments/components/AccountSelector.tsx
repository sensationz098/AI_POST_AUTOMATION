'use client';

import React from 'react';
import { SocialAccount } from '@/lib/types';
import { Facebook, Instagram, ShieldCheck, ChevronDown, Layers } from 'lucide-react';

interface AccountSelectorProps {
  accounts: SocialAccount[];
  selectedAccountId: string;
  onSelectAccount: (accountId: string) => void;
}

export default function AccountSelector({
  accounts,
  selectedAccountId,
  onSelectAccount,
}: AccountSelectorProps) {
  const selectedAccount = accounts.find(
    (acc) => String(acc.id) === String(selectedAccountId)
  );

  const getPlatformIcon = (platform: string, size = 'w-4 h-4') => {
    if (platform?.toLowerCase() === 'facebook') {
      return <Facebook className={`${size} text-blue-400 fill-current`} />;
    }
    return <Instagram className={`${size} text-pink-400`} />;
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800/90 rounded-2xl p-4 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
      {/* Account Info Badge */}
      <div className="flex items-center space-x-3.5 min-w-0">
        <div className="w-11 h-11 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-center flex-shrink-0 shadow-inner">
          {selectedAccountId === 'ALL' ? (
            <Layers className="w-5 h-5 text-indigo-400" />
          ) : (
            getPlatformIcon(selectedAccount?.platform || '', 'w-5 h-5')
          )}
        </div>

        <div className="min-w-0 space-y-0.5">
          <div className="flex items-center space-x-2 flex-wrap gap-y-1">
            <h2 className="text-base font-bold text-slate-100 truncate">
              {selectedAccountId === 'ALL'
                ? 'All Connected Social Accounts'
                : selectedAccount?.account_name || `Account #${selectedAccountId}`}
            </h2>

            {selectedAccountId !== 'ALL' && selectedAccount && (
              <span className="px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-300 border border-emerald-800/80 text-[10px] font-bold flex items-center space-x-1">
                <ShieldCheck className="w-3 h-3 text-emerald-400" />
                <span>Active Isolation</span>
              </span>
            )}
          </div>

          <p className="text-xs text-slate-400 truncate flex items-center space-x-2">
            <span>
              {selectedAccountId === 'ALL'
                ? 'Aggregated multi-platform view across Facebook & Instagram'
                : `${selectedAccount?.platform?.toUpperCase()} · ${selectedAccount?.account_id || ''}`}
            </span>
          </p>
        </div>
      </div>

      {/* Account Switcher Dropdown */}
      <div className="relative flex items-center flex-shrink-0">
        <select
          value={selectedAccountId}
          onChange={(e) => onSelectAccount(e.target.value)}
          className="bg-slate-950 border border-slate-700/80 text-slate-100 text-xs font-semibold rounded-xl pl-4 pr-10 py-2.5 outline-none focus:border-indigo-500 transition cursor-pointer appearance-none shadow-sm hover:border-slate-600"
        >
          <option value="ALL">All Connected Accounts</option>
          {accounts.map((acc) => (
            <option key={acc.id} value={acc.id}>
              {acc.platform === 'facebook' ? 'Facebook' : 'Instagram'}: {acc.account_name}
            </option>
          ))}
        </select>
        <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3 pointer-events-none" />
      </div>
    </div>
  );
}
