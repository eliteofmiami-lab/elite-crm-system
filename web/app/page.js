"use client";
import { useEffect, useState, useCallback } from "react";
import { supabase } from "../lib/supabaseClient";

function Login() {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");
  async function go(e) {
    e.preventDefault();
    setErr("");
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    if (error) setErr("Login inválido — confira e-mail e senha.");
  }
  return (
    <form className="login" onSubmit={go}>
      <h1>⚡ Elite CRM</h1>
      <input placeholder="e-mail" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="senha" type="password" value={pw} onChange={(e) => setPw(e.target.value)} />
      <button className="btn primary big" type="submit">Entrar</button>
      {err && <div className="err">{err}</div>}
    </form>
  );
}

function Card({ c, onManualDone }) {
  const how = (c.how && c.how.passos) || [];
  return (
    <div className={`card l${c.layer}`}>
      <span className={`badge l${c.layer}`}>
        {c.layer === 1 ? "URGENTE" : c.layer === 2 ? "HOJE" : "FILA"}
      </span>
      {c.score ? <span className="score">{c.score}</span> : null}
      <h3>{c.title}</h3>
      <div className="why">{c.why}</div>
      {how.length > 0 && (
        <ul>{how.map((p, i) => <li key={i}>{p}</li>)}</ul>
      )}
      <div className="btnrow">
        <a className="btn primary" href={c.ghl_link} target="_blank" rel="noreferrer">
          Abrir no GHL →
        </a>
        {c.type === "quote_followup" && (
          <button className="btn ghost" onClick={() => onManualDone(c)}>feito ✓</button>
        )}
      </div>
    </div>
  );
}

export default function Fila() {
  const [session, setSession] = useState(undefined);
  const [cards, setCards] = useState([]);
  const [shift, setShift] = useState(null);
  const role =
    session?.user?.app_metadata?.role ||
    (session?.user?.email || "").includes("rafael") ? "owner" : "operator";

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  const load = useCallback(async () => {
    const { data } = await supabase
      .from("cards")
      .select("*")
      .eq("status", "open")
      .order("layer", { ascending: true })
      .order("score", { ascending: false, nullsFirst: false })
      .order("created_at", { ascending: true })
      .limit(60);
    setCards(data || []);
    if (session?.user?.email) {
      const { data: sh } = await supabase
        .from("shifts")
        .select("*")
        .eq("user_email", session.user.email)
        .is("clock_out", null)
        .limit(1);
      setShift((sh && sh[0]) || null);
    }
  }, [session]);

  useEffect(() => {
    if (!session) return;
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, [session, load]);

  if (session === undefined) return <div className="center">carregando…</div>;
  if (!session) return <Login />;

  async function clockIn() {
    await supabase.from("shifts").insert({ user_email: session.user.email });
    load();
  }
  async function clockOut() {
    await supabase.from("shifts").update({ clock_out: new Date().toISOString() }).eq("id", shift.id);
    load();
  }
  async function manualDone(c) {
    await supabase.from("cards").update({
      status: "done", result: "confirmado manualmente", closed_by: "manual-quote",
      closed_at: new Date().toISOString(),
    }).eq("id", c.id);
    load();
  }

  const gated = role !== "owner" && !shift;

  return (
    <div className="container">
      <div className="topbar">
        <h1>⚡ Fila {cards.length > 0 && `(${cards.length})`}</h1>
        {shift ? (
          <button className="btn ghost" onClick={clockOut}>sair ⏸</button>
        ) : (
          <span className="muted">{session.user.email.split("@")[0]}</span>
        )}
      </div>

      {!shift && (
        <div className="clockbar">
          <p className="muted" style={{ marginBottom: 10 }}>
            {gated ? "Bata o ponto para liberar a fila" : "Ponto não iniciado"}
          </p>
          <button className="btn primary big" onClick={clockIn}>▶ Clock in — começar o dia</button>
        </div>
      )}

      {!gated &&
        cards.map((c) => <Card key={c.id} c={c} onManualDone={manualDone} />)}
      {!gated && cards.length === 0 && (
        <div className="center">🎉 Fila limpa — nada pendente.</div>
      )}

      <nav className="tabs">
        <a href="/" className="active">📋 Fila</a>
        <a href="/placar">📊 Placar</a>
      </nav>
    </div>
  );
}
