'use client';

import React from 'react';
import { 
  TrendingUp, 
  Users, 
  Eye, 
  Heart, 
  MessageSquare, 
  Share2, 
  Send, 
  AlertCircle,
  Calendar,
  Sparkles
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  BarChart,
  Bar,
  CartesianGrid,
} from 'recharts';

const dailyTrendsData = [
  { day: 'Mon', reach: 2400, impressions: 3800, engagement: 310 },
  { day: 'Tue', reach: 3100, impressions: 4600, engagement: 420 },
  { day: 'Wed', reach: 4500, impressions: 6200, engagement: 590 },
  { day: 'Thu', reach: 5200, impressions: 7800, engagement: 740 },
  { day: 'Fri', reach: 6800, impressions: 9400, engagement: 890 },
  { day: 'Sat', reach: 8100, impressions: 11200, engagement: 1150 },
  { day: 'Sun', reach: 9600, impressions: 13500, engagement: 1380 },
];

const platformBreakdown = [
  { platform: 'Instagram Business', posts: 24, engagement: '9.2%' },
  { platform: 'Facebook Page', posts: 18, engagement: '7.8%' },
];

export default function AnalyticsDashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center space-x-2">
            <TrendingUp className="w-5 h-5 text-indigo-400" />
            <span>Social Performance & Analytics</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time Meta Graph API reach, impressions, engagement rates, and growth metrics.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-xl text-xs font-semibold text-slate-300 flex items-center space-x-2">
            <Calendar className="w-4 h-4 text-indigo-400" />
            <span>Last 7 Days</span>
          </div>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Reach */}
        <div className="glass-panel p-5 rounded-2xl space-y-2 border-l-4 border-indigo-500">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Reach</span>
            <Users className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h3 className="text-2xl font-black text-white">39,700</h3>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              +18.4%
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Unique accounts reached across FB & IG</p>
        </div>

        {/* Total Impressions */}
        <div className="glass-panel p-5 rounded-2xl space-y-2 border-l-4 border-purple-500">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Impressions</span>
            <Eye className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h3 className="text-2xl font-black text-white">56,500</h3>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              +24.1%
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Total post views and screen feeds</p>
        </div>

        {/* Avg Engagement Rate */}
        <div className="glass-panel p-5 rounded-2xl space-y-2 border-l-4 border-pink-500">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Avg Engagement</span>
            <Heart className="w-4 h-4 text-pink-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h3 className="text-2xl font-black text-white">8.6%</h3>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              +3.2%
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Likes, comments & saves ratio</p>
        </div>

        {/* Total Interactions */}
        <div className="glass-panel p-5 rounded-2xl space-y-2 border-l-4 border-cyan-500">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-medium">Total Interactions</span>
            <MessageSquare className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline justify-between">
            <h3 className="text-2xl font-black text-white">5,480</h3>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              +12.8%
            </span>
          </div>
          <p className="text-[11px] text-slate-500">Likes, comments & shares combined</p>
        </div>
      </div>

      {/* Visual Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Reach & Impression Trend Chart */}
        <div className="lg:col-span-8 glass-panel p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Reach & Impression Trends</h3>
              <p className="text-xs text-slate-400">Daily trajectory of organic & AI boosted reach</p>
            </div>
            <div className="flex items-center space-x-4 text-xs">
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded-full bg-indigo-500" />
                <span className="text-slate-300">Reach</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="w-3 h-3 rounded-full bg-purple-500" />
                <span className="text-slate-300">Impressions</span>
              </div>
            </div>
          </div>

          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={dailyTrendsData}>
                <defs>
                  <linearGradient id="reachGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366F1" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#6366F1" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="impGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#A855F7" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#A855F7" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                <XAxis dataKey="day" stroke="#64748B" fontSize={12} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={12} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    borderColor: '#374151',
                    borderRadius: '0.75rem',
                    color: '#fff',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="reach"
                  stroke="#6366F1"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#reachGrad)"
                />
                <Area
                  type="monotone"
                  dataKey="impressions"
                  stroke="#A855F7"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#impGrad)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Engagement Distribution Bar Chart */}
        <div className="lg:col-span-4 glass-panel p-6 rounded-2xl space-y-4">
          <h3 className="text-sm font-bold text-white">Daily Interactions</h3>
          <p className="text-xs text-slate-400">Total likes, comments & shares per day</p>

          <div className="h-72 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyTrendsData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" vertical={false} />
                <XAxis dataKey="day" stroke="#64748B" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748B" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#111827',
                    borderColor: '#374151',
                    borderRadius: '0.75rem',
                  }}
                />
                <Bar dataKey="engagement" fill="#06B6D4" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
