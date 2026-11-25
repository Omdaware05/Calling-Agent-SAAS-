import React, { useMemo, useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import {
  PhoneCall,
  Target,
  Heart,
  Clock,
  Download,
  Plus,
  ArrowRight,
  CalendarClock,
  BarChart3,
  Building2,
} from 'lucide-react';
import { statsApi } from '../../services/api/stats';
import { leadsApi } from '../../services/api/leads';
import { agentsApi } from '../../services/api/agents';
import { callsApi } from '../../services/api/calls';
import { useBusiness } from '../../app/providers/BusinessProvider';
import { useActiveCalls } from '../../hooks/useActiveCalls';
import { useToast } from '../../app/providers/ToastProvider';
import type { CallDocument, LeadDocument } from '../../types/api';
import { MCard, MStatCard, Avatar, Pill, ScoreBar, scorePct, leadStatusMeta, fmtDuration, timeAgo, primaryPill, whitePill } from './ui';
import { parseServerDate } from '../../utils/dateUtils';

/* ---------- date bucketing helpers ---------- */
function dayKey(d: Date): string {
  return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
}

function lastNDays(n: number): { key: string; label: string }[] {
  const out: { key: string; label: string }[] = [];
  const now = new Date();
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(now.getDate() - i);
    out.push({
      key: dayKey(d),
      label: d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
    });
  }
  return out;
}

function bucketize<T extends { created_at: string }>(items: T[], days: { key: string; label: string }[]) {
  const counts = new Map(days.map((d) => [d.key, 0]));
  for (const it of items) {
    const d = parseServerDate(it.created_at);
    if (d) {
      const k = dayKey(d);
      if (counts.has(k)) counts.set(k, (counts.get(k) || 0) + 1);
    }
  }
  return days.map((d) => counts.get(d.key) || 0);
}

function pctChange(series: number[]): number | null {
  const n = series.length;
  const cur = series.slice(n - 7).reduce((a, b) => a + b, 0);
  const prev = series.slice(n - 14, n - 7).reduce((a, b) => a + b, 0);
  if (prev === 0) return cur > 0 ? 100 : null;
  return ((cur - prev) / prev) * 100;
}

/* Optional Web Audio DTMF beep on keypad press */
function playTone(freq1: number, freq2: number) {
  try {
    const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc1 = ctx.createOscillator();
    const osc2 = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.value = 0.04;
    osc1.frequency.value = freq1;
    osc2.frequency.value = freq2;
    osc1.connect(gain);
    osc2.connect(gain);
    gain.connect(ctx.destination);
    osc1.start();
    osc2.start();
    setTimeout(() => {
      osc1.stop();
      osc2.stop();
      ctx.close();
    }, 70);
  } catch (e) {
    // AudioContext might be blocked until user gesture, ignore silently
  }
}

const DTMF_FREQS: Record<string, [number, number]> = {
  '1': [697, 1209], '2': [697, 1336], '3': [697, 1477],
  '4': [770, 1209], '5': [770, 1336], '6': [770, 1477],
  '7': [852, 1209], '8': [852, 1336], '9': [852, 1477],
  '*': [941, 1209], '0': [941, 1336], '#': [941, 1477],
};

