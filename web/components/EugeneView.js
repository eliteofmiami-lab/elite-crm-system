"use client";
import { useMemo, useState } from "react";
import { supabase } from "../lib/supabaseClient";

const CHIP = {
  callback: { cls: "hot", label: "Hot" },
  first_touch: { cls: "hot", label: "First contact" },
  quote_followup: { cls: "quote", label: "Quote" },
  confirm_appt: { cls: "appt", label: "Appointment" },
  nice_to_talk: { cls: "quote", label: "Approve" },
};
// prioridade dentro da camada 2: first_touch SEMPRE acima (regra do Rafael)
const TYPE_RANK = { first_touch: 0 };
function chipFor(c) {
  if (CHIP[c.type]) return CHIP[c.type];
  const t = (c.title || "") + " " + (c.why || "");
  if (t.includes("HOT LEADS")) return { cls: "hot", label: "Hot" };
  if (t.includes("New Lead")) return { cls: "new", label: "New lead" };
  return { cls: "cold", label: "Cold" };
}
function fmtDur(from) {
  const m = Math.max(0, Math.floor((Date.now() - new Date(from).getTime()) / 60000));
  return `${Math.floor(m / 60)}h ${m % 60}m`;
}

function Snooze({ card, reload }) {
  const [reason, setReason] = useState("");
  const [chip, setChip] = useState("");
  const CHIPS = ["Client asked for later", "Waiting on info", "Line busy / no channel", "Other"];
  async function send() {
    const txt = [chip, reason].filter(Boolean).join(" — ");
    if (!txt) return;
    const back = new Date(Date.now() + 2 * 3600 * 1000).toISOString();
    await supabase.from("cards").update({
      status: "snoozed", snooze_reason: txt, due_at: back,
    }).eq("id", card.id);
    reload();
  }
  return (
    <div className="snooze">
      <div className="sl">Tell the system why — it will reschedule this task and learn from the reason:</div>
      <div className="rchips">
        {CHIPS.map((c) => (
          <span key={c} className={`rchip${chip === c ? " sel" : ""}`} onClick={() => setChip(c)}>{c}</span>
        ))}
      </div>
      <input placeholder="e.g. John texted asking me to call after 3 PM"
        value={reason} onChange={(e) => setReason(e.target.value)} />
      <button className="btn primary sm" onClick={send}>Send &amp; reschedule</button>
    </div>
  );
}

