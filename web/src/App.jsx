import React, { useState, useEffect, useMemo } from "react";
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from "recharts";
import {
  Crown, Activity, Gauge, BookOpen, ChevronDown, ChevronRight, ExternalLink,
  Globe, AlertTriangle, ArrowUpRight, ArrowDownRight, Minus, RefreshCw,
} from "lucide-react";

/* ROI — presentational front-end. All data comes from board.json, which the
   engine computes server-side from real sources. The browser holds no keys and
   invents nothing. */

const C = {
  ink: "#0B1220", panel: "#111C32", panel2: "#0F1A2E", line: "rgba(200,162,75,0.16)",
  lineSoft: "rgba(255,255,255,0.06)", gold: "#C8A24B", goldBright: "#E2C26A",
  emerald: "#2FB67A", emeraldSoft: "rgba(47,182,122,0.12)", rose: "#E2566B",
  roseSoft: "rgba(226,86,107,0.12)", amber: "#E0A23B", text: "#E8EAF2",
  mut: "#8A93A8", mut2: "#5E6883",
};
const serif = "Georgia, 'Times New Roman', serif";
const mono = "ui-monospace, 'SF Mono', Menlo, monospace";
const sans = "system-ui, -apple-system, 'Segoe UI', sans-serif";
const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));

const fmtUSD = (n) => {
  if (n == null || isNaN(n)) return "—";
  if (Math.abs(n) >= 1) return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return "$" + n.toLocaleString(undefined, { maximumFractionDigits: 6 });
};
const fmtPct = (n) => (n == null || isNaN(n) ? "—" : (n >= 0 ? "+" : "") + Number(n).toFixed(2) + "%");

