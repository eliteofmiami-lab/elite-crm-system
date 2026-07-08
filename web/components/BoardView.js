"use client";
// PAINEL DIÁRIO (missão definitiva 2026-07-08) — espelho do GHL, gabarito visual:
// docs/design/mockup-painel-diario.html. Zero IA · zero escrita no GHL.
// Únicos writes (Supabase): clock in/out, pausas, beta_feedback (Owner).
import { useEffect, useMemo, useRef, useState } from "react";
import { supabase } from "../lib/supabaseClient";

const GHL = "https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/";
const COLS = [
  { n: 1, title: "Return · Reply · Hot", cap: "missed calls, unanswered SMS, HOT LEADS · oldest first" },
  { n: 2, title: "New Leads — Call ASAP", cap: "stage New Lead · oldest first" },
  { n: 3, title: "Tasks & Quote follow-ups", cap: "GHL tasks due · Urable no reply · quote without task = red" },
  { n: 4, title: "Pipeline — Contact 1/2/3", cap: "newest first · 1–2 calls/day · 2 moves today = done till tomorrow" },
  { n: 7, title: "Follow-ups", cap: "task due today/overdue · no task = red flag" },
  { n: 5, title: "Appointments · next 2 days", cap: "confirm the pending · know who's coming" },
  { n: 6, title: "Warm up", cap: "daily ration · Lost recoverable + 30d+ idle" },
];
const RED_KINDS = new Set(["followup_notask", "quote_notask"]);

function ageOf(ts) {
  if (!ts) return "";
  const m = (Date.now() - new Date(ts).getTime()) / 60000;
  if (m < 60) return `${Math.max(1, Math.round(m))}m`;
  if (m < 60 * 24) return `${Math.round(m / 60)}h`;
  return `${Math.round(m / 1440)}d`;
}
function ageClass(ts) {
  const h = (Date.now() - new Date(ts).getTime()) / 3600000;
  return h >= 48 ? "bad" : h >= 4 ? "warn" : "";
}
function beep() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.frequency.value = 880; g.gain.value = 0.08;
    o.start(); o.stop(ctx.currentTime + 0.35);
  } catch (_) { /* sem som, sem drama */ }
}

function KCard({ c, conf, isSpanish, isOwner, onSpanish }) {
  const [open, setOpen] = useState(false);
  const red = RED_KINDS.has(c.kind);
  return (
    <div className={`kcard${conf ? " conf" : ""}${open ? " open" : ""}`}
      style={red ? { border: "1.5px solid var(--red-border)", borderLeft: "4px solid var(--red)", background: "#FFFBFA" } : undefined}
      onClick={(e) => { if (e.target.closest("a,button,input")) return; setOpen(!open); }}>
      <div className="nm">{isSpanish ? "🇪🇸 " : ""}{c.nome || "—"}
        {conf
          ? <span className="ok">✓ {new Date(c.appt_start).toLocaleString("en-US", { weekday: "short", hour: "2-digit", minute: "2-digit" })}</span>
          : <span className={`age ${ageClass(c.origem_ts)}`}>{c.kind === "appt_confirm" && c.appt_start
              ? new Date(c.appt_start).toLocaleString("en-US", { weekday: "short", hour: "2-digit", minute: "2-digit" })
              : ageOf(c.origem_ts)}</span>}
      </div>
      <div className="veh">{c.veh || "—"} · {c.interest || "interest not set"}</div>
      <div className="org"><b>{(c.origem || "").split("·")[0]}</b>·{(c.origem || "").split("·").slice(1).join("·")}</div>
      {conf && (c.last_note
        ? <div className="note"><b>{c.last_note.split(":")[0]}:</b>{c.last_note.split(":").slice(1).join(":")}</div>
        : <div className="note empty">No notes on this contact yet — add the call notes so the visit starts prepared.</div>)}
      <div className="kx">
        <div className="row">
          <span className="ph">📞 {c.phone || "—"}</span>
          {onSpanish && (
            <button onClick={() => onSpanish(c, !isSpanish)}
              title={isSpanish ? "Send back to Eugene's board" : "Send to Rafael's board (Spanish speaker)"}
              style={{ border: "1px solid var(--line)", background: "var(--card)", borderRadius: 8,
                padding: "6px 10px", font: "600 11.5px Inter", cursor: "pointer", color: "var(--sub)" }}>
              {isSpanish ? (isOwner ? "Remove 🇪🇸 flag" : "🇪🇸 flagged") : "🇪🇸 Spanish only"}
            </button>
          )}
          <a className="open" href={GHL + c.contact_id} target="_blank" rel="noreferrer">Open ↗</a>
        </div>
        {c.closes_when && <div className="closes"><b>Closes when:</b>{c.closes_when.replace("Closes when:", "")}</div>}
        {isSpanish && <div style={{ fontSize: 11, color: "var(--purple-text)", marginTop: 6, fontWeight: 600 }}>
          Spanish speaker — lives on Rafael&apos;s board, off Eugene&apos;s.</div>}
      </div>
    </div>
  );
}

