-- Run in Supabase SQL Editor. Use a SERVER-SIDE secret/service-role key only.
create table if not exists public.profile (
  id integer primary key default 1 check (id = 1),
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
create table if not exists public.daily_logs (
  id bigint generated always as identity primary key,
  date date not null,
  content text not null check (length(trim(content)) > 0),
  processed boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists public.applications (
  id uuid primary key default gen_random_uuid(),
  company text not null,
  job_title text not null,
  jd_text text not null,
  cv_json jsonb not null,
  cover_letter_json jsonb not null,
  model_used text not null,
  profile_snapshot jsonb not null,
  recruiter_email text not null default '',
  hiring_manager text not null default '',
  email_json jsonb not null default '{}'::jsonb,
  warnings jsonb not null default '[]'::jsonb,
  reviewed boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists public.email_logs (
  id bigint generated always as identity primary key,
  application_id uuid references public.applications(id) on delete set null,
  to_email text not null,
  subject text not null,
  status text not null,
  error text,
  sent_at timestamptz not null default now()
);
alter table public.profile enable row level security;
alter table public.daily_logs enable row level security;
alter table public.applications enable row level security;
alter table public.email_logs enable row level security;
-- No browser/anon policies: the password-protected Python server uses service_role.
revoke all on public.profile, public.daily_logs, public.applications, public.email_logs from anon, authenticated;
create or replace function public.approve_profile_updates(new_profile jsonb, log_ids bigint[])
returns void language plpgsql set search_path = public as $$
begin
  insert into public.profile(id, data, updated_at) values (1, new_profile, now())
  on conflict(id) do update set data = excluded.data, updated_at = now();
  update public.daily_logs set processed = true where id = any(log_ids);
end;
$$;
revoke all on function public.approve_profile_updates(jsonb, bigint[]) from public, anon, authenticated;
grant execute on function public.approve_profile_updates(jsonb, bigint[]) to service_role;
