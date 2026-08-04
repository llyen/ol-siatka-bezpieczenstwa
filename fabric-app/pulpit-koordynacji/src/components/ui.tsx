import type { ReactNode } from 'react';

/**
 * Wspolne elementy interfejsu. Styl instytucjonalny: jasne tlo, granatowy
 * naglowek, kolory ryzyka wg KPZK, duze wskazniki, minimum ozdobnikow.
 */

/** Kolory z dim_hazard sa slowne, wiec mapujemy je na klasy Tailwinda. */
const HAZARD_COLORS: Record<string, string> = {
  czerwony: 'bg-red-600 text-white border-red-700',
  pomarańczowy: 'bg-orange-500 text-white border-orange-600',
  pomaranczowy: 'bg-orange-500 text-white border-orange-600',
  żółty: 'bg-amber-400 text-slate-900 border-amber-500',
  zolty: 'bg-amber-400 text-slate-900 border-amber-500',
  zielony: 'bg-emerald-600 text-white border-emerald-700',
};

export function hazardColorClass(color: string): string {
  return HAZARD_COLORS[color] ?? 'bg-slate-500 text-white border-slate-600';
}

const STATUS_COLORS: Record<string, string> = {
  gotowe: 'bg-emerald-100 text-emerald-800 ring-emerald-600/30',
  'w toku': 'bg-amber-100 text-amber-800 ring-amber-600/30',
  'nie rozpoczęto': 'bg-slate-100 text-slate-700 ring-slate-500/30',
  zablokowane: 'bg-red-100 text-red-800 ring-red-600/30',
};

export function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_COLORS[status] ?? 'bg-slate-100 text-slate-700 ring-slate-500/30';
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}>
      {status}
    </span>
  );
}

const CRITICALITY_COLORS: Record<string, string> = {
  krytyczna: 'bg-red-50 text-red-700 ring-red-600/30',
  wysoka: 'bg-orange-50 text-orange-700 ring-orange-600/30',
  średnia: 'bg-amber-50 text-amber-700 ring-amber-600/30',
  niska: 'bg-slate-50 text-slate-600 ring-slate-500/30',
};

export function CriticalityBadge({ value }: { value: string }) {
  const cls = CRITICALITY_COLORS[value] ?? 'bg-slate-50 text-slate-600 ring-slate-500/30';
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}>
      {value}
    </span>
  );
}

export function RoleBadge({ role }: { role: string }) {
  const leading = role === 'wiodący' || role === 'wiodacy';
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
        leading
          ? 'bg-blue-100 text-blue-900 ring-blue-700/30'
          : 'bg-slate-100 text-slate-600 ring-slate-500/30'
      }`}
    >
      {role}
    </span>
  );
}

export type KpiTone = 'neutral' | 'good' | 'warn' | 'bad';

const KPI_TONES: Record<KpiTone, string> = {
  neutral: 'text-slate-900',
  good: 'text-emerald-700',
  warn: 'text-amber-700',
  bad: 'text-red-700',
};

export function KpiCard({
  label,
  value,
  suffix,
  hint,
  tone = 'neutral',
}: {
  label: string;
  value: number | string;
  suffix?: string;
  hint?: string;
  tone?: KpiTone;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-3xl font-semibold tabular-nums ${KPI_TONES[tone]}`}>
        {value}
        {suffix && <span className="ml-1 text-lg font-normal text-slate-400">{suffix}</span>}
      </div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function Panel({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </header>
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Button({
  variant = 'secondary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'success';
}) {
  const variants = {
    primary: 'bg-[#0f2a52] text-white hover:bg-[#173a6d] disabled:bg-slate-300',
    secondary: 'bg-white text-slate-700 ring-1 ring-inset ring-slate-300 hover:bg-slate-50 disabled:text-slate-400',
    danger: 'bg-red-600 text-white hover:bg-red-700 disabled:bg-slate-300',
    success: 'bg-emerald-600 text-white hover:bg-emerald-700 disabled:bg-slate-300',
  } as const;
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center rounded px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed ${variants[variant]} ${className}`}
    />
  );
}

/** Prosty wykres slupkowy poziomy - bez biblioteki, zeby paczka pozostala mala. */
export function BarChart({
  rows,
  max,
}: {
  rows: { label: string; value: number; sub?: string; tone?: 'bad' | 'warn' | 'normal' }[];
  max?: number;
}) {
  const peak = max ?? Math.max(1, ...rows.map((r) => r.value));
  const tones = {
    bad: 'bg-red-600',
    warn: 'bg-amber-500',
    normal: 'bg-[#0f2a52]',
  } as const;
  return (
    <div className="space-y-2">
      {rows.map((row) => (
        <div key={row.label} className="grid grid-cols-[minmax(0,14rem)_1fr_2.5rem] items-center gap-3">
          <div className="truncate text-xs text-slate-700" title={row.label}>
            {row.label}
            {row.sub && <span className="ml-1 text-slate-400">{row.sub}</span>}
          </div>
          <div className="h-4 rounded bg-slate-100">
            <div
              className={`h-4 rounded ${tones[row.tone ?? 'normal']}`}
              style={{ width: `${Math.max(2, (row.value / peak) * 100)}%` }}
            />
          </div>
          <div className="text-right text-xs font-semibold tabular-nums text-slate-700">{row.value}</div>
        </div>
      ))}
    </div>
  );
}

export function Toast({
  message,
  tone,
  onClose,
}: {
  message: string;
  tone: 'success' | 'error';
  onClose: () => void;
}) {
  return (
    <div
      role="status"
      className={`fixed bottom-6 right-6 z-50 max-w-md rounded-lg px-4 py-3 text-sm shadow-lg ${
        tone === 'success' ? 'bg-emerald-700 text-white' : 'bg-red-700 text-white'
      }`}
    >
      <div className="flex items-start gap-3">
        <span className="flex-1 whitespace-pre-line">{message}</span>
        <button onClick={onClose} className="text-white/70 hover:text-white" aria-label="Zamknij">
          ✕
        </button>
      </div>
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <div className="rounded border border-dashed border-slate-300 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
      {children}
    </div>
  );
}

export function formatTimestamp(value: string | Date | null): string {
  if (!value) return '—';
  const date = typeof value === 'string' ? new Date(value) : value;
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('pl-PL', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function downloadCsv(filename: string, csv: string) {
  // BOM jest konieczny, zeby Excel poprawnie odczytal polskie znaki.
  const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
