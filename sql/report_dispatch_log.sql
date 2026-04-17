-- Execute esta migration no Supabase SQL Editor
-- Garante idempotencia persistente de relatorios diarios e mensais por continente e data local.

create table if not exists public.report_dispatch_log (
  id uuid primary key default gen_random_uuid(),
  report_type text not null check (report_type in ('daily', 'monthly')),
  continente text not null,
  report_date date not null,
  timezone text not null,
  sent_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create unique index if not exists uq_report_dispatch_unique
  on public.report_dispatch_log (report_type, continente, report_date);

create index if not exists idx_report_dispatch_sent_at
  on public.report_dispatch_log (sent_at desc);
