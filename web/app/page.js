"use client";
import { useEffect, useState, useCallback } from "react";
import { supabase } from "../lib/supabaseClient";
import EugeneView from "../components/EugeneView";
import OwnerView from "../components/OwnerView";

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

const EUGENE_EMAIL = "eugenebaruelova@gmail.com";

export default function Home() {
  const [session, setSession] = useState(undefined);
  const [data, setData] = useState(null);
  const [viewAs, setViewAs] = useState(null); // null | "eugene"

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
    const [cards, snoozed, doneToday, calls, analyses, shifts, pauses, comms, cfg] =
      await Promise.all([
        supabase.from("cards").select("*").eq("status", "open")
          .order("layer").order("score", { ascending: false, nullsFirst: false })
          .order("created_at").limit(40),
        supabase.from("cards").select("*").eq("status", "snoozed").limit(10),
        supabase.from("cards").select("*").eq("status", "done").gte("closed_at", iso),
        supabase.from("calls").select("id,direction,called_at,contact_id").gte("called_at", iso),
        supabase.from("analyses").select("payload,created_at,calls(contact_id)")
          .gte("created_at", iso).order("created_at", { ascending: false }).limit(8),
        supabase.from("shifts").select("*").gte("clock_in", iso),
        supabase.from("pauses").select("*").gte("started_at", iso),
        supabase.from("commissions").select("*").gte("booked_at", monthStart),
        supabase.from("config").select("key,value").in("key", ["stats_today", "bonus_period"]),
      ]);
    setData({
      cards: cards.data || [], snoozed: snoozed.data || [],
      doneToday: doneToday.data || [], calls: calls.data || [],
      analyses: analyses.data || [], shifts: shifts.data || [],
      pauses: pauses.data || [], commissions: comms.data || [],
      config: Object.fromEntries((cfg.data || []).map((r) => [r.key, r.value])),
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

  const role =
    session.user.app_metadata?.role ||
    ((session.user.email || "").includes("rafael") ? "owner" : "operator");

  if (role === "owner" && viewAs === "eugene") {
    return (
      <>
        <div style={{
          position: "sticky", top: 0, zIndex: 50, display: "flex",
          justifyContent: "center", padding: "8px 0", background: "#101828",
        }}>
          <span style={{ color: "#fff", fontSize: 13, fontWeight: 600, marginRight: 12, alignSelf: "center" }}>
            👁 Você está vendo a tela do Eugene (ao vivo, somente leitura)
          </span>
          <button className="btn primary sm" onClick={() => setViewAs(null)}>
            ← Voltar à visão do dono
          </button>
        </div>
        <EugeneView session={session} data={data} reload={load}
          preview previewEmail={EUGENE_EMAIL} />
      </>
    );
  }

  return role === "owner" ? (
    <OwnerView session={session} data={data} reload={load}
      onViewEugene={() => setViewAs("eugene")} />
  ) : (
    <EugeneView session={session} data={data} reload={load} />
  );
}
