'use client';

import React, { useMemo } from 'react';
import { useAgent, useSessionContext, useTracks, useTrackVolume } from '@livekit/components-react';
import { Track } from 'livekit-client';
import { Radio, Mic, Volume2, PhoneOff, Loader2 } from 'lucide-react';
import { cn } from '@/lib/shadcn/utils';
import { motion } from 'motion/react';

interface AgentBlobVisualizerProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function AgentBlobVisualizer({ className = '', size = 'lg' }: AgentBlobVisualizerProps) {
  const session = useSessionContext();
  const { state: agentState } = useAgent();
  const isConnected = session.isConnected;

  // Get agent audio track to map volume to animation
  const tracks = useTracks([Track.Source.Microphone]);
  const agentTrack = tracks.find(t => t.participant.isAgent);
  const volume = useTrackVolume(agentTrack); // 0 to 1

  // Determine 5 states
  let currentState: 'ready' | 'connecting' | 'listening' | 'speaking' | 'disconnected' = 'ready';
  if (!isConnected) {
    currentState = 'ready';
  } else if (agentState === 'disconnected') {
    currentState = 'disconnected';
  } else if (agentState === 'initializing' || agentState === 'connecting') {
    currentState = 'connecting';
  } else if (agentState === 'listening') {
    currentState = 'listening';
  } else if (agentState === 'speaking' || agentState === 'thinking') {
    currentState = 'speaking';
  }

  const dimensions = {
    sm: 'w-24 h-24',
    md: 'w-40 h-40 md:w-48 md:h-48',
    lg: 'w-64 h-64 md:w-80 md:h-80',
  }[size];

  // Base state configurations for 3D soap bubble effect
  const stateStyles = {
    ready: {
      color: 'border border-amber-300/40',
      glow: 'shadow-[inset_15px_15px_25px_rgba(255,255,255,0.8),inset_-15px_-15px_30px_rgba(245,158,11,0.7),inset_0_-25px_40px_rgba(251,191,36,0.6),0_0_25px_rgba(245,158,11,0.3)]',
      bg: 'bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.6)_0%,rgba(245,158,11,0.05)_40%,rgba(245,158,11,0.15)_100%)]',
      scale: 1,
      badgeColor: 'text-amber-300 border-amber-400/30 bg-amber-400/10',
      icon: Radio,
      label: 'Ready to connect',
      animation: 'blob-slow',
    },
    connecting: {
      color: 'border border-amber-300/60',
      glow: 'shadow-[inset_20px_20px_30px_rgba(255,255,255,0.9),inset_-20px_-20px_40px_rgba(245,158,11,0.8),inset_0_-30px_50px_rgba(251,191,36,0.7),0_0_40px_rgba(245,158,11,0.5)]',
      bg: 'bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.7)_0%,rgba(245,158,11,0.1)_40%,rgba(245,158,11,0.25)_100%)]',
      scale: 1.05,
      badgeColor: 'text-amber-300 border-amber-500/40 bg-amber-500/20',
      icon: Loader2,
      label: 'Connecting...',
      animation: 'blob-spin',
    },
    listening: {
      color: 'border border-emerald-300/40',
      glow: 'shadow-[inset_15px_15px_25px_rgba(255,255,255,0.8),inset_-15px_-15px_30px_rgba(16,185,129,0.7),inset_0_-25px_40px_rgba(52,211,153,0.6),0_0_35px_rgba(16,185,129,0.4)]',
      bg: 'bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.7)_0%,rgba(16,185,129,0.05)_40%,rgba(16,185,129,0.2)_100%)]',
      scale: 1.1,
      badgeColor: 'text-emerald-300 border-emerald-400/40 bg-emerald-400/20',
      icon: Mic,
      label: 'Listening to you...',
      animation: 'blob-morph',
    },
    speaking: {
      color: 'border border-amber-200/60',
      glow: 'shadow-[inset_25px_25px_40px_rgba(255,255,255,0.9),inset_-25px_-25px_50px_rgba(217,119,6,0.9),inset_0_-40px_60px_rgba(245,158,11,0.8),0_0_50px_rgba(245,158,11,0.6)]',
      bg: 'bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.8)_0%,rgba(245,158,11,0.15)_40%,rgba(245,158,11,0.3)_100%)]',
      scale: 1.1 + (volume * 0.4),
      badgeColor: 'text-amber-200 border-amber-500/50 bg-amber-500/30',
      icon: Volume2,
      label: 'Dukaan Sathi speaking...',
      animation: 'blob-energetic',
    },
    disconnected: {
      color: 'border border-red-300/30',
      glow: 'shadow-[inset_10px_10px_20px_rgba(255,255,255,0.6),inset_-10px_-10px_25px_rgba(239,68,68,0.6),inset_0_-20px_30px_rgba(248,113,113,0.5),0_0_20px_rgba(239,68,68,0.2)]',
      bg: 'bg-[radial-gradient(circle_at_30%_30%,rgba(255,255,255,0.5)_0%,rgba(239,68,68,0.05)_40%,rgba(239,68,68,0.15)_100%)]',
      scale: 0.95,
      badgeColor: 'text-red-300 border-red-500/40 bg-red-500/20',
      icon: PhoneOff,
      label: 'Call ended',
      animation: 'blob-static',
    },
  }[currentState];

