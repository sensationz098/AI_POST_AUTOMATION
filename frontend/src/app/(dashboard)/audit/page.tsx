'use client';

import React from 'react';
import { ShieldCheck, UserCheck, Activity, Terminal } from 'lucide-react';
import { AuditLog } from '@/lib/types';

const sampleLogs: AuditLog[] = [
  {
    id: 1,
    user_id: 1,
    action: 'POST_PUBLISHED',
    resource_type: 'Post',
    resource_id: 101,
    details: { fb_id: 'fb_post_1092834', ig_id: 'ig_media_9823471' },
    ip_address: '127.0.0.1',
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 2,
    user_id: 1,
    action: 'POST_SCHEDULED',
    resource_type: 'Post',
    resource_id: 102,
    details: { scheduled_at: new Date(Date.now() + 86400000).toISOString() },
    ip_address: '127.0.0.1',
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 3,
    user_id: 1,
    action: 'AI_CONTENT_GENERATED',
    resource_type: 'AIService',
    details: { topic: 'Launching Next-Gen AI Social Automation Studio' },
    ip_address: '127.0.0.1',
    created_at: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: 4,
    user_id: 1,
    action: 'META_ACCOUNT_CONNECTED',
    resource_type: 'MetaAccount',
    details: { fb_page: 'Apex Innovations', ig_username: 'apex_innovations' },
    ip_address: '127.0.0.1',
    created_at: new Date(Date.now() - 86400000).toISOString(),
  },
];

export default function AuditLogsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-indigo-400" />
          <span>Audit Logs & Activity History</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Complete compliance trail of user actions, AI generation events, and automated Celery publishing tasks.
        </p>
      </div>

      <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
        <div className="p-4 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-300 flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-indigo-400" />
            <span>Activity Trail</span>
          </span>
          <span className="text-[11px] text-slate-500 font-mono">Showing recent 50 events</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-4">Action</th>
                <th className="p-4">Resource</th>
                <th className="p-4">Details</th>
                <th className="p-4">IP Address</th>
                <th className="p-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {sampleLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30 transition">
                  <td className="p-4">
                    <span className="px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-mono font-bold text-[11px]">
                      {log.action}
                    </span>
                  </td>
                  <td className="p-4 text-slate-300 font-medium">
                    {log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}
                  </td>
                  <td className="p-4 text-slate-400 font-mono text-[11px] max-w-xs truncate">
                    {JSON.stringify(log.details)}
                  </td>
                  <td className="p-4 text-slate-400 font-mono text-[11px]">
                    {log.ip_address}
                  </td>
                  <td className="p-4 text-slate-400 font-mono text-[11px]">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
