import React, { useState } from 'react';
import {
  Menu,
  Sun,
  Moon,
  Search,
  Layers,
  Sparkles,
} from 'lucide-react';
import { useTheme, type Look } from '../../app/providers/ThemeProvider';
import { BusinessSelector } from '../ui/BusinessSelector';

interface HeaderProps {
  onOpenMobileSidebar: () => void;
  onOpenQuickDial?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ onOpenMobileSidebar }) => {
  const { resolvedTheme, toggleTheme, look, setLook } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <header className="sticky top-0 z-40 h-[72px] bg-white/75 dark:bg-[var(--header-glass-bg)] backdrop-blur-[20px] saturate-[140%] border-b border-slate-200/80 dark:border-white/[0.08] px-4 sm:px-6 flex items-center justify-between transition-colors">
      {/* Left: Mobile Trigger & Search Field */}
      <div className="flex items-center gap-3 sm:gap-4 flex-1 max-w-xl">
        <button
          type="button"
          onClick={onOpenMobileSidebar}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:text-neutral-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-white/[0.05] md:hidden shrink-0"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Search Bar (matches reference visual) */}
        <div className="relative w-full max-w-md hidden sm:block">
          <Search className="w-4 h-4 text-slate-400 dark:text-neutral-500 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search businesses, leads, calls, agents..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-100/80 dark:bg-white/[0.04] border border-slate-200/80 dark:border-white/[0.08] text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-neutral-500 focus:outline-none focus:border-orange-500/50 focus:ring-1 focus:ring-orange-500/20 transition-all"
          />
        </div>
      </div>

      {/* Right: Business Selector, Controls */}
      <div className="flex items-center gap-2.5 shrink-0">
        {/* Business Workspace Selector */}
        <BusinessSelector />

        {/* Look Switcher: Classic (glass) vs Modern (clean light) */}
        <div
          className="flex items-center p-1 rounded-full bg-slate-100 dark:bg-white/[0.06] border border-slate-200 dark:border-white/[0.08]"
          role="group"
          aria-label="Interface look"
          title="Switch interface look"
        >
          {(
            [
              { id: 'classic', label: 'Classic', Icon: Layers },
              { id: 'modern', label: 'Modern', Icon: Sparkles },
            ] as { id: Look; label: string; Icon: typeof Layers }[]
          ).map(({ id, label, Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setLook(id)}
              aria-pressed={look === id}
              className={
                look === id
                  ? 'flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-full bg-white text-slate-900 shadow-sm text-[11px] font-semibold transition-all'
                  : 'flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-full text-slate-500 dark:text-neutral-400 hover:text-slate-900 dark:hover:text-white text-[11px] font-semibold transition-all'
              }
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden lg:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* Theme Switcher (classic look only — modern is always light) */}
        {look === 'classic' && (
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:text-neutral-400 dark:hover:text-white bg-slate-100 dark:bg-white/[0.04] hover:bg-slate-200 dark:hover:bg-white/[0.08] transition-colors border border-slate-200 dark:border-white/[0.08]"
            title={`Switch to ${resolvedTheme === 'dark' ? 'Light' : 'Dark'} mode`}
          >
            {resolvedTheme === 'dark' ? (
              <Sun className="w-4 h-4 text-orange-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-700" />
            )}
          </button>
        )}
      </div>
    </header>
  );
};

