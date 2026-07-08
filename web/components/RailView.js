"use client";
// MVP (2026-07-08): a fila e SÓ a fila, em coluna única (?layout=rail) — pensada
// para viver dentro do GHL via Custom Menu Link. SOMENTE LEITURA: nenhum botão
// escreve em nada; o Eugene registra tudo direto no GHL.
import { useState } from "react";

const STATE_LABEL = {
  ativo_venda: { txt: "Active", bg: "#EFF4FF", fg: "#1D4ED8" },
  callback_devido: { txt: "📞 CALLBACK OWED", bg: "#FEF3F2", fg: "#B42318" },
  aguardando_decisao_cliente: { txt: "Client deciding — don't chase", bg: "#F4F0FF", fg: "#5925DC" },
  aguardando_evento_externo: { txt: "Waiting external event", bg: "#F4F0FF", fg: "#5925DC" },
  agendado: { txt: "Scheduled", bg: "#ECFDF3", fg: "#067647" },
  esfriou: { txt: "Cold", bg: "#F2F4F7", fg: "#475467" },
};

function triggerRank(c, hour) {
  const t = c.title || "";
  if (c.layer === 1) {
    if (t.includes("CALLBACK OWED")) return 0;
    if (t.includes("BONUS GUARD")) return 1;
    if (c.type === "new_lead" || t.includes("NEW LEAD")) return 1;
    if (t.includes("MISSED CALL")) return 2;
    return 3;
  }
  if (c.layer === 2) {
    return { confirm_appt: hour < 11 ? 0 : 2.5, first_touch: 1, follow_up: 2, quote_followup: 3 }[c.type] ?? 4;
  }
  return 0;
}

export default function RailView({ data }) {
  const [openId, setOpenId] = useState(null);
  const hour = new Date().getHours();
  const states = data.states || {};
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
      {queue.map((c, i) => {
        const st = states[c.contact_id] || {};
        const sit = (c.how && c.how.state) || st.situacao;
        const lbl = STATE_LABEL[sit];
        const veh = st.state && st.state.vehicle
          ? [st.state.vehicle.year, st.state.vehicle.make, st.state.vehicle.model]
            .filter(Boolean).join(" ") : null;
        const interest = c.how && c.how.interest && c.how.interest.value;
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
              <span style={{ fontSize: 12, fontWeight: 600, color: "#475467", whiteSpace: "nowrap" }}
                title={c.score_breakdown || ""}>
                {c.score ? `${c.score}/${c.score_max || "?"}` : "—"}
                {c.score_badge === "call-verified" ? " ✓" : c.score_badge ? " ◌" : ""}
              </span>
            </div>
            {lbl && (
              <span style={{ display: "inline-block", margin: "6px 0 0", padding: "2px 8px",
                borderRadius: 999, fontSize: 11.5, fontWeight: 600,
                background: lbl.bg, color: lbl.fg }}>{lbl.txt}</span>
            )}
            {open && (
              <div style={{ marginTop: 8, fontSize: 13, lineHeight: 1.45 }}
                onClick={(e) => e.stopPropagation()}>
                {(veh || interest) && (
                  <div style={{ color: "#475467" }}>
                    {veh ? <>🚗 {veh}</> : null}{veh && interest ? " · " : ""}
                    {interest ? <>Looking for <b>{interest}</b></> : null}
                  </div>
                )}
                <div style={{ margin: "6px 0", color: "#101828" }}>{c.why}</div>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8 }}>
                  {c.phone && <span style={{ fontWeight: 700, fontSize: 14.5 }}>{c.phone}</span>}
                  <a href={c.ghl_link} target="_blank" rel="noreferrer"
                    style={{ marginLeft: "auto", background: "#2970FF", color: "#fff",
                      padding: "6px 12px", borderRadius: 8, fontSize: 12.5,
                      fontWeight: 600, textDecoration: "none" }}>Open contact ↗</a>
                </div>
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