function LogCall({ card, userEmail, reload }) {
  const [f, setF] = useState({ outcome: "", make: "", model: "", year: "", momento: "",
    interest: "", prices: "", hook: "", next_step: "", next_date: "", notes: "" });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function save() {
    setSaving(true);
    // 1) registro no banco (fonte da verdade; entrada manual VENCE o cérebro)
    const { data: rows } = await supabase.from("manual_logs").insert({
      contact_id: card.contact_id, card_id: card.id, fields: f, logged_by: userEmail,
    }).select();
    const row = rows && rows[0];
    // 2) write-through imediato via API (se o servidor tiver a credencial GHL)
    let instant = false;
    try {
      const { data: s } = await supabase.auth.getSession();
      const res = await fetch("/api/log-call", {
        method: "POST",
        headers: { "Content-Type": "application/json",
                   Authorization: `Bearer ${s.session.access_token}` },
        body: JSON.stringify({ contact_id: card.contact_id, fields: f }),
      });
      instant = res.ok;
      if (instant && row) {
        await supabase.from("manual_logs").update({
          status: "synced", synced_at: new Date().toISOString() }).eq("id", row.id);
      }
    } catch (_) { /* fallback: worker sincroniza em ≤5 min */ }
    setSaving(false);
    setSaved(instant ? "Saved to GHL ✓" : "Saved — syncing to GHL (≤5 min)");
    reload();
  }
  const sel = { width: "100%", border: "1px solid var(--line)", borderRadius: 8,
    padding: "9px 11px", font: "400 13px Inter,system-ui,sans-serif", color: "var(--ink)",
    background: "var(--card)", marginBottom: 8 };
  return (
    <div className="snooze" style={{ marginTop: 10 }}>
      <div className="sl"><b>Log call details</b> — what you type here wins over the AI; it only fills the blanks.</div>
      <select style={sel} value={f.outcome} onChange={set("outcome")}>
        <option value="">Outcome…</option>
        <option>Answered — good talk</option><option>Answered — not interested</option>
        <option>No answer</option><option>Voicemail left</option><option>Wrong number</option>
      </select>
      <div style={{ display: "flex", gap: 8 }}>
        <input style={sel} placeholder="Make" value={f.make} onChange={set("make")} />
        <input style={sel} placeholder="Model" value={f.model} onChange={set("model")} />
        <input style={sel} placeholder="Year" value={f.year} onChange={set("year")} />
      </div>
      <select style={sel} value={f.momento} onChange={set("momento")}>
        <option value="">Car timing…</option>
        <option>Just delivered / brand new</option><option>Arriving soon</option>
        <option>Bought under 3 months ago</option><option>3–6 months</option>
        <option>6–12 months</option><option>Over a year</option><option>Unknown</option>
      </select>
      <select style={sel} value={f.interest} onChange={set("interest")}>
        <option value="">Interest level…</option>
        <option>Hot — ready to move</option><option>Warm — interested, needs follow-up</option>
        <option>Just exploring</option><option>Not interested</option>
      </select>
      <input style={sel} placeholder="Prices discussed (e.g. Full front PPF $2,200)"
        value={f.prices} onChange={set("prices")} />
      <input style={sel} placeholder="Personal note / hook (e.g. daughter's birthday trip, back Wednesday)"
        value={f.hook} onChange={set("hook")} />
      <div style={{ display: "flex", gap: 8 }}>
        <select style={sel} value={f.next_step} onChange={set("next_step")}>
          <option value="">Next step…</option>
          <option>Follow up</option><option>Send quote</option>
          <option>Book appointment</option><option>None</option>
        </select>
        <input style={sel} type="datetime-local" value={f.next_date} onChange={set("next_date")} />
      </div>
      <input style={sel} placeholder="Anything else worth remembering"
        value={f.notes} onChange={set("notes")} />
      <button className="btn primary sm" onClick={save} disabled={saving}>
        {saving ? "Saving…" : "Save call log"}
      </button>
      {saved && <span style={{ marginLeft: 10, fontSize: 12.5, color: "#067647", fontWeight: 600 }}>{saved}</span>}
    </div>
  );
}

function Task({ c, idx, current, reload, preview = false, spanish = false, sinkSpanish = false, userEmail = "" }) {
  const [showSnooze, setShowSnooze] = useState(false);
  const [showLog, setShowLog] = useState(false);
  const chip = spanish ? { cls: "appt", label: "🇪🇸 Spanish" } : chipFor(c);
  const how = (c.how && c.how.passos) || [];
  async function toggleSpanish() {
    if (preview) return;
    if (spanish) {
      await supabase.from("lead_flags").delete().eq("contact_id", c.contact_id);
    } else {
      await supabase.from("lead_flags").upsert(
        { contact_id: c.contact_id, spanish_only: true, set_by: userEmail },
        { onConflict: "contact_id" }
      );
    }
    reload();
  }
  if (!current) {
    return (
      <div className="task">
        <div className="row">
          <span className="num">{idx}</span>
          <div className="grow">
            <div className="ttl">{c.title}</div>
            <div className="meta">
              {spanish && sinkSpanish ? "🇪🇸 Spanish-only — Rafael handles this one · " : ""}{c.why}
            </div>
          </div>
          <span className={`chip ${chip.cls}`}>{chip.label}</span>
          <span className={`score${c.score ? "" : " mid"}`}>{c.score || "—"}</span>
          <span className="chev">›</span>
        </div>
      </div>
    );
  }
  return (
    <div className="task current">
      <div className="row">
        <span className="num">1</span>
        <div className="grow"><div className="ttl">{c.title}</div></div>
        <span className={`chip ${chip.cls}`}>{chip.label}</span>
        {c.score ? <span className="score">Score {c.score}</span> : null}
      </div>
      <div className="detail">
        <div className="dsec">
          <div className="dl">Why now</div>
          <p>{c.why}</p>
          {c.how && c.how.exhibit ? <span className="exh">{c.how.exhibit}</span> : null}
        </div>
        {how.length > 0 && (
          <div className="dsec">
            <div className="dl">How to play it</div>
            <p>{how.join(" · ")}</p>
          </div>
        )}
        <div className="actions">
          <a className="btn primary" href={c.ghl_link} target="_blank" rel="noreferrer">Open in GHL ↗</a>
          {!preview && (
            <button className="btn ghost" onClick={() => setShowLog(!showLog)}>Log call details</button>
          )}
          {!preview && (
            <button className="btn ghost" onClick={() => setShowSnooze(!showSnooze)}>Can&apos;t do now</button>
          )}
          {!preview && (
            <button className="btn ghost" onClick={toggleSpanish}>
              {spanish ? "Remove 🇪🇸 flag" : "🇪🇸 Spanish only"}
            </button>
          )}
          {!preview && c.type === "quote_followup" && (
            <button className="btn ghost" onClick={async () => {
              await supabase.from("cards").update({
                status: "done", result: "confirmado manualmente",
                closed_by: "manual-quote", closed_at: new Date().toISOString(),
              }).eq("id", c.id);
              reload();
            }}>Done ✓</button>
          )}
        </div>
        {showLog && <LogCall card={c} userEmail={userEmail} reload={reload} />}
        {showSnooze && <Snooze card={c} reload={reload} />}
      </div>
    </div>
  );
}

