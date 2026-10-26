import React, { useState, useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Select } from '../ui/Select';
import { agentsApi } from '../../services/api/agents';
import { useToast } from '../../app/providers/ToastProvider';
import { ProviderType } from '../../types/api';
import {
  PhoneCall,
  Volume2,
  Bot,
  AlertCircle,
  ArrowUpRight,
  Laptop,
  Phone,
  Mic,
  MicOff,
  Send,
  RotateCcw,
  Play,
  Zap,
  Activity,
  CheckCircle2,
} from 'lucide-react';
import { apiClient, getErrorMessage } from '../../services/api/client';
import { Link } from 'react-router-dom';

export interface QuickDialModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialAgentId?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  audioBase64?: string;
  metrics?: {
    stt_ms?: number;
    llm_ttfb_ms?: number;
    llm_total_ms?: number;
    tts_ms?: number;
    total_ms?: number;
  };
}

// -------------------------------------------------------------
// Native 16kHz WAV Recorder (Zero Internet, Zero External Libs)
// -------------------------------------------------------------
class WavRecorder {
  private audioCtx: AudioContext | null = null;
  private mediaStream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private pcmChunks: Float32Array[] = [];

  async start() {
    this.pcmChunks = [];
    this.mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    this.audioCtx = new AudioContextClass({ sampleRate: 16000 });
    const source = this.audioCtx.createMediaStreamSource(this.mediaStream);
    this.processor = this.audioCtx.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (e) => {
      const channelData = e.inputBuffer.getChannelData(0);
      this.pcmChunks.push(new Float32Array(channelData));
    };
    source.connect(this.processor);
    this.processor.connect(this.audioCtx.destination);
  }

  stop(): Blob {
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((t) => t.stop());
      this.mediaStream = null;
    }
    if (this.audioCtx) {
      this.audioCtx.close();
      this.audioCtx = null;
    }

    let totalLength = 0;
    for (const chunk of this.pcmChunks) totalLength += chunk.length;
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of this.pcmChunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Wrap into 16-bit PCM WAV
    const buffer = new ArrayBuffer(44 + merged.length * 2);
    const view = new DataView(buffer);

