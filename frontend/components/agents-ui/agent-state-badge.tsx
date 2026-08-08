'use client';

import React from 'react';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { Radio, Mic, Volume2, PhoneOff, Loader2 } from 'lucide-react';

export interface AgentStateBadgeProps {
  className?: string;
}

export function AgentStateBadge({ className = '' }: AgentStateBadgeProps) {
  const session = useSessionContext();
  const { state: agentState } = useAgent();

  // Determine which of the 5 states we are currently in:
  // 1. Ready: Not connected yet
  // 2. Connecting: session connected but agent initializing / connecting state
  // 3. Listening: Agent state is 'listening'
  // 4. Speaking: Agent state is 'speaking'
  // 5. Call ended: Disconnected after being active

  if (!session.isConnected) {
    return (
      <div className={`inline-flex items-center gap-2 rounded-full bg-amber-500/10 px-4 py-1.5 border border-amber-500/30 text-amber-300 text-xs font-semibold tracking-wide backdrop-blur-md ${className}`}>
        <Radio className="size-3.5 text-amber-400 animate-pulse" />
        <span>Ready — Ready to Connect (दुकान साथी तैयार है)</span>
      </div>
    );
  }

  if (agentState === 'initializing' || agentState === 'connecting' || agentState === 'disconnected') {
    if (agentState === 'disconnected') {
      return (
        <div className={`inline-flex items-center gap-2 rounded-full bg-red-500/10 px-4 py-1.5 border border-red-500/30 text-red-300 text-xs font-semibold tracking-wide backdrop-blur-md ${className}`}>
          <PhoneOff className="size-3.5 text-red-400" />
          <span>Call ended — Ready to Start Again (कॉल समाप्त)</span>
        </div>
      );
    }
    return (
      <div className={`inline-flex items-center gap-2 rounded-full bg-amber-500/20 px-4 py-1.5 border border-amber-500/40 text-amber-300 text-xs font-semibold tracking-wide backdrop-blur-md ${className}`}>
        <Loader2 className="size-3.5 text-amber-400 animate-spin" />
        <span>Connecting — Joining Call... (दुकानदार से जुड़ रहे हैं)</span>
      </div>
    );
  }

  if (agentState === 'listening') {
    return (
      <div className={`inline-flex items-center gap-2 rounded-full bg-emerald-500/20 px-4 py-1.5 border border-emerald-500/40 text-emerald-300 text-xs font-semibold tracking-wide backdrop-blur-md animate-pulse-emerald ${className}`}>
        <Mic className="size-3.5 text-emerald-400 animate-bounce" />
        <span>Listening — Listening to you... (आपकी बात सुन रहे हैं)</span>
      </div>
    );
  }

  if (agentState === 'speaking') {
    return (
      <div className={`inline-flex items-center gap-2 rounded-full bg-amber-500/25 px-4 py-1.5 border border-amber-500/50 text-amber-200 text-xs font-semibold tracking-wide backdrop-blur-md animate-pulse-saffron ${className}`}>
        <Volume2 className="size-3.5 text-amber-400 animate-pulse" />
        <span>Speaking — Dukaan Sathi is speaking... (दुकान साथी बोल रही है)</span>
      </div>
    );
  }

  // Fallback connected state
  return (
    <div className={`inline-flex items-center gap-2 rounded-full bg-amber-500/15 px-4 py-1.5 border border-amber-500/30 text-amber-300 text-xs font-semibold tracking-wide backdrop-blur-md ${className}`}>
      <Radio className="size-3.5 text-amber-400 animate-pulse" />
      <span>Connected — Dukaan Sathi Active</span>
    </div>
  );
}
