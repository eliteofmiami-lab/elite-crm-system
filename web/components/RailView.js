"use client";
// MVP (2026-07-08): a fila e SÓ a fila, em coluna única (?layout=rail) — pensada
// para viver dentro do GHL via Custom Menu Link. SOMENTE LEITURA no GHL: nenhum
// botão escreve nada lá; o Eugene registra tudo direto no GHL. (Pendências e
// "Reportar erro" gravam apenas no Supabase — itens 6 e 7 do MVP.)
import { useState } from "react";
import { supabase } from "../lib/supabaseClient";

const STATE_LABEL = {
  ativo_venda: { txt: "Active", bg: "#EFF4FF", fg: "#1D4ED8" },
  callback_devido: { txt: "📞 CALLBACK OWED", bg: "#FEF3F2", fg: "#B42318" },
  aguardando_decisao_cliente: { txt: "Client deciding — don't chase", bg: "#F4F0FF", fg: "#5925DC" },
  aguardando_evento_externo: { txt: "Waiting external event", bg: "#F4F0FF", fg: "#5925DC" },
  agendado: { txt: "Scheduled", bg: "#ECFDF3", fg: "#067647" },
  esfriou: { txt: "Cold", bg: "#F2F4F7", fg: "#475467" },
};
const COMP_LABEL = { car: ["Car", 35], momento: ["Timing", 25], eng: ["Engagement", 25], int: ["Intent", 15] };
const FEEDBACK_CHIPS = [
  ["score_errado", "Wrong score"], ["estado_errado", "Wrong state"],
  ["nao_deveria_estar", "Shouldn't be in queue"], ["ordem_errada", "Wrong order"],
  ["pendencia_incorreta", "Wrong pending item"], ["outro", "Other"],
];

function triggerRank(c, hour) {
  // BONUS GUARD: congelado nesta etapa (não aparece); quote_rescue = foco do dia
  const t = c.title || "";
  if (c.layer === 1) {
    if (t.includes("CALLBACK OWED")) return 0;
    if (c.type === "new_lead" || t.includes("NEW LEAD")) return 1;
    if (t.includes("MISSED CALL")) return 2;
    return 3;
  }
  if (c.layer === 2) {
    return { confirm_appt: hour < 11 ? 0 : 2.5, first_touch: 1, follow_up: 2,
      quote_followup: 3, quote_rescue: 3.5 }[c.type] ?? 4;
  }
  return 0;
}

function ScoreBreakdown({ comps }) {
  // item 4: a CONTAGEM — componente · valor · fonte · evidência em 1 linha
  return (
    <div style={{ background: "#F9FAFB", border: "1px solid #E4E7EC", borderRadius: 8,
      padding: "8px 10px", margin: "6px 0", fontSize: 12.2, lineHeight: 1.5 }}>
      {Object.entries(COMP_LABEL).map(([k, [lab, max]]) => {
        const comp = (comps || {})[k] || {};
        const v = comp.value === null || comp.value === undefined ? "?" : comp.value;
        return (
          <div key={k}>
            <b>{lab} {v}</b><span style={{ color: "#98A2B3" }}>/{max}</span>
            {" — "}{comp.reason || "no data yet"}
            {comp.source ? <span style={{ color: "#98A2B3" }}> · {comp.source}</span> : null}
          </div>
        );
      })}
      <div style={{ color: "#98A2B3", marginTop: 4 }}>? = no data — never counted as zero.</div>
    </div>
  );
}