    const writeStr = (v: DataView, off: number, s: string) => {
      for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i));
    };

    writeStr(view, 0, 'RIFF');
    view.setUint32(4, 36 + merged.length * 2, true);
    writeStr(view, 8, 'WAVE');
    writeStr(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, 16000, true); // 16kHz
    view.setUint32(28, 16000 * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(view, 36, 'data');
    view.setUint32(40, merged.length * 2, true);

    let p = 44;
    for (let i = 0; i < merged.length; i++) {
      const s = Math.max(-1, Math.min(1, merged[i]));
      view.setInt16(p, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      p += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
  }
}

export const QuickDialModal: React.FC<QuickDialModalProps> = ({
  isOpen,
  onClose,
  initialAgentId,
}) => {
  // Modal Mode: 'local' (laptop test) or 'phone' (real call)
  const [activeTab, setActiveTab] = useState<'local' | 'phone'>('local');

  // Phone Call State
  const [phoneNumber, setPhoneNumber] = useState('');
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [provider, setProvider] = useState<ProviderType>('vobiz');
  const [language, setLanguage] = useState('English');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const toast = useToast();

  // Local Voice Test State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [typedMessage, setTypedMessage] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [sessionStarted, setSessionStarted] = useState(false);

  const recorderRef = useRef<WavRecorder | null>(null);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const chatScrollRef = useRef<HTMLDivElement | null>(null);

  const {
    data: agents = [],
    refetch,
    isLoading,
  } = useQuery({
    queryKey: ['agents'],
    queryFn: () => agentsApi.getAgents(100),
    staleTime: 0,
    refetchOnMount: 'always',
  });

  // Listen to global quick dial events
  useEffect(() => {
    const handleQuickDial = (e: Event) => {
      const customEvent = e as CustomEvent<{ agentId?: string }>;
      if (customEvent.detail?.agentId) {
        setSelectedAgentId(customEvent.detail.agentId);
      }
    };
    window.addEventListener('voxora-quick-dial', handleQuickDial);
    return () => window.removeEventListener('voxora-quick-dial', handleQuickDial);
  }, []);

  // Set initial agent or refetch when modal opens
  useEffect(() => {
    if (isOpen) {
      refetch();
    } else {
      // Clean up audio when modal closes
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
      if (recorderRef.current && isRecording) {
        try {
          recorderRef.current.stop();
        } catch {}
        setIsRecording(false);
      }
    }
  }, [isOpen, refetch]);

  // Handle agent selection synchronization
  useEffect(() => {
    if (!isOpen || agents.length === 0) return;

    if (initialAgentId && agents.some((a) => (a.agent_id || a.id) === initialAgentId)) {
      setSelectedAgentId(initialAgentId);
      const ag = agents.find((a) => (a.agent_id || a.id) === initialAgentId);
      if (ag?.default_language) setLanguage(ag.default_language);
      return;
    }

    const lastSelected = sessionStorage.getItem('last_selected_agent_id');
    if (lastSelected && agents.some((a) => (a.agent_id || a.id) === lastSelected)) {
      setSelectedAgentId(lastSelected);
      const ag = agents.find((a) => (a.agent_id || a.id) === lastSelected);
      if (ag?.default_language) setLanguage(ag.default_language);
      return;
    }

    const currentExists = agents.some((a) => (a.agent_id || a.id) === selectedAgentId);
    if (!selectedAgentId || !currentExists) {
      const topAgent = agents[0];
      const topId = topAgent.agent_id || topAgent.id || '';
      setSelectedAgentId(topId);
      if (topAgent.default_language) {
        setLanguage(topAgent.default_language);
      }
    }
  }, [isOpen, agents, initialAgentId, selectedAgentId]);

  // Auto-scroll chat box
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages, isProcessing]);

  const selectedAgent = agents.find((ag) => (ag.agent_id || ag.id) === selectedAgentId);

  // Play audio helper
  const playAudio = (base64Audio: string) => {
    if (!base64Audio) return;
    try {
      if (currentAudioRef.current) {
        currentAudioRef.current.pause();
      }
      const audio = new Audio(`data:audio/wav;base64,${base64Audio}`);
      currentAudioRef.current = audio;
      setIsPlayingAudio(true);
      audio.onended = () => setIsPlayingAudio(false);
      audio.onerror = () => setIsPlayingAudio(false);
      audio.play().catch((e) => {
        console.warn('Audio play notice:', e);
        setIsPlayingAudio(false);
      });
    } catch (e) {
      console.warn('Error playing audio:', e);
      setIsPlayingAudio(false);
    }
  };

  // Start Local Voice Session (play greeting)
  const handleStartLocalSession = async () => {
    if (!selectedAgentId) return;
    setIsProcessing(true);
    setSessionStarted(true);
    setChatMessages([]);

    try {
      const resp = await apiClient.post('/api/v1/voice/test-greeting', {
        agent_id: selectedAgentId,
      });
      const data = resp.data;

      const greetingMsg: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'assistant',
        text: data.greeting_text || 'नमस्ते! बताइए, मैं आपकी क्या सहायता कर सकता हूँ?',
        audioBase64: data.audio_base64,
        metrics: data.metrics,
      };

      setChatMessages([greetingMsg]);
      if (data.audio_base64) {
        playAudio(data.audio_base64);
      }
    } catch (err: any) {
      toast.error('Failed to start local test', getErrorMessage(err));
      setSessionStarted(false);
    } finally {
      setIsProcessing(false);
    }
  };

  // Send turn (either audio Blob or text)
  const sendTurn = async (audioBlob?: Blob, textInput?: string) => {
    if (!selectedAgentId) return;
    if (!audioBlob && !textInput?.trim()) return;

    setIsProcessing(true);

    // Optimistically add user message if text
    if (textInput?.trim()) {
      setChatMessages((prev) => [
        ...prev,
        { id: `user-${Date.now()}`, role: 'user', text: textInput.trim() },
      ]);
      setTypedMessage('');
    }

    try {
      const formData = new FormData();
      formData.append('agent_id', selectedAgentId);
      if (textInput?.trim()) {
        formData.append('text', textInput.trim());
      }
      if (audioBlob) {
        formData.append('audio', audioBlob, 'mic.wav');
      }

      // History for multi-turn context
      const history = chatMessages.map((m) => ({
        role: m.role,
        content: m.text,
      }));
      formData.append('history', JSON.stringify(history));

      const resp = await apiClient.post('/api/v1/voice/test-turn', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data = resp.data;

      // If speech was transcribed from audio, add the user bubble
      if (audioBlob && data.user_text) {
        setChatMessages((prev) => [
          ...prev,
          { id: `user-${Date.now()}`, role: 'user', text: data.user_text },
        ]);
      }

      // Add assistant reply
      const assistantMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        text: data.agent_reply,
        audioBase64: data.audio_base64,
        metrics: data.metrics,
      };

      setChatMessages((prev) => [...prev, assistantMsg]);

      // Play audio response directly on laptop speakers
      if (data.audio_base64) {
        playAudio(data.audio_base64);
      }
    } catch (err: any) {
      toast.error('Voice Turn Processing Error', getErrorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  };

  // Toggle Microphone Record
  const handleToggleMic = async () => {
    if (!sessionStarted) {
      await handleStartLocalSession();
      return;
    }

    if (isRecording) {
      // Stop recording and send audio
      try {
        if (recorderRef.current) {
          const blob = recorderRef.current.stop();
          setIsRecording(false);
          await sendTurn(blob);
        }
      } catch (err: any) {
        setIsRecording(false);
        toast.error('Recording Error', err.message || 'Could not record microphone');
      }
    } else {
      // Start recording
      try {
        if (currentAudioRef.current) {
          currentAudioRef.current.pause();
          setIsPlayingAudio(false);
        }
        recorderRef.current = new WavRecorder();
        await recorderRef.current.start();
        setIsRecording(true);
      } catch (err: any) {
        toast.error('Microphone Access Denied', 'Please allow microphone access in your browser to test.');
      }
    }
  };

  // Phone Call Outbound Submit
  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phoneNumber.trim()) {
      toast.error('Phone number is required');
      return;
    }
    if (!selectedAgentId) {
      toast.error('Please select an agent');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await agentsApi.startCalls(selectedAgentId, {
        phone_numbers: [phoneNumber.trim()],
        concurrency: 1,
        provider,
        language,
      });
      toast.success('Call Initiated', `Dispatched call to ${phoneNumber} (${res.status})`);
      setPhoneNumber('');
      onClose();
    } catch (err: any) {
      toast.error('Failed to initiate call', getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Quick Call & Voice Test"
      description="Test voice agents instantly on your laptop or place an outbound carrier call."
      size="lg"
    >
      {agents.length === 0 && !isLoading ? (
        <div className="py-6 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-amber-500/10 dark:bg-amber-400/10 text-amber-500 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-zinc-100">
              No Voice Agents Available
            </h4>
            <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 max-w-xs mx-auto">
              You need at least one configured AI voice agent before placing outbound test calls.
            </p>
          </div>
          <Link
            to="/agents"
            onClick={onClose}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-orange-500 text-white hover:bg-orange-600 shadow-md shadow-orange-500/20 transition-all"
          >
            Create Agent in Agents Tab
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Dual Mode Switcher Tabs */}
          <div className="flex p-1 bg-slate-100 dark:bg-white/[0.04] rounded-xl border border-slate-200/80 dark:border-white/[0.08]">
            <button
              type="button"
              onClick={() => setActiveTab('local')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'local'
                  ? 'bg-white dark:bg-zinc-800 text-orange-600 dark:text-orange-400 shadow-sm border border-slate-200/60 dark:border-white/[0.08]'
                  : 'text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Laptop className="w-3.5 h-3.5" />
              <span>💻 Test on Laptop (0% Internet)</span>
              <span className="hidden sm:inline-block px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 font-mono">
                Offline
              </span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('phone')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeTab === 'phone'
                  ? 'bg-white dark:bg-zinc-800 text-orange-600 dark:text-orange-400 shadow-sm border border-slate-200/60 dark:border-white/[0.08]'
                  : 'text-slate-600 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              <Phone className="w-3.5 h-3.5" />
              <span>📞 Phone Call (VoBiz / Cellular)</span>
            </button>
          </div>

          {/* ========================================================= */}
          {/* TAB 1: LOCAL LAPTOP VOICE TEST (ZERO INTERNET / MIC + SPK) */}
          {/* ========================================================= */}
          {activeTab === 'local' && (
            <div className="space-y-4">
              {/* Agent Picker & Latency Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 p-3 rounded-xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/[0.08]">
                <div className="flex-1 min-w-0">
                  <label className="text-[10px] font-semibold text-slate-400 dark:text-neutral-400 uppercase tracking-wider block mb-1">
                    Select Agent to Test
                  </label>
                  <select
                    value={selectedAgentId}
                    onChange={(e) => {
                      setSelectedAgentId(e.target.value);
                      setSessionStarted(false);
                      setChatMessages([]);
                    }}
                    className="w-full text-xs font-medium bg-transparent border-0 text-slate-900 dark:text-white focus:outline-none cursor-pointer"
                  >
                    {agents.map((ag) => (
                      <option key={ag.agent_id || ag.id} value={ag.agent_id || ag.id} className="dark:bg-zinc-900">
                        {ag.name} ({ag.default_language || 'Hindi'})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    100% Local GPU (Offline)
                  </span>
                  {sessionStarted && (
                    <button
                      type="button"
                      onClick={handleStartLocalSession}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:hover:text-white hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-colors"
                      title="Restart conversation"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>

              {/* Conversation Box */}
              {!sessionStarted ? (
                <div className="py-8 px-4 text-center rounded-2xl border-2 border-dashed border-slate-200 dark:border-white/[0.08] bg-slate-50/50 dark:bg-white/[0.01] space-y-3">
                  <div className="w-12 h-12 rounded-full bg-orange-500/10 text-orange-500 flex items-center justify-center mx-auto shadow-inner">
                    <Laptop className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-slate-800 dark:text-zinc-100">
                      Direct Laptop Voice Simulation
                    </h4>
                    <p className="text-xs text-slate-500 dark:text-neutral-400 mt-1 max-w-sm mx-auto">
                      Test <strong>{selectedAgent?.name || 'Agent'}</strong> using your laptop's microphone and speakers. Zero phone network latency, zero Ngrok relay, 100% offline local GPU inference.
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    onClick={handleStartLocalSession}
                    isLoading={isProcessing}
                    leftIcon={<Play className="w-3.5 h-3.5 fill-current" />}
                  >
                    Start Laptop Voice Test
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {/* Chat bubbles container */}
                  <div
                    ref={chatScrollRef}
                    className="h-64 overflow-y-auto p-3.5 rounded-2xl bg-slate-100/70 dark:bg-black/30 border border-slate-200/80 dark:border-white/[0.08] space-y-3"
                  >
                    {chatMessages.map((msg) => {
                      const isAsst = msg.role === 'assistant';
                      return (
                        <div
                          key={msg.id}
                          className={`flex flex-col ${isAsst ? 'items-start' : 'items-end'}`}
                        >
                          <div className="flex items-center gap-1.5 mb-1 px-1">
                            <span className="text-[10px] font-semibold text-slate-400 dark:text-neutral-500">
                              {isAsst ? selectedAgent?.name || 'AI Assistant' : 'You (Microphone)'}
                            </span>
                            {isAsst && msg.metrics && (
                              <span className="inline-flex items-center gap-1 text-[9px] font-mono px-1.5 py-0.5 rounded-md bg-orange-500/10 text-orange-500 dark:text-orange-400 font-semibold border border-orange-500/20">
                                <Zap className="w-2.5 h-2.5" />
                                {msg.metrics.total_ms ? `${(msg.metrics.total_ms / 1000).toFixed(2)}s` : 'fast'}
                              </span>
                            )}
                          </div>
                          <div
                            className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed shadow-sm ${
                              isAsst
                                ? 'bg-white dark:bg-zinc-800 text-slate-800 dark:text-zinc-100 border border-slate-200/80 dark:border-white/[0.08]'
                                : 'bg-gradient-to-r from-orange-500 to-orange-600 text-white font-medium'
                            }`}
                          >
                            <p>{msg.text}</p>
                            {/* Latency Breakdown Pill & Replay Button */}
                            {isAsst && msg.metrics && (
                              <div className="mt-2 pt-1.5 border-t border-slate-100 dark:border-white/[0.08] flex items-center justify-between gap-2 text-[10px] text-slate-400 dark:text-neutral-400 font-mono">
                                <span>
                                  {msg.metrics.stt_ms ? `STT: ${msg.metrics.stt_ms}ms | ` : ''}
                                  LLM: {msg.metrics.llm_ttfb_ms || msg.metrics.llm_total_ms || 0}ms | TTS: {msg.metrics.tts_ms || 0}ms
                                </span>
                                {msg.audioBase64 && (
                                  <button
                                    type="button"
                                    onClick={() => playAudio(msg.audioBase64!)}
                                    className="p-1 rounded hover:bg-slate-100 dark:hover:bg-white/[0.1] text-orange-500 hover:text-orange-600 transition-colors"
                                    title="Replay Audio"
                                  >
                                    <Volume2 className="w-3 h-3" />
                                  </button>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {isProcessing && (
                      <div className="flex items-center gap-2 text-xs text-orange-500 font-medium py-1 animate-pulse">
                        <Activity className="w-4 h-4 animate-spin" />
                        <span>Processing locally on RTX 4060 GPU (STT → LLM → TTS)...</span>
                      </div>
                    )}
                  </div>

                  {/* Audio Status & Interactive Mic / Input Bar */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleToggleMic}
                      disabled={isProcessing}
                      className={`relative flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-xs transition-all shadow-md cursor-pointer select-none ${
                        isRecording
                          ? 'bg-rose-500 hover:bg-rose-600 text-white animate-pulse shadow-rose-500/30'
                          : 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-400 hover:to-orange-500 text-white shadow-orange-500/20'
                      }`}
                    >
                      {isRecording ? (
                        <>
                          <MicOff className="w-4 h-4 animate-bounce" />
                          <span>Stop & Send Voice</span>
                        </>
                      ) : (
                        <>
                          <Mic className="w-4 h-4" />
                          <span>Push to Speak</span>
                        </>
                      )}
                    </button>

                    {/* Text input alternative */}
                    <div className="flex-1 flex items-center gap-1.5 bg-slate-100 dark:bg-white/[0.04] border border-slate-200/80 dark:border-white/[0.08] rounded-xl px-2.5 py-1">
                      <input
                        type="text"
                        value={typedMessage}
                        onChange={(e) => setTypedMessage(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            if (typedMessage.trim() && !isProcessing) {
                              sendTurn(undefined, typedMessage);
                            }
                          }
                        }}
                        placeholder="Or type Hindi/English text..."
                        disabled={isProcessing || isRecording}
                        className="flex-1 text-xs bg-transparent border-0 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none"
                      />
                      <button
                        type="button"
                        onClick={() => {
                          if (typedMessage.trim() && !isProcessing) {
                            sendTurn(undefined, typedMessage);
                          }
                        }}
                        disabled={!typedMessage.trim() || isProcessing}
                        className="p-1 rounded-lg text-orange-500 hover:text-orange-600 disabled:opacity-30 disabled:pointer-events-none transition-colors"
                      >
                        <Send className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================= */}
          {/* TAB 2: OUTBOUND PHONE CALL (VOBIZ TELEPHONY) */}
          {/* ========================================================= */}
          {activeTab === 'phone' && (
            <form onSubmit={handlePhoneSubmit} className="flex flex-col gap-4">
              <Input
                label="Phone Number"
                placeholder="+919876543210"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                required
                helperText="Include full country code (e.g. +91 for India)"
                leftIcon={<PhoneCall className="w-4 h-4 text-slate-400" />}
              />

              <div className="space-y-1.5">
                <Select
                  label="Select AI Agent"
                  value={selectedAgentId}
                  onChange={(e) => {
                    const newId = e.target.value;
                    setSelectedAgentId(newId);
                    sessionStorage.setItem('last_selected_agent_id', newId);
                    const found = agents.find((ag) => (ag.agent_id || ag.id) === newId);
                    if (found?.default_language) {
                      setLanguage(found.default_language);
                    }
                  }}
                  required
                >
                  {agents.map((ag) => {
                    const id = ag.agent_id || ag.id;
                    const voice = ag.voice_name ? ` • ${ag.voice_name}` : '';
                    const engine = ag.tts_provider ? ` [${ag.tts_provider.toUpperCase()}]` : '';
                    return (
                      <option key={id} value={id}>
                        {ag.name} ({ag.default_language || 'English'}{voice}{engine})
                      </option>
                    );
                  })}
                </Select>

                {selectedAgent && (
                  <div className="p-3 rounded-xl bg-slate-50 dark:bg-white/[0.03] border border-slate-200/80 dark:border-white/[0.08] text-[11px] space-y-1.5">
                    <div className="flex items-center justify-between text-slate-600 dark:text-neutral-400">
                      <span className="flex items-center gap-1.5 font-medium text-slate-800 dark:text-neutral-200">
                        <Bot className="w-3.5 h-3.5 text-orange-400" />
                        {selectedAgent.name}
                      </span>
                      <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-neutral-200 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 border border-transparent dark:border-white/[0.06]">
                        {selectedAgent.tts_provider || 'dograh'} TTS
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-slate-500 dark:text-neutral-400">
                      <Volume2 className="w-3 h-3 text-slate-400" />
                      <span className="truncate">
                        Voice: <strong>{selectedAgent.voice_name || 'Standard Voice'}</strong>
                        {selectedAgent.speaking_speed && ` (${selectedAgent.speaking_speed}x speed)`}
                      </span>
                    </div>
                    {selectedAgent.purpose && (
                      <p className="text-slate-500 dark:text-neutral-400 line-clamp-1 italic">
                        "{selectedAgent.purpose}"
                      </p>
                    )}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <Select
                  label="Telephony Carrier"
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as ProviderType)}
                >
                  <option value="vobiz">VoBiz (Active Carrier - +918065354620)</option>
                  <option value="twilio">Twilio (US/Global - +13344895368)</option>
                  <option value="plivo">Plivo</option>
                </Select>

                <Select
                  label="Dialect / Language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                >
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Hinglish">Hinglish</option>
                  <option value="Marathi">Marathi</option>
                  <option value="Tamil">Tamil</option>
                  <option value="Telugu">Telugu</option>
                  <option value="Kannada">Kannada</option>
                  <option value="Bengali">Bengali</option>
                  <option value="Gujarati">Gujarati</option>
                </Select>
              </div>

              <div className="flex items-center justify-end gap-2.5 pt-4 border-t border-slate-100 dark:border-zinc-800 mt-2">
                <Button variant="ghost" size="sm" onClick={onClose} disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  isLoading={isSubmitting}
                >
                  Start Call Now
                </Button>
              </div>
            </form>
          )}
        </div>
      )}
    </Modal>
  );
};