export default function BoardView({ session, data, reload, role }) {
  const [tab, setTab] = useState("board");
  const [live, setLive] = useState(null);
  const beeped = useRef({});
  const reloadT = useRef(0);
  const email = session.user.email;
  const isOwner = role === "owner";

  // CAMADA 2 — Supabase Realtime: mudança em board_cards chega na tela no segundo
  // da ingestão (zero F5). Throttle de 1.5s pra rajadas.
  useEffect(() => {
    const ch = supabase
      .channel("board-live")
      .on("postgres_changes", { event: "*", schema: "public", table: "board_cards" }, () => {
        const t = Date.now();
        if (t - reloadT.current > 1500) { reloadT.current = t; reload && reload(); }
      })
      .on("postgres_changes", { event: "*", schema: "public", table: "config",
        filter: "key=eq.board_live" }, (payload) => {
        setLive(payload.new?.value || null);
      })
      .subscribe();
    return () => { supabase.removeChannel(ch); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // CAMADA 3 — delta 60s: o navegador pinga /api/delta (throttle no servidor)
  useEffect(() => {
    let stop = false;
    async function ping() {
      try {
        const { data: s } = await supabase.auth.getSession();
        // cache-buster: URL única por chamada — CDN nunca serve HIT do delta
        await fetch(`/api/delta?t=${Date.now()}`, {
          cache: "no-store",
          headers: { Authorization: `Bearer ${s?.session?.access_token || ""}` } });
      } catch (_) { /* delta é reconciliação — falha silenciosa */ }
    }
    ping();
    const t = setInterval(() => { if (!stop) ping(); }, 60000);
    return () => { stop = true; clearInterval(t); };
  }, []);

  const liveVal = live || data.config.board_live || null;
  const lastEventTs = liveVal?.last_event ? new Date(liveVal.last_event) : null;
  const liveStale = !lastEventTs || (Date.now() - lastEventTs.getTime()) > 12 * 60000;
  const cfg = data.config.board_config || {};
  const goal = cfg.goal_calls || 100;
  const tiers = cfg.tiers || { t1: 30, t2: 35, t3: 40, rate1: 10, rate2: 20, bonus: 50, cap: 600 };

  const cards = data.boardCards || [];
  const open = cards.filter((c) => c.status === "open");
  const attempts = data.attempts || [];
  const myShift = (data.shifts || []).find((s) => s.user_email === email && !s.clock_out);
  const myPause = (data.pauses || []).find((p) => !p.ended_at &&
    (data.shifts || []).some((s) => s.id === p.shift_id && s.user_email === email));

  const validToday = attempts.filter((a) => a.user_key === "eugene" && a.valid).length;
  const comms = data.commissions || [];
  const won = comms.filter((c) => c.eligible && c.status === "won");
  const wonN = won.length;
  const earned = wonN <= tiers.t1 ? wonN * tiers.rate1
    : tiers.t1 * tiers.rate1 + Math.min(wonN - tiers.t1, tiers.t3 - tiers.t1) * tiers.rate2;
  const awaiting = comms.filter((c) => c.eligible && ["done_waiting", "confirmed", "booked"].includes(c.status));
  const nextRate = wonN >= tiers.t1 ? tiers.rate2 : tiers.rate1;
  const potential = awaiting.length * nextRate;
  const toConfirm = open.filter((c) => c.kind === "appt_confirm").length;
  const booked = comms.filter((c) => c.eligible).length;
  const confirmed = comms.filter((c) => c.eligible && ["confirmed", "done_waiting", "won"].includes(c.status)).length;
  const expired = comms.filter((c) => c.eligible && c.status === "expired").length;

  const days = data.boardDays || [];
  const now = new Date();
  const fortnightStart = now.getDate() <= 15 ? 1 : 16;
  const fdays = days.filter((d) => {
    const dd = new Date(d.day + "T12:00:00");
    return dd.getMonth() === now.getMonth() && dd.getDate() >= fortnightStart && dd.getDate() < now.getDate();
  });
  const cleanDays = fdays.filter((d) => d.clean).length;
  const bonusLost = fdays.some((d) => d.clean === false);
  const fortLabel = fortnightStart === 1 ? `${now.toLocaleString("en-US", { month: "short" })} 1–15`
    : `${now.toLocaleString("en-US", { month: "short" })} 16–${new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()}`;

  const myUnres = open.filter((c) => c.unres && c.unres_call_user === "eugene");
  const rafUnres = open.filter((c) => c.unres && c.unres_call_user === "rafael");

  // inatividade: última tentativa/atividade do Eugene (só quando clocked-in, fora de pausa)
  const lastAct = useMemo(() => {
    const ts = attempts.filter((a) => a.user_key === "eugene").map((a) => new Date(a.call_ts).getTime());
    return ts.length ? Math.max(...ts) : (myShift ? new Date(myShift.clock_in).getTime() : null);
  }, [attempts, myShift]);
  const idleMin = myShift && !myPause && lastAct ? (Date.now() - lastAct) / 60000 : 0;
  const hhmm = now.getHours() * 60 + now.getMinutes();
  const [ckH, ckM] = (cfg.checkpoint || "13:00").split(":").map(Number);
  const behindPace = hhmm >= ckH * 60 + ckM && validToday < goal * 0.5;

  useEffect(() => {
    if (idleMin >= 15 && !beeped.current.idle) { beep(); beeped.current.idle = true; }
    if (idleMin < 10) beeped.current.idle = false;
    if (behindPace && !beeped.current.pace) { beep(); beeped.current.pace = true; }
  }, [idleMin, behindPace]);

  async function clockIn() {
    await supabase.from("shifts").insert({ user_email: email });
    reload();
  }
  async function clockOut() {
    if (myShift) await supabase.from("shifts").update({ clock_out: new Date().toISOString() }).eq("id", myShift.id);
    reload();
  }
  async function breakToggle() {
    if (myPause) await supabase.from("pauses").update({ ended_at: new Date().toISOString() }).eq("id", myPause.id);
    else if (myShift) await supabase.from("pauses").insert({ shift_id: myShift.id, kind: "break" });
    reload();
  }

  // gate de clock-in (só operador)
  if (!isOwner && !myShift) {
    return (
      <div className="wrap" style={{ maxWidth: 520, textAlign: "center", paddingTop: 60 }}>
        <img src="/elite-logo.png" alt="Elite" style={{ height: 34, marginBottom: 18 }} />
        <h1 style={{ fontSize: 20, marginBottom: 6 }}>Daily Board</h1>
        <p style={{ color: "var(--sub)", marginBottom: 8 }}>
          {open.length} cards waiting · {open.filter((c) => c.coluna === 5 && c.kind === "appt_confirm").length} appointments to confirm
        </p>
        <button className="btn" style={{ background: "var(--blue)", color: "#fff", borderColor: "var(--blue)", fontSize: 15, padding: "12px 30px" }}
          onClick={clockIn}>Clock in</button>
        <p style={{ color: "var(--faint)", fontSize: 12, marginTop: 12 }}>The board unlocks after clock-in.</p>
      </div>
    );
  }

  // 🇪🇸 Spanish-only: sai do board do Eugene, vive no do Rafael (lead_flags — Supabase)
  const spanishSet = data.spanish || new Set();
  async function flagSpanish(c, on) {
    if (on) {
      await supabase.from("lead_flags").upsert(
        { contact_id: c.contact_id, spanish_only: true, set_by: email },
        { onConflict: "contact_id" });
    } else {
      await supabase.from("lead_flags").update({ spanish_only: false })
        .eq("contact_id", c.contact_id);
    }
    reload && reload();
  }
  const openByCol = (n) => open.filter((c) => c.coluna === n)
    .filter((c) => (isOwner ? true : !spanishSet.has(c.contact_id)))
    .sort((a, b) => {
      // regra Rafael: Pipeline (col 4) = mais NOVOS primeiro; resto mais antigo primeiro.
      // Vermelhos de task faltando sobem pro topo da coluna deles.
      const redDiff = (RED_KINDS.has(b.kind) ? 1 : 0) - (RED_KINDS.has(a.kind) ? 1 : 0);
      if (redDiff) return redDiff;
      const ta = new Date(a.origem_ts || a.created_at);
      const tb = new Date(b.origem_ts || b.created_at);
      return n === 4 ? tb - ta : ta - tb;
    });
  const today = new Date().toISOString().slice(0, 10);
  const createdToday = (n) => cards.filter((c) => c.coluna === n && c.day_created === today).length;
  const resolvedToday = (n) => cards.filter((c) => c.coluna === n && c.status === "resolved" &&
    (c.resolved_at || "").slice(0, 10) === today).length;
  const aging = open.filter((c) => (Date.now() - new Date(c.origem_ts || c.created_at)) / 86400000 >= 2 && c.coluna !== 5);
  const act = (data.config.board_activity || {}).users || {};

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="tt"><h1>Daily Board</h1>
          <span className="d">{now.toLocaleString("en-US", { weekday: "long", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
            {" · "}
            <span style={{ color: liveStale ? "var(--amber-text)" : "var(--green-text)", fontWeight: 600 }}>
              {liveStale ? "⟳ syncing" : "● Live"}
              {lastEventTs ? ` · last event ${lastEventTs.toLocaleTimeString("en-US", { hour12: false })}` : ""}
            </span>
          </span></div>
        {isOwner && (
          <div className="tabs">
            <button className={`tab${tab === "board" ? " on" : ""}`} onClick={() => setTab("board")}>Board</button>
            <button className={`tab${tab === "owner" ? " on" : ""}`} onClick={() => setTab("owner")}>Owner · Rafael</button>
          </div>
        )}
        <div className="pills">
          {myShift
            ? <span className="pill"><span className="dot"></span>Clocked in {new Date(myShift.clock_in).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}{myPause ? " · on break" : ""}</span>
            : <span className="pill" style={{ background: "#F2F4F7", borderColor: "var(--line)", color: "var(--sub)" }}>off shift</span>}
          {myShift && <button className="btn" onClick={breakToggle}>{myPause ? "End break" : "Start break"}</button>}
          {myShift && <button className="btn out" onClick={clockOut}>Clock out</button>}
          {!myShift && isOwner && <button className="btn" onClick={clockIn}>Clock in</button>}
        </div>
      </div>

      {tab === "board" && (
        <div>
          {idleMin >= 15 && <div className="banner" style={{ background: "var(--red-soft)", borderColor: "var(--red-border)", color: "var(--red-text)" }}>⏰ {Math.floor(idleMin)} min without activity — the board is waiting</div>}
          {idleMin >= 10 && idleMin < 15 && <div className="banner">⚠ {Math.floor(idleMin)} min without activity — the board is waiting</div>}
          {behindPace && <div className="banner">🕐 Midday check: {validToday}/{goal} valid calls — behind pace. Hit the queue and warm-up list.</div>}

          <div className="earn">
            <div className="earnrow">
              <div className="sec"><div className="lbl">Calls today · goal {goal}</div>
                <div className="big">{validToday}<span style={{ fontSize: 13, color: "var(--sub)" }}>/{goal} valid</span></div>
                <div className="pbar"><i style={{ width: `${Math.min(100, validToday / goal * 100)}%` }} /></div>
                <div className="sub2">valid: answered · or 25s+ voicemail + your text ≤10m · yours only</div></div>
              <div className="sec"><div className="lbl">Sales goal · {now.toLocaleString("en-US", { month: "long" })} · min {tiers.t1}</div>
                <div className="big">{wonN}<span style={{ fontSize: 13, color: "var(--sub)" }}>/{tiers.t3}</span></div>
                <div className="gbar"><i style={{ width: `${Math.min(100, wonN / tiers.t3 * 100)}%` }} />
                  <span className="mk m30"><span>{tiers.t1}</span></span><span className="mk m35"><span>{tiers.t2}</span></span></div>
                <div className="sub2" style={{ marginTop: 0 }}>${tiers.rate1} up to {tiers.t1} · <b>${tiers.rate2} for sales {tiers.t1 + 1}–{tiers.t3}</b></div></div>
              <div className="sec"><div className="lbl">Your wins · {now.toLocaleString("en-US", { month: "long" })}</div>
                <div className="big">${earned}<span style={{ fontSize: 13, color: "var(--sub)" }}> earned</span></div>
                <div className="sub2">{booked} booked · {confirmed} confirmed · <b>{wonN} won</b> · {expired} expired</div></div>
              <div className="sec"><div className="lbl">Potential</div>
                <div className="big" style={{ color: "var(--green-text)" }}>${potential}</div>
                <div className="sub2"><b>{awaiting.length} awaiting</b> · booked &amp; done, waiting to close</div>
                {toConfirm > 0 && <div className="sub2" style={{ color: "var(--amber-text)", fontWeight: 600 }}>⚠ {toConfirm} to confirm — miss = clean day lost</div>}</div>
              <div className="sec"><div className="lbl">Clean-board bonus · {fortLabel}</div>
                <div className="big">${tiers.bonus} <span style={{ fontSize: 13, color: bonusLost ? "var(--red-text)" : "var(--green-text)" }}>
                  {bonusLost ? "lost" : `${cleanDays}/${fdays.length || 0} · on track`}</span></div>
                <div className="sub2">{bonusLost
                  ? `bonus lost — restarts on the ${fortnightStart === 1 ? "16th" : "1st"}`
                  : "all days clean → paid · one miss = restarts next fortnight"}</div></div>
            </div>
            <div className="earnfoot">
              <div className="foot-note"><b>Ladder:</b> {tiers.t1} = ${tiers.t1 * tiers.rate1} · {tiers.t2} = ${tiers.t1 * tiers.rate1 + (tiers.t2 - tiers.t1) * tiers.rate2} · {tiers.t3} = ${tiers.t1 * tiers.rate1 + (tiers.t3 - tiers.t1) * tiers.rate2} &nbsp;·&nbsp; <b>Clean day:</b> {goal} valid calls + zero unresolved + confirmations &amp; today's tasks done · fortnight bonus is all-or-nothing</div>
              <div className="day"><div className="lbl">Max this month</div>
                <div className="big" style={{ fontSize: 16 }}>${tiers.t1 * tiers.rate1 + (tiers.t3 - tiers.t1) * tiers.rate2 + 2 * tiers.bonus}</div>
                <div className="sub2">${tiers.t1 * tiers.rate1 + (tiers.t3 - tiers.t1) * tiers.rate2} sales + ${2 * tiers.bonus} clean-board</div>
                <div className="ok" style={{ marginTop: 4 }}>Today: {myUnres.length === 0 ? "✔ on track" : `${myUnres.length} to resolve`}</div></div>
            </div>
          </div>

          {myUnres.length > 0 && (
            <div className="nores">
              <div className="nh">⏱ YOUR CALLS WITHOUT RESOLUTION · {myUnres.length} <span style={{ fontWeight: 500, fontSize: 11, opacity: .8 }}>— only calls made by you; Rafael&apos;s show on his tab</span></div>
              {myUnres.map((c) => (
                <div className="ncard" key={c.id}>
                  <div style={{ flex: 1, minWidth: 240 }}>
                    <div className="t">Call {c.unres_call_ts ? new Date(c.unres_call_ts).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) : ""} with {c.nome} — {c.unres_call_answered ? `answered (${Math.floor((c.unres_call_dur || 0) / 60)}m ${(c.unres_call_dur || 0) % 60}s)` : "not answered"} · no resolution registered</div>
                    <div className="why">Every finished call needs one outcome in GHL:</div>
                    <div className="tree"><b>Book appointment</b> (calendar) · <b>Create follow-up task</b> (with date) · <b>Send estimate</b> (Urable link + move to Quote Sent) · <b>Not interested → mark Lost with reason</b>. Unanswered call: <b>move to next stage</b>.</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 8, alignItems: "flex-end" }}>
                    <span className="age">open {ageOf(c.unres_call_ts)}</span>
                    <a className="open" href={GHL + c.contact_id} target="_blank" rel="noreferrer"
                      style={{ font: "600 12px Inter", color: "#fff", background: "var(--red)", borderRadius: 8, padding: "7px 12px", textDecoration: "none" }}>Open ↗</a>
                  </div>
                </div>
              ))}
            </div>
          )}

          <div className="board">
            {COLS.map((col) => {
              const items = openByCol(col.n);
              const toConf = items.filter((c) => c.grupo === "to_confirm");
              const confd = items.filter((c) => c.grupo === "confirmed");
              return (
                <div className="col" key={col.n}>
                  <h2>{col.title} <span className="n">{items.length}</span></h2>
                  <div className="cap">{col.cap}</div>
                  {col.n === 5 ? (
                    <>
                      <div className="subhead">To confirm · {toConf.length}</div>
                      {toConf.map((c) => <KCard key={c.id} c={c}
                        isSpanish={spanishSet.has(c.contact_id)} isOwner={isOwner} onSpanish={flagSpanish} />)}
                      <div className="subhead">✓ Confirmed — who&apos;s coming · {confd.length}</div>
                      {confd.map((c) => <KCard key={c.id} c={c} conf
                        isSpanish={spanishSet.has(c.contact_id)} isOwner={isOwner} onSpanish={flagSpanish} />)}
                    </>
                  ) : items.map((c) => <KCard key={c.id} c={c}
                    isSpanish={spanishSet.has(c.contact_id)} isOwner={isOwner} onSpanish={flagSpanish} />)}
                  {items.length === 0 && <div style={{ color: "var(--faint)", fontSize: 12, padding: "8px 4px" }}>clear ✓</div>}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {tab === "owner" && isOwner && (
        <div>
          {liveStale && (
            <div className="banner">⚠ Realtime feed stale — no push/delta event in 12+ min. Check the GHL webhook workflows and the Vercel env vars (GUIA_WEBHOOKS_REALTIME.md).</div>
          )}
          {data.config.board_live_error && (
            <div className="banner" style={{ background: "var(--red-soft)", borderColor: "var(--red-border)", color: "var(--red-text)" }}>
              ✕ Push handler error at {String(data.config.board_live_error.at || "").slice(11, 19)}: {String(data.config.board_live_error.error || "").slice(0, 120)}
            </div>
          )}
          <div className="grid2">
            <div className="ccard">
              <h3>Today by column</h3>
              <table className="ct"><thead><tr><th>Column</th><th>Created</th><th>Resolved</th><th>Open</th></tr></thead><tbody>
                {COLS.map((col) => (
                  <tr key={col.n}><td>{col.title}</td><td>{createdToday(col.n)}</td><td>{resolvedToday(col.n)}</td><td>{openByCol(col.n).length}</td></tr>
                ))}
                <tr><td><b>No resolution (calls)</b></td><td>—</td><td>—</td>
                  <td className="bad">{myUnres.length + rafUnres.length}</td></tr>
              </tbody></table>
            </div>
            <div className="ccard">
              <h3>No resolution + aging cards</h3>
              {[...myUnres.map((c) => ({ ...c, who: "Eugene" })), ...rafUnres.map((c) => ({ ...c, who: "Rafael" }))].map((c) => (
                <div className="lrow" key={c.id}><span className="tag">No resolution</span>
                  <span><b>{c.nome}</b> — call {c.unres_call_answered ? "answered" : "not answered"} {c.unres_call_ts ? new Date(c.unres_call_ts).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }) : ""} · <b>by {c.who}</b></span>
                  <span className="mono">open {ageOf(c.unres_call_ts)}</span></div>
              ))}
              {aging.slice(0, 10).map((c) => (
                <div className="lrow" key={c.id}><span className="tag old">2+ days</span>
                  <span><b>{c.nome}</b> — {(c.origem || "").slice(0, 70)}</span>
                  <span className="mono">{ageOf(c.origem_ts)}</span></div>
              ))}
              {myUnres.length + rafUnres.length + aging.length === 0 && <p style={{ color: "var(--faint)", fontSize: 12.5 }}>Nothing — clean board.</p>}
            </div>
          </div>
          <div className="ccard" style={{ marginBottom: 14 }}>
            <h3>Appointments — next 2 days</h3>
            {openByCol(5).map((c) => (
              <div className="lrow" key={c.id}>
                <span className={c.grupo === "confirmed" ? "tag" : "tag old"}
                  style={c.grupo === "confirmed" ? { background: "var(--green-soft)", color: "var(--green-text)" } : {}}>
                  {c.grupo === "confirmed" ? "✓ " : "To confirm · "}
                  {c.appt_start ? new Date(c.appt_start).toLocaleString("en-US", { weekday: "short", hour: "numeric", minute: "2-digit" }) : ""}
                </span>
                <span><b>{c.nome}</b> · {c.veh || "—"} · {c.interest || "—"}{c.last_note ? <> — {c.last_note.slice(0, 120)}</> : c.grupo === "confirmed" ? <> — <b style={{ color: "var(--amber-text)" }}>no notes on contact</b></> : null}</span>
              </div>
            ))}
            {openByCol(5).length === 0 && <p style={{ color: "var(--faint)", fontSize: 12.5 }}>No appointments in the window.</p>}
          </div>
          <div className="ccard" style={{ marginBottom: 14 }}>
            <h3>Eugene&apos;s earnings — {now.toLocaleString("en-US", { month: "long" })}</h3>
            <p style={{ fontSize: 13, color: "var(--sub)" }}>
              <b>Sales this month: {wonN} · tiers {tiers.t1} / {tiers.t2} / {tiers.t3}</b> (${tiers.rate1} up to {tiers.t1}; ${tiers.rate2} for {tiers.t1 + 1}–{tiers.t3}) ·
              confirmed commissions: <b style={{ color: "var(--green-text)" }}>${earned}</b> · potential: ${potential} ({awaiting.length} awaiting) · expired: {expired} ·
              <b> Fortnight bonus ({fortLabel}): ${tiers.bonus} at stake — {cleanDays}/{fdays.length} clean days{bonusLost ? " · LOST" : ""}</b> ·
              <b> monthly incentive cap: ${tiers.t1 * tiers.rate1 + (tiers.t3 - tiers.t1) * tiers.rate2 + 2 * tiers.bonus}</b>.
              Clean day = <b>{goal} valid attempts</b> + zero unresolved calls + confirmations done + today&apos;s tasks completed.
            </p>
            <div style={{ marginTop: 8, fontSize: 12, color: "var(--faint)" }}>
              Commission audit trail: {comms.filter((c) => c.eligible).slice(0, 6).map((c) => `${c.nome || c.contact_id} (${c.reason})`).join(" · ") || "—"}
            </div>
          </div>
          <OwnerFeedback email={email} />
          <div className="ccard" style={{ marginTop: 14 }}>
            <h3>🇪🇸 Spanish-only leads — yours</h3>
            <p style={{ fontSize: 13, color: "var(--sub)" }}>
              {open.filter((c) => spanishSet.has(c.contact_id)).length} open card(s) flagged Spanish
              — hidden from Eugene&apos;s board, visible on yours (badge 🇪🇸 on the card).
              Flag/unflag lives inside each card.
            </p>
          </div>
          <div className="ccard" style={{ marginTop: 14 }}>
            <h3>Activity by user — today</h3>
            <p style={{ fontSize: 13, color: "var(--sub)" }}>
              <b>Eugene:</b> {(act.eugene || {}).dials || 0} dials · {(act.eugene || {}).valid || 0} valid · {(act.eugene || {}).sms || 0} SMS
              &nbsp;·&nbsp; <b>Rafael:</b> {(act.rafael || {}).dials || 0} calls · {(act.rafael || {}).sms || 0} SMS <span style={{ color: "var(--faint)" }}>(not counted in Eugene&apos;s goals)</span>
              &nbsp;·&nbsp; <b>Automation:</b> {(act.automation || {}).sms || 0} SMS
            </p>
          </div>
          <div className="ccard" style={{ marginTop: 14 }}>
            <h3>Eugene&apos;s shift</h3>
            <p style={{ fontSize: 13, color: "var(--sub)" }}>
              {(() => {
                const es = (data.shifts || []).find((s) => s.user_email?.includes("eugene") && !s.clock_out) ||
                  (data.shifts || []).find((s) => s.user_email?.includes("eugene"));
                const blocks = (data.inactivity || []);
                return es
                  ? <>Clock-in <b>{new Date(es.clock_in).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</b>
                    {es.clock_out ? <> · clock-out <b>{new Date(es.clock_out).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</b></> : " · on shift"}
                    · declared breaks: {(data.pauses || []).filter((p) => p.shift_id === es.id).length}
                    · inactivity blocks: <b style={{ color: blocks.length ? "var(--amber-text)" : "inherit" }}>{blocks.length}</b>
                    · valid attempts: <b>{validToday}/{goal}</b></>
                  : "No clock-in today.";
              })()}
            </p>
          </div>
        </div>
      )}
      <style>{MOCKUP_CSS}</style>
    </div>
  );
}

function OwnerFeedback({ email }) {
  const [ref, setRef] = useState("");
  const [txt, setTxt] = useState("");
  const [sent, setSent] = useState(false);
  return (
    <div className="ccard">
      <h3>Beta feedback <span style={{ fontWeight: 500, fontSize: 11.5, color: "var(--faint)" }}>· owner only — goes to BETA_FEEDBACK.md</span></h3>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 6 }}>
        <input placeholder="Lead / card (e.g. K Washington — quote follow-up)" value={ref}
          onChange={(e) => setRef(e.target.value)}
          style={{ flex: 1, minWidth: 220, border: "1px solid var(--line)", borderRadius: 8, padding: "9px 11px", font: "400 12.5px Inter" }} />
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        <input placeholder="What's wrong or missing…" value={txt} onChange={(e) => setTxt(e.target.value)}
          style={{ flex: 1, border: "1px solid var(--line)", borderRadius: 8, padding: "9px 11px", font: "400 12.5px Inter" }} />
        <button className="btn" style={{ background: "var(--blue)", borderColor: "var(--blue)", color: "#fff" }}
          onClick={async () => {
            if (!txt && !ref) return;
            await supabase.from("beta_feedback").insert({
              tipo: "outro", texto: `[${ref}] ${txt}`, reported_by: email,
              snapshot: { referencia: ref } });
            setSent(true); setRef(""); setTxt("");
          }}>Send</button>
      </div>
      {sent && <p style={{ color: "var(--green-text)", fontSize: 12, marginTop: 6 }}>✓ Logged — nothing changes automatically; it goes to the daily BETA_FEEDBACK.md.</p>}
    </div>
  );
}

const MOCKUP_CSS = `
  :root{--bg:#F4F6FA;--card:#FFFFFF;--line:#E4E7EC;--ink:#101828;--sub:#475467;--faint:#98A2B3;--blue:#2970FF;--blue-deep:#1D4ED8;--blue-soft:#EFF4FF;--green:#12B76A;--green-soft:#ECFDF3;--green-text:#067647;--green-border:#ABEFC6;--amber:#F79009;--amber-soft:#FFFAEB;--amber-text:#B54708;--amber-border:#FEDF89;--red:#F04438;--red-soft:#FEF3F2;--red-text:#B42318;--red-border:#FDA29B;--purple-soft:#F4F0FF;--purple-text:#5925DC;--shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.08)}
  body{background:var(--bg);color:var(--ink);font-family:'Inter',system-ui,sans-serif;font-size:13.5px;line-height:1.5}
  .wrap{max-width:1600px;margin:0 auto;padding:18px 16px 40px}
  .topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:12px}
  .tt{display:flex;align-items:baseline;gap:10px}.tt h1{font-size:18px;font-weight:700}.tt .d{font-size:12px;color:var(--faint)}
  .tabs{display:flex;gap:4px;background:#E9EDF3;border-radius:10px;padding:3px}
  .tab{border:none;background:transparent;font:600 12.5px 'Inter';color:var(--sub);padding:7px 14px;border-radius:8px;cursor:pointer}
  .tab.on{background:var(--card);color:var(--ink);box-shadow:var(--shadow)}
  .pills{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .pill{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:500;padding:6px 12px;border-radius:999px;border:1px solid var(--green-border);background:var(--green-soft);color:var(--green-text)}
  .pill .dot{width:7px;height:7px;border-radius:50%;background:var(--green)}
  .btn{appearance:none;cursor:pointer;border-radius:8px;font:600 12px 'Inter';padding:8px 13px;background:var(--card);border:1px solid #D0D5DD;color:#344054}
  .btn:hover{background:#F9FAFB}.btn.out{color:var(--red-text);border-color:var(--red-border)}
  .banner{display:flex;align-items:center;gap:10px;background:var(--amber-soft);border:1px solid var(--amber-border);color:var(--amber-text);border-radius:10px;padding:9px 14px;font-weight:500;margin-bottom:12px;font-size:13px}
  .earn{background:var(--green-soft);border:1px solid var(--green-border);border-radius:12px;padding:16px 20px 14px;margin-bottom:12px}
  .earnrow{display:grid;grid-template-columns:repeat(5,1fr);gap:20px;align-items:start}
  @media (max-width:1100px){.earnrow{grid-template-columns:repeat(2,1fr)}}
  .earnrow .sec{min-width:0}
  .foot-note{font-size:10.5px;color:var(--sub);line-height:1.5;max-width:62%}
  .earnfoot{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;margin-top:10px;padding-top:8px;border-top:1px dashed var(--green-border)}
  .earn .big{font-size:20px;font-weight:700;color:var(--green-text)}
  .earn .lbl{font-size:11px;font-weight:600;letter-spacing:.03em;text-transform:uppercase;color:var(--green-text);opacity:.75}
  .earn .sec{min-width:150px}.earn .sub2{font-size:11.5px;color:var(--sub);margin-top:6px;line-height:1.5}
  .earn .day{text-align:right}
  .pbar{width:100%;height:8px;background:#D7F0E1;border-radius:99px;overflow:hidden;margin-top:5px}
  .pbar i{display:block;height:100%;background:var(--green);border-radius:99px}
  .gbar{position:relative;width:100%;height:10px;background:#D7F0E1;border-radius:99px;margin-top:8px;margin-bottom:20px}
  .gbar i{display:block;height:100%;background:var(--green);border-radius:99px}
  .gbar .mk{position:absolute;top:-3px;width:2px;height:16px;background:var(--green-text);opacity:.55}
  .gbar .mk.m30{left:75%}.gbar .mk.m35{left:87.5%}
  .gbar .mk span{position:absolute;top:16px;left:-14px;font-size:9.5px;font-weight:700;color:var(--green-text);white-space:nowrap}
  .earn .ok{font-weight:700;color:var(--green-text);font-size:13px}
  .nores{background:var(--red-soft);border:1.5px solid var(--red-border);border-radius:12px;padding:12px 14px;margin-bottom:14px}
  .nores .nh{display:flex;align-items:center;gap:8px;font-weight:700;color:var(--red-text);font-size:13.5px;margin-bottom:8px}
  .nores .ncard{background:var(--card);border:1px solid var(--red-border);border-left:4px solid var(--red);border-radius:10px;padding:11px 14px;display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap;margin-bottom:8px}
  .nores .ncard .t{font-weight:700}.nores .ncard .why{color:var(--sub);font-size:12.5px;margin-top:2px}
  .nores .tree{font-size:12px;color:var(--ink);background:#FFF7F6;border:1px dashed var(--red-border);border-radius:8px;padding:8px 11px;margin-top:8px;line-height:1.55}
  .nores .age{margin-left:auto;font-weight:700;color:var(--red-text);white-space:nowrap;font-size:12.5px}
  .board{display:flex;gap:12px;overflow-x:auto;padding-bottom:8px}
  .col{background:#EEF1F6;border:1px solid var(--line);border-radius:12px;min-width:285px;max-width:285px;padding:10px;flex:none}
  .col h2{font-size:12px;font-weight:700;letter-spacing:.03em;text-transform:uppercase;color:var(--sub);display:flex;justify-content:space-between;align-items:center;margin:2px 4px 10px}
  .col h2 .n{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:1px 9px;font-size:11.5px;color:var(--ink)}
  .col .cap{font-size:10.5px;color:var(--faint);margin:-6px 4px 8px;font-weight:500}
  .kcard{background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow);padding:10px 12px;margin-bottom:8px;cursor:pointer}
  .kcard:hover{border-color:#C7D2E2}
  .kcard .nm{font-weight:600;font-size:13.5px;display:flex;justify-content:space-between;gap:8px}
  .kcard .age{font-size:10.5px;font-weight:700;color:var(--faint);white-space:nowrap}
  .kcard .age.warn{color:var(--amber-text)}.kcard .age.bad{color:var(--red-text)}
  .kcard .veh{font-size:12px;color:var(--sub);margin-top:1px}
  .kcard .org{font-size:11px;color:var(--faint);margin-top:5px;display:flex;align-items:center;gap:5px}
  .kcard .org b{color:var(--sub);font-weight:600}
  .kx{display:none;border-top:1px solid var(--line);margin-top:9px;padding-top:9px}
  .kcard.open .kx{display:block}
  .kx .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:7px}
  .kx .ph{font-size:12.5px;color:var(--sub);font-weight:500}
  .kx a.open{font:600 12px 'Inter';color:#fff;background:var(--blue);border-radius:8px;padding:7px 12px;text-decoration:none}
  .kx .closes{font-size:11px;color:var(--faint);line-height:1.5;background:#F8FAFC;border-radius:8px;padding:7px 10px}
  .kx .closes b{color:var(--sub)}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
  @media (max-width:820px){.grid2{grid-template-columns:1fr}}
  .ccard{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);padding:16px 18px}
  .ccard h3{font-size:14px;font-weight:600;margin-bottom:10px}
  table.ct{width:100%;border-collapse:collapse;font-size:12.5px}
  .ct th,.ct td{padding:7px 8px;border-top:1px solid var(--line);text-align:right}
  .ct th:first-child,.ct td:first-child{text-align:left}
  .ct thead th{color:var(--sub);font-weight:600;font-size:11.5px;border-top:none}
  .ct .bad{color:var(--red-text);font-weight:700}
  .lrow{display:flex;gap:10px;padding:8px 0;border-bottom:1px solid var(--line);font-size:12.5px;align-items:baseline}
  .lrow:last-child{border-bottom:none}
  .lrow .tag{font-size:10px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:3px 8px;border-radius:999px;background:var(--red-soft);color:var(--red-text);flex:none}
  .lrow .tag.old{background:var(--amber-soft);color:var(--amber-text)}
  .lrow .mono{margin-left:auto;color:var(--faint);white-space:nowrap;font-size:11.5px}
  .kcard.conf{border-left:3px solid var(--green);background:#FBFEFC}
  .kcard.conf .ok{font-size:10.5px;font-weight:700;color:var(--green-text);letter-spacing:.03em}
  .note{font-size:11.5px;color:var(--sub);background:#F6F8FA;border:1px solid var(--line);border-radius:8px;padding:7px 10px;margin-top:7px;line-height:1.5}
  .note b{color:var(--ink)}
  .note.empty{color:var(--amber-text);background:var(--amber-soft);border-color:var(--amber-border);font-weight:500}
  .subhead{font-size:10.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--faint);margin:12px 4px 8px}
`;
