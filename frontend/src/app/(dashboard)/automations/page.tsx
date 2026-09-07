'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  Bot,
  Plus,
  Search,
  RefreshCw,
  Filter,
  CheckCircle2,
  Pause,
  Layers,
  Sparkles,
  Zap,
  ShieldCheck,
  AlertCircle,
  Loader2,
  ChevronDown
} from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';
import { Automation, SocialAccount } from '@/lib/types';
import { apiClient } from '@/lib/api';
import AutomationCard from './components/AutomationCard';
import AutomationEmptyState from './components/AutomationEmptyState';
import AutomationWizardModal from './components/AutomationWizardModal';
import AutomationDeleteModal from './components/AutomationDeleteModal';

export default function AutomationsPage() {
  // Data State
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [socialAccounts, setSocialAccounts] = useState<SocialAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Filters & Search State
  const [searchQuery, setSearchQuery] = useState('');
  const [platformFilter, setPlatformFilter] = useState<'ALL' | 'instagram' | 'facebook'>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'PAUSED' | 'DRAFT'>('ALL');

  // Modal State
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [editingAutomation, setEditingAutomation] = useState<Automation | null>(null);

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [deletingAutomation, setDeletingAutomation] = useState<Automation | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch Automations & Accounts
  const fetchData = async () => {
    setIsLoading(true);
    setFetchError(null);
    try {
      const [automationsRes, accountsRes] = await Promise.all([
        apiClient.get<Automation[]>('/automations'),
        apiClient.get<SocialAccount[]>('/social-accounts'),
      ]);

      setAutomations(automationsRes.data || []);
      setSocialAccounts(accountsRes.data || []);
    } catch (err: any) {
      console.error('Failed to load automations or accounts:', err);
      setFetchError(
        err.response?.data?.detail || 'Failed to load automations. Please check your backend connection.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Compute Metrics from real API data
  const metrics = useMemo(() => {
    const total = automations.length;
    const active = automations.filter((a) => a.status === 'ACTIVE').length;
    const paused = automations.filter((a) => a.status === 'PAUSED').length;
    const drafts = automations.filter((a) => a.status === 'DRAFT').length;
    return { total, active, paused, drafts };
  }, [automations]);

  // Filtered Automations List
  const filteredAutomations = useMemo(() => {
    return automations.filter((a) => {
      // Platform filter
      if (platformFilter !== 'ALL' && a.platform !== platformFilter) return false;

      // Status filter
      if (statusFilter !== 'ALL' && a.status !== statusFilter) return false;

      // Search filter
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        const matchesName = a.name.toLowerCase().includes(q);
        const keywords = a.trigger_config?.keywords || [];
        const matchesKeywords = keywords.some((k) => k.toLowerCase().includes(q));
        return matchesName || matchesKeywords;
      }

      return true;
    });
  }, [automations, platformFilter, statusFilter, searchQuery]);

  // Account Lookup Map
  const accountMap = useMemo(() => {
    const map = new Map<number, SocialAccount>();
    socialAccounts.forEach((acc) => map.set(acc.id, acc));
    return map;
  }, [socialAccounts]);

  // Modal Trigger Handlers
  const handleOpenCreate = () => {
    setEditingAutomation(null);
    setIsWizardOpen(true);
  };

  const handleOpenEdit = (auto: Automation) => {
    setEditingAutomation(auto);
    setIsWizardOpen(true);
  };

  const handleOpenDelete = (auto: Automation) => {
    setDeletingAutomation(auto);
    setIsDeleteModalOpen(true);
  };

  // Callback after successful Create or Edit
  const handleWizardSuccess = (savedAuto: Automation) => {
    setAutomations((prev) => {
      const exists = prev.some((a) => a.id === savedAuto.id);
      if (exists) {
        return prev.map((a) => (a.id === savedAuto.id ? savedAuto : a));
      }
      return [savedAuto, ...prev];
    });
  };

  // Callback after Status Toggle (Activate/Pause)
  const handleStatusChange = (updated: Automation) => {
    setAutomations((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
  };

  // Confirm Delete
  const handleConfirmDelete = async () => {
    if (!deletingAutomation) return;
    setIsDeleting(true);
    try {
      await apiClient.delete(`/automations/${deletingAutomation.id}`);
      toast.success(`Automation "${deletingAutomation.name}" deleted`);
      setAutomations((prev) => prev.filter((a) => a.id !== deletingAutomation.id));
      setIsDeleteModalOpen(false);
      setDeletingAutomation(null);
    } catch (err: any) {
      console.error('Failed to delete automation:', err);
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to delete automation');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fadeIn font-sans">
      <Toaster position="top-right" />

      {/* 1. Header & Primary Action */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <h1 className="text-xl md:text-2xl font-black text-slate-100 tracking-tight">
              Comment Automations
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              V1
            </span>
          </div>
          <p className="text-xs md:text-sm text-slate-400 max-w-2xl leading-relaxed">
            Automatically respond to comments and start conversations with people who engage with your posts.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={fetchData}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-slate-900/80 hover:bg-slate-800 border border-slate-800 text-slate-300 transition"
            title="Refresh Automations"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin text-indigo-400' : ''}`} />
          </button>

          <button
            type="button"
            onClick={handleOpenCreate}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition shadow-lg shadow-indigo-600/30 flex items-center space-x-2 group focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          >
            <Plus className="w-4 h-4 group-hover:rotate-90 transition-transform duration-200" />
            <span>Create Automation</span>
          </button>
        </div>
      </div>

      {/* 2. Metrics Summary Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {/* Total */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 shadow-sm flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 flex-shrink-0">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total</span>
            <p className="text-lg font-black text-slate-100">{metrics.total}</p>
          </div>
        </div>

        {/* Active */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 shadow-sm flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 flex items-center justify-center text-emerald-400 flex-shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Active</span>
            <p className="text-lg font-black text-emerald-400">{metrics.active}</p>
          </div>
        </div>

        {/* Paused */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 shadow-sm flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center text-amber-400 flex-shrink-0">
            <Pause className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Paused</span>
            <p className="text-lg font-black text-amber-400">{metrics.paused}</p>
          </div>
        </div>

        {/* Drafts */}
        <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800/80 shadow-sm flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-slate-400 flex-shrink-0">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Drafts</span>
            <p className="text-lg font-black text-slate-300">{metrics.drafts}</p>
          </div>
        </div>
      </div>

      {/* 3. Search & Filter Bar */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-sm flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by automation name or keyword..."
            className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex items-center space-x-2.5 flex-wrap gap-y-2">
          {/* Platform Filter */}
          <div className="relative">
            <select
              value={platformFilter}
              onChange={(e) => setPlatformFilter(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs font-semibold rounded-xl pl-3 pr-8 py-2 outline-none focus:border-indigo-500 appearance-none cursor-pointer"
            >
              <option value="ALL">All Platforms</option>
              <option value="instagram">Instagram</option>
              <option value="facebook">Facebook</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs font-semibold rounded-xl pl-3 pr-8 py-2 outline-none focus:border-indigo-500 appearance-none cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active</option>
              <option value="PAUSED">Paused</option>
              <option value="DRAFT">Draft</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>
      </div>

      {/* 4. Automations Content / List / Empty State */}
      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center space-y-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
          <p className="text-xs font-semibold">Loading comment automations...</p>
        </div>
      ) : fetchError ? (
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-5 h-5 text-rose-400 flex-shrink-0" />
            <span>{fetchError}</span>
          </div>
          <button
            type="button"
            onClick={fetchData}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-semibold text-xs transition"
          >
            Retry
          </button>
        </div>
      ) : automations.length === 0 ? (
        <AutomationEmptyState onCreateClick={handleOpenCreate} />
      ) : filteredAutomations.length === 0 ? (
        <div className="py-16 text-center text-slate-400 space-y-2 bg-slate-900/40 border border-slate-800/60 rounded-3xl p-8">
          <Filter className="w-8 h-8 mx-auto text-slate-600" />
          <p className="text-xs font-bold text-slate-200">No matching automations found</p>
          <p className="text-[11px] text-slate-500">Try adjusting your search query or filters.</p>
          <button
            type="button"
            onClick={() => {
              setSearchQuery('');
              setPlatformFilter('ALL');
              setStatusFilter('ALL');
            }}
            className="mt-2 text-xs font-semibold text-indigo-400 hover:underline"
          >
            Reset Filters
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredAutomations.map((auto) => (
            <AutomationCard
              key={auto.id}
              automation={auto}
              account={accountMap.get(auto.social_account_id)}
              onEdit={handleOpenEdit}
              onDelete={handleOpenDelete}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}

      {/* 5. Create / Edit Wizard Modal */}
      <AutomationWizardModal
        isOpen={isWizardOpen}
        editingAutomation={editingAutomation}
        socialAccounts={socialAccounts}
        onClose={() => {
          setIsWizardOpen(false);
          setEditingAutomation(null);
        }}
        onSuccess={handleWizardSuccess}
      />

      {/* 6. Delete Confirmation Modal */}
      <AutomationDeleteModal
        isOpen={isDeleteModalOpen}
        automation={deletingAutomation}
        isDeleting={isDeleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => {
          setIsDeleteModalOpen(false);
          setDeletingAutomation(null);
        }}
      />
    </div>
  );
}
