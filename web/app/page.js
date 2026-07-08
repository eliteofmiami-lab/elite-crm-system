"use client";
import { useEffect, useState, useCallback } from "react";
import { supabase } from "../lib/supabaseClient";
import EugeneView from "../components/EugeneView";
import OwnerView from "../components/OwnerView";
import RailView from "../components/RailView";
import BoardView from "../components/BoardView";

const EUGENE_EMAIL = "eugenebaruelova@gmail.com";
// PAINEL DIÁRIO (missão definitiva 2026-07-08): espelho do GHL — visão única.
// EugeneView/OwnerView/RailView ficam preservadas no código, ocultas da UI.
const MVP_QUEUE_ONLY = true;

function Login() {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  async function go(e) {
    e.preventDefault();
    setErr("");
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    if (error) setErr("Invalid login — check e-mail and password.");
  }
  return (
    <form className="login" onSubmit={go}>
      <div className="lg"><img src="/elite-logo.png" alt="Elite Premium Detailing" style={{ height: 38 }} /></div>
      <input placeholder="e-mail" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="password" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      <button className="btn primary big" type="submit">Sign in</button>
      {err && <div className="err">{err}</div>}
    </form>
  );
}

export default function Home() {
  const [session, setSession] = useState(undefined);
  const [data, setData] = useState(null);
  const [mode, setMode] = useState("dashboard"); // owner: dashboard | queue | spy

  useEffect(() => {
    supabase.auth.getSession().then(({ data: d }) => setSession(d.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  const load = useCallback(async () => {
    if (!session) return;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const iso = today.toISOString();
    const monthStart = new Date(today.getFullYear(), today.getMonth(), 1).toISOString();
    const [cards, snoozed, wrapups, doneToday, calls, analyses, shifts, pauses, comms, cfg, flags, reports, techObs, priceAlerts, leadStates, leadScores, pendencias, boardCards, boardAttempts, boardComms, boardDays, inactivity] =
      await Promise.all([
        supabase.from("cards").select("*").eq("status", "open")
          .order("layer").order("score", { ascending: false, nullsFirst: false })
          .order("created_at").limit(40),
        supabase.from("cards").select("*").eq("status", "snoozed").limit(10),
        supabase.from("cards").select("*").eq("status", "wrapup").limit(10),
        supabase.from("cards").select("*").eq("status", "done").gte("closed_at", iso),
        supabase.from("calls").select("id,direction,called_at,contact_id").gte("called_at", iso),
        supabase.from("analyses").select("payload,created_at,calls(contact_id)")
          .gte("created_at", iso).order("created_at", { ascending: false }).limit(8),
        supabase.from("shifts").select("*").gte("clock_in", iso),
        supabase.from("pauses").select("*").gte("started_at", iso),
        supabase.from("commissions").select("*").gte("booked_at", monthStart),
        supabase.from("config").select("key,value").in("key",
          ["stats_today", "bonus_period", "test_contact_ids", "prices", "bonus_guard",
           "visit_briefing", "appointments_board", "board_config", "board_activity",
           "board_live", "board_live_error", "warmup_pool"]),
        supabase.from("lead_flags").select("contact_id,spanish_only,visited_store,visit_probable")
          .or("spanish_only.eq.true,visited_store.eq.true,visit_probable.not.is.null"),
        supabase.from("reports").select("*").order("report_date", { ascending: false }).limit(4),
        supabase.from("technical_observations").select("*").eq("status", "observacao")
          .order("created_at", { ascending: false }).limit(20),
        supabase.from("price_alerts").select("*")
          .order("created_at", { ascending: false }).limit(15),
        supabase.from("lead_states").select("contact_id,situacao,state"),
        supabase.from("lead_scores").select("contact_id,known,max_possible,badge,components"),
        supabase.from("pendencias").select("*").eq("status", "open").limit(300),
        supabase.from("board_cards").select("*")
          .or(`status.eq.open,day_created.eq.${new Date().toISOString().slice(0, 10)},resolved_at.gte.${iso}`)
          .limit(800),
        supabase.from("board_attempts").select("*").eq("day", new Date().toISOString().slice(0, 10)),
        supabase.from("board_commissions").select("*").gte("created_at", monthStart),
        supabase.from("board_days").select("*").gte("day", monthStart.slice(0, 10)),
        supabase.from("inactivity_blocks").select("*").gte("started_at", iso),
      ]);
    setData({
      cards: cards.data || [], snoozed: snoozed.data || [], wrapups: wrapups.data || [],
      doneToday: doneToday.data || [], calls: calls.data || [],
      analyses: analyses.data || [], shifts: shifts.data || [],
      pauses: pauses.data || [], commissions: comms.data || [],
      config: Object.fromEntries((cfg.data || []).map((r) => [r.key, r.value])),
      spanish: new Set((flags.data || []).filter((f) => f.spanish_only).map((f) => f.contact_id)),
      flags: Object.fromEntries((flags.data || []).map((f) => [f.contact_id, f])),
      reports: reports.data || [],
      techObs: techObs.data || [],
      priceAlerts: priceAlerts.data || [],
      states: Object.fromEntries((leadStates.data || []).map((s) => [s.contact_id, s])),
      scores: Object.fromEntries((leadScores.data || []).map((s) => [s.contact_id, s])),
      pendencias: pendencias.data || [],
      boardCards: boardCards.data || [],
      attempts: boardAttempts.data || [],
      commissions: boardComms.data || [],
      boardDays: boardDays.data || [],
      inactivity: inactivity.data || [],
    });
  }, [session]);

  useEffect(() => {
    if (!session) return;
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, [session, load]);

  if (session === undefined) return <div className="center">loading…</div>;
  if (!session) return <Login />;
  if (!data) return <div className="center">loading…</div>;

  const roleNow =
    session.user.app_metadata?.role ||
    ((session.user.email || "").includes("rafael") ? "owner" : "operator");

  // PAINEL DIÁRIO: visão única (Board; aba Owner só para o Rafael)
  if (MVP_QUEUE_ONLY) {
    return <BoardView session={session} data={data} reload={load} role={roleNow} />;
  }

  const role =
    session.user.app_metadata?.role ||
    ((session.user.email || "").includes("rafael") ? "owner" : "operator");

  if (role !== "owner") {
    // operador (Eugene): fila normal; cards em espanhol afundam com aviso
    return <EugeneView session={session} data={data} reload={load} sinkSpanish />;
  }

  if (mode === "queue") {
    return (
      <>
        <div style={{
          position: "sticky", top: 0, zIndex: 50, display: "flex",
          justifyContent: "center", gap: 12, padding: "8px 0", background: "#1D4ED8",
        }}>
          <span style={{ color: "#fff", fontSize: 13, fontWeight: 600, alignSelf: "center" }}>
            🛠 Working the queue as {session.user.email.split("@")[0]} — your clock-in, your tasks
          </span>
          <button className="btn ghost sm" onClick={() => setMode("dashboard")}>← Back to dashboard</button>
        </div>
        <EugeneView session={session} data={data} reload={load} />
      </>
    );
  }

  if (mode === "spy") {
    return (
      <>
        <div style={{
          position: "sticky", top: 0, zIndex: 50, display: "flex",
          justifyContent: "center", gap: 12, padding: "8px 0", background: "#101828",
        }}>
          <span style={{ color: "#fff", fontSize: 13, fontWeight: 600, alignSelf: "center" }}>
            👁 Viewing Eugene&apos;s screen (live, read-only)
          </span>
          <button className="btn primary sm" onClick={() => setMode("dashboard")}>← Back to dashboard</button>
        </div>
        <EugeneView session={session} data={data} reload={load}
          preview previewEmail={EUGENE_EMAIL} sinkSpanish />
      </>
    );
  }

  return (
    <OwnerView session={session} data={data}
      onViewEugene={() => setMode("spy")}
      onWorkQueue={() => setMode("queue")} />
  );
}
