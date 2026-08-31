import React from 'react';
import { Clock } from 'lucide-react';

export default function ComingSoonPage({ title }) {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-10">
      <Clock className="text-slate-400 mb-4" size={64} />
      <h1 className="text-2xl font-bold text-slate-700 mb-2">{title}</h1>
      <p className="text-slate-500 text-center max-w-md">
        This module is currently under development. It will be wired to the live backend soon.
      </p>
    </div>
  );
}
