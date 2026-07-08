-- =====================================================================
-- Elite CRM — Supabase schema (Fase 1)
-- Aplicar no SQL Editor do projeto `elite-crm`.
-- Worker usa SERVICE_ROLE (bypassa RLS). Painel usa ANON + auth (RLS por papel).
-- =====================================================================

-- ---------- Papéis ----------
-- Usuários no Supabase Auth: eugene (operador) e rafael (owner).
-- O papel fica em auth.users.raw_app_meta_data->>'role' ('operator' | 'owner').
create or replace function public.user_role() returns text
language sql stable as $$
  select coalesce(auth.jwt()->'app_metadata'->>'role', '')
$$;

-- ---------- Estado do worker ----------
create table if not exists worker_state (
  key text primary key,               -- ex.: 'last_scan_ts', 'last_call_message_id'
  value jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- ---------- Config operacional (editável pelo painel/owner) ----------
create table if not exists config (
  key text primary key,               -- 'eugene_phone', 'google_ads_number', 'pausas', ...
  value jsonb not null,
  updated_at timestamptz not null default now()
);

-- ---------- Chamadas ingeridas ----------
create table if not exists calls (
  id text primary key,                -- messageId do GHL
  contact_id text not null,
  conversation_id text,
  opportunity_id text,
  direction text check (direction in ('inbound','outbound')),
  status text,                        -- completed | no-answer | voicemail...
  duration_sec int,
  dialed_number text,                 -- 'to' (p/ rastrear Google Ads)
  user_id text,                       -- quem discou/atendeu (Eugene/Rafael)
  called_at timestamptz,
  recording_downloaded boolean default false,
  created_at timestamptz not null default now()
);

-- ---------- Transcrições ----------
create table if not exists transcripts (
  call_id text primary key references calls(id),
  provider text not null default 'deepgram',
  language text,
  diarized jsonb,                     -- [{speaker, start, end, text}]
  full_text text,
  raw jsonb,                          -- resposta bruta (auditoria)
  created_at timestamptz not null default now()
);

-- ---------- Análises (Claude 2.2) ----------
create table if not exists analyses (
  call_id text primary key references calls(id),
  model text not null,
  payload jsonb not null,             -- o JSON estruturado do 2.2
  score_before int,
  score_after int,
  created_at timestamptz not null default now()
);

-- ---------- Cards da fila ----------
create table if not exists cards (
  id uuid primary key default gen_random_uuid(),
  type text not null,                 -- new_lead | callback | follow_up | quote | confirm_appt | cold_call | nice_to_talk
  layer int not null default 2 check (layer in (1,2,3)),
  contact_id text not null,
  opportunity_id text,
  title text not null,                -- O QUÊ
  why text,                           -- POR QUÊ (score, gancho)
  how jsonb,                          -- COMO (coaching por tipo)
  ghl_link text,
  score int,
  due_at timestamptz,                 -- quando deve aparecer (tasks com hora)
  status text not null default 'open' check (status in ('open','done','expired','retry')),
  result text,                        -- fechado por evidência: o que aconteceu
  closed_by text,                     -- 'auto' | 'manual-quote'
  evidence jsonb,                     -- evento que fechou (call id, sms id, link...)
  draft_message text,                 -- p/ nice-to-talk e envio de quote
  created_at timestamptz not null default now(),
  closed_at timestamptz
);
create index if not exists cards_open_idx on cards(status, layer, due_at);

-- ---------- Turnos e pausas (clock in/out) ----------
create table if not exists shifts (
  id uuid primary key default gen_random_uuid(),
  user_email text not null,
  clock_in timestamptz not null default now(),
  clock_out timestamptz
);
create table if not exists pauses (
  id uuid primary key default gen_random_uuid(),
  shift_id uuid not null references shifts(id),
  kind text not null default 'break',  -- lunch | break
  started_at timestamptz not null default now(),
  ended_at timestamptz
);

-- ---------- Blocos de inatividade (nudges 20min) ----------
create table if not exists inactivity_blocks (
  id uuid primary key default gen_random_uuid(),
  shift_id uuid references shifts(id),
  started_at timestamptz not null,
  ended_at timestamptz,
  nudges_sent int default 0,
  queue_size int                      -- quantos cards esperando quando começou
);

-- ---------- Comissões (A4: $10/appointment que vira venda) ----------
create table if not exists commissions (
  id uuid primary key default gen_random_uuid(),
  appointment_id text not null unique,
  contact_id text not null,
  opportunity_id text,
  lead_name text,
  amount_usd numeric not null default 10,
  status text not null default 'potencial'
    check (status in ('potencial','confirmado','expirado')),
  booked_at timestamptz not null,
  resolved_at timestamptz,            -- quando virou confirmado/expirado
  transitions jsonb not null default '[]'::jsonb,  -- trilha [{from,to,at,reason}]
  created_at timestamptz not null default now()
);

-- ---------- Relatórios diários ----------
create table if not exists reports (
  id uuid primary key default gen_random_uuid(),
  report_date date not null,
  audience text not null check (audience in ('eugene','rafael')),
  content_md text not null,
  metrics jsonb,                      -- funil, metas binárias, ganhos
  created_at timestamptz not null default now(),
  unique (report_date, audience)
);

-- =====================================================================
-- RLS
-- =====================================================================
alter table worker_state enable row level security;
alter table config enable row level security;
alter table calls enable row level security;
alter table transcripts enable row level security;
alter table analyses enable row level security;
alter table cards enable row level security;
alter table shifts enable row level security;
alter table pauses enable row level security;
alter table inactivity_blocks enable row level security;
alter table commissions enable row level security;
alter table reports enable row level security;

-- Leitura: qualquer usuário autenticado do painel (eugene e rafael)
do $$ declare t text;
begin
  foreach t in array array['config','calls','transcripts','analyses','cards',
                           'shifts','pauses','inactivity_blocks','commissions','reports']
  loop
    execute format('create policy %I on %I for select to authenticated using (true)', t||'_read', t);
  end loop;
end $$;

-- worker_state: só owner lê (debug)
create policy worker_state_read on worker_state for select to authenticated
  using (public.user_role() = 'owner');

-- Escritas do painel (operador):
--   clock in/out e pausas próprias
create policy shifts_ins on shifts for insert to authenticated with check (true);
create policy shifts_upd on shifts for update to authenticated using (true);
create policy pauses_ins on pauses for insert to authenticated with check (true);
create policy pauses_upd on pauses for update to authenticated using (true);
--   fechar card de quote manualmente / editar rascunho
create policy cards_upd on cards for update to authenticated using (true);
--   relatório eugene: só owner vê o do rafael
drop policy if exists reports_read on reports;
create policy reports_read on reports for select to authenticated
  using (audience = 'eugene' or public.user_role() = 'owner');
--   config: só owner altera
create policy config_write on config for all to authenticated
  using (public.user_role() = 'owner') with check (public.user_role() = 'owner');

-- Demais escritas: somente service_role (worker) — sem policy de insert p/ authenticated.

-- ============ A12 (2026-07-08): integridade de score + portão de advice ============
create table if not exists lead_scores (
  contact_id text primary key,
  known int not null,
  max_possible int not null,
  badge text not null default 'partial',      -- call-verified | partial
  components jsonb not null,                  -- {car|momento|eng|int: {value,reason,source}}
  breakdown text,
  visited_store boolean default false,
  computed_at timestamptz not null default now()
);
alter table cards add column if not exists score_max int;
alter table cards add column if not exists score_badge text;
alter table cards add column if not exists score_breakdown text;

create table if not exists advice_rejected (
  id uuid primary key default gen_random_uuid(),
  call_id text, contact_id text,
  advice_en text, advice_pt text, evidencia text,
  motivo text not null,
  rejected_by text not null default 'haiku-critic',
  created_at timestamptz not null default now()
);

alter table lead_flags add column if not exists visited_store boolean default false;
alter table lead_flags add column if not exists visit_probable jsonb;
alter table lead_flags add column if not exists analysis_priority int;

create table if not exists technical_observations (   -- A11.1 modo observação
  id uuid primary key default gen_random_uuid(),
  call_id text, contact_id text, contact_name text,
  pergunta text, categoria text,
  transferida boolean, resposta_improvisada boolean,
  como_tratou text,
  promised_callback boolean default false,
  status text not null default 'observacao',
  created_at timestamptz not null default now()
);

create table if not exists daily_snapshots (           -- baseline análise total
  id uuid primary key default gen_random_uuid(),
  snapshot_date date not null unique,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table if not exists price_alerts (              -- A9.1 validação de ballpark
  id uuid primary key default gen_random_uuid(),
  call_id text, contact_id text,
  servico text, valor_falado text,
  kind text not null,            -- below_starting | off_table
  detail text, tier text,
  created_at timestamptz not null default now()
);

create table if not exists coupons (                   -- A13 cupom $200
  id uuid primary key default gen_random_uuid(),
  contact_id text not null, call_id text,
  source text not null default 'manual',
  contexto text, offered_by text,
  status text not null default 'offered',
  created_at timestamptz not null default now()
);
create table if not exists appointment_actions (       -- A14 Appointments Board
  id uuid primary key default gen_random_uuid(),
  event_id text not null, contact_id text,
  action text not null, value_usd numeric, acted_by text,
  status text not null default 'pending', error text,
  created_at timestamptz not null default now(), synced_at timestamptz
);

create table if not exists lead_states (               -- A16 Regra Zero: estado por lead
  contact_id text primary key,
  situacao text,
  state jsonb not null,
  computed_at timestamptz not null default now()
);

alter table cards add column if not exists phone text;   -- MVP rail: telefone no card

create table if not exists pendencias (                -- MVP item 6: verificador pós-call
  id uuid primary key default gen_random_uuid(),
  contact_id text not null, call_id text,
  kind text not null, fato text not null, acao text not null,
  resolucoes jsonb not null, snapshot jsonb,
  status text not null default 'open', resolved_by text,
  created_at timestamptz not null default now(), resolved_at timestamptz
);
create table if not exists beta_feedback (             -- MVP item 7: erro vira dado
  id uuid primary key default gen_random_uuid(),
  contact_id text, card_id uuid,
  tipo text not null, texto text, snapshot jsonb, reported_by text,
  created_at timestamptz not null default now()
);
