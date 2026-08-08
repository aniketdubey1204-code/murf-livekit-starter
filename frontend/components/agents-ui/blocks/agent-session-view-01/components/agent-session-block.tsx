'use client';

import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import { useAgent, useSessionContext, useSessionMessages } from '@livekit/components-react';
import { AgentChatTranscript } from '@/components/agents-ui/agent-chat-transcript';
import {
  AgentControlBar,
  type AgentControlBarControls,
} from '@/components/agents-ui/agent-control-bar';
import { AgentStateBadge } from '@/components/agents-ui/agent-state-badge';
import { MicPermissionBanner } from '@/components/agents-ui/mic-permission-banner';
import { AgentBlobVisualizer } from '@/components/agents-ui/agent-blob-visualizer';
import { Shimmer } from '@/components/ai-elements/shimmer';
import { cn } from '@/lib/shadcn/utils';
import { Store } from 'lucide-react';

const MotionMessage = motion.create(Shimmer);

const BOTTOM_VIEW_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      translateY: '0%',
    },
    hidden: {
      opacity: 0,
      translateY: '100%',
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.3,
    delay: 0.5,
    ease: 'easeOut',
  },
};

const CHAT_MOTION_PROPS: MotionProps = {
  variants: {
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeOut',
        duration: 0.3,
      },
    },
    visible: {
      opacity: 1,
      transition: {
        delay: 0.2,
        ease: 'easeOut',
        duration: 0.3,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

const SHIMMER_MOTION_PROPS: MotionProps = {
  variants: {
    visible: {
      opacity: 1,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0.8,
      },
    },
    hidden: {
      opacity: 0,
      transition: {
        ease: 'easeIn',
        duration: 0.5,
        delay: 0,
      },
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
};

interface FadeProps {
  top?: boolean;
  bottom?: boolean;
  className?: string;
}

export function Fade({ top = false, bottom = false, className }: FadeProps) {
  return (
    <div
      className={cn(
        'from-background pointer-events-none h-4 bg-linear-to-b to-transparent',
        top && 'bg-linear-to-b',
        bottom && 'bg-linear-to-t',
        className
      )}
    />
  );
}

export interface AgentSessionView_01Props {
  preConnectMessage?: string;
  supportsChatInput?: boolean;
  supportsVideoInput?: boolean;
  supportsScreenShare?: boolean;
  isPreConnectBufferEnabled?: boolean;
  className?: string;
}

export function AgentSessionView_01({
  preConnectMessage = 'Dukaan Sathi is active — ask about item rates or store info',
  supportsChatInput = true,
  supportsVideoInput = false,
  supportsScreenShare = false,
  isPreConnectBufferEnabled = true,
  ref,
  className,
  ...props
}: React.ComponentProps<'section'> & AgentSessionView_01Props) {
  const session = useSessionContext();
  const { messages } = useSessionMessages(session);
  const [chatOpen, setChatOpen] = useState(true);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { state: agentState } = useAgent();

  const controls: AgentControlBarControls = {
    leave: true,
    microphone: true,
    chat: supportsChatInput,
    camera: false,
    screenShare: false,
  };

  useEffect(() => {
    const lastMessage = messages.at(-1);
    const lastMessageIsLocal = lastMessage?.from?.isLocal === true;

    if (scrollAreaRef.current && lastMessageIsLocal) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section
      ref={ref}
      className={cn('bg-[#0b1326] relative z-10 h-full w-full overflow-hidden flex flex-col', className)}
      {...props}
    >
      {/* Mic permission banner */}
      <MicPermissionBanner />

      {/* Top Header Bar */}
      <header className="absolute top-0 inset-x-0 z-40 p-4 md:px-8 flex items-center justify-between pointer-events-auto bg-gradient-to-b from-[#0b1326] via-[#0b1326]/80 to-transparent backdrop-blur-md border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400">
            <Store className="size-5" />
          </div>
          <div>
            <h2 className="text-sm md:text-base font-bold text-white leading-tight">Dukaan Sathi (दुकान साथी)</h2>
            <p className="text-[10px] md:text-xs text-amber-200/70 font-medium">Digital Kirana Assistant</p>
          </div>
        </div>

        {/* 5-State Agent Badge */}
        <AgentStateBadge />
      </header>

      {/* Central Content Area: Left Blob + Right Chat */}
      <div className="relative inset-0 flex flex-1 min-h-0 w-full max-w-6xl mx-auto px-4 pt-20 pb-36 md:pb-28 items-center justify-center gap-6 lg:gap-16">
        {/* LEFT: Dynamic Fluid Blob Visualizer */}
        <div className="hidden sm:flex flex-col items-center justify-center p-4 w-72 md:w-96 shrink-0 md:-ml-8 lg:-ml-16">
          <AgentBlobVisualizer size="lg" />
        </div>

        {/* RIGHT: Live Chat Transcript Container */}
        <div className="flex-1 h-full w-full flex flex-col justify-end overflow-hidden relative">
          {/* Mobile Blob header inside chat area if small screen */}
          <div className="flex sm:hidden justify-center pb-2">
            <AgentBlobVisualizer size="sm" />
          </div>

          <AnimatePresence>
            {chatOpen && (
              <motion.div
                {...CHAT_MOTION_PROPS}
                className="flex h-full w-full flex-col gap-4 transition-opacity duration-300 ease-out"
              >
                <AgentChatTranscript
                  agentState={agentState}
                  messages={messages}
                  className="w-full [&_.is-user>div]:rounded-[22px] [&>div>div]:px-2 md:[&>div>div]:px-4"
                />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Bottom Control Bar */}
      <motion.div
        {...BOTTOM_VIEW_MOTION_PROPS}
        className="absolute inset-x-3 bottom-0 z-50 md:inset-x-12"
      >
        {/* Pre-connect message */}
        {isPreConnectBufferEnabled && messages.length === 0 && (
          <AnimatePresence>
            <MotionMessage
              key="pre-connect-message"
              duration={2}
              aria-hidden={messages.length > 0}
              {...SHIMMER_MOTION_PROPS}
              className="pointer-events-none mx-auto block w-full max-w-2xl pb-2 text-center text-xs font-semibold text-amber-300/80"
            >
              {preConnectMessage}
            </MotionMessage>
          </AnimatePresence>
        )}

        <div className="bg-[#0b1326]/90 backdrop-blur-xl border-t border-white/10 relative mx-auto max-w-2xl rounded-t-2xl p-3 md:pb-6 shadow-2xl">
          <AgentControlBar
            variant="livekit"
            controls={controls}
            isChatOpen={chatOpen}
            isConnected={session.isConnected}
            onDisconnect={session.end}
            onIsChatOpenChange={setChatOpen}
          />
        </div>
      </motion.div>
    </section>
  );
}