function FeedbackBox({ c, states, onDone }) {
  const [tipo, setTipo] = useState(null);
  const [texto, setTexto] = useState("");
  const [sent, setSent] = useState(false);
  if (sent) return <div style={{ color: "#067647", fontSize: 12.5, margin: "6px 0" }}>✓ Reported — thank you. Nothing changes automatically; Rafael reviews it.</div>;
  return (
    <div style={{ border: "1px dashed #FEDF89", background: "#FFFAEB", borderRadius: 8,
      padding: 8, margin: "6px 0" }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {FEEDBACK_CHIPS.map(([k, lab]) => (
          <button key={k} onClick={() => setTipo(k)}
            style={{ border: `1px solid ${tipo === k ? "#B54708" : "#FEDF89"}`,
              background: tipo === k ? "#FEF0C7" : "#fff", borderRadius: 999,
              padding: "3px 9px", fontSize: 11.5, cursor: "pointer" }}>{lab}</button>
        ))}
      </div>
      <textarea value={texto} onChange={(e) => setTexto(e.target.value)}
        placeholder="What's wrong? (optional but helps)"
        style={{ width: "100%", minHeight: 44, marginTop: 6, fontSize: 12.5,
          border: "1px solid #E4E7EC", borderRadius: 6, padding: 6 }} />
      <button disabled={!tipo} onClick={async () => {
        const { data: s } = await supabase.auth.getSession();
        await supabase.from("beta_feedback").insert({
          contact_id: c.contact_id, card_id: c.id, tipo, texto,
          snapshot: { score: c.score, score_max: c.score_max, badge: c.score_badge,
            breakdown: c.score_breakdown, layer: c.layer, type: c.type,
            situacao: (states[c.contact_id] || {}).situacao, title: c.title },
          reported_by: s?.session?.user?.email || "?",
        });
        setSent(true); onDone && onDone();
      }} style={{ marginTop: 6, background: tipo ? "#B54708" : "#D0D5DD", color: "#fff",
        border: "none", borderRadius: 8, padding: "5px 12px", fontSize: 12, cursor: "pointer" }}>
        Send report
      </button>
    </div>
  );
}

export default function RailView({ data, reload }) {
  const [openId, setOpenId] = useState(null);
  const [showCount, setShowCount] = useState(null);
  const [showFb, setShowFb] = useState(null);
  const [gone, setGone] = useState({});
  const hour = new Date().getHours();
  const states = data.states || {};
  async function closeCard(c) {
    setGone({ ...gone, [c.id]: true });
    await supabase.from("cards").update({
      status: "done", result: "closed manually in rail", closed_by: "manual-rail",
      closed_at: new Date().toISOString(),
    }).eq("id", c.id);
    reload && reload();
  }
  const scores = data.scores || {};
  const pendById = {};
  (data.pendencias || []).forEach((p) => {
    (pendById[p.contact_id] = pendById[p.contact_id] || []).push(p);
  });
  const queue = [...data.cards].sort((a, b) =>
    (a.layer - b.layer) || (triggerRank(a, hour) - triggerRank(b, hour)) ||
    ((b.score || 0) - (a.score || 0)) || (new Date(a.created_at) - new Date(b.created_at)));

  return (
    <div style={{ maxWidth: 460, margin: "0 auto", padding: "10px 10px 40px",
      font: "400 14px Inter,system-ui,sans-serif", color: "#101828" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 2px 12px" }}>
        <img src="/elite-logo.png" alt="Elite" style={{ height: 26 }} />
        <b>Call queue</b>
        <span style={{ color: "#98A2B3" }}>· {queue.length} · sorted for you — take #1</span>
      </div>
      {queue.filter((c) => !gone[c.id]).map((c, i) => {
        const st = states[c.contact_id] || {};
        const sit = (c.how && c.how.state) || st.situacao;
        const lbl = STATE_LABEL[sit];
        const veh = (c.how && c.how.veh) || (st.state && st.state.vehicle
          ? [st.state.vehicle.year, st.state.vehicle.make, st.state.vehicle.model]
            .filter(Boolean).join(" ") : null);
        const interest = c.how && c.how.interest && c.how.interest.value;
        const pends = pendById[c.contact_id] || [];
        const open = openId === c.id || (openId === null && i === 0);
        return (
          <div key={c.id} onClick={() => setOpenId(open && i !== 0 ? null : c.id)}
            style={{ background: "#fff", border: "1px solid #E4E7EC",
              borderLeft: c.layer === 1 ? "3px solid #F04438" : "1px solid #E4E7EC",
              borderRadius: 12, padding: "10px 12px", marginBottom: 8, cursor: "pointer",
              boxShadow: "0 1px 2px rgba(16,24,40,.05)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ minWidth: 22, height: 22, borderRadius: 999,
                background: i === 0 ? "#2970FF" : "#F2F4F7",
                color: i === 0 ? "#fff" : "#475467", fontSize: 12, fontWeight: 600,
                display: "inline-flex", alignItems: "center", justifyContent: "center" }}>{i + 1}</span>
              <span style={{ fontWeight: 600, flex: 1, fontSize: 13.5 }}>{c.title}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: "#475467", whiteSpace: "nowrap" }}>
                {c.score ? `${c.score}/${c.score_max || "?"}` : "—"}
                {c.score_badge === "call-verified" ? " ✓" : c.score_badge ? " ◌" : ""}
              </span>
              <button onClick={(e) => { e.stopPropagation(); setShowCount(showCount === c.id ? null : c.id); }}
                title="How this score was counted"
                style={{ border: "1px solid #E4E7EC", background: "#fff", borderRadius: 999,
                  width: 20, height: 20, fontSize: 11, cursor: "pointer", color: "#475467" }}>i</button>
            </div>
            {(veh || interest) && (
              <div style={{ marginTop: 4, fontSize: 12.2, color: "#475467" }}>
                {veh ? <>🚗 <b>{veh}</b></> : null}
                {veh && interest ? " · " : ""}
                {interest ? <>looking for <b>{interest}</b></> : null}
              </div>
            )}
            {lbl && (
              <span style={{ display: "inline-block", margin: "6px 0 0", padding: "2px 8px",
                borderRadius: 999, fontSize: 11.5, fontWeight: 600,
                background: lbl.bg, color: lbl.fg }}>{lbl.txt}</span>
            )}
            {showCount === c.id && (
              <div onClick={(e) => e.stopPropagation()}>
                <ScoreBreakdown comps={(scores[c.contact_id] || {}).components} />
              </div>
            )}
            {open && (
              <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.45 }}
                onClick={(e) => e.stopPropagation()}>
                <div style={{ margin: "6px 0", color: "#101828" }}>{c.why}</div>
                {pends.length > 0 && (
                  <div style={{ background: "#FEF3F2", border: "1px solid #FECDCA",
                    borderRadius: 8, padding: "7px 9px", margin: "6px 0", fontSize: 12.3 }}>
                    <b style={{ color: "#B42318" }}>Pending in GHL ({pends.length})</b>
                    {pends.map((p) => (
                      <div key={p.id} style={{ marginTop: 4 }}>
                        {p.fato} <b>→ {p.acao}</b>
                      </div>
                    ))}
                    <div style={{ color: "#98A2B3", marginTop: 4 }}>
                      Fix it in GHL — this clears itself on the next cycle.
                    </div>
                  </div>
                )}
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
                  {c.phone && <span style={{ fontWeight: 700, fontSize: 14.5 }}>{c.phone}</span>}
                  <button onClick={() => setShowFb(showFb === c.id ? null : c.id)}
                    style={{ border: "1px solid #E4E7EC", background: "#fff", borderRadius: 8,
                      padding: "5px 9px", fontSize: 11.5, cursor: "pointer", color: "#475467" }}>
                    ⚑ Report error
                  </button>
                  <button onClick={() => closeCard(c)}
                    title="Close this card (queue only — GHL is not touched)"
                    style={{ border: "1px solid #ABEFC6", background: "#ECFDF3", borderRadius: 8,
                      padding: "5px 9px", fontSize: 11.5, cursor: "pointer",
                      color: "#067647", fontWeight: 600 }}>
                    ✓ Done
                  </button>
                  <a href={c.ghl_link} target="_blank" rel="noreferrer"
                    style={{ marginLeft: "auto", background: "#2970FF", color: "#fff",
                      padding: "6px 12px", borderRadius: 8, fontSize: 12.5,
                      fontWeight: 600, textDecoration: "none" }}>Open contact ↗</a>
                </div>
                {showFb === c.id && <FeedbackBox c={c} states={states} />}
              </div>
            )}
          </div>
        );
      })}
      {queue.length === 0 && (
        <div style={{ textAlign: "center", color: "#98A2B3", padding: 30 }}>
          Queue is clear. New events re-sort it automatically.
        </div>
      )}
      <p style={{ color: "#98A2B3", fontSize: 11.5, marginTop: 14 }}>
        Read-only: log everything directly in GHL — the brain reads it on the next cycle
        and re-sorts. Cards close themselves when your call/text is detected.
      </p>
    </div>
  );
}