export default function EugeneView({ session, data, reload, preview = false, previewEmail = null, sinkSpanish = false }) {
  const email = preview ? previewEmail : session.user.email;
  // ordenação: camada → first_touch acima na L2 → score desc → mais recente primeiro
  const ranked = [...data.cards].sort((a, b) =>
    (a.layer - b.layer) ||
    ((TYPE_RANK[a.type] ?? 1) - (TYPE_RANK[b.type] ?? 1)) ||
    ((b.score || 0) - (a.score || 0)) ||
    (new Date(b.created_at) - new Date(a.created_at))
  );
  // espanhol afunda na fila do Eugene (ele não fala ES); na fila do Rafael fica na ordem normal
  const orderedCards = sinkSpanish
    ? [...ranked.filter((c) => !data.spanish.has(c.contact_id)),
       ...ranked.filter((c) => data.spanish.has(c.contact_id))]
    : ranked;
  const myShift = data.shifts.find((s) => s.user_email === email && !s.clock_out);
  const myPause = data.pauses.find(
    (p) => !p.ended_at && data.shifts.some((s) => s.id === p.shift_id && s.user_email === email)
  );

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
  const timeStr = now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

  // KPIs
  const callsToday = data.calls.length;
  const inQueue = data.cards.length;
  const quotesPending = data.cards.filter((c) => c.type === "quote_followup").length;

  // commissions
  const conf = data.commissions.filter((c) => c.status === "confirmado");
  const pot = data.commissions.filter((c) => c.status === "potencial");
  const confSum = conf.reduce((a, c) => a + Number(c.amount_usd || 0), 0);
  const potSum = pot.reduce((a, c) => a + Number(c.amount_usd || 0), 0);
  const today0 = new Date(); today0.setHours(0, 0, 0, 0);
  const bookedToday = data.commissions
    .filter((c) => new Date(c.booked_at) >= today0)
    .reduce((a, c) => a + Number(c.amount_usd || 0), 0);
  const day = now.getDate();
  const fortnightDay = day <= 15 ? day : day - 15;
  const fortnightLen = day <= 15 ? 15 : new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate() - 15;

  // bonus guard
  const guardItems = data.cards.filter((c) => c.type === "confirm_appt" || c.layer === 1);
  const monthName = now.toLocaleDateString("en-US", { month: "long" });

  // inactivity (visual): minutes since last event today
  const lastEvents = [
    ...data.doneToday.map((c) => c.closed_at),
    myShift && myShift.clock_in,
  ].filter(Boolean).map((t) => new Date(t).getTime());
  const idleMin = myShift && !myPause && lastEvents.length
    ? Math.floor((Date.now() - Math.max(...lastEvents)) / 60000) : 0;

  const advices = useMemo(
    () => data.analyses
      .map((a) => ({
        text: a.payload && (a.payload.advice_en || a.payload.coaching),
        cid: a.calls && a.calls.contact_id,
      }))
      .filter((a) => a.text),
    [data.analyses]
  );

  async function clockIn() {
    if (preview) return; // somente leitura no modo espiar
    await supabase.from("shifts").insert({ user_email: email });
    reload();
  }
  async function clockOut() {
    if (preview) return;
    await supabase.from("shifts").update({ clock_out: new Date().toISOString() }).eq("id", myShift.id);
    reload();
  }
  async function toggleBreak() {
    if (preview) return;
    if (myPause) {
      await supabase.from("pauses").update({ ended_at: new Date().toISOString() }).eq("id", myPause.id);
    } else {
      await supabase.from("pauses").insert({ shift_id: myShift.id });
    }
    reload();
  }

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="brand">
          <div className="logoplate"><img src="/elite-logo.png" alt="Elite Premium Detailing" /></div>
          <div>
            <div className="t">Work queue</div>
            <div className="d">{dateStr} · {timeStr}</div>
          </div>
        </div>
        <div className="pills">
          {myShift ? (
            <>
              <span className="pill ok"><span className="dot"></span>
                Clocked in {new Date(myShift.clock_in).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })} · {fmtDur(myShift.clock_in)}
              </span>
              <span className="pill money">$ Today +${bookedToday}</span>
              <button className="btn ghost sm" onClick={toggleBreak}>
                {myPause ? "End break" : "Start break"}
              </button>
              <button className="btn ghost sm out" onClick={clockOut}>Clock out</button>
            </>
          ) : (
            <span className="pill"><span className="dot"></span>Off shift</span>
          )}
        </div>
      </div>

      {!myShift && preview ? (
        <div className="gate">
          <h2>Eugene ainda não bateu o ponto</h2>
          <p>{inQueue} tasks esperando na fila dele · a tela abaixo é o que ele verá ao entrar</p>
        </div>
      ) : null}
      {!myShift && !preview ? (
        <div className="gate">
          <h2>Your day is ready</h2>
          <p>{inQueue} tasks in the queue · {data.cards.filter((c) => c.type === "confirm_appt").length} appointments to confirm</p>
          <button className="btn primary big" onClick={clockIn}>▶ Clock in</button>
        </div>
      ) : null}
      {(myShift || preview) && (
        <>
          <div className="kpis">
            <div className="kpi"><div className="l">Calls today</div><div className="v">{callsToday}<small> / ~100</small></div></div>
            <div className="kpi"><div className="l">In queue</div><div className="v">{inQueue}</div></div>
            <div className="kpi"><div className="l">Quotes pending</div><div className="v">{quotesPending}</div></div>
            <div className="kpi"><div className="l">Avg response</div><div className="v">—<small> min</small></div></div>
          </div>

          <div className="earn">
            <div>
              <div className="lbl">My commissions — {monthName}</div>
              <div className="big">${confSum} <small>confirmed</small></div>
            </div>
            <div className="mini">${potSum}<small>potential</small></div>
            <div className="mini">{pot.length}<small>awaiting sale</small></div>
            <div className="mini">+${bookedToday}<small>booked today</small></div>
            <div className="mini" style={{ color: "#067647" }}>$50<small>rule bonus · on track {fortnightDay}/{fortnightLen}</small></div>
            <div className="note">$10 per booked appointment that closes · +$50 every 2 weeks with zero critical misses</div>
            {guardItems.length > 0 ? (
              <div className="guard"><b>Bonus guard</b> · {guardItems.length} item{guardItems.length > 1 ? "s" : ""} need attention today: {guardItems[0].title}</div>
            ) : (
              <div className="guard clear"><b>Bonus guard</b> · all clear — nothing threatens your bonus today</div>
            )}
          </div>

          {idleMin >= 10 && (
            <div className={`banner${idleMin >= 15 ? " red" : ""}`}>
              ⚠ {idleMin} min without activity — {inQueue} leads are waiting in your queue
            </div>
          )}

          <div className="qcard">
            <div className="qhead">
              <h2>Task queue <span>· {inQueue}</span></h2>
              <span className="cap">Auto-sorted by priority — always take task 1</span>
            </div>
            {orderedCards.map((c, i) => (
              <Task key={c.id} c={c} idx={i + 1} current={i === 0} reload={reload}
                preview={preview} spanish={data.spanish.has(c.contact_id)}
                sinkSpanish={sinkSpanish} userEmail={session.user.email} />
            ))}
            {data.snoozed.map((c) => (
              <div className="task snoozed" key={c.id}>
                <div className="row">
                  <span className="num">↷</span>
                  <div className="grow">
                    <div className="ttl">{c.title}</div>
                    <div className="meta">
                      Snoozed{c.due_at ? ` to ${new Date(c.due_at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}` : ""} — “{c.snooze_reason}”
                    </div>
                  </div>
                  <span className="chip snz">Snoozed</span>
                  <span className="score mid">{c.score || "—"}</span>
                </div>
              </div>
            ))}
            {inQueue === 0 && data.snoozed.length === 0 && (
              <div className="center">🎉 Queue clear — nothing pending.</div>
            )}
          </div>

          {data.cards.filter((c) => c.type === "nice_to_talk").map((c) => (
            <div className="approve" key={`ap-${c.id}`}>
              <div className="ic">✓</div>
              <div className="msg">
                <div className="t">{c.title}</div>
                <div className="p">{c.draft_message}</div>
              </div>
              <button className="btn ghost">Edit</button>
              <button className="btn primary">Approve &amp; send</button>
            </div>
          ))}

          <div className="advice">
            <h3>Advice from today&apos;s calls</h3>
            {advices.length === 0 && <div className="center" style={{ padding: "14px 0" }}>No calls analyzed yet today.</div>}
            {advices.map((a, i) => (
              <div className="arow" key={i}>
                <span className="atag">Advice</span>
                <span>{a.text}</span>
                {a.cid && (
                  <a href={`https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/${a.cid}`}
                    target="_blank" rel="noreferrer">View lead ↗</a>
                )}
              </div>
            ))}
            <div className="afoot">Advice never affects your pay — it exists to help you close more. Each note also reappears on that lead&apos;s card the next time you call.</div>
          </div>

          <div className="rules">
            <h3>The rules — read once, live by them</h3>
            <div className="rgrid">
              <div className="rcol earnc">
                <div className="rt">How you earn</div>
                <ul>
                  <li><b>$10</b> for every appointment you book that turns into a <b>closed sale</b> — shows as potential when booked, confirmed when it closes.</li>
                  <li><b>+$50 rule bonus</b> every fortnight (1–15 and 16–end of month) with <b>zero critical misses</b>.</li>
                  <li>No-shows that never rebook and lost deals expire the potential — confirmations and connection protect your money.</li>
                </ul>
              </div>
              <div className="rcol missc">
                <div className="rt">Critical misses — these cost the $50</div>
                <ul>
                  <li>A new lead (business hours) with <b>no contact attempt</b> all day</li>
                  <li>A quote discussed on a call <b>not sent</b> by end of next business day</li>
                  <li>An appointment in the next 2 days <b>left unconfirmed</b></li>
                  <li>A score-80+ lead <b>orphaned 24h+</b> (no contact, no dated task)</li>
                  <li>Inactivity over <b>45 min</b> with no break or reason</li>
                  <li><b>3+ postponements</b> with rejected reasons in the period</li>
                </ul>
              </div>
            </div>
            <div className="rfoot">Minor slips — one late call, one missed voicemail — do <b>not</b> take the bonus; they show up as advice notes. If a critical miss happens, the panel tells you the same day. Next fortnight always starts clean.</div>
          </div>

          <p className="footnote">Tasks complete themselves when the call or text is detected in GHL — nothing to mark as done.</p>
        </>
      )}
    </div>
  );
}
