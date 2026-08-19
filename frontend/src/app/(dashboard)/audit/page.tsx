'use client';

import React, { useEffect, useState } from 'react';
import { ShieldCheck, Activity, Terminal, Loader2, FileCode } from 'lucide-react';
import { AuditLog } from '@/lib/types';
import { apiClient } from '@/lib/api';

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchAuditLogs() {
      setIsLoading(true);
      try {
        const res = await apiClient.get('/audit/logs');
        if (Array.isArray(res.data)) {
          setLogs(res.data);
        } else {
          setLogs([]);
        }
      } catch (e) {
        setLogs([]);
      } finally {
        setIsLoading(false);
      }
    }
    fetchAuditLogs();
  }, []);

  return (
    <div className="space-y-6 font-sans text-xs select-none">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border-color)]">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)] tracking-tight flex items-center space-x-2">
            <ShieldCheck className="w-5 h-5 text-[var(--accent-color)]" />
            <span>Audit Logs & Compliance Trail</span>
          </h1>
          <p className="text-xs text-[var(--text-secondary)] mt-1">
            Audit trail of user actions, AI generation requests, Meta credentials updates, and Celery publishing tasks.
          </p>
        </div>

        <div className="flex items-center space-x-2 bg-[var(--bg-secondary)] border border-[var(--border-color)] px-3 py-1.5 rounded text-xs font-mono text-[var(--success-color)] self-start sm:self-auto">
          <Activity className="w-3.5 h-3.5 text-[var(--success-color)] animate-pulse" />
          <span>Real-time Logging Active</span>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="pub-card overflow-hidden">
        <div className="px-4 py-3 bg-[var(--bg-tertiary)] border-b border-[var(--border-color)] flex items-center justify-between">
          <span className="text-xs font-semibold text-[var(--text-primary)] flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-[var(--accent-color)]" />
            <span>Security Event Log</span>
          </span>
          <span className="text-[11px] text-[var(--text-tertiary)] font-mono">
            {logs.length > 0 ? `Showing recent ${logs.length} events` : '0 events'}
          </span>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12 text-[var(--text-tertiary)] space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-[var(--accent-color)]" />
            <span>Loading security audit logs...</span>
          </div>
        ) : logs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="pub-table">
              <thead>
                <tr>
                  <th className="p-3">Action Event</th>
                  <th className="p-3">Target Resource</th>
                  <th className="p-3">Payload Details</th>
                  <th className="p-3">Client IP</th>
                  <th className="p-3">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--accent-color)] font-mono text-[10px] font-medium">
                        {log.action}
                      </span>
                    </td>
                    <td className="p-3 text-[var(--text-primary)] font-medium font-mono text-[11px]">
                      {log.resource_type} {log.resource_id ? `#${log.resource_id}` : ''}
                    </td>
                    <td className="p-3 text-[var(--text-secondary)] font-mono text-[11px] max-w-xs truncate">
                      {typeof log.details === 'object' ? JSON.stringify(log.details) : String(log.details || '')}
                    </td>
                    <td className="p-3 text-[var(--text-tertiary)] font-mono text-[11px]">
                      {log.ip_address || '127.0.0.1'}
                    </td>
                    <td className="p-3 text-[var(--text-secondary)] font-mono text-[11px]">
                      {new Date(log.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-12 text-center space-y-3">
            <FileCode className="w-10 h-10 text-[var(--text-tertiary)] mx-auto" />
            <div>
              <h3 className="text-sm font-semibold text-[var(--text-primary)]">No Audit Events Logged</h3>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                System events and publishing API logs will appear here in real-time.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