export const ModernDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { selectedBusiness, selectedBusinessId, isAllBusinesses } = useBusiness();
  const { activeCalls } = useActiveCalls();

  // Softphone Interactive State
  const [dialNumber, setDialNumber] = useState('98765 43210');
  const [selectedPersona, setSelectedPersona] = useState('Priya Sharma (Mumbai Line)');
  const [languageMode, setLanguageMode] = useState<'Auto' | 'Hinglish' | 'Hindi' | 'English'>('Auto');
  const [callDurationSeconds, setCallDurationSeconds] = useState(427); // 07:07 start
  const [isMuted, setIsMuted] = useState(false);
  const [isLiveStreaming, setIsLiveStreaming] = useState(true);
  const [whisperOpen, setWhisperOpen] = useState(false);
  const [whisperText, setWhisperText] = useState('');
  const [callStatusMessage, setCallStatusMessage] = useState<string | null>(null);

  const toast = useToast();

  // Live timer tick
  useEffect(() => {
    if (!isLiveStreaming) return;
    const interval = setInterval(() => {
      setCallDurationSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [isLiveStreaming]);

  const fmtTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleKeypadPress = (key: string) => {
    if (DTMF_FREQS[key]) {
      playTone(DTMF_FREQS[key][0], DTMF_FREQS[key][1]);
    }
    setDialNumber((prev) => prev + key);
  };

  const handleClear = () => {
    setDialNumber((prev) => prev.slice(0, -1));
  };

  const handleInitiateCall = async () => {
    if (!dialNumber.trim()) return;
    const cleaned = dialNumber.replace(/\s+/g, '');
    const fullNumber = cleaned.startsWith('+') ? cleaned : `+91${cleaned.replace(/^\+?91/, '')}`;

    const agent = agents[0];
    if (agent) {
      try {
        setCallStatusMessage('Initiating carrier connection...');
        await agentsApi.startCalls(agent.agent_id || (agent as any).id, {
          phone_numbers: [fullNumber],
          concurrency: 1,
          provider: 'vobiz',
          language: languageMode === 'Auto' ? 'Hindi' : languageMode,
        });
        setCallStatusMessage(`Call dispatched to ${fullNumber}!`);
        toast.success('Call Initiated', `Dispatched call to ${fullNumber}`);
        setTimeout(() => setCallStatusMessage(null), 3500);
      } catch (err: any) {
        window.dispatchEvent(new CustomEvent('voxora-quick-dial'));
        setCallStatusMessage(null);
      }
    } else {
      window.dispatchEvent(new CustomEvent('voxora-quick-dial'));
    }
  };

  // Queries
  const { data: stats } = useQuery({
    queryKey: ['global-stats', selectedBusinessId],
    queryFn: () => statsApi.getStats(isAllBusinesses ? undefined : selectedBusinessId),
    refetchInterval: 15000,
  });
  const { data: leads = [] } = useQuery<LeadDocument[]>({
    queryKey: ['leads', selectedBusinessId],
    queryFn: () => leadsApi.getLeads({ limit: 500 }),
    refetchInterval: 15000,
  });
  const { data: agents = [] } = useQuery({
    queryKey: ['agents', selectedBusinessId],
    queryFn: () => agentsApi.getAgents(50),
  });
  const { data: calls = [] } = useQuery<CallDocument[]>({
    queryKey: ['modern-calls', selectedBusinessId],
    queryFn: () => callsApi.getCalls({ limit: 200 }),
    refetchInterval: 15000,
  });

  // Scope calls, leads and agents to selected business
  const scopedCalls = useMemo(() => {
    if (isAllBusinesses || !selectedBusiness) return calls;
    const assignedSet = new Set(selectedBusiness.assignedAgentIds || []);
    return calls.filter((c) => {
      if ((c as any).tenant_id && (c as any).tenant_id === selectedBusiness.id) return true;
      if ((c as any).business_id && (c as any).business_id === selectedBusiness.id) return true;
      if (c.agent_id && assignedSet.has(c.agent_id)) return true;
      return false;
    });
  }, [calls, selectedBusiness, isAllBusinesses]);

  const scopedLeads = useMemo(() => {
    if (isAllBusinesses || !selectedBusiness) return leads;
    const assignedSet = new Set(selectedBusiness.assignedAgentIds || []);
    return leads.filter((l) => {
      if (l.tenant_id && l.tenant_id === selectedBusiness.id) return true;
      if (l.agent_id && assignedSet.has(l.agent_id)) return true;
      return false;
    });
  }, [leads, selectedBusiness, isAllBusinesses]);

  const days = useMemo(() => lastNDays(14), []);
  const callsPerDay = useMemo(() => bucketize(scopedCalls, days), [scopedCalls, days]);
  const leadsPerDay = useMemo(() => bucketize(scopedLeads, days), [scopedLeads, days]);
  const activity = days.map((d, i) => ({ ...d, Calls: callsPerDay[i], Leads: leadsPerDay[i] }));

  const interested = scopedLeads.filter((l) => ['interested', 'qualified'].includes((l.status || '').toLowerCase())).length;
  const interestedRate = scopedLeads.length ? Math.round((interested / scopedLeads.length) * 100) : 0;

  const completedCount = isAllBusinesses ? (stats?.completed || 0) : scopedCalls.filter(c => c.state === 'COMPLETED').length;
  const failedCount = isAllBusinesses ? (stats?.failed || 0) : scopedCalls.filter(c => c.state === 'FAILED').length;
  const busyCount = isAllBusinesses ? (stats?.busy || 0) : scopedCalls.filter(c => c.state === 'BUSY').length;
  const noAnswerCount = isAllBusinesses ? (stats?.no_answer || 0) : scopedCalls.filter(c => c.state === 'NO_ANSWER').length;

  const outcomeData = [
    { name: 'Completed', value: completedCount, color: '#10B981' },
    { name: 'Failed', value: failedCount, color: '#F43F5E' },
    { name: 'Busy', value: busyCount, color: '#F59E0B' },
    { name: 'No answer', value: noAnswerCount, color: '#C4CBD4' },
  ];
  const outcomeTotal = outcomeData.reduce((a, b) => a + b.value, 0);

  const kpis = [
    {
      label: 'Total Calls',
      value: (isAllBusinesses ? (stats?.total_calls ?? calls.length) : scopedCalls.length).toLocaleString('en-IN'),
      icon: PhoneCall,
      iconClass: 'bg-slate-50 text-slate-800 border border-slate-200',
      deltaPct: pctChange(callsPerDay),
    },
    {
      label: 'Leads Captured',
      value: scopedLeads.length.toLocaleString('en-IN'),
      icon: Target,
      iconClass: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
      deltaPct: pctChange(leadsPerDay),
    },
    {
      label: 'Interested Rate',
      value: `${interestedRate}%`,
      icon: Heart,
      iconClass: 'bg-purple-50 text-purple-700 border border-purple-200',
      subtext: `${interested} of ${scopedLeads.length} leads`,
    },
    {
      label: 'Avg. Call Duration',
      value: fmtDuration(stats?.average_duration_seconds),
      icon: Clock,
      iconClass: 'bg-blue-50 text-blue-700 border border-blue-200',
      subtext: 'per completed call',
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* MAIN DUAL-COLUMN WORKSPACE */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: INTERACTIVE SOFTPHONE & DIALER (xl:col-span-5) */}
        <div className="xl:col-span-5 flex flex-col gap-5">
          <div className="bg-white rounded-xl p-6 shadow-xs flex flex-col gap-5 border border-slate-200/90">
            {/* Softphone Header */}
            <div className="flex items-center justify-between pb-1">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-headline-sm text-slate-900 text-lg font-bold">Interactive Softphone</h2>
                  <span className="px-2 py-0.5 bg-slate-100 text-slate-700 font-label-xs text-[10px] rounded font-semibold">
                    LIVE RTP
                  </span>
                </div>
                <p className="font-body-sm text-slate-500 text-xs mt-0.5">AI Outbound &amp; Inbound Call Console</p>
              </div>
              <div className="h-8 w-8 rounded-full bg-slate-50 flex items-center justify-center text-slate-600 border border-slate-200/70">
                <span className="material-symbols-outlined text-base">dialpad</span>
              </div>
            </div>

            {/* Phone Input */}
            <div className="flex flex-col gap-1.5">
              <div className="flex items-center bg-slate-50 border border-slate-300 rounded-lg p-1.5 focus-within:bg-white focus-within:ring-2 focus-within:ring-slate-900 transition-all">
                <div className="relative flex items-center pl-2 pr-1">
                  <span className="text-xs">🇮🇳</span>
                  <span className="font-code-metric text-slate-900 font-semibold text-xs ml-1.5">+91</span>
                </div>
                <div className="h-5 w-px bg-slate-200 mx-1.5"></div>
                <input
                  className="w-full bg-transparent px-2 font-code-metric text-slate-900 text-base tracking-wider focus:outline-none"
                  id="dialerDisplay"
                  placeholder="Enter number..."
                  type="text"
                  value={dialNumber}
                  onChange={(e) => setDialNumber(e.target.value)}
                />
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-1 text-slate-400 hover:text-slate-900 transition-colors cursor-pointer"
                  title="Backspace / Clear"
                >
                  <span className="material-symbols-outlined text-base">backspace</span>
                </button>
              </div>
            </div>

            {/* Keypad Grid */}
            <div className="grid grid-cols-3 gap-2 py-1">
              {[
                { key: '1', sub: '\u00A0' },
                { key: '2', sub: 'ABC' },
                { key: '3', sub: 'DEF' },
                { key: '4', sub: 'GHI' },
                { key: '5', sub: 'JKL' },
                { key: '6', sub: 'MNO' },
                { key: '7', sub: 'PQRS' },
                { key: '8', sub: 'TUV' },
                { key: '9', sub: 'WXYZ' },
                { key: '*', sub: 'TONE' },
                { key: '0', sub: '+' },
                { key: '#', sub: 'HASH' },
              ].map((btn) => (
                <button
                  key={btn.key}
                  type="button"
                  onClick={() => handleKeypadPress(btn.key)}
                  className="keypad-btn flex flex-col items-center justify-center py-2.5 bg-white hover:bg-slate-50 active:bg-slate-100 border border-slate-200/80 rounded-lg shadow-xs transition-all cursor-pointer"
                >
                  <span className="font-title-md text-slate-900 leading-none font-semibold text-base">
                    {btn.key}
                  </span>
                  <span className="text-[9px] text-slate-400 mt-0.5 tracking-wider font-mono-sm">
                    {btn.sub}
                  </span>
                </button>
              ))}
            </div>

            {/* Single Persona & Carrier Selector */}
            <div className="flex flex-col gap-1">
              <div className="flex items-center justify-between">
                <label className="font-label-xs uppercase tracking-wider text-slate-500 text-[11px] font-semibold">
                  Agent Persona &amp; Line
                </label>
                <span className="flex items-center gap-1 font-label-xs text-emerald-700 text-[11px] font-medium">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Prompt Synced
                </span>
              </div>
              <div className="relative">
                <select
                  value={selectedPersona}
                  onChange={(e) => setSelectedPersona(e.target.value)}
                  className="w-full appearance-none bg-slate-50 hover:bg-slate-100 py-2 pl-3 pr-8 rounded-lg font-body-sm text-slate-900 text-xs focus:outline-none transition-colors cursor-pointer border border-slate-200"
                >
                  <option>Priya Sharma (Mumbai Line)</option>
                  <option>Aryan Verma (Delhi Line)</option>
                  <option>Direct Browser Softphone</option>
                  {agents.map((a) => (
                    <option key={a.agent_id} value={a.name}>
                      {a.name} ({(a as any).default_language || (a as any).language || 'Multi-Indic'})
                    </option>
                  ))}
                </select>
                <span className="material-symbols-outlined text-slate-400 absolute right-2.5 top-2 pointer-events-none text-base">
                  unfold_more
                </span>
              </div>
            </div>

            {/* Clean Segmented Language Control */}
            <div className="flex flex-col gap-1">
              <label className="font-label-xs uppercase tracking-wider text-slate-500 text-[11px] font-semibold">
                Language Mode
              </label>
              <div className="grid grid-cols-4 gap-1 p-1 bg-slate-100 rounded-lg text-center font-label-xs text-xs">
                {(['Auto', 'Hinglish', 'Hindi', 'English'] as const).map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => setLanguageMode(lang)}
                    className={clsx(
                      'py-1 rounded transition-all font-medium',
                      languageMode === lang
                        ? 'bg-white text-slate-900 font-semibold shadow-xs'
                        : 'text-slate-600 hover:text-slate-900'
                    )}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            </div>

            {/* Call Status Feedback */}
            {callStatusMessage && (
              <div className="p-2 bg-emerald-50 text-emerald-800 text-xs font-medium rounded-md border border-emerald-200 text-center animate-fade-in">
                {callStatusMessage}
              </div>
            )}

            {/* Primary Action Buttons */}
            <div className="flex flex-col gap-2 pt-1">
              <button
                type="button"
                onClick={handleInitiateCall}
                className="w-full py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-label-md flex items-center justify-center gap-2 shadow-xs transition-all group cursor-pointer active:scale-[0.99]"
                id="launchCallBtn"
              >
                <span className="material-symbols-outlined text-base group-hover:animate-pulse">call</span>
                <span className="tracking-wide font-semibold text-sm">Initiate AI Voice Call</span>
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => navigate('/calendar')}
                  className="py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-slate-700 font-label-md text-xs rounded-lg flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm text-slate-400">calendar_today</span>
                  <span>Schedule</span>
                </button>
                <button
                  type="button"
                  onClick={() => navigate('/calls')}
                  className="py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200/80 text-slate-700 font-label-md text-xs rounded-lg flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm text-slate-400">upload_file</span>
                  <span>Batch CSV</span>
                </button>
              </div>
            </div>
          </div>

          {/* Agent Profile & MOS Performance Card */}
          <div className="bg-white rounded-xl p-4 shadow-xs flex items-center justify-between border border-slate-200/90">
            <div className="flex items-center gap-3">
              <img
                className="w-10 h-10 rounded-full object-cover border border-slate-200"
                alt="Priya Sharma"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuA8mLeY67C7L6YRStUB91ZsSNmw3_dQ5mByOsyK1NOKTaypHRrpUdoPrlp6iPRt6gAdZMRbaWd5a7MTmnSQxuTDSBFHpuVkQCBdLKVW5TEzg-4Kd2ngiICJn0NY-nlr280v_8rasQy_D3xa4tHBdAVQpVvFXuSsg-txY0e9vbzFIeBKzcOZeNxYD97n2BQVGhRrF2pCP_1YH0EGZMjhY67kGH7FYg5aPOw0rMlP5l1y"
              />
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <span className="font-title-sm text-sm text-slate-900 font-semibold">Priya Sharma</span>
                  <span className="px-1.5 py-0.5 bg-emerald-50 text-emerald-700 font-label-xs text-[10px] rounded font-medium">
                    99.4% Match
                  </span>
                </div>
                <span className="text-xs text-slate-500">Voice: Warm &amp; Professional</span>
              </div>
            </div>
            <div className="text-right">
              <span className="font-label-xs uppercase tracking-wider text-slate-400 block text-[10px] font-semibold">
                Rating
              </span>
              <span className="font-title-sm text-slate-900 font-semibold text-sm">
                4.8 <span className="text-xs text-slate-400 font-normal">/ 5.0</span>
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: ACTIVE LIVE CALL STREAMING CONSOLE (xl:col-span-7) */}
        <div className="xl:col-span-7 flex flex-col gap-5">
          <div className="bg-white rounded-xl shadow-xs flex flex-col border border-slate-200/90 overflow-hidden">
            {/* Live Call Status Bar */}
            <div className="p-5 flex flex-wrap items-center justify-between gap-3 bg-slate-50/70 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <span className="flex h-3 w-3 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-title-md text-slate-900 font-semibold text-base">
                      Connected: +91 98765 43210
                    </span>
                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 font-label-xs rounded font-semibold tracking-wider text-[10px]">
                      LIVE STREAMING
                    </span>
                  </div>
                  <span className="font-body-sm text-slate-500 text-xs">Rohit Sharma (Admissions Lead #8841)</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200/80 rounded-lg shadow-2xs font-code-metric text-slate-900">
                  <span className="material-symbols-outlined text-sm text-slate-400">timer</span>
                  <span className="font-semibold text-sm" id="callDuration">
                    {fmtTimer(callDurationSeconds)}
                  </span>
                </div>
                <div className="flex items-center gap-1 px-2.5 py-1.5 bg-white border border-slate-200/80 rounded-lg shadow-2xs font-code-metric text-xs text-slate-600">
                  <span className="material-symbols-outlined text-xs text-emerald-600">bolt</span>
                  <span>168ms RTT</span>
                </div>
              </div>
            </div>

            {/* DUAL AUDIO WAVEFORM EQUALIZER */}
            <div className="p-5 flex flex-col gap-4 border-b border-slate-100">
              {/* Track 1: AI Speech Output */}
              <div className="p-3 bg-slate-50/80 rounded-lg border border-slate-100 flex flex-col gap-1.5">
                <div className="flex items-center justify-between font-label-xs">
                  <span className="font-medium text-xs text-slate-900 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-sm text-slate-900">record_voice_over</span>
                    AI Voice (Priya)
                  </span>
                  <span className="text-[11px] font-code-metric text-emerald-600 font-medium">Speaking</span>
                </div>
                <div className="flex items-end gap-1 h-8 w-full overflow-hidden px-1">
                  <span className="w-1.5 bg-slate-900 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-4 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-7 anim-eq-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-8 anim-eq-3"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-6 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-5 anim-eq-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-3 anim-eq-3"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-7 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-8 anim-eq-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-4 anim-eq-3"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-6 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-8 anim-eq-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-5 anim-eq-3"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-3 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-6 anim-eq-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-7 anim-eq-3"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-4 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-3 anim-eq-2"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-5 anim-eq-3"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-6 anim-eq-1"></span>
                  <span className="w-1.5 bg-slate-900 rounded-full h-2"></span>
                </div>
              </div>

              {/* Track 2: Caller Inbound Audio */}
              <div className="p-3 bg-slate-50/80 rounded-lg border border-slate-100 flex flex-col gap-1.5">
                <div className="flex items-center justify-between font-label-xs">
                  <span className="font-medium text-xs text-slate-500 flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-sm text-slate-400">hearing</span>
                    Caller (Rohit)
                  </span>
                  <span className="text-[11px] font-code-metric text-slate-500 font-medium">Listening</span>
                </div>
                <div className="flex items-end gap-1 h-5 w-full overflow-hidden px-1">
                  <span className="w-1.5 bg-slate-300 rounded-full h-1.5"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-3"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-4"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-1.5"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-4"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-1.5"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-3"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-4"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-3"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-1.5"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-4"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-1.5"></span>
                  <span className="w-1.5 bg-slate-400 rounded-full h-3"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-1.5"></span>
                  <span className="w-1.5 bg-slate-300 rounded-full h-2"></span>
                </div>
              </div>
            </div>

            {/* LIVE DIALOGUE TRANSCRIPTION STREAM */}
            <div className="p-5 flex flex-col gap-3 border-b border-slate-100">
              <div className="flex items-center justify-between pb-1">
                <span className="font-label-xs uppercase tracking-wider text-slate-500 text-[11px] font-semibold">
                  Live Transcript
                </span>
                <span className="font-code-metric text-[11px] text-slate-500">
                  Latency: <strong className="text-slate-900 font-semibold">112ms</strong>
                </span>
              </div>
              <div className="flex flex-col gap-2.5 max-h-56 overflow-y-auto pr-1">
                {/* Turn 1 */}
                <div className="flex gap-2.5 items-start">
                  <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center shrink-0 text-slate-800 font-bold text-xs border border-slate-200">
                    P
                  </div>
                  <div className="flex flex-col gap-0.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-900">Priya (AI)</span>
                      <span className="font-code-metric text-[10px] text-slate-400">00:04</span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200/70 px-3 py-2 rounded-lg rounded-tl-none font-body-sm text-xs text-slate-900 leading-normal">
                      "Namaste Rohit ji! Calling from Apex University regarding your B.Tech inquiry. Do you have a quick minute?"
                    </div>
                  </div>
                </div>

                {/* Turn 2 */}
                <div className="flex gap-2.5 items-start">
                  <div className="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center shrink-0 text-slate-900 font-bold text-xs border border-slate-300">
                    R
                  </div>
                  <div className="flex flex-col gap-0.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-900">Rohit (Caller)</span>
                      <span className="font-code-metric text-[10px] text-slate-400">00:19</span>
                    </div>
                    <div className="bg-white border border-slate-200 shadow-2xs px-3 py-2 rounded-lg rounded-tl-none font-body-sm text-xs text-slate-900 leading-normal">
                      "Yes Priya! Could you tell me about the scholarship cutoff and fee structure?"
                    </div>
                  </div>
                </div>

                {/* Turn 3 */}
                <div className="flex gap-2.5 items-start">
                  <div className="w-6 h-6 rounded-full bg-slate-100 flex items-center justify-center shrink-0 text-slate-800 font-bold text-xs border border-slate-200">
                    P
                  </div>
                  <div className="flex flex-col gap-0.5 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-900">Priya (AI)</span>
                      <span className="font-code-metric text-[10px] text-slate-400">00:38</span>
                      <span className="inline-flex items-center gap-1 text-[10px] text-emerald-600 font-medium">
                        <span className="material-symbols-outlined text-[10px] animate-spin">progress_activity</span>
                        Speaking
                      </span>
                    </div>
                    <div className="bg-slate-50 border border-slate-200/70 px-3 py-2 rounded-lg rounded-tl-none font-body-sm text-xs text-slate-900 leading-normal">
                      "Sure! For 90%+ in 12th boards, you qualify for our 50% merit scholarship on CSE tuition."
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* COGNITIVE EXTRACTION & TELEMETRY MINI CARDS */}
            <div className="p-5 grid grid-cols-1 md:grid-cols-3 gap-3 border-b border-slate-100">
              <div className="bg-slate-50 border border-slate-200/80 p-2.5 rounded-lg flex items-center justify-between">
                <span className="font-label-xs uppercase tracking-wider text-slate-400 text-[10px] font-semibold">
                  Intent
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="font-title-sm text-xs text-slate-900 font-semibold">Scholarship Inquiry</span>
                  <span className="text-[10px] font-code-metric text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded font-medium">
                    96%
                  </span>
                </div>
              </div>
              <div className="bg-slate-50 border border-slate-200/80 p-2.5 rounded-lg flex items-center justify-between">
                <span className="font-label-xs uppercase tracking-wider text-slate-400 text-[10px] font-semibold">
                  Sentiment
                </span>
                <div className="flex items-center gap-1.5">
                  <span className="font-title-sm text-xs text-slate-900 font-semibold">Engaged &amp; Positive</span>
                  <span className="text-[10px] font-code-metric text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded font-medium">
                    +0.88
                  </span>
                </div>
              </div>
              <div className="bg-slate-50 border border-slate-200/80 p-2.5 rounded-lg flex items-center justify-between">
                <span className="font-label-xs uppercase tracking-wider text-slate-400 text-[10px] font-semibold">
                  Variables
                </span>
                <div className="flex items-center gap-2 font-code-metric text-xs">
                  <span className="text-slate-900 font-medium">B.Tech CSE</span>
                  <span className="text-slate-300">•</span>
                  <span className="text-slate-600">92% Board</span>
                </div>
              </div>
            </div>

            {/* SUPERVISION & CALL CONTROL BAR */}
            <div className="p-5 flex flex-col gap-2">
              <div className="p-2.5 bg-white border border-slate-200/80 shadow-2xs rounded-lg flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setIsMuted(!isMuted)}
                    className={clsx(
                      'px-3 py-1.5 font-label-md text-xs rounded-md flex items-center gap-1.5 transition-colors border',
                      isMuted
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-slate-50 hover:bg-slate-100 text-slate-800 border-slate-200/70'
                    )}
                  >
                    <span className="material-symbols-outlined text-sm">{isMuted ? 'mic' : 'mic_off'}</span>
                    <span>{isMuted ? 'Unmute' : 'Mute'}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setWhisperOpen(!whisperOpen)}
                    className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 font-label-md text-xs rounded-md flex items-center gap-1.5 transition-colors border border-slate-200/70"
                  >
                    <span className="material-symbols-outlined text-sm">edit_note</span>
                    <span>Whisper Note</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setCallStatusMessage('Initiating Handover to Real Agent...');
                      setTimeout(() => setCallStatusMessage('Call transferred to Executive Queue!'), 1500);
                    }}
                    className="px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 font-label-md text-xs rounded-md flex items-center gap-1.5 transition-colors border border-slate-200/70"
                  >
                    <span className="material-symbols-outlined text-sm">phone_forwarded</span>
                    <span>Transfer</span>
                  </button>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setIsLiveStreaming(false);
                    setCallStatusMessage('Call ended.');
                  }}
                  className="px-3.5 py-1.5 bg-red-600 text-white hover:bg-red-700 font-label-md text-xs rounded-md flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
                >
                  <span className="material-symbols-outlined text-sm">call_end</span>
                  <span>End Call</span>
                </button>
              </div>

              {whisperOpen && (
                <div className="flex gap-2 mt-1">
                  <input
                    type="text"
                    value={whisperText}
                    onChange={(e) => setWhisperText(e.target.value)}
                    placeholder="Whisper guidance directly to AI agent..."
                    className="flex-1 text-xs border border-slate-300 rounded-md px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setWhisperText('');
                      setWhisperOpen(false);
                      setCallStatusMessage('Whisper instruction delivered to agent');
                      setTimeout(() => setCallStatusMessage(null), 2500);
                    }}
                    className="px-3 py-1.5 bg-slate-900 text-white text-xs rounded-md font-medium"
                  >
                    Inject
                  </button>
                </div>
              )}
            </div>

            {/* DIAGNOSTIC RAG & SIP STRIP */}
            <div className="p-4 bg-slate-50/60 rounded-b-xl border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 font-code-metric text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-sm text-slate-400">verified</span>
                <span>Admissions Guide 2025 RAG Synced</span>
              </div>
              <div className="flex items-center gap-3">
                <span>
                  Quality: <strong className="text-emerald-700 font-semibold">100%</strong>
                </span>
                <span>
                  Region: <strong className="text-slate-900 font-semibold">Mumbai</strong>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI METRICS STRIP */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        {kpis.map((k, i) => (
          <MStatCard key={k.label} {...k} delay={i * 70} />
        ))}
      </div>

      {/* CHARTS SECTION */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <MCard className="p-6 xl:col-span-2">
          <div className="anim-enter" style={{ animationDelay: '120ms' }}>
            <div className="flex items-start justify-between mb-1">
              <div>
                <h3 className="text-[15px] font-bold text-slate-900">Call Activity</h3>
                <p className="text-xs text-slate-500 mt-0.5">Calls placed and leads captured · last 14 days</p>
              </div>
              <div className="flex items-center gap-4 text-xs font-medium text-slate-500">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-slate-900" /> Calls
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Leads
                </span>
              </div>
            </div>
            <div className="h-[240px] mt-3">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={activity} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
                  <defs>
                    <linearGradient id="actCalls" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0f172a" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#0f172a" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="actLeads" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#10B981" stopOpacity={0.25} />
                      <stop offset="100%" stopColor="#10B981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} dy={6} interval={1} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: 10,
                      boxShadow: '0 4px 12px rgba(0,0,0,0.06)',
                      fontSize: 12,
                    }}
                  />
                  <Area type="monotone" dataKey="Calls" stroke="#0f172a" strokeWidth={2} fill="url(#actCalls)" />
                  <Area type="monotone" dataKey="Leads" stroke="#10B981" strokeWidth={2} fill="url(#actLeads)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </MCard>

        {/* Outcome Breakdown Donut */}
        <MCard className="p-6">
          <div className="anim-enter" style={{ animationDelay: '180ms' }}>
            <h3 className="text-[15px] font-bold text-slate-900">Outcome Distribution</h3>
            <p className="text-xs text-slate-500 mt-0.5">Disposition breakdown across all calls</p>
            <div className="h-[180px] relative mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={outcomeData} dataKey="value" innerRadius={55} outerRadius={78} paddingAngle={3}>
                    {outcomeData.map((e) => (
                      <Cell key={e.name} fill={e.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #e2e8f0',
                      borderRadius: 10,
                      fontSize: 12,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="text-2xl font-extrabold text-slate-900 tabular-nums">{outcomeTotal}</span>
                <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2 pt-2 border-t border-slate-100 text-xs">
              {outcomeData.map((o) => (
                <div key={o.name} className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-slate-600">
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: o.color }} />
                    {o.name}
                  </span>
                  <span className="font-semibold text-slate-900 tabular-nums">{o.value}</span>
                </div>
              ))}
            </div>
          </div>
        </MCard>
      </div>
    </div>
  );
};