function CrownMark({ size = 34 }) {
  return (
    <svg width={size} height={size * 0.8} viewBox="0 0 40 32" aria-hidden>
      <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={C.goldBright} /><stop offset="1" stopColor={C.gold} />
      </linearGradient></defs>
      <path d="M3 26 L6 9 L14 18 L20 5 L26 18 L34 9 L37 26 Z" fill="url(#cg)" />
      <rect x="3" y="26" width="34" height="4.5" rx="1.2" fill="url(#cg)" />
      <circle cx="6" cy="8" r="2.2" fill={C.goldBright} /><circle cx="20" cy="4" r="2.4" fill={C.goldBright} />
      <circle cx="34" cy="8" r="2.2" fill={C.goldBright} />
    </svg>
  );
}
function ScoreDial({ value, tone = "gold", size = 50, label }) {
  const col = tone === "emerald" ? C.emerald : C.gold;
  const r = size / 2 - 5, circ = 2 * Math.PI * r, off = circ * (1 - clamp(value, 0, 100) / 100);
  return (
    <div className="dial">
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke={C.lineSoft} strokeWidth="5" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={col} strokeWidth="5" fill="none"
          strokeDasharray={circ} strokeDashoffset={off} strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`} />
        <text x="50%" y="52%" textAnchor="middle" dominantBaseline="middle"
          style={{ fontFamily: mono, fontSize: 15, fontWeight: 700, fill: C.text }}>{Math.round(value)}</text>
      </svg>
      {label && <div className="dial-l">{label}</div>}
    </div>
  );
}
function Bar({ label, value }) {
  return (
    <div className="bar">
      <div className="bar-l">{label}</div>
      <div className="bar-t"><div className="bar-f" style={{ width: clamp(value, 0, 100) + "%" }} /></div>
      <div className="bar-v">{Math.round(value)}</div>
    </div>
  );
}
function Pill({ children, tone = "neutral" }) {
  const map = {
    low: [C.emeraldSoft, C.emerald], med: ["rgba(224,162,59,0.14)", C.amber],
    high: [C.roseSoft, C.rose], hold: ["rgba(200,162,75,0.12)", C.gold],
    neutral: ["rgba(255,255,255,0.05)", C.mut],
  };
  const [bg, fg] = map[tone] || map.neutral;
  return <span style={{ background: bg, color: fg }} className="pill">{children}</span>;
}
function Spark({ data, up }) {
  const d = (data || []).map((v, i) => ({ i, v }));
  if (d.length < 2) return <div style={{ height: 38 }} />;
  return (
    <ResponsiveContainer width="100%" height={38}>
      <LineChart data={d} margin={{ top: 2, bottom: 2, left: 0, right: 0 }}>
        <YAxis domain={["dataMin", "dataMax"]} hide /><Tooltip content={() => null} />
        <Line type="monotone" dataKey="v" stroke={up ? C.emerald : C.rose} strokeWidth={1.6} dot={false} isAnimationActive={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
function Src({ s }) {
  if (!s || !s.url) return null;
  return <a className="src" href={s.url} target="_blank" rel="noreferrer"><ExternalLink size={11} /> {s.title || s.url}</a>;
}
function Act({ tone, title, body }) {
  const col = tone === "buy" ? C.emerald : tone === "warn" ? C.rose : C.gold;
  const Icon = tone === "buy" ? ArrowUpRight : tone === "warn" ? ArrowDownRight : Minus;
  return <div className="act"><Icon size={14} color={col} /><div><b style={{ color: col }}>{title}.</b> {body}</div></div>;
}

function Card({ it, horizon, open, onToggle }) {
  const crown = it.tier === "crown";
  const up = (it.changes?.d7 ?? 0) >= 0;
  const comp = it.components || {};
  return (
    <div className="card" style={{ borderLeft: `2px solid ${crown ? C.emerald : C.line}`, background: open ? C.panel : C.panel2 }}>
      <button className="card-h" onClick={onToggle}>
        <div className="rank" style={{ color: crown ? C.emerald : C.mut }}>{it.rank}</div>
        {it.image && <img src={it.image} alt="" width={24} height={24} style={{ borderRadius: 999 }} />}
        <div className="card-id">
          <div className="card-name">
            <span>{it.name}</span><span className="tkr">{it.ticker}</span>{crown && <Crown size={12} color={C.emerald} />}
          </div>
          <div className="card-sec">{it.sector}</div>
        </div>
        <div className="spark-w"><Spark data={it.spark} up={up} /></div>
        <div className="px">
          <div className="px-v">{fmtUSD(it.price)}</div>
          <div className="px-c" style={{ color: up ? C.emerald : C.rose }}>{fmtPct(it.changes?.d7)} 7d</div>
        </div>
        <Pill tone={it.risk}>{it.risk}</Pill>
        <ScoreDial value={it.signal} tone={crown ? "emerald" : "gold"} />
        {open ? <ChevronDown size={16} color={C.mut} /> : <ChevronRight size={16} color={C.mut} />}
      </button>
      {open && (
        <div className="card-b">
          <p className="thesis">{it.thesis}</p>
          <div className="stats">
            <Stat k="RSI (14)" v={it.rsi?.toFixed(0)} note={it.rsi >= 70 ? "overbought" : it.rsi <= 30 ? "oversold" : "neutral"} />
            <Stat k="Volatility" v={it.volatility?.toFixed(1) + "%"} note="annualised" />
            <Stat k="24h" v={fmtPct(it.changes?.d1)} tone={it.changes?.d1 >= 0 ? "up" : "down"} />
            <Stat k="30d" v={fmtPct(it.changes?.d30)} tone={it.changes?.d30 >= 0 ? "up" : "down"} />
            <Stat k="Security" v={it.security} note="resilience" />
            <Stat k="Pivot" v={fmtUSD(it.levels?.pivot)} note="30d mean" />
            <Stat k="Support" v={fmtUSD(it.levels?.support)} note="30d low" />
            <Stat k="Signal" v={it.signal} note={horizon === "long" ? "long-term" : "short-term"} />
          </div>
          <div className="grid2">
            <div>
              <div className="lbl">Signal composition</div>
              <div className="bars">
                {horizon === "long" ? (<>
                  <Bar label="30d trend" value={comp.trend30d} /><Bar label="Market depth" value={comp.market_depth} />
                  <Bar label="Low volatility" value={comp.low_volatility} /><Bar label="RSI balance" value={comp.rsi_balance} />
                </>) : (<>
                  <Bar label="24h momentum" value={comp.momentum} /><Bar label="7d trend" value={comp.trend7d} />
                  <Bar label="RSI balance" value={comp.rsi_balance} /><Bar label="Low volatility" value={comp.low_volatility} />
                </>)}
              </div>
              <p className="fine">A weighted blend of the bars above, computed from real price data. A heuristic ranking — not a probability of profit.</p>
            </div>
            <div>
              <div className="lbl">Discipline — when to act</div>
              <div className="acts">
                <Act tone="buy" title="Buy" body={it.buy} />
                <Act tone="hold" title="Hold" body={it.hold} />
                <Act tone="warn" title="Sell / trim" body={it.sell} />
              </div>
            </div>
          </div>
          {(it.flow_note || it.catalyst_note) && (
            <div className="flow">
              {it.flow_note && <span><b style={{ color: C.gold }}>Flows.</b> {it.flow_note}</span>}
              {it.catalyst_note && <span><b style={{ color: C.amber }}>Filings.</b> {it.catalyst_note}</span>}
            </div>
          )}
          <div className="srcs">{(it.sources || []).map((s, i) => <Src key={i} s={s} />)}</div>
        </div>
      )}
    </div>
  );
}
function Stat({ k, v, note, tone }) {
  const col = tone === "up" ? C.emerald : tone === "down" ? C.rose : C.text;
  return <div className="stat"><div className="stat-k">{k}</div><div className="stat-v" style={{ color: col }}>{v}</div>{note && <div className="stat-n">{note}</div>}</div>;
}

function SectorGroups({ items, horizon, openKey, setOpenKey }) {
  const groups = useMemo(() => {
    const g = {};
    items.forEach((it) => { (g[it.sector || "Other"] = g[it.sector || "Other"] || []).push(it); });
    return Object.entries(g).sort((a, b) =>
      Math.min(...a[1].map((x) => x.rank)) - Math.min(...b[1].map((x) => x.rank)));
  }, [items]);
  return (
    <div className="groups">
      {groups.map(([sector, arr]) => (
        <div key={sector}>
          <div className="sector"><span className="dot" /><span>{sector}</span><span className="rule" /></div>
          {arr.map((it) => {
            const key = sector + it.ticker + it.rank;
            return <Card key={key} it={it} horizon={horizon} open={openKey === key} onToggle={() => setOpenKey(openKey === key ? null : key)} />;
          })}
        </div>
      ))}
    </div>
  );
}

function Macro({ macro }) {
  if (!macro || !macro.available) {
    return <div className="macro"><div className="macro-h"><Globe size={14} color={C.gold} /><span className="lbl">State of the world</span></div>
      <div className="fine">Macro feed not configured (add a free FRED_API_KEY to light this up).</div></div>;
  }
  return (
    <div className="macro">
      <div className="macro-h"><Globe size={14} color={C.gold} /><span className="lbl">State of the world</span><Pill tone="hold">{macro.regime}</Pill></div>
      <div className="macro-b">
        <p className="macro-sum">{macro.summary}</p>
        <div className="macro-r">
          {(macro.metrics || []).slice(0, 6).map((m, i) => (
            <div key={i} className="metric"><span className="m-l">{m.label}</span>
              <span className="m-v">{Number(m.value).toLocaleString(undefined, { maximumFractionDigits: 2 })}
                <span style={{ color: m.delta >= 0 ? C.emerald : C.rose, marginLeft: 6, fontSize: 10 }}>{m.delta >= 0 ? "▲" : "▼"}</span></span>
            </div>
          ))}
        </div>
      </div>
      <div className="srcs">{(macro.sources || []).map((s, i) => <Src key={i} s={s} />)}</div>
    </div>
  );
}

function Methodology({ prov }) {
  const rows = [
    ["Equities — computed from real prices", "Daily closes & volume come from " + (prov?.prices || "Stooq") + ". RSI(14), annualised volatility, 1d/7d/30d momentum, the 30-day pivot and support are all calculated, not asserted. Liquidity depth is a real dollar-volume percentile across the universe."],
    ["Catalysts & flows — official sources", "SEC EDGAR surfaces recent 8-K / Form 4 (insider) / 10-Q filings. Congressional (STOCK Act) disclosures are aggregated from public mirrors. Each shows on the card with a link."],
    ["Macro — FRED", "Rates, the 10y–2y curve, CPI, unemployment, VIX, USD and oil drive a plain-English regime read straight from the St. Louis Fed."],
    ["Signal (0–100) — a heuristic, not a promise", "A transparent weighted blend of the component bars on each card. Short-term weights momentum; long-term weights durable trend, depth and low volatility. It ranks relative attractiveness — never a probability of profit."],
    ["Crown Tier (emerald)", "The three most resilient names per board: deeper, lower-volatility, RSI in a healthy band. 'More secure' means lower drawdown risk, never zero risk."],
    ["Discipline", "Each name carries concrete buy / hold / sell triggers tied to its real pivot, support and RSI bands — so the decision is pre-committed before emotion arrives."],
  ];
  return (
    <div className="method">
      <h2>How ROI thinks</h2>
      <p className="lede">ROI is the brain of a portfolio, not a fund. It does not take your money or place trades. It computes a ranked, sourced, risk-aware view from real data and shows its work.</p>
      {rows.map(([t, d], i) => <div key={i} className="m-row"><div className="m-t">{t}</div><div className="m-d">{d}</div></div>)}
      <div className="disc"><div className="disc-h"><AlertTriangle size={14} color={C.rose} /><b>Not financial advice</b></div>
        <p>ROI is an information and research tool — not a broker, adviser, or fiduciary, and nothing here is a recommendation to buy or sell. Markets carry real risk of loss. Verify with primary sources and a licensed professional before acting.</p></div>
    </div>
  );
}

export default function App() {
  const [board, setBoard] = useState(null);
  const [err, setErr] = useState(null);
  const [asset, setAsset] = useState("equities");
  const [horizon, setHorizon] = useState("long");
  const [openKey, setOpenKey] = useState(null);

  useEffect(() => {
    fetch("board.json", { cache: "no-store" })
      .then((r) => { if (!r.ok) throw new Error("no board.json yet"); return r.json(); })
      .then(setBoard)
      .catch((e) => setErr(e.message));
  }, []);

  const items = useMemo(() => {
    if (!board) return [];
    const side = asset === "equities" ? board.equities : board.crypto;
    return (side && side[horizon]) || [];
  }, [board, asset, horizon]);

  const stamp = board?.generated_at ? new Date(board.generated_at) : null;

  return (
    <div className="app">
      <style>{CSS}</style>
      <div className="glow" />
      <div className="wrap">
        <header>
          <div className="brand">
            <CrownMark size={34} />
            <div>
              <div className="word">R<span style={{ color: C.gold }}>O</span>I</div>
              <div className="tag">Investing Intelligence</div>
            </div>
          </div>
          <div className="meta">
            <div className="meta-d">{stamp ? stamp.toLocaleString() : "—"}</div>
            <div className="meta-s">The brain of your portfolio · not a fund</div>
          </div>
        </header>
        <div className="hr" />

        {!board && !err && <div className="state">Loading today's board…</div>}
        {err && (
          <div className="state">
            <AlertTriangle size={22} color={C.rose} />
            <p>No board to show yet — <code>board.json</code> hasn't been built.</p>
            <p className="fine">Run <code>python -m engine.build_board</code> (or let the daily job run once), then refresh.</p>
          </div>
        )}

        {board && (
          <>
            <Macro macro={board.macro} />
            <div className="controls">
              <nav className="tabs">
                {[["equities", "Equities", Activity], ["crypto", "Crypto", Gauge], ["method", "Method", BookOpen]].map(([k, l, Icon]) => (
                  <button key={k} onClick={() => { setAsset(k); setOpenKey(null); }}
                    className={"tab" + (asset === k ? " on" : "")}><Icon size={13} /> {l}</button>
                ))}
              </nav>
              {asset !== "method" && (
                <div className="tabs">
                  {[["long", "Long-term"], ["short", "Short-term"]].map(([k, l]) => (
                    <button key={k} onClick={() => { setHorizon(k); setOpenKey(null); }}
                      className={"tab2" + (horizon === k ? " on" : "")}>{l}</button>
                  ))}
                </div>
              )}
            </div>

            {asset !== "method" && (
              <div className="board-h">
                <h1>{asset === "equities" ? "Equity" : "Crypto"} board</h1>
                <span>· {horizon === "long" ? "12–36 month conviction" : "2–8 week tactical"} · ranked 1–8 · Crown-Tier in emerald</span>
              </div>
            )}

            <main>
              {asset === "method" ? <Methodology prov={board.provenance} /> :
                items.length ? <SectorGroups items={items} horizon={horizon} openKey={openKey} setOpenKey={setOpenKey} />
                  : <div className="state">No {asset} names in this board yet. The source may have been unavailable at build time — check the next run.</div>}
            </main>

            <footer>
              <div className="f-l"><Crown size={12} color={C.gold} /><span>ROI — le roi de votre portefeuille</span></div>
              <span className="f-r">Research tool, not financial advice. Markets carry risk of loss.</span>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}

const CSS = `
* { box-sizing: border-box; }
.app { min-height:100vh; background:${C.ink}; color:${C.text}; font-family:${sans}; position:relative; }
.glow { position:fixed; inset:0; background:radial-gradient(900px 500px at 50% -10%, rgba(200,162,75,0.10), transparent 60%); pointer-events:none; }
.wrap { position:relative; max-width:1080px; margin:0 auto; padding:0 16px; }
header { padding:26px 0 14px; display:flex; align-items:flex-end; justify-content:space-between; flex-wrap:wrap; gap:12px; }
.brand { display:flex; align-items:center; gap:12px; }
.word { font-family:${serif}; font-size:30px; letter-spacing:.04em; line-height:1; }
.tag { font-size:10.5px; letter-spacing:.22em; color:${C.mut}; text-transform:uppercase; margin-top:3px; }
.meta { text-align:right; }
.meta-d { font-family:${mono}; font-size:12px; color:${C.mut}; }
.meta-s { font-size:10.5px; color:${C.mut2}; letter-spacing:.05em; }
.hr { height:1px; background:linear-gradient(90deg, ${C.gold}, transparent); opacity:.5; margin-bottom:18px; }
.macro { background:linear-gradient(180deg, ${C.panel}, ${C.panel2}); border:1px solid ${C.line}; border-radius:12px; padding:14px 16px; margin-bottom:18px; }
.macro-h { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.lbl { font-size:10px; letter-spacing:.12em; color:${C.gold}; text-transform:uppercase; font-weight:600; }
.macro-b { display:flex; gap:14px; flex-wrap:wrap; }
.macro-sum { font-size:13px; color:${C.text}; line-height:1.55; flex:1; min-width:240px; margin:0; }
.macro-r { display:grid; grid-template-columns:1fr 1fr; gap:6px 16px; min-width:240px; }
.metric { display:flex; justify-content:space-between; gap:10px; }
.m-l { font-size:11px; color:${C.mut}; } .m-v { font-family:${mono}; font-size:12px; }
.pill { font-size:10.5px; font-weight:600; padding:3px 9px; border-radius:999px; }
.controls { display:flex; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:16px; }
.tabs { display:flex; gap:4px; background:${C.panel2}; padding:4px; border-radius:10px; border:1px solid ${C.line}; }
.tab { display:inline-flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600; padding:7px 14px; border-radius:7px; color:${C.mut}; background:transparent; border:none; cursor:pointer; }
.tab.on { color:${C.ink}; background:${C.gold}; }
.tab2 { font-size:12.5px; font-weight:600; padding:7px 14px; border-radius:7px; color:${C.mut}; background:transparent; border:1px solid transparent; cursor:pointer; }
.tab2.on { color:${C.text}; background:${C.panel}; border-color:${C.line}; }
.board-h { display:flex; align-items:baseline; gap:8px; margin-bottom:14px; flex-wrap:wrap; }
.board-h h1 { font-family:${serif}; font-size:22px; margin:0; }
.board-h span { font-size:12px; color:${C.mut}; }
.groups { display:flex; flex-direction:column; gap:16px; }
.sector { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.sector span:nth-child(2) { font-size:11px; letter-spacing:.1em; color:${C.mut}; text-transform:uppercase; font-weight:600; }
.dot { width:5px; height:5px; border-radius:999px; background:${C.gold}; }
.rule { flex:1; height:1px; background:${C.lineSoft}; }
.card { border-radius:8px; margin-bottom:8px; }
.card-h { width:100%; text-align:left; padding:11px 14px; display:flex; align-items:center; gap:12px; background:transparent; border:none; cursor:pointer; color:${C.text}; }
.rank { font-family:${mono}; font-size:12px; width:20px; font-weight:700; }
.card-id { min-width:0; flex:1; }
.card-name { display:flex; align-items:center; gap:8px; }
.card-name span:first-child { font-weight:650; font-size:14px; }
.tkr { font-family:${mono}; font-size:11px; color:${C.mut2}; text-transform:uppercase; }
.card-sec { font-size:11px; color:${C.mut}; }
.spark-w { width:84px; } @media(max-width:640px){ .spark-w{ display:none; } }
.px { text-align:right; width:92px; }
.px-v { font-family:${mono}; font-size:13px; } .px-c { font-family:${mono}; font-size:11px; }
.dial { display:flex; flex-direction:column; align-items:center; }
.dial-l { font-size:9.5px; letter-spacing:.09em; color:${C.mut}; margin-top:4px; text-transform:uppercase; }
.card-b { padding:0 14px 16px; border-top:1px solid ${C.lineSoft}; }
.thesis { font-size:13px; line-height:1.6; margin:12px 0; }
.stats { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px; }
@media(max-width:640px){ .stats{ grid-template-columns:repeat(2,1fr); } }
.stat-k { font-size:9.5px; letter-spacing:.07em; color:${C.mut}; text-transform:uppercase; }
.stat-v { font-family:${mono}; font-size:14px; margin-top:2px; } .stat-n { font-size:9.5px; color:${C.mut2}; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; } @media(max-width:640px){ .grid2{ grid-template-columns:1fr; } }
.bars { display:flex; flex-direction:column; gap:6px; margin-top:8px; }
.bar { display:flex; align-items:center; gap:8px; }
.bar-l { font-size:10.5px; color:${C.mut}; width:92px; }
.bar-t { flex:1; height:6px; border-radius:999px; background:${C.lineSoft}; }
.bar-f { height:6px; border-radius:999px; background:${C.gold}; }
.bar-v { font-family:${mono}; font-size:10.5px; width:26px; text-align:right; }
.fine { font-size:11px; color:${C.mut2}; margin-top:8px; line-height:1.5; }
.acts { display:flex; flex-direction:column; gap:8px; margin-top:8px; }
.act { display:flex; gap:8px; font-size:12px; line-height:1.5; } .act b { font-weight:700; }
.flow { display:flex; flex-wrap:wrap; gap:14px; margin-top:14px; font-size:12px; color:${C.text}; }
.srcs { display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:12px; }
.src { display:inline-flex; align-items:center; gap:4px; font-size:11px; color:${C.gold}; text-decoration:none; }
.src:hover { text-decoration:underline; }
.method { max-width:760px; }
.method h2 { font-family:${serif}; font-size:22px; margin:0 0 6px; }
.lede { font-size:13px; color:${C.mut}; line-height:1.65; margin-bottom:14px; }
.m-row { padding:12px 0; border-bottom:1px solid ${C.lineSoft}; }
.m-t { font-size:13.5px; font-weight:650; } .m-d { font-size:12.5px; color:${C.mut}; margin-top:3px; line-height:1.6; }
.disc { background:${C.roseSoft}; border:1px solid rgba(226,86,107,0.3); border-radius:8px; padding:12px 14px; margin-top:16px; }
.disc-h { display:flex; align-items:center; gap:8px; margin-bottom:4px; color:${C.rose}; font-size:12px; }
.disc p { font-size:12px; color:${C.text}; line-height:1.6; margin:0; }
.state { display:flex; flex-direction:column; align-items:center; gap:8px; text-align:center; padding:48px 20px; color:${C.mut}; }
.state code { font-family:${mono}; color:${C.gold}; }
footer { border-top:1px solid ${C.lineSoft}; padding:16px 0 40px; display:flex; justify-content:space-between; flex-wrap:wrap; gap:8px; }
.f-l { display:flex; align-items:center; gap:8px; font-family:${serif}; font-size:13px; color:${C.mut}; }
.f-r { font-size:10.5px; color:${C.mut2}; }
`;
