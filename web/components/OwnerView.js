"use client";
import { useMemo } from "react";

const FUNIL_COLORS = ["#2970FF", "#58A6FF", "#7A5AF8", "#B4A5FC", "#06AED4", "#12B76A"];

export default function OwnerView({ session, data, onViewEugene }) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "short" });

  // status do Eugene
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

  // funil (snapshot do worker)
  const st = data.config.stats_today || {};
  const f = st.funil || {};
  const funil = [
    ["Leads novos", f.novos], ["Hot leads", f.hot], ["Qualificados", f.qualificados],
    ["Quotes", f.quotes], ["Appointments", f.appointments], ["Win", f.win],
  ];
  const maxF = Math.max(1, ...funil.map(([, v]) => v || 0));

  // metas auditadas (v1: as verificáveis com dados atuais)
  const openConfirm = data.cards.filter((c) => c.type === "confirm_appt").length;
  const openUrgent = data.cards.filter((c) => c.layer === 1).length;
  const goals = [
    ["Speed to lead ≤ 15 min", null, "—"],
    ["Resposta a lead ≤ 30 min", null, "—"],
    ["Voicemail em 100% das perdidas", null, "—"],
    ["Quote enviada no dia", quotesSent > 0 || data.cards.filter((c) => c.type === "quote_followup").length === 0, `${quotesSent} hoje`],
    ["Confirmações até 11:00", openConfirm === 0, openConfirm === 0 ? "ok" : `${openConfirm} pendentes`],
    ["Zero lead 80+ órfão", openUrgent === 0, openUrgent === 0 ? "ok" : `${openUrgent} urgentes`],
  ];

  // atividade por hora (cards fechados)
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

  // alertas + advice PT + reportes de snooze
  const rows = [];
  data.cards.filter((c) => c.layer === 1).forEach((c) =>
    rows.push({ tag: "Alerta", cls: "alert", text: c.title, cid: c.contact_id }));
  data.analyses.forEach((a) => {
    const t = a.payload && (a.payload.advice_pt || a.payload.advice_en);
    if (t) rows.push({ tag: "Advice", cls: "", text: t, cid: a.calls && a.calls.contact_id });
  });
  data.snoozed.forEach((c) =>
    rows.push({ tag: "Reporte", cls: "", text: `Eugene adiou "${c.title}" — motivo: ${c.snooze_reason}`, cid: c.contact_id }));

  return (
    <div className="wrap">
      <div className="topbar">
        <div className="brand">
          <div className="logoplate"><img src="/elite-logo.png" alt="Elite Premium Detailing" /></div>
          <div>
            <div className="t">Visão do dono</div>
            <div className="d">{dateStr}</div>
          </div>
        </div>
        <div className="pills">
          {eugeneShift ? (
            <span className="pill ok"><span className="dot"></span>
              Eugene ativo · clock-in {new Date(eugeneShift.clock_in).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
              {lastMin !== null ? ` · última ação há ${lastMin} min` : ""}
            </span>
          ) : (
            <span className="pill"><span className="dot"></span>Eugene fora do turno</span>
          )}
          <button className="btn ghost sm" onClick={onViewEugene}>👁 Ver tela do Eugene</button>
        </div>
      </div>

      <div className="kpis">
        <div className="kpi"><div className="l">Ligações</div><div className="v">{callsToday}<small> / ~100</small></div></div>
        <div className="kpi"><div className="l">Quotes enviadas</div><div className="v">{quotesSent}</div></div>
        <div className="kpi"><div className="l">Appointments</div><div className="v">{appts}</div></div>
        <div className="kpi hl">
          <div className="l">Comissão Eugene · mês</div>
          <div className="v">${confSum}</div>
          <div className="l" style={{ marginTop: 4 }}>Bônus quinzena $50 · em curso — {fDay}/{fLen} dias, 0 falhas graves</div>
        </div>
      </div>

      <div className="grid2">
        <div className="panel">
          <h3>Funil de hoje</h3>
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
          <h3>Metas de hoje — auditadas</h3>
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
          <h3>Atividade por hora</h3>
          <div className="hours">
            {Object.entries(hours).map(([h, v]) => (
              <div className="hcol" key={h}>
                <div className="hbar" style={{ height: `${(v / maxH) * 70 + 2}px` }} />
                <span className="hlbl">{h}h</span>
              </div>
            ))}
          </div>
          <p className="meta" style={{ marginTop: 8 }}>
            Barras = ações concluídas por hora · blocos de inatividade aparecem em âmbar quando registrados
          </p>
        </div>

        <div className="panel">
          <h3>Alertas e recomendações</h3>
          {rows.length === 0 && <div className="center" style={{ padding: "10px 0" }}>Nada por enquanto.</div>}
          {rows.slice(0, 8).map((r, i) => (
            <div className="arow" key={i}>
              <span className={`atag ${r.cls}`}>{r.tag}</span>
              <span>{r.text}</span>
              {r.cid && (
                <a href={`https://app.gohighlevel.com/v2/location/Ao5ER8XBg3AtCJMccesF/contacts/detail/${r.cid}`}
                  target="_blank" rel="noreferrer">Ver lead ↗</a>
              )}
            </div>
          ))}
        </div>
      </div>

      <p className="footnote">Relatório completo do dia gerado às 18:30 · comissões conciliáveis com as vendas no fechamento do mês.</p>
    </div>
  );
}
