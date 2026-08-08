'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { AgentStateBadge } from '@/components/agents-ui/agent-state-badge';
import { MicPermissionBanner } from '@/components/agents-ui/mic-permission-banner';
import { Store, ShieldCheck, Mic, Sparkles, Clock, MapPin, PhoneCall } from 'lucide-react';

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref} className="relative min-h-screen w-full flex flex-col items-center justify-center p-4 md:p-8 overflow-y-auto">
      {/* Microphone permission error banner */}
      <MicPermissionBanner />

      {/* Main Glassmorphic Container */}
      <div className="glass-card w-full max-w-xl rounded-3xl p-6 md:p-10 flex flex-col items-center text-center shadow-2xl space-y-6 relative overflow-hidden border border-amber-500/20">
        {/* Decorative Top Accent Glow */}
        <div className="absolute -top-24 -left-24 size-48 rounded-full bg-amber-500/20 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 size-48 rounded-full bg-emerald-500/15 blur-3xl pointer-events-none" />

        {/* Store Icon Badge */}
        <div className="relative">
          <div className="size-20 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-600 p-0.5 shadow-lg shadow-amber-500/30 flex items-center justify-center">
            <div className="size-full bg-[#0b1326] rounded-[14px] flex items-center justify-center">
              <Store className="size-10 text-amber-400" />
            </div>
          </div>
          <div className="absolute -bottom-1 -right-1 bg-emerald-500 text-slate-950 p-1 rounded-full shadow-md" title="Verified Kirana Assistant">
            <ShieldCheck className="size-4" />
          </div>
        </div>

        {/* Title & Subtitle */}
        <div className="space-y-2 max-w-md">
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-white font-sans">
            Dukaan Sathi <span className="text-amber-400">(दुकान साथी)</span>
          </h1>
          <p className="text-amber-200/80 text-xs md:text-sm font-medium">
            24/7 Digital Voice Assistant for Local Kirana Stores & Neighborhood Customers
          </p>
        </div>

        {/* 5-State Badge Indicator */}
        <AgentStateBadge />

        {/* Store Highlights Grid */}
        <div className="grid grid-cols-2 gap-3 w-full max-w-md pt-2 text-left">
          <div className="glass-pill rounded-xl p-3 flex items-start gap-2.5">
            <Clock className="size-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-[11px] font-bold text-amber-300">Store Timings</p>
              <p className="text-[10px] text-slate-300">Open Daily: 8 AM - 9:30 PM</p>
            </div>
          </div>

          <div className="glass-pill rounded-xl p-3 flex items-start gap-2.5">
            <MapPin className="size-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="text-[11px] font-bold text-amber-300">Location</p>
              <p className="text-[10px] text-slate-300">Sector 4, Main Market</p>
            </div>
          </div>
        </div>

        {/* Primary Action Button (State 1: Ready) */}
        <div className="w-full max-w-xs pt-3 space-y-3">
          <Button
            size="lg"
            onClick={onStartCall}
            className="w-full h-13 rounded-2xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 font-bold text-sm tracking-wide shadow-lg shadow-amber-500/25 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] flex items-center justify-center gap-2"
          >
            <Mic className="size-5 text-slate-950 animate-pulse" />
            <span>{startButtonText}</span>
          </Button>

          <p className="text-[11px] text-slate-400 flex items-center justify-center gap-1">
            <Sparkles className="size-3 text-amber-400" />
            Speaks Hindi, Hinglish & English naturally
          </p>
        </div>
      </div>

      {/* Footer info */}
      <footer className="mt-6 text-center text-xs text-slate-400">
        <p className="flex items-center justify-center gap-1 text-slate-300/80">
          <PhoneCall className="size-3 text-emerald-400" />
          Powered by <strong>Murf Falcon</strong> — Fastest TTS API (~130ms) & Deepgram Nova-3
        </p>
      </footer>
    </div>
  );
};