  const IconComponent = stateStyles.icon;

  // Generate dynamic waveform bars for speaking state
  const waveformBars = useMemo(() => {
    return Array.from({ length: 5 }).map((_, i) => (
      <motion.div
        key={i}
        className="w-1.5 bg-amber-200 rounded-full"
        animate={{
          height: currentState === 'speaking' ? 20 + Math.random() * (volume * 60 + 10) : 4,
        }}
        transition={{
          duration: 0.1,
          repeat: Infinity,
          repeatType: 'reverse',
          delay: i * 0.1,
        }}
      />
    ));
  }, [currentState, volume]);

  return (
    <div className={cn('relative flex flex-col items-center justify-center shrink-0 select-none group', className)}>
      
      {/* 
        Custom CSS Morphing Blob 
        No iframes, no white backgrounds. Just pure dynamic CSS shapes.
      */}
      <div className={cn('relative flex items-center justify-center transition-all duration-300', dimensions)}>
        
        {/* The Blob Layer */}
        <motion.div
          animate={{ scale: stateStyles.scale }}
          transition={{ type: 'spring', stiffness: 200, damping: 15 }}
          className={cn(
            'absolute inset-0 rounded-[60%_40%_30%_70%/60%_30%_70%_40%] backdrop-blur-md flex items-center justify-center transition-colors duration-500',
            stateStyles.color,
            stateStyles.bg,
            stateStyles.glow,
            // Custom CSS animations defined in globals.css
            stateStyles.animation === 'blob-slow' && 'animate-blob-slow',
            stateStyles.animation === 'blob-spin' && 'animate-blob-spin',
            stateStyles.animation === 'blob-morph' && 'animate-blob-morph',
            stateStyles.animation === 'blob-energetic' && 'animate-blob-energetic',
            stateStyles.animation === 'blob-static' && 'rounded-full'
          )}
        >
          {/* Animated Waveform Equalizer when Speaking */}
          {currentState === 'speaking' && (
            <div className="flex items-center gap-1.5 h-16">
              {waveformBars}
            </div>
          )}
        </motion.div>
      </div>

      {/* Dynamic State Badge below Blob */}
      <div className={cn(
        'mt-4 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold backdrop-blur-md border shadow-lg transition-all duration-500',
        stateStyles.badgeColor
      )}>
        <IconComponent className={cn(
          'size-3.5', 
          currentState === 'connecting' && 'animate-spin', 
          currentState === 'listening' && 'animate-bounce'
        )} />
        <span>{stateStyles.label}</span>
      </div>
    </div>
  );
}
