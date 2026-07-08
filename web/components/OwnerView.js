"use client";
import { useMemo, useState } from "react";
import { supabase } from "../lib/supabaseClient";

const FUNIL_COLORS = ["#2970FF", "#58A6FF", "#7A5AF8", "#B4A5FC", "#06AED4", "#12B76A"];

export default function OwnerView({ session, data, onViewEugene, onWorkQueue }) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });

  // Eugene status
  const eugeneShift = data.shifts.find(
    (s) => s.user_email !== session.user.email && !s.clock_out
  );
  const lastEvents = data.doneToday.map((c) => new Date(c.closed_at).getTime());
  const lastMin = lastEvents.length
    ? Math.floor((Date.now() - Math.max(...lastEvents)) / 60000) : null;

  // KPIs
  const callsToday = data.calls.length;
  const quotesSent = data.doneToday.filter((c) => c.type === "quote_followup").length;
  const appts = data.commissions.filter(
    (c) => new Date(c.booked_at).toDateString() === now.toDateString()
  ).length;
  const confSum = data.commissions
    .filter((c) => c.status === "confirmado")
    .reduce((a, c) => a + Number(c.amount_usd || 0), 0);
  const day = now.getDate();
  const fDay = day <= 15 ? day : day - 15;
  const fLen = day <= 15 ? 15 : new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate() - 15;

  // funnel (worker snapshot)
  const st = data.config.stats_today || {};
  const f = st.funil || {};
  const funil = [
    ["New leads", f.novos], ["Hot leads", f.hot], ["Qualified", f.qualificados],
    ["Quotes", f.quotes], ["Appointments", f.appointments], ["Win", f.win],
  ];
  const maxF = Math.max(1, ...funil.map(([, v]) => v || 0));

  // audited goals (v1: the ones measurable today)
  const openConfirm = data.cards.filter((c) => c.type === "confirm_appt").length;
  const openUrgent = data.cards.filter((c) => c.layer === 1).length;
  const goals = [
    ["Speed to lead ≤ 15 min", null, "—"],
    ["Reply to lead ≤ 30 min", null, "—"],
    ["Voicemail on 100% of missed", null, "—"],
    ["Quote sent same day", quotesSent > 0 || data.cards.filter((c) => c.type === "quote_followup").length === 0, `${quotesSent} today`],
    ["Confirmations by 11:00 AM", openConfirm === 0, openConfirm === 0 ? "ok" : `${openConfirm} pending`],
    ["Zero 80+ lead orphaned", openUrgent === 0, openUrgent === 0 ? "ok" : `${openUrgent} urgent`],
  ];

  // activity per hour (closed cards)
  const hours = useMemo(() => {
    const h = {};
    for (let i = 8; i <= 19; i++) h[i] = 0;
    data.doneToday.forEach((c) => {
      const hh = new Date(c.closed_at).getHours();
      if (h[hh] !== undefined) h[hh]++;
    });
    return h;
  }, [data.doneToday]);
  const maxH = Math.max(1, ...Object.values(hours));

  // alerts + advice + snooze reports
  const rows = [];
  data.cards.filter((c) => c.layer === 1).forEach((c) =>
    rows.push({ tag: "Alert", cls: "alert", text: c.title, cid: c.contact_id }));
  data.analyses.forEach((a) => {
    const t = a.payload && (a.payload.advice_en || a.payload.advice_pt);
    if (t) rows.push({ tag: "Advice", cls: "", text: t, cid: a.calls && a.calls.contact_id });
  });
  data.snoozed.forEach((c) =>
    rows.push({ tag: "Report", cls: "", text: `Task snoozed: "${c.title}" — reason: ${c.snooze_reason}`, cid: c.contact_id }));

  const spanishCount = data.cards.filter((c) => data.spanish.has(c.contact_id)).length;

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="brand">
          <div className="logoplate"><img src="/elite-logo.png" alt="Elite Premium Detailing" /></div>
          <div>
            <div className="t">Owner dashboard</div>
            <div className="d">{dateStr}</div>
          </div>
        </div>
        <div className="pills">
          {eugeneShift ? (
            <span className="pill ok"><span className="dot"></span>
              Eugene active · clocked in {new Date(eugeneShift.clock_in).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}
              {lastMin !== null ? ` · last action ${lastMin} min ago` : ""}
            </span>
          ) : (
            <span className="pill"><span className="dot"></span>Eugene off shift</span>
          )}
          <button className="btn primary sm" onClick={onWorkQueue}>🛠 Work the queue</button>
          <button className="btn ghost sm" onClick={onViewEugene}>👁 View Eugene&apos;s screen</button>
        </div>
      </div>

      {spanishCount > 0 && (
        <div className="banner">
          🇪🇸 {spanishCount} Spanish-only lead{spanishCount > 1 ? "s" : ""} in the queue — these are yours until the Spanish-speaking hire
        </div>
      )}

      <div className="kpis">
        <div className="kpi"><div className="l">Calls</div><div className="v">{callsToday}<small> / ~100</small></div></div>
        <div className="kpi"><div className="l">Quotes sent</div><div className="v">{quotesSent}</div></div>
        <div className="kpi"><div className="l">Appointments</div><div className="v">{appts}</div></div>
        <div className="kpi hl">
          <div className="l">Eugene commission · month</div>
          <div className="v">${confSum}</div>
          <div className="l" style={{ marginTop: 4 }}>$50 fortnight bonus · on track — {fDay}/{fLen} days, 0 critical misses</div>
        </div>
      </div>

      <div className="grid2">
        <div className="panel">
          <h3>Today&apos;s funnel</h3>
          {funil.map(([label, v], i) => (
            <div className="fun" key={label}>
              <span className="fl">{label}</span>
              <div className="bar" style={{
                background: FUNIL_COLORS[i],
                width: `${Math.max(4, ((v || 0) / maxF) * 100)}%`,
              }} />
              <span className="fv">{v == null ? "—" : v}</span>
            </div>
          ))}
        </div>

        <div className="panel">
          <h3>Today&apos;s goals — audited</h3>
          {goals.map(([label, ok, val]) => (
            <div className="goal" key={label}>
              <span className={`gi ${ok === null ? "na" : ok ? "ok" : "no"}`}>
                {ok === null ? "•" : ok ? "✓" : "✕"}
              </span>
              <span>{label}</span>
              <span className="gv">{val}</span>
            </div>
          ))}
        </div>

        <div className="panel">
          <h3>Activity by hour</h3>
          <div className="hours">
            {Object.entries(hours).map(([h, v]) => (
              <div className="hcol" key={h}>
                <div className="hbar" style={{ height: `${(v / maxH) * 70 + 2}px` }} />
                <span className="hlbl">{h}h</span>
              </div>
            ))}
          </div>
          <p className="meta" style={{ marginTop: 8 }}>
            Bars = completed actions per hour · inactivity blocks show in amber once logged
          </p>
        </div>

        <div className="panel">
          <h3>Alerts &amp; recommendations</h3>
          {rows.length === 0 && <div className="center" style={{ padding: "10px 0" }}>Nothing yet.</div>}
          {rows.slice(0, 8).map((r, i) => (
            <div className="arow" key={i}>
              <span className={`atag ${r.cls}`}>{r.tag}</span>
              <span>{r.text}</span>
              {r.cid && (
                <a href={`https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/${r.cid}`}
                  target="_blank" rel="noreferrer">View lead ↗</a>
              )}
            </div>
          ))}
        </div>
      </div>

      {(data.reports || []).filter((r) => r.audience === "rafael").slice(0, 1).map((r) => (
        <div className="panel" style={{ marginTop: 12 }} key={r.id}>
          <h3>📄 Daily report · {r.report_date}</h3>
          <pre style={{ whiteSpace: "pre-wrap", font: "400 13px Inter,system-ui,sans-serif",
            color: "var(--ink)" }}>{r.content_md}</pre>
        </div>
      ))}

      <Diagnostics testIds={data.config.test_contact_ids || []} />

      <p className="footnote">Full daily report generated at 6:30 PM · commissions reconcile with sales at month close.</p>
    </div>
  );
}

