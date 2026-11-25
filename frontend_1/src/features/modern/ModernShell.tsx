import React, { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { clsx } from 'clsx';
import { LookToggle } from '../../components/layout/LookToggle';
import { BusinessSelector } from '../../components/ui/BusinessSelector';
import { useActiveCalls } from '../../hooks/useActiveCalls';

interface NavItem {
  name: string;
  href: string;
  iconName: string;
  end?: boolean;
  live?: boolean;
}

const PRIMARY_NAV: NavItem[] = [
  { name: 'Dashboard & Live Monitor', href: '/', iconName: 'monitoring', end: true },
  { name: 'AI Voice Agents', href: '/agents', iconName: 'record_voice_over' },
  { name: 'Quick Dialer & Softphone', href: '/calls', iconName: 'dialpad', live: true },
  { name: 'Call History & Intelligence', href: '/leads', iconName: 'history_toggle_off' },
  { name: 'Telephony & API Gateway', href: '/settings', iconName: 'settings_input_component' },
];

const SECONDARY_NAV: NavItem[] = [
  { name: 'Businesses', href: '/businesses', iconName: 'apartment' },
  { name: 'Contacts', href: '/contacts', iconName: 'group' },
  { name: 'Follow-ups', href: '/followups', iconName: 'event_repeat' },
  { name: 'Calendar', href: '/calendar', iconName: 'calendar_month' },
  { name: 'Reports', href: '/reports', iconName: 'bar_chart' },
  { name: 'Billing', href: '/invoices', iconName: 'receipt_long' },
  { name: 'Questionnaires', href: '/questionnaires', iconName: 'assignment' },
];

/**
 * Modern Shell: ARB SoftTech Operational Hub & Telephony Console
 * Implements the exact layout and theme from the enterprise design system.
 */
export const ModernShell: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { activeCount } = useActiveCalls();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const handleOpenQuickDial = () => {
    window.dispatchEvent(new CustomEvent('voxora-quick-dial'));
  };

  const navLinkClass = (isActive: boolean) =>
    clsx(
      'flex items-center gap-2.5 px-3 py-2 rounded-lg transition-colors font-body-md text-sm',
      isActive
        ? 'bg-slate-100 text-slate-900 font-semibold'
        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
    );

  return (
    <div className="bg-surface font-body-md text-on-surface antialiased min-h-screen">
      {/* SIDEBAR NAVIGATION (FIXED LEFT w-64) */}
      <aside
        className={clsx(
          'fixed left-0 top-0 h-full w-64 bg-surface-card border-r border-slate-200 z-50 flex flex-col justify-between transition-transform duration-200 ease-in-out md:translate-x-0',
          mobileMenuOpen ? 'translate-x-0 shadow-2xl' : '-translate-x-full md:translate-x-0'
        )}
      >
        <div className="flex flex-col min-h-0 flex-1 overflow-y-auto">
          {/* Logo & Platform Info Header */}
          <div className="h-16 px-4 flex items-center justify-between border-b border-slate-100 bg-white shrink-0">
            <NavLink to="/" className="flex items-center gap-3 min-w-0" onClick={() => setMobileMenuOpen(false)}>
              <img
                alt="ARB SoftTech AI Voice Logo"
                className="h-8 w-auto object-contain"
                src="https://lh3.googleusercontent.com/aida/AEtjO1VUJ3lz28td1r8cdfwck0t-SIb6Z2Axe8F15LdpnA9HSvoW8o-m16do9TshV3zbZU4NPcOlDQItOmTBsN_rR5SBEkdKLCx4446IrmdK3wS_lPyyYt53p7k3QgqpZtdbrwoyC-VJhZDO9RMTFU4tAlc1_DW6_K24lpErmRVoDukdsVeSvFIsYuAJUc4aVYyVTCgjI7DRCWvKNPCgI3m9pqRWGd3nlXX-eAE2AuCNPPaNSQ"
              />
              <div className="flex flex-col min-w-0">
                <span className="font-headline-sm text-sm font-bold text-slate-900 tracking-tight truncate">
                  ARB Voice
                </span>
                <span className="font-mono-sm text-[11px] text-slate-500 truncate">Core v2.4 Fast-API</span>
              </div>
            </NavLink>
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="md:hidden p-1 text-slate-400 hover:text-slate-700"
              aria-label="Close Navigation"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>
          </div>

          {/* Operational Hub Section */}
          <div className="px-4 pt-5 pb-2">
            <span className="font-label-sm text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
              Operational Hub
            </span>
          </div>
          <nav className="flex flex-col gap-1 px-3">
            {PRIMARY_NAV.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                end={item.end}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) => navLinkClass(isActive)}
              >
                <span className="material-symbols-outlined text-slate-700 text-lg">{item.iconName}</span>
                <span className="truncate flex-1">{item.name}</span>
                {item.live && activeCount > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-mono-sm font-semibold">
                    {activeCount}
                  </span>
                )}
              </NavLink>
            ))}
          </nav>

          {/* Workspace Management Section */}
          <div className="px-4 pt-5 pb-2">
            <span className="font-label-sm text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
              Workspace & Data
            </span>
          </div>
          <nav className="flex flex-col gap-1 px-3 pb-4">
            {SECONDARY_NAV.map((item) => (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) => navLinkClass(isActive)}
              >
                <span className="material-symbols-outlined text-slate-500 text-lg">{item.iconName}</span>
                <span className="truncate">{item.name}</span>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* System Health Widget */}
        <div className="p-3.5 bg-slate-50 mx-3 mb-4 rounded-lg border border-slate-200/80 shrink-0">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200/60">
            <span className="font-label-sm text-[11px] text-slate-500 uppercase tracking-wider font-semibold">
              System Health
            </span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <div className="flex flex-col gap-1.5 mt-2">
            <div className="flex items-center justify-between font-mono-sm text-[11px]">
              <span className="text-slate-500">Active Lines</span>
              <span className="text-emerald-700 font-medium">{activeCount > 0 ? `${activeCount}/8 Active` : '8/8 Ready'}</span>
            </div>
            <div className="flex items-center justify-between font-mono-sm text-[11px]">
              <span className="text-slate-500">Service Status</span>
              <span className="text-emerald-700 font-medium">Online</span>
            </div>
            <div className="flex items-center justify-between font-mono-sm text-[11px]">
              <span className="text-slate-500">Response Time</span>
              <span className="text-slate-700 font-medium">Fast (&lt;200ms)</span>
            </div>
          </div>
        </div>
      </aside>

      {/* Backdrop for mobile menu */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-slate-900/40 z-40 md:hidden backdrop-blur-xs transition-opacity"
        />
      )}

      {/* MAIN LAYOUT WRAPPER (pl-64 on desktop) */}
      <div className="md:pl-64">
        {/* FIXED TOP HEADER */}
        <header className="fixed top-0 left-0 md:left-64 right-0 h-16 bg-white/95 backdrop-blur-md border-b border-slate-200 z-40 flex items-center justify-between px-4 sm:px-8">
          {/* Left Telemetry & Mobile Hamburger */}
          <div className="flex items-center gap-3 overflow-x-auto py-1">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-1.5 text-slate-600 hover:text-slate-900 rounded-md hover:bg-slate-100"
              aria-label="Open Navigation"
            >
              <span className="material-symbols-outlined text-2xl">menu</span>
            </button>

            <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 px-3 py-1 rounded-md font-mono-sm text-xs text-slate-600 whitespace-nowrap">
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
              <span className="text-slate-900 font-semibold">Line:</span>
              <span>Active</span>
              <span className="text-slate-300">|</span>
              <span className="text-slate-900 font-semibold">Network:</span>
              <span className="text-emerald-700 font-medium">Stable</span>
              <span className="text-slate-300">|</span>
              <span className="text-slate-900 font-semibold">Voice Engine:</span>
              <span className="text-emerald-700 font-medium">Active</span>
            </div>

            <div className="hidden lg:flex items-center gap-1.5 bg-slate-50 border border-slate-200 px-3 py-1 rounded-md font-mono-sm text-xs text-slate-700 whitespace-nowrap">
              <span className="material-symbols-outlined text-slate-500 text-sm">translate</span>
              <span className="text-slate-600">Indic Neural TTS:</span>
              <span className="text-slate-900 font-medium">Hi/En/Mr/Ta active</span>
            </div>
          </div>

          {/* Right Header Actions */}
          <div className="flex items-center gap-3 sm:gap-3.5">
            {/* Search Input */}
            <div className="relative hidden xl:flex items-center">
              <span className="material-symbols-outlined absolute left-3 text-slate-400 text-lg">search</span>
              <input
                className="bg-slate-50 border border-slate-200 pl-9 pr-3.5 py-1.5 rounded-md font-body-sm text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-slate-400 focus:bg-white w-64 transition-all"
                placeholder="Search sessions, CDRs, agent IDs..."
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Business Selector */}
            <div className="hidden sm:block">
              <BusinessSelector />
            </div>

            {/* Launch Call Button */}
            <button
              onClick={handleOpenQuickDial}
              className="flex items-center gap-1.5 bg-slate-900 text-white px-3.5 py-1.5 rounded-md font-label-md text-xs hover:bg-slate-800 transition-all font-medium cursor-pointer shadow-xs active:scale-95"
            >
              <span className="material-symbols-outlined text-base">add_call</span>
              <span className="hidden sm:inline">Launch Call</span>
            </button>

            {/* Look Toggle Switch (Modern <-> Classic) */}
            <LookToggle />

            {/* Notification Bell */}
            <button
              type="button"
              className="relative p-2 text-slate-500 hover:text-slate-900 rounded-md hover:bg-slate-100 transition-colors"
              title="Notifications"
            >
              <span className="material-symbols-outlined text-xl">notifications</span>
              <span className="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-slate-900"></span>
            </button>

            {/* Profile Avatar */}
            <img
              alt="Profile"
              className="w-8 h-8 rounded-full object-cover border border-slate-200"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuCuomLdYgsWMIMSScyfHgR8etmb7eeUvv6JLn-ncrQ4ktVds-xRDx0wXCqPKs5RaDZ3_ehBKTfGTdcp5_s0HSF_xc-RDzx49r42fpadEoc4nQjCTp2V3xWNa4SslNWHYiXkANhl4QMZK6-G_d2_rWCJKvvHc9pzANkqlhwrNqIGGKXSU8R_EAW6dM2gbEA557EWKHN8DW0DJWPjfHkuh-YXPaRGl0u5aindOVg6pZY_"
            />
          </div>
        </header>

        {/* MAIN RUNTIME STAGE */}
        <main className="relative pt-16 bg-[#f8fafc] min-h-screen px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col w-full pb-12 pt-6">
            {/* TOP TELEPHONY TELEMETRY & RUNTIME STRIP */}
            <div className="w-full bg-white rounded-xl p-4 shadow-xs mb-6 flex flex-wrap items-center justify-between gap-4 border border-slate-200/90">
              <div className="flex flex-wrap items-center gap-6">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-2.5 w-2.5 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                  </span>
                  <span className="font-title-sm text-slate-900 font-semibold text-sm">Line Active</span>
                  <span className="text-xs font-mono-sm text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-medium">
                    HD Audio
                  </span>
                </div>
                <div className="h-4 w-px bg-slate-200 hidden sm:block"></div>
                <div className="flex items-center gap-1.5 font-mono-sm text-xs text-slate-500">
                  <span>Session:</span>
                  <span className="font-medium text-slate-900">#ARB-90821</span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className="inline-flex items-center gap-1 text-xs font-mono-sm text-emerald-700">
                  <span className="material-symbols-outlined text-sm">check_circle</span> 168ms RTT
                </span>
                <button
                  type="button"
                  onClick={() => navigate('/settings')}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 hover:bg-slate-100 text-slate-800 rounded-lg transition-colors font-label-md text-xs border border-slate-200/80 font-medium"
                >
                  <span className="material-symbols-outlined text-sm">settings</span>
                  <span>Settings</span>
                </button>
              </div>
            </div>

            {/* ROUTE CONTENT */}
            <div key={location.pathname} className="anim-page">
              <Outlet />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};
