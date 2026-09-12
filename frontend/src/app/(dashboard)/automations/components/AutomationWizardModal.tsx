'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  X,
  Bot,
  Facebook,
  Instagram,
  ArrowRight,
  ArrowLeft,
  Check,
  Plus,
  Trash2,
  Image as ImageIcon,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Zap,
  AlertCircle,
  Loader2,
  ExternalLink,
  Layers,
  HelpCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import {
  Automation,
  AutomationPlatform,
  TriggerType,
  SocialAccount,
  PlatformPost,
  AutomationCreateInput,
  AutomationUpdateInput,
} from '@/lib/types';
import { apiClient } from '@/lib/api';
import PostPickerModal from './PostPickerModal';

export interface AutomationPrefillData {
  platform?: AutomationPlatform;
  social_account_id?: number | null;
  external_post_id?: string | null;
  post_title?: string | null;
  post_thumbnail?: string | null;
  name?: string;
  keywords?: string[];
  sample_comment?: string;
}

interface AutomationWizardModalProps {
  isOpen: boolean;
  editingAutomation: Automation | null;
  socialAccounts: SocialAccount[];
  initialValues?: AutomationPrefillData | null;
  onClose: () => void;
  onSuccess: (automation: Automation) => void;
}

export default function AutomationWizardModal({
  isOpen,
  editingAutomation,
  socialAccounts,
  initialValues,
  onClose,
  onSuccess,
}: AutomationWizardModalProps) {
  // Wizard Step (1 to 6)
  const [currentStep, setCurrentStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [platform, setPlatform] = useState<AutomationPlatform>('instagram');
  const [selectedAccountId, setSelectedAccountId] = useState<number | null>(null);

  // Target Post State (Real Platform Post)
  const [selectedPost, setSelectedPost] = useState<PlatformPost | null>(null);
  const [internalPostId, setInternalPostId] = useState<number | null>(null);
  const [externalPostId, setExternalPostId] = useState<string | null>(null);
  const [isPostPickerOpen, setIsPostPickerOpen] = useState(false);

  // Trigger State
  const [triggerType, setTriggerType] = useState<TriggerType>('KEYWORD');
  const [keywords, setKeywords] = useState<string[]>(['price', 'info', 'link']);
  const [keywordInput, setKeywordInput] = useState('');

  // Public Reply State
  const [publicReplyEnabled, setPublicReplyEnabled] = useState(true);
  const [variations, setVariations] = useState<string[]>([
    'Thanks for your comment! Check your DM 👋',
    'I just sent you the details in private message!',
  ]);

  // Private Message State
  const [privateMessageEnabled, setPrivateMessageEnabled] = useState(true);
  const [privateMessage, setPrivateMessage] = useState(
    "Hey! Thanks for your interest. Here's the information and direct link you asked for!"
  );

  // Prepopulate state if editing or prefilled
  useEffect(() => {
    if (!isOpen) return;

    if (editingAutomation) {
      setName(editingAutomation.name || '');
      setPlatform(editingAutomation.platform);
      setSelectedAccountId(editingAutomation.social_account_id);
      setInternalPostId(editingAutomation.internal_post_id);
      setExternalPostId(editingAutomation.external_post_id);
      setTriggerType((editingAutomation.trigger_type as TriggerType) || 'ANY_COMMENT');
      setKeywords(editingAutomation.trigger_config?.keywords || []);

      const pubReply = editingAutomation.action_config?.public_reply;
      setPublicReplyEnabled(pubReply?.enabled ?? false);
      setVariations(
        pubReply?.variations && pubReply.variations.length > 0
          ? pubReply.variations
          : ['Thanks for your comment! Check your DM 👋']
      );

      const privMsg = editingAutomation.action_config?.private_message;
      setPrivateMessageEnabled(privMsg?.enabled ?? false);
      setPrivateMessage(privMsg?.message || '');

      // Initialize selected post from editing automation
      if (editingAutomation.external_post_id) {
        setSelectedPost({
          id: editingAutomation.external_post_id,
          platform: editingAutomation.platform,
          internal_post_id: editingAutomation.internal_post_id,
        });

        // Optionally fetch richer details from Meta account if available
        if (editingAutomation.social_account_id) {
          apiClient
            .get<{ items: PlatformPost[] }>(
              `/social-accounts/${editingAutomation.social_account_id}/platform-posts`,
              { params: { limit: 50 } }
            )
            .then((res) => {
              const match = (res.data?.items || []).find(
                (p) => p.id === editingAutomation.external_post_id
              );
              if (match) setSelectedPost(match);
            })
            .catch((err) => console.error('Error fetching platform post for editing:', err));
        }
      }
      setCurrentStep(1);
    } else if (initialValues) {
      // Prefilled new automation from a comment
      setName(initialValues.name || (initialValues.sample_comment ? `Auto-Reply: "${initialValues.sample_comment.slice(0, 24)}..."` : 'New Comment Automation'));
      const targetPlat = initialValues.platform || 'instagram';
      setPlatform(targetPlat);
      const matchedAcc = initialValues.social_account_id
        ? socialAccounts.find((a) => a.id === initialValues.social_account_id)
        : (socialAccounts.find((a) => a.platform === targetPlat) || socialAccounts[0]);
      setSelectedAccountId(matchedAcc ? matchedAcc.id : null);
      
      if (initialValues.external_post_id) {
        setExternalPostId(initialValues.external_post_id);
        setSelectedPost({
          id: initialValues.external_post_id,
          platform: targetPlat,
          caption: initialValues.post_title || undefined,
          media_url: initialValues.post_thumbnail || undefined,
          thumbnail_url: initialValues.post_thumbnail || undefined,
        });
      } else {
        setSelectedPost(null);
        setExternalPostId(null);
      }
      setInternalPostId(null);
      setTriggerType('KEYWORD');
      setKeywords(initialValues.keywords && initialValues.keywords.length > 0 ? initialValues.keywords : ['price', 'info', 'link']);
      setKeywordInput('');
      setPublicReplyEnabled(true);
      setVariations([
        'Thanks for your comment! Check your DM 👋',
        'I just sent you the details in private message!',
      ]);
      setPrivateMessageEnabled(true);
      setPrivateMessage(
        "Hey! Thanks for your interest. Here's the information and direct link you asked for!"
      );
      setCurrentStep(1);
    } else {
      // Default new automation initialization
      setName('');
      setPlatform('instagram');
      const defaultAcc = socialAccounts.find((a) => a.platform === 'instagram') || socialAccounts[0];
      setSelectedAccountId(defaultAcc ? defaultAcc.id : null);
      setSelectedPost(null);
      setInternalPostId(null);
      setExternalPostId(null);
      setTriggerType('KEYWORD');
      setKeywords(['price', 'info', 'link']);
      setKeywordInput('');
      setPublicReplyEnabled(true);
      setVariations([
        'Thanks for your comment! Check your DM 👋',
        'I just sent you the details in private message!',
      ]);
      setPrivateMessageEnabled(true);
      setPrivateMessage(
        "Hey! Thanks for your interest. Here's the information and direct link you asked for!"
      );
      setCurrentStep(1);
    }
    setErrorMessage(null);
  }, [isOpen, editingAutomation, initialValues, socialAccounts]);

  if (!isOpen) return null;

  // Filter accounts by chosen platform
  const platformAccounts = socialAccounts.filter((acc) => acc.platform === platform);

  // Auto-select first account if selected is invalid for platform
  const handlePlatformChange = (newPlatform: AutomationPlatform) => {
    setPlatform(newPlatform);
    const validAccs = socialAccounts.filter((acc) => acc.platform === newPlatform);
    if (validAccs.length > 0) {
      setSelectedAccountId(validAccs[0].id);
    } else {
      setSelectedAccountId(null);
    }
    // Clear post selection on platform switch
    setSelectedPost(null);
    setInternalPostId(null);
    setExternalPostId(null);
  };

  // Keyword Helpers
  const handleAddKeyword = () => {
    const trimmed = keywordInput.trim().toLowerCase();
    if (!trimmed) return;
    if (keywords.includes(trimmed)) {
      toast.error('Keyword already added');
      return;
    }
    setKeywords([...keywords, trimmed]);
    setKeywordInput('');
  };

  const handleRemoveKeyword = (index: number) => {
    setKeywords(keywords.filter((_, i) => i !== index));
  };

  // Public Reply Helpers
  const handleAddVariation = () => {
    setVariations([...variations, '']);
  };

  const handleVariationChange = (index: number, val: string) => {
    const updated = [...variations];
    updated[index] = val;
    setVariations(updated);
  };

  const handleRemoveVariation = (index: number) => {
    if (variations.length <= 1) {
      toast.error('At least one variation is required when public reply is enabled');
      return;
    }
    setVariations(variations.filter((_, i) => i !== index));
  };

  // Step Validation Check
  const validateStep = (step: number): boolean => {
    setErrorMessage(null);
    if (step === 1) {
      if (!selectedAccountId) {
        setErrorMessage('Please select a connected social account.');
        return false;
      }
      return true;
    }

    if (step === 2) {
      if (!selectedPost && !externalPostId) {
        setErrorMessage('Please select a specific real platform post for this automation.');
        return false;
      }
      return true;
    }

    if (step === 3) {
      if (triggerType === 'KEYWORD') {
        const validKws = keywords.filter((k) => k.trim().length > 0);
        if (validKws.length === 0) {
          setErrorMessage('Please add at least one keyword for keyword matching.');
          return false;
        }
      }
      return true;
    }

    if (step === 4) {
      if (publicReplyEnabled) {
        const validVariations = variations.filter((v) => v.trim().length > 0);
        if (validVariations.length === 0) {
          setErrorMessage('Please provide at least one non-empty public reply variation.');
          return false;
        }
      }
      return true;
    }

    if (step === 5) {
      if (privateMessageEnabled) {
        if (!privateMessage.trim()) {
          setErrorMessage('Please enter a private message content.');
          return false;
        }
      }
      // Action Validation: at least one action must be enabled
      if (!publicReplyEnabled && !privateMessageEnabled) {
        setErrorMessage('Please enable at least one action (Public Reply or Private Message).');
        return false;
      }
      return true;
    }

    if (step === 6) {
      if (!name.trim()) {
        setErrorMessage('Please provide a name for this automation.');
        return false;
      }
      return true;
    }

    return true;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      if (currentStep === 5 && !name.trim()) {
        // Auto-generate a friendly default name if blank
        const postLabel = selectedPost?.caption
          ? selectedPost.caption.slice(0, 24) + '...'
          : selectedPost?.id || 'Post';
        setName(`${platform === 'facebook' ? 'Facebook' : 'Instagram'} - ${postLabel}`);
      }
      setCurrentStep((prev) => Math.min(prev + 1, 6));
    }
  };

  const handleBack = () => {
    setErrorMessage(null);
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  // Submit Handler
  const handleSubmit = async () => {
    if (!validateStep(6)) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    const cleanKeywords = keywords.map((k) => k.trim().toLowerCase()).filter(Boolean);
    const cleanVariations = variations.map((v) => v.trim()).filter(Boolean);

    try {
      if (editingAutomation) {
        // Update Payload
        const updatePayload: AutomationUpdateInput = {
          name: name.trim(),
          platform,
          social_account_id: selectedAccountId!,
          post_target_type: 'SPECIFIC_POST',
          internal_post_id: selectedPost?.internal_post_id ?? internalPostId,
          external_post_id: selectedPost?.id || externalPostId,
          trigger_type: triggerType,
          trigger_config: {
            keywords: triggerType === 'KEYWORD' ? cleanKeywords : [],
          },
          action_config: {
            public_reply: {
              enabled: publicReplyEnabled,
              variations: publicReplyEnabled ? cleanVariations : [],
            },
            private_message: {
              enabled: privateMessageEnabled,
              message: privateMessageEnabled ? privateMessage.trim() : null,
            },
          },
        };

        const res = await apiClient.patch<Automation>(
          `/automations/${editingAutomation.id}`,
          updatePayload
        );
        toast.success('Automation updated successfully!');
        onSuccess(res.data);
        onClose();
      } else {
        // Create Payload
        const createPayload: AutomationCreateInput = {
          name: name.trim(),
          platform,
          social_account_id: selectedAccountId!,
          post_target_type: 'SPECIFIC_POST',
          internal_post_id: selectedPost?.internal_post_id ?? null,
          external_post_id: selectedPost?.id || externalPostId || null,
          trigger_type: triggerType,
          trigger_config: {
            keywords: triggerType === 'KEYWORD' ? cleanKeywords : [],
          },
          action_config: {
            public_reply: {
              enabled: publicReplyEnabled,
              variations: publicReplyEnabled ? cleanVariations : [],
            },
            private_message: {
              enabled: privateMessageEnabled,
              message: privateMessageEnabled ? privateMessage.trim() : null,
            },
          },
        };

        const res = await apiClient.post<Automation>('/automations', createPayload);
        toast.success('Automation created as Draft!');
        onSuccess(res.data);
        onClose();
      }
    } catch (err: any) {
      console.error('Error saving automation:', err);
      const detail = err.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : 'Failed to save automation. Please check your inputs.';
      setErrorMessage(msg);
      toast.error(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const selectedAccountObj = socialAccounts.find((a) => a.id === selectedAccountId);

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-3 md:p-6 bg-black/80 backdrop-blur-md animate-fadeIn">
        <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-2xl w-full max-h-[92vh] flex flex-col shadow-2xl overflow-hidden relative">
          {/* Header */}
          <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between bg-slate-950/40">
            <div className="flex items-center space-x-3">
              <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-100">
                  {editingAutomation ? 'Edit Comment Automation' : 'Create Comment Automation'}
                </h2>
                <p className="text-[11px] text-slate-400">Step {currentStep} of 6</p>
              </div>
            </div>

            <button
              type="button"
              onClick={onClose}
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-xl hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Stepper Progress Bar */}
          <div className="w-full bg-slate-950 h-1.5 flex">
            {[1, 2, 3, 4, 5, 6].map((st) => (
              <div
                key={st}
                className={`flex-1 h-full transition-all duration-300 ${
                  st <= currentStep ? 'bg-indigo-500' : 'bg-slate-800'
                }`}
              />
            ))}
          </div>

          {/* Modal Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5 text-xs text-slate-200">
            {/* Error Banner */}
            {errorMessage && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center space-x-2.5">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-400" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* STEP 1: Platform & Account */}
            {currentStep === 1 && (
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Step 1: Choose Platform & Account</h3>
                  <p className="text-slate-400 text-xs mt-0.5">
                    Select the social platform and connected profile where this automation will listen for comments.
                  </p>
                </div>

                {/* Platform Selection */}
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Select Platform
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => handlePlatformChange('instagram')}
                      className={`p-4 rounded-2xl border flex items-center space-x-3 transition text-left select-none ${
                        platform === 'instagram'
                          ? 'bg-pink-950/40 border-pink-500 ring-2 ring-pink-500/30 text-white'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
                      }`}
                    >
                      <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600 flex items-center justify-center text-white flex-shrink-0 shadow-sm">
                        <Instagram className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="font-bold text-xs text-slate-100">Instagram</div>
                        <p className="text-[10px] text-slate-400">Post Comments & DMs</p>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => handlePlatformChange('facebook')}
                      className={`p-4 rounded-2xl border flex items-center space-x-3 transition text-left select-none ${
                        platform === 'facebook'
                          ? 'bg-blue-950/40 border-blue-500 ring-2 ring-blue-500/30 text-white'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 text-slate-300'
                      }`}
                    >
                      <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white flex-shrink-0 shadow-sm">
                        <Facebook className="w-5 h-5 fill-current" />
                      </div>
                      <div>
                        <div className="font-bold text-xs text-slate-100">Facebook</div>
                        <p className="text-[10px] text-slate-400">Page Comments & Messenger</p>
                      </div>
                    </button>
                  </div>
                </div>

                {/* Social Account Picker */}
                <div className="space-y-2 pt-2">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Connected Account
                  </label>

                  {platformAccounts.length === 0 ? (
                    <div className="p-5 rounded-2xl bg-slate-950 border border-slate-800 text-center space-y-3">
                      <p className="text-xs text-slate-400">
                        No connected {platform === 'facebook' ? 'Facebook Pages' : 'Instagram Accounts'} found.
                      </p>
                      <Link
                        href="/meta-connect"
                        className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                      >
                        <span>Connect {platform === 'facebook' ? 'Facebook' : 'Instagram'}</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {platformAccounts.map((acc) => {
                        const isSelected = selectedAccountId === acc.id;
                        return (
                          <div
                            key={acc.id}
                            onClick={() => setSelectedAccountId(acc.id)}
                            className={`p-3.5 rounded-2xl border flex items-center justify-between transition cursor-pointer select-none ${
                              isSelected
                                ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                                : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                            }`}
                          >
                            <div className="flex items-center space-x-3 min-w-0">
                              <div
                                className={`w-9 h-9 rounded-full flex items-center justify-center text-white text-xs font-bold ${
                                  platform === 'facebook'
                                    ? 'bg-blue-600'
                                    : 'bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600'
                                }`}
                              >
                                {platform === 'facebook' ? (
                                  <Facebook className="w-4 h-4 fill-current" />
                                ) : (
                                  <Instagram className="w-4 h-4" />
                                )}
                              </div>
                              <div className="min-w-0">
                                <p className="font-bold text-xs text-slate-100 truncate">
                                  {acc.account_name}
                                </p>
                                <p className="text-[10px] text-slate-400 font-mono truncate">
                                  ID: {acc.account_id}
                                </p>
                              </div>
                            </div>

                            <div className="flex items-center space-x-2">
                              {isSelected && (
                                <span className="w-5 h-5 rounded-full bg-indigo-500 flex items-center justify-center text-white">
                                  <Check className="w-3.5 h-3.5 stroke-[3]" />
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* STEP 2: Target Post */}
            {currentStep === 2 && (
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Step 2: Choose Target Post</h3>
                  <p className="text-slate-400 text-xs mt-0.5">
                    This automation will listen for incoming comments on this specific platform post.
                  </p>
                </div>

                {selectedPost ? (
                  <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/50 space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex gap-3 min-w-0">
                        <div className="w-16 h-16 rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex-shrink-0 flex items-center justify-center">
                          {selectedPost.thumbnail_url || selectedPost.media_url ? (
                            <img
                              src={selectedPost.thumbnail_url || selectedPost.media_url}
                              alt="Post"
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <ImageIcon className="w-6 h-6 text-slate-600" />
                          )}
                        </div>
                        <div className="min-w-0 space-y-1">
                          <span className="font-bold text-xs text-slate-100 truncate block">
                            {platform === 'instagram' ? 'Instagram Media' : 'Facebook Post'}
                          </span>
                          <p className="text-[11px] text-slate-300 line-clamp-2">
                            {selectedPost.caption || 'No caption text'}
                          </p>
                          <div className="space-y-0.5 pt-0.5">
                            <span className="text-[10px] font-mono text-indigo-400 block truncate">
                              {platform === 'instagram' ? 'Instagram Media ID: ' : 'Facebook Post ID: '}
                              <span className="text-slate-100 font-bold">{selectedPost.id}</span>
                            </span>
                            {selectedPost.internal_post_id ? (
                              <span className="text-[9px] font-mono text-emerald-400 block">
                                Local Post: #{selectedPost.internal_post_id}
                              </span>
                            ) : null}
                          </div>
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => setIsPostPickerOpen(true)}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition flex-shrink-0"
                      >
                        Change Post
                      </button>
                    </div>

                    <div className="p-2.5 rounded-xl bg-indigo-900/30 border border-indigo-800/40 text-[11px] text-indigo-300 flex items-center space-x-2">
                      <ShieldCheck className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span>This automation will listen for comments on this exact platform post.</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 rounded-2xl bg-slate-950/60 border border-dashed border-slate-800 text-center space-y-3">
                    <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto text-slate-500">
                      <ImageIcon className="w-6 h-6" />
                    </div>
                    <div>
                      <p className="text-xs font-bold text-slate-200">No Post Selected</p>
                      <p className="text-[11px] text-slate-400 max-w-sm mx-auto mt-0.5">
                        Select any real published post directly from your connected {platform === 'facebook' ? 'Facebook Page' : 'Instagram Account'}.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setIsPostPickerOpen(true)}
                      className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-md shadow-indigo-600/30"
                    >
                      Browse {platform === 'facebook' ? 'Facebook' : 'Instagram'} Posts
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* STEP 3: Trigger */}
            {currentStep === 3 && (
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Step 3: Trigger Configuration</h3>
                  <p className="text-slate-400 text-xs mt-0.5">
                    Define when this automation should be triggered by a commenter.
                  </p>
                </div>

                <div className="space-y-3">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    When should this automation run?
                  </label>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div
                      onClick={() => setTriggerType('KEYWORD')}
                      className={`p-4 rounded-2xl border transition cursor-pointer select-none space-y-1 ${
                        triggerType === 'KEYWORD'
                          ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-slate-100">Comment contains a keyword</span>
                        {triggerType === 'KEYWORD' && <Check className="w-4 h-4 text-indigo-400" />}
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Trigger only when the comment mentions specific target words.
                      </p>
                    </div>

                    <div
                      onClick={() => setTriggerType('ANY_COMMENT')}
                      className={`p-4 rounded-2xl border transition cursor-pointer select-none space-y-1 ${
                        triggerType === 'ANY_COMMENT'
                          ? 'bg-indigo-950/40 border-indigo-500 ring-2 ring-indigo-500/30'
                          : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-slate-100">Any comment</span>
                        {triggerType === 'ANY_COMMENT' && <Check className="w-4 h-4 text-indigo-400" />}
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Trigger for every comment posted on the selected post.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Keyword Editor */}
                {triggerType === 'KEYWORD' && (
                  <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 animate-fadeIn">
                    <label className="text-xs font-semibold text-slate-200">
                      Target Keywords ({keywords.length})
                    </label>

                    {/* Tag list */}
                    <div className="flex flex-wrap gap-2">
                      {keywords.map((kw, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 text-xs font-semibold"
                        >
                          <span>{kw}</span>
                          <button
                            type="button"
                            onClick={() => handleRemoveKeyword(idx)}
                            className="hover:text-rose-400 transition"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </span>
                      ))}
                    </div>

                    {/* Add Keyword Input */}
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={keywordInput}
                        onChange={(e) => setKeywordInput(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ',') {
                            e.preventDefault();
                            handleAddKeyword();
                          }
                        }}
                        placeholder="Type keyword and press Enter (e.g. price, link)..."
                        className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={handleAddKeyword}
                        className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition flex items-center space-x-1"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add</span>
                      </button>
                    </div>

                    <p className="text-[11px] text-slate-500 flex items-center space-x-1.5">
                      <HelpCircle className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                      <span>Keywords are matched without case sensitivity.</span>
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* STEP 4: Public Reply */}
            {currentStep === 4 && (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">Step 4: Public Reply</h3>
                    <p className="text-slate-400 text-xs mt-0.5">
                      Automatically post a public reply to the comment under your post.
                    </p>
                  </div>

                  {/* Toggle Switch */}
                  <button
                    type="button"
                    onClick={() => setPublicReplyEnabled(!publicReplyEnabled)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                      publicReplyEnabled ? 'bg-indigo-600' : 'bg-slate-800'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        publicReplyEnabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                {publicReplyEnabled ? (
                  <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3.5 animate-fadeIn">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-slate-200">
                        Reply Variations ({variations.length})
                      </label>
                      <button
                        type="button"
                        onClick={handleAddVariation}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center space-x-1"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Variation</span>
                      </button>
                    </div>

                    <div className="space-y-2.5">
                      {variations.map((variation, idx) => (
                        <div key={idx} className="flex items-center gap-2">
                          <input
                            type="text"
                            value={variation}
                            onChange={(e) => handleVariationChange(idx, e.target.value)}
                            placeholder={`Variation #${idx + 1} (e.g. Thanks for asking! Check your DM 👋)`}
                            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-3.5 py-2.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                          />
                          {variations.length > 1 && (
                            <button
                              type="button"
                              onClick={() => handleRemoveVariation(idx)}
                              className="text-slate-500 hover:text-rose-400 p-2 rounded-lg transition"
                              title="Delete variation"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    <p className="text-[11px] text-slate-400 flex items-center space-x-1.5 pt-1">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
                      <span>Multiple variations help keep replies from feeling repetitive.</span>
                    </p>
                  </div>
                ) : (
                  <div className="p-6 rounded-2xl bg-slate-950/40 border border-slate-800/60 text-center text-slate-400 text-xs">
                    Public reply is disabled. No public comment will be posted.
                  </div>
                )}
              </div>
            )}

            {/* STEP 5: Private Message */}
            {currentStep === 5 && (
              <div className="space-y-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">Step 5: Private Message</h3>
                    <p className="text-slate-400 text-xs mt-0.5">
                      Send a private direct message to the person who commented.
                    </p>
                  </div>

                  {/* Toggle Switch */}
                  <button
                    type="button"
                    onClick={() => setPrivateMessageEnabled(!privateMessageEnabled)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none ${
                      privateMessageEnabled ? 'bg-indigo-600' : 'bg-slate-800'
                    }`}
                  >
                    <span
                      className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                        privateMessageEnabled ? 'translate-x-6' : 'translate-x-1'
                      }`}
                    />
                  </button>
                </div>

                {privateMessageEnabled ? (
                  <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 animate-fadeIn">
                    <label className="text-xs font-semibold text-slate-200">Direct Message Content</label>
                    <textarea
                      rows={4}
                      value={privateMessage}
                      onChange={(e) => setPrivateMessage(e.target.value)}
                      placeholder="Hey! Thanks for your interest. Here's the information you asked for..."
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none leading-relaxed"
                    />

                    <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-amber-300 flex items-start space-x-2">
                      <HelpCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                      <span>
                        Message delivery will become active when the automation execution engine is enabled in Phase 3+.
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 rounded-2xl bg-slate-950/40 border border-slate-800/60 text-center text-slate-400 text-xs">
                    Private direct message is disabled.
                  </div>
                )}
              </div>
            )}

            {/* STEP 6: Review & Finalize */}
            {currentStep === 6 && (
              <div className="space-y-5">
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Step 6: Review Automation</h3>
                  <p className="text-slate-400 text-xs mt-0.5">
                    Review your automation configuration before saving.
                  </p>
                </div>

                {/* Name Input */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Automation Name
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Price Inquiry Auto-Responder"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs font-semibold text-slate-100 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                {/* Review Card */}
                <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3.5">
                  {/* Platform & Account */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                    <span className="text-slate-400">Platform & Account</span>
                    <span className="font-semibold text-slate-200 flex items-center space-x-1.5">
                      {platform === 'facebook' ? (
                        <Facebook className="w-3.5 h-3.5 text-blue-400 fill-current" />
                      ) : (
                        <Instagram className="w-3.5 h-3.5 text-pink-400" />
                      )}
                      <span>{selectedAccountObj?.account_name || 'Account'}</span>
                    </span>
                  </div>

                  {/* Target Post */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                    <span className="text-slate-400">Target Post</span>
                    <span className="font-semibold text-slate-200 truncate max-w-[260px] text-right">
                      {selectedPost ? (
                        <span>
                          {platform === 'instagram' ? 'IG Media ' : 'FB Post '}
                          <span className="font-mono text-indigo-300">{selectedPost.id}</span>
                          {selectedPost.internal_post_id ? (
                            <span className="text-[10px] text-emerald-400 ml-1.5 font-normal">(Local #{selectedPost.internal_post_id})</span>
                          ) : null}
                        </span>
                      ) : externalPostId ? (
                        <span className="font-mono text-indigo-300">{externalPostId}</span>
                      ) : (
                        'None'
                      )}
                    </span>
                  </div>

                  {/* Trigger */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                    <span className="text-slate-400">Trigger</span>
                    <span className="font-semibold text-slate-200">
                      {triggerType === 'ANY_COMMENT'
                        ? 'Any comment'
                        : `Keywords: ${keywords.join(', ')}`}
                    </span>
                  </div>

                  {/* Public Reply */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                    <span className="text-slate-400">Public Reply</span>
                    <span
                      className={`font-semibold ${
                        publicReplyEnabled ? 'text-emerald-400' : 'text-slate-500'
                      }`}
                    >
                      {publicReplyEnabled
                        ? `✓ Enabled (${variations.length} variations)`
                        : 'Disabled'}
                    </span>
                  </div>

                  {/* Private Message */}
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
                    <span className="text-slate-400">Private Message</span>
                    <span
                      className={`font-semibold ${
                        privateMessageEnabled ? 'text-emerald-400' : 'text-slate-500'
                      }`}
                    >
                      {privateMessageEnabled ? '✓ Enabled' : 'Disabled'}
                    </span>
                  </div>

                  {/* Initial Status */}
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Initial Status</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                      {editingAutomation ? editingAutomation.status : 'DRAFT'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Modal Footer Controls */}
          <div className="px-6 py-4 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
            <button
              type="button"
              onClick={currentStep === 1 ? onClose : handleBack}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs transition flex items-center space-x-1.5 disabled:opacity-50"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>{currentStep === 1 ? 'Cancel' : 'Back'}</span>
            </button>

            {currentStep < 6 ? (
              <button
                type="button"
                onClick={handleNext}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition flex items-center space-x-1.5 shadow-md shadow-indigo-600/30"
              >
                <span>Continue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <button
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
                className="px-6 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition flex items-center space-x-2 shadow-lg shadow-indigo-600/30 disabled:opacity-50"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>{editingAutomation ? 'Update Automation' : 'Create Automation'}</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Embedded Post Picker Modal */}
      <PostPickerModal
        isOpen={isPostPickerOpen}
        socialAccountId={selectedAccountId}
        platform={platform}
        selectedPostId={selectedPost?.id || externalPostId}
        onSelectPost={(p) => {
          setSelectedPost(p);
          setExternalPostId(p.id);
          setInternalPostId(p.internal_post_id ?? null);
        }}
        onClose={() => setIsPostPickerOpen(false)}
      />
    </>
  );
}
