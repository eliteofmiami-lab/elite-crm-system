"use client";
import { useEffect, useState } from "react";
import { supabase } from "../../lib/supabaseClient";

export default function Placar() {
  const [session, setSession] = useState(undefined);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
  }, []);

  useEffect(() => {
    if (!session) return;
    (async () => {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const iso = today.toISOString();
      const [open, doneToday, shifts] = await Promise.all([
        supabase.from("cards").select("id,layer", { count: "exact" }).eq("status", "open"),
        supabase.from("cards").select("id,result", { count: "exact" })
          .eq("status", "done").gte("closed_at", iso),
        supabase.from("shifts").select("*").gte("clock_in", iso),
      ]);
      const byLayer = { 1: 0, 2: 0, 3: 0 };
      (open.data || []).forEach((c) => { byLayer[c.layer] = (byLayer[c.layer] || 0) + 1; });
      const calls = (doneToday.data || []).filter((c) => (c.result || "").includes("liga")).length;
      const sms = (doneToday.data || []).filter((c) => (c.result || "").includes("SMS")).length;
      setStats({
        open: open.count || 0, byLayer,
        done: doneToday.count || 0, calls, sms,
        shifts: shifts.data || [],
      });
    })();
  }, [session]);

  if (session === undefined) return <div className="center">carregando…</div>;
  if (!session) { if (typeof window !== "undefined") window.location.href = "/"; return null; }

  return (
    <div className="container">
      <div className="topbar"><h1>📊 Placar de hoje</h1></div>
      {!stats ? (
        <div className="center">calculando…</div>
      ) : (
        <>
          <div className="stat"><span>✅ Cards resolvidos hoje</span><b>{stats.done}</b></div>
          <div className="stat"><span>📞 — por ligação</span><b>{stats.calls}</b></div>
          <div className="stat"><span>💬 — por SMS</span><b>{stats.sms}</b></div>
          <div className="stat"><span>📋 Fila aberta agora</span><b>{stats.open}</b></div>
          <div className="stat"><span>🔴 Urgentes esperando</span><b>{stats.byLayer[1]}</b></div>
          <div className="stat"><span>🟡 Do dia (quotes/confirmações)</span><b>{stats.byLayer[2]}</b></div>
          <div className="stat"><span>🔵 Fila fria/morna</span><b>{stats.byLayer[3]}</b></div>
          <div className="stat">
            <span>⏱ Turnos hoje</span>
            <b>{stats.shifts.map((s) => s.user_email.split("@")[0]).join(", ") || "—"}</b>
          </div>
        </>
      )}
      <nav className="tabs">
        <a href="/">📋 Fila</a>
        <a href="/placar" className="active">📊 Placar</a>
      </nav>
    </div>
  );
}
