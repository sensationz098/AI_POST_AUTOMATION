'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Bot, Mail, Lock, ArrowRight, ShieldCheck, KeyRound, AlertCircle } from 'lucide-react';
import { apiClient } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fillTestCredentials = () => {
    setEmail('testadmin@socialai.com');
    setPassword('TestAdmin123!');
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const res = await apiClient.post('/auth/login', {
        email: email.trim(),
        password,
      });

      if (res.data?.access_token) {
        localStorage.setItem('social_ai_token', res.data.access_token);
        if (res.data?.user_id) {
          localStorage.setItem('social_ai_user', JSON.stringify({
            id: res.data.user_id,
            email: res.data.email,
            full_name: res.data.full_name,
            role: res.data.role,
          }));
        }
        apiClient.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`;
        router.push('/studio');
      } else {
        setError('Authentication response did not return an access token.');
      }
    } catch (err: any) {
      console.error('Login error:', err);
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg || 'Invalid input').join(', '));
      } else {
        setError('Failed to connect to authentication server. Please check backend status.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] flex items-center justify-center p-4 font-sans select-none transition-colors duration-150">
      <div className="w-full max-w-md space-y-6">
        {/* Branding */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--accent-color)] text-xs font-semibold">
            <Bot className="w-4 h-4 text-[var(--accent-color)]" />
            <span>Sensationz Publishing Studio</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            Welcome Back
          </h1>
          <p className="text-xs text-[var(--text-secondary)]">
            Sign in to manage AI workflows & Meta Graph publishing
          </p>
        </div>

        {/* Card */}
        <div className="pub-card p-6 space-y-5">
          {/* Quick Test Credentials Box */}
          <div className="p-3.5 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-xs font-bold text-[var(--accent-color)]">
                <KeyRound className="w-4 h-4 text-[var(--accent-color)]" />
                <span>Test Credentials Ready</span>
              </div>
              <button
                type="button"
                onClick={fillTestCredentials}
                className="btn-secondary text-[11px] py-1 px-2.5"
              >
                <span>1-Click Fill</span>
              </button>
            </div>
            <div className="text-[11px] text-[var(--text-secondary)] font-mono space-y-0.5 pt-1 border-t border-[var(--border-color)]">
              <p><span className="text-[var(--text-tertiary)]">Email:</span> testadmin@socialai.com</p>
              <p><span className="text-[var(--text-tertiary)]">Pass:</span> TestAdmin123!</p>
            </div>
          </div>

          {/* Error Alert */}
          {error && (
            <div className="p-3 rounded bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--danger-color)] text-xs flex items-start space-x-2">
              <AlertCircle className="w-4 h-4 text-[var(--danger-color)] shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Email Address
              </label>
              <div className="relative flex items-center">
                <Mail className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3.5 pointer-events-none z-10" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@socialai.com"
                  className="input-field w-full !pl-10"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-[var(--text-secondary)]">
                Password
              </label>
              <div className="relative flex items-center">
                <Lock className="w-4 h-4 text-[var(--text-tertiary)] absolute left-3.5 pointer-events-none z-10" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="input-field w-full !pl-10"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full text-xs py-2.5 space-x-2"
            >
              {isLoading ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center text-xs text-[var(--text-secondary)] border-t border-[var(--border-color)]">
            <span>Don't have an account yet? </span>
            <Link href="/register" className="font-semibold text-[var(--accent-color)] hover:underline">
              Create New Account
            </Link>
          </div>
        </div>

        {/* Footer info */}
        <div className="space-y-2 text-center text-[11px] text-[var(--text-tertiary)]">
          <div className="flex items-center justify-center space-x-2">
            <ShieldCheck className="w-3.5 h-3.5 text-[var(--success-color)]" />
            <span>Encrypted JWT Token & Role-Based Security</span>
          </div>
        </div>
      </div>
    </div>
  );
}
