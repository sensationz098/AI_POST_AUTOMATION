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
    <div className="space-y-8 select-none">
      {/* 2026 SaaS Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900/80 border border-slate-800 p-6 md:p-8 rounded-3xl shadow-xl">
        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center space-x-2.5">
            <div className="p-2 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <span>Audit Logs & Activity Trail</span>
          </h1>
          <p className="text-xs md:text-sm text-slate-400 leading-relaxed max-w-xl">
            Complete enterprise compliance trail of user actions, AI generation events, Meta API tokens, and automated Celery publishing tasks.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-slate-950 px-3.5 py-2 rounded-2xl border border-slate-800 text-xs font-semibold text-slate-300 shadow-inner">
          <Activity className="w-4 h-4 text-emerald-400 animate-pulse" />
          <span>Real-time Event Logging Active</span>
        </div>
      </div>

      {/* Activity Table */}
      <div className="saas-card rounded-3xl overflow-hidden border border-slate-800 shadow-xl">
        <div className="p-5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
          <span className="text-xs font-extrabold text-slate-200 flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-indigo-400" />
            <span>Enterprise Activity Log</span>
          </span>
          <span className="text-xs text-slate-400 font-mono">Showing latest 50 security events</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-950/40 border-b border-slate-800 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <th className="p-5">Action Event</th>
                <th className="p-5">Resource Target</th>
                <th className="p-5">Payload Details</th>
                <th className="p-5">Client IP</th>
                <th className="p-5">Event Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 text-xs">
              {sampleLogs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/40 transition-colors duration-150">
                  <td className="p-5">
                    <span className="px-3 py-1 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 font-mono font-bold text-xs shadow-sm">
                      {log.action}
                    </span>
                  </td>
                  <td className="p-5 text-white font-bold tracking-tight">
                    {log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}
                  </td>
                  <td className="p-5 text-slate-400 font-mono text-xs max-w-sm truncate">
                    {JSON.stringify(log.details)}
                  </td>
                  <td className="p-5 text-slate-400 font-mono text-xs font-semibold">
                    {log.ip_address}
                  </td>
                  <td className="p-5 text-slate-300 font-mono text-xs font-semibold">
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
