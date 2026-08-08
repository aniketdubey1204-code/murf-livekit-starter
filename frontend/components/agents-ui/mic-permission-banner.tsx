'use client';

import React, { useEffect, useState } from 'react';
import { AlertTriangle, MicOff, RefreshCw, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useLocalParticipant, useSessionContext } from '@livekit/components-react';

export function MicPermissionBanner() {
  const [micBlocked, setMicBlocked] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  
  const { isConnected } = useSessionContext();
  const { isMicrophoneEnabled, localParticipant } = useLocalParticipant();
  const isIntentionallyMuted = isConnected && localParticipant && !isMicrophoneEnabled;

  useEffect(() => {
    // Check initial mic permission status if supported
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions
        .query({ name: 'microphone' as PermissionName })
        .then((permissionStatus) => {
          if (permissionStatus.state === 'denied') {
            setMicBlocked(true);
          }
          permissionStatus.onchange = () => {
            setMicBlocked(permissionStatus.state === 'denied');
          };
        })
        .catch(() => {
          // Ignore if permission query fails
        });
    }

    // Also listen for unhandled errors or media device errors
    const handleError = (e: ErrorEvent) => {
      if (
        e.message?.includes('Permission denied') ||
        e.message?.includes('NotAllowedError') ||
        e.message?.includes('microphone')
      ) {
        setMicBlocked(true);
      }
    };

    window.addEventListener('error', handleError);
    return () => window.removeEventListener('error', handleError);
  }, []);

  if ((!micBlocked && !isIntentionallyMuted) || dismissed) {
    return null;
  }

  // Handle intentional mute from dashboard
  if (isIntentionallyMuted && !micBlocked) {
    return (
      <div className="fixed top-4 inset-x-4 z-50 mx-auto max-w-xl rounded-xl border border-amber-500/40 bg-amber-950/80 p-3 text-amber-100 backdrop-blur-xl shadow-2xl transition-all">
        <div className="flex items-center gap-3">
          <div className="rounded-full bg-amber-500/20 p-2 text-amber-400">
            <MicOff className="size-4" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm font-bold text-amber-200">
              Microphone is Muted
            </h4>
            <p className="text-xs text-amber-300/80">
              You turned off the microphone from the control panel.
            </p>
          </div>
          <Button
            size="sm"
            variant="ghost"
            className="text-[10px] bg-amber-900/30 text-amber-200 hover:bg-amber-800/40"
            onClick={() => localParticipant?.setMicrophoneEnabled(true)}
          >
            Turn On
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-amber-300 hover:bg-amber-900/50 hover:text-white ml-2"
            onClick={() => setDismissed(true)}
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed top-4 inset-x-4 z-50 mx-auto max-w-xl rounded-xl border border-red-500/40 bg-red-950/80 p-4 text-red-100 backdrop-blur-xl shadow-2xl transition-all">
      <div className="flex items-start gap-3">
        <div className="rounded-full bg-red-500/20 p-2 text-red-400">
          <MicOff className="size-5" />
        </div>
        <div className="flex-1 space-y-1">
          <h4 className="flex items-center gap-2 text-sm font-bold text-red-200">
            <AlertTriangle className="size-4 text-amber-400" />
            Microphone Access Blocked (माइक्रोफ़ोन की अनुमति ब्लॉक है)
          </h4>
          <p className="text-xs text-red-300/90 leading-relaxed">
            Dukaan Sathi needs microphone access to listen to your voice. Please enable microphone permissions in your browser:
          </p>
          <ol className="list-decimal list-inside text-xs text-red-200/80 space-y-0.5 pt-1 font-mono">
            <li>Click the lock or tune icon <span className="text-amber-300">🔒</span> next to the site URL in your address bar.</li>
            <li>Toggle <strong>Microphone</strong> to <strong>Allow</strong>.</li>
            <li>Reload the page and tap <em>Connect to Dukaan Sathi</em> again.</li>
          </ol>
        </div>
        <div className="flex flex-col gap-1">
          <Button
            size="icon"
            variant="ghost"
            className="size-7 text-red-300 hover:bg-red-900/50 hover:text-white"
            onClick={() => setDismissed(true)}
          >
            <X className="size-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-[10px] border-red-500/50 bg-red-900/30 text-red-200 hover:bg-red-800/40"
            onClick={() => window.location.reload()}
          >
            <RefreshCw className="size-3 mr-1" />
            Reload
          </Button>
        </div>
      </div>
    </div>
  );
}
