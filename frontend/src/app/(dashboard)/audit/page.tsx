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
    <div className="space-y-5 select-none font-sans text-xs">
      {/* Linear Style Context Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-800/60">
        <div>
          <h1 className="text-lg font-bold text-slate-100 tracking-tight flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-indigo-400" />
            <span>Enterprise Audit Logs & Activity Trail</span>
          </h1>
          <p className="text-[11px] text-slate-400">
            Compliance trail of user actions, AI generation events, Meta API credentials, and Celery publishing tasks.
          </p>
        </div>

        <div className="flex items-center space-x-1.5 bg-slate-900/60 border border-slate-800 px-2.5 py-1 rounded text-[10px] font-mono text-emerald-400">
          <Activity className="w-3 h-3 text-emerald-400 animate-pulse" />
          <span>Real-time Logging Active</span>
        </div>
      </div>

      {/* Activity Table Surface */}
      <div className="linear-panel rounded-lg overflow-hidden border border-slate-800/80">
        <div className="px-3.5 py-2.5 bg-slate-900/60 border-b border-slate-800/80 flex items-center justify-between">
          <span className="text-xs font-semibold text-slate-200 flex items-center space-x-2">
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span>Security Event Trail</span>
          </span>
          <span className="text-[10px] text-slate-400 font-mono">Showing latest 50 events</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-900/40 border-b border-slate-800/80 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-3">Action Event</th>
                <th className="p-3">Target Resource</th>
                <th className="p-3">Payload Details</th>
                <th className="p-3">Client IP</th>
                <th className="p-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {sampleLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40 transition-colors duration-150">
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 font-mono text-[10px] font-medium">
                      {log.action}
                    </span>
                  </td>
                  <td className="p-3 text-slate-200 font-medium font-mono text-[11px]">
                    {log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}
                  </td>
                  <td className="p-3 text-slate-400 font-mono text-[11px] max-w-sm truncate">
                    {JSON.stringify(log.details)}
                  </td>
                  <td className="p-3 text-slate-400 font-mono text-[11px]">
                    {log.ip_address}
                  </td>
                  <td className="p-3 text-slate-300 font-mono text-[11px]">
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
