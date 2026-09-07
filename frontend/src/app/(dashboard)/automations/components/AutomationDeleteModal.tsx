'use client';

import React from 'react';
import { AlertTriangle, Trash2, Loader2, X } from 'lucide-react';
import { Automation } from '@/lib/types';

interface AutomationDeleteModalProps {
  isOpen: boolean;
  automation: Automation | null;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function AutomationDeleteModal({
  isOpen,
  automation,
  isDeleting,
  onConfirm,
  onCancel,
}: AutomationDeleteModalProps) {
  if (!isOpen || !automation) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 relative">
        {/* Close Button */}
        <button
          type="button"
          onClick={onCancel}
          disabled={isDeleting}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-200 transition p-1 rounded-lg hover:bg-slate-800 disabled:opacity-50"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-start space-x-3.5">
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 flex-shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-100">Delete Automation</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Are you sure you want to delete <span className="font-semibold text-slate-200">"{automation.name}"</span>?
            </p>
          </div>
        </div>

        {/* Explanation Alert */}
        <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800/80 text-xs text-slate-300 space-y-1.5">
          <p className="font-semibold text-rose-300">This action cannot be undone.</p>
          <p className="text-slate-400 text-[11px] leading-relaxed">
            This will remove the automation configuration. Existing execution history will follow the backend's configured retention/deletion behavior.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition flex items-center space-x-2 shadow-lg shadow-rose-600/30 disabled:opacity-50"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete Automation</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
