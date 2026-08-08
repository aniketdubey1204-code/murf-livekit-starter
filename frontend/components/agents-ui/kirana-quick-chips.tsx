'use client';

import React from 'react';
import { ShoppingBag, Clock, FileText, CreditCard, Sparkles } from 'lucide-react';
import { useChat } from '@livekit/components-react';

export function KiranaQuickChips() {
  const { send } = useChat();

  const chips = [
    { label: '🛒 Aata, Chawal & Dal Rates', icon: ShoppingBag, prompt: 'Aata aur dal ka kya rate hai?' },
    { label: '⏰ Store Timing & Location', icon: Clock, prompt: 'Dukaan kab khulti hai aur kaha hai?' },
    { label: '📝 Place Pre-Order List', icon: FileText, prompt: 'Mujhe rashan list note karvani hai.' },
    { label: '💳 Payment & Udhaar Rules', icon: CreditCard, prompt: 'Payment kaise le sakte hain?' },
  ];

  const handleChipClick = async (promptText: string) => {
    if (send) {
      await send(promptText);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto py-2">
      <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold text-amber-400/90 uppercase tracking-wider">
        <Sparkles className="size-3.5" />
        <span>Quick Kirana Inquiries (त्वरित प्रश्न):</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {chips.map((chip, idx) => {
          const IconComponent = chip.icon;
          return (
            <button
              key={idx}
              onClick={() => handleChipClick(chip.prompt)}
              className="inline-flex items-center gap-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 px-3 py-1.5 border border-amber-500/30 text-amber-200 text-xs font-medium backdrop-blur-md transition-all active:scale-95 shadow-sm"
            >
              <IconComponent className="size-3.5 text-amber-400" />
              <span>{chip.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