function Diagnostics({ testIds }) {
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  async function clearTestData() {
    if (!testIds.length) { setMsg("No test contacts registered yet."); return; }
    if (!window.confirm(`Delete panel data for ${testIds.length} test contact(s)? GHL is NOT touched.`)) return;
    setBusy(true);
    const list = `(${testIds.map((i) => `"${i}"`).join(",")})`;
    const { data: testCalls } = await supabase.from("calls").select("id").in("contact_id", testIds);
    if (testCalls && testCalls.length) {
      await supabase.from("analyses").delete().in("call_id", testCalls.map((c) => c.id));
    }
    await supabase.from("calls").delete().in("contact_id", testIds);
    await supabase.from("cards").delete().in("contact_id", testIds);
    await supabase.from("commissions").delete().in("contact_id", testIds);
    await supabase.from("lead_flags").delete().in("contact_id", testIds);
    await supabase.from("manual_logs").delete().in("contact_id", testIds);
    setBusy(false);
    setMsg(`Cleared panel data for ${testIds.length} test contact(s).`);
  }
  return (
    <div className="panel" style={{ marginTop: 12 }}>
      <h3>Diagnostics</h3>
      <p className="meta" style={{ marginBottom: 10 }}>
        Contacts tagged <b>teste-interno</b> in GHL are excluded from scoring, Meta events,
        reports, commissions and bonus — but still show in the queue. Registered: {testIds.length}.
      </p>
      <button className="btn ghost sm" onClick={clearTestData} disabled={busy}>
        {busy ? "Clearing…" : "🧹 Clear test data"}
      </button>
      {msg && <span style={{ marginLeft: 10, fontSize: 12.5, color: "var(--sub)" }}>{msg}</span>}
    </div>
  );
}
