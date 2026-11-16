// AI Studio ploča: svake 2,5 s povuče /api/state i osvježi prikaz.

const AGENTS = {
  Scout:     { c: "#00e5ff", hair: "#2b1a0e", skin: "#f2c39b", shirt: "#00b8d4", style: "cap",  screen: "bars" },
  Writer:    { c: "#ffd400", hair: "#5b2a86", skin: "#ffd8b5", shirt: "#ff9f1a", style: "long", screen: "lines" },
  Clipper:   { c: "#ff3b5c", hair: "#111111", skin: "#c98b62", shirt: "#e0244a", style: "short", screen: "bars" },
  Editor:    { c: "#ff7a1a", hair: "#ff5a1f", skin: "#f5c9a4", shirt: "#ffb800", style: "long", screen: "bars" },
  Designer:  { c: "#18ff8a", hair: "#1d6b3a", skin: "#8d5a3b", shirt: "#12c46b", style: "cap",  screen: "bars" },
  Publisher: { c: "#ff2bd6", hair: "#2a0f3d", skin: "#ffd8b5", shirt: "#d91fb5", style: "short", screen: "lines" },
  Analyst:   { c: "#4d9dff", hair: "#3a2414", skin: "#e8b48a", shirt: "#2f6fff", style: "short", screen: "bars" },
  Community: { c: "#b06bff", hair: "#ff8a00", skin: "#f7cfae", shirt: "#8a3cff", style: "long", screen: "lines" },
};

const PLATFORM = {
  youtube:   { c: "#ff2a4d", short: "YT" },
  tiktok:    { c: "#00e5ff", short: "TT" },
  instagram: { c: "#ff2bd6", short: "IG" },
};

const STATUS = {
  idea: ["Ideja", "#8f80b8"], approved: ["Odobreno", "#00e5ff"], writing: ["Piše se", "#ffd400"],
  scripted: ["Scenarij", "#ffd400"], producing: ["U izradi", "#ff7a1a"], review: ["Čeka OK", "#ff2bd6"],
  scheduled: ["Zakazano", "#00e5ff"], publishing: ["Objavljuje", "#ff2bd6"], published: ["Objavljeno", "#18ff8a"],
  rejected: ["Odbijeno", "#5d5280"], failed: ["Greška", "#ff3b5c"],
};

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e4 ? (n / 1e3).toFixed(1) + "K" : Number(n || 0).toLocaleString("hr-HR"));
let TZ = "Europe/Zagreb";
const time = (ts) => new Date(ts * 1000).toLocaleTimeString("hr-HR", { hour: "2-digit", minute: "2-digit", timeZone: TZ });

// ---------- pixel likovi ----------
const BODY = [
  ".SSSSSSSSSS.",
  ".SSEESSEESS.",
  ".SSSSSSSSSS.",
  "..SSSMMSSS..",
  "...SSSSSS...",
  "..TTTTTTTT..",
  ".TTTTTTTTTT.",
  "STTTTTTTTTTS",
  "STTTTTTTTTTS",
];
const HAIR = {
  short: ["..HHHHHHHH..", ".HHHHHHHHHH.", ".HHSSSSSSHH."],
  long:  ["..HHHHHHHH..", ".HHHHHHHHHH.", "HHHSSSSSSHHH"],
  cap:   ["..CCCCCCCC..", ".CCCCCCCCCCCC", ".HHSSSSSSHH."],
};
function sprite(name) {
  const a = AGENTS[name];
  const rows = [...HAIR[a.style], ...BODY];
  if (a.style === "long") rows[4] = "HSSEESSEESSH", rows[5] = "HSSSSSSSSSSH";
  const col = { H: a.hair, S: a.skin, E: "#1a1030", M: "#b8456b", T: a.shirt, C: a.c };
  let rects = "";
  rows.forEach((r, y) => [...r].forEach((ch, x) => {
    if (col[ch]) rects += `<rect x="${x}" y="${y}" width="1.02" height="1.02" fill="${col[ch]}"/>`;
  }));
  return `<svg viewBox="0 0 13 12" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg">${rects}</svg>`;
}

function buildOffice() {
  $("office").innerHTML = Object.keys(AGENTS).map((n) => {
    const a = AGENTS[n];
    return `<div class="desk" id="desk-${n}" style="--c:${a.c}">
      <div class="bubble" id="bubble-${n}"></div>
      <div class="scene">
        <div class="person">${sprite(n)}</div>
        <div class="monitor"><div class="screen ${a.screen === "lines" ? "lines" : ""}"><i></i><i></i><i></i><i></i><i></i></div></div>
        <div class="table"></div>
      </div>
      <div class="tag">${n}</div>
    </div>`;
  }).join("");
}

// ---------- kanali ----------
let SELECTED = null; // null = svi kanali
try { SELECTED = Number(new URLSearchParams(location.search).get("channel") || localStorage.getItem("channel")) || null; } catch { /* nema spremanja */ }
let CHANNELS = [];
const chById = (id) => CHANNELS.find((c) => c.id === id);
// oznaka kanala na stavci, samo kad gledaš sve kanale
const chip = (cid) => {
  const c = chById(cid);
  return !SELECTED && c ? `<span class="chip" style="--c:${esc(c.color)}">${esc(c.name)}</span>` : "";
};

function renderPicker(s) {
  CHANNELS = s.channels;
  const sel = $("channel");
  const key = JSON.stringify(s.channels.map((c) => [c.id, c.name, c.active]));
  if (sel.dataset.key !== key) {
    sel.dataset.key = key;
    sel.innerHTML = `<option value="">Svi kanali (${s.channels.length})</option>` +
      s.channels.map((c) => `<option value="${c.id}">${esc(c.name)}${c.active ? "" : " (pauza)"}</option>`).join("");
  }
  sel.value = SELECTED || "";
  const c = chById(SELECTED);
  $("ch-color").style.background = c ? c.color : "linear-gradient(90deg,#ff2bd6,#00e5ff)";
}

$("channel").addEventListener("change", (e) => {
  SELECTED = Number(e.target.value) || null;
  try { localStorage.setItem("channel", SELECTED || ""); } catch { /* nema spremanja */ }
  history.replaceState(null, "", SELECTED ? `/?channel=${SELECTED}` : "/");
  approvalKey = null; latestId = null; tick();
});

// ---------- dijelovi ploče ----------
function spark(values, color) {
  if (values.length < 2) return "";
  const max = Math.max(...values), min = Math.min(...values), span = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * 100},${30 - ((v - min) / span) * 26}`).join(" ");
  return `<svg viewBox="0 0 100 32" preserveAspectRatio="none"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke" style="filter:drop-shadow(0 0 4px ${color})"/></svg>`;
}

function renderKpis(s) {
  const k = s.kpi, views = s.series.map((p) => p.views), fol = s.series.map((p) => p.followers);
  const tiles = [
    ["Pregledi ukupno", fmt(k.views_total), `+${fmt(k.views_24h)} u 24 h`, spark(views, "#00e5ff")],
    ["Pratitelji", fmt(k.followers), `+${fmt(k.followers_24h)} u 24 h`, spark(fol, "#18ff8a")],
    ["Objave danas", k.posts_today, `${k.posts_total} ukupno`, ""],
    ["Lajkovi", fmt(k.likes), "sve platforme", ""],
    ["U izradi", k.in_production, "videa u pipelineu", ""],
  ];
  $("kpis").innerHTML = tiles.map(([l, v, d, sp]) =>
    `<div class="panel kpi"><div class="label">${l}</div><div class="value">${v}</div><div class="delta">${d}</div>${sp}</div>`).join("");
}

function renderTeam(s) {
  const working = s.agents.filter((a) => a.state === "working").length;
  $("online").textContent = s.agents.length;
  $("team-count").textContent = `${working} radi`;
  $("team").innerHTML = s.agents.map((a) => {
    const m = AGENTS[a.name] || { c: "#fff" };
    return `<div class="agent ${a.state}" style="--c:${m.c}">
      <div class="av">${sprite(a.name)}</div>
      <div class="meta"><div class="name">${esc(a.name)} <span class="role">${esc(a.role)}</span></div>
        <div class="task" title="${esc(a.task)}">${esc(a.task)}</div>
        <div class="bar"><i style="width:${Math.round((a.progress || 0) * 100)}%"></i></div></div>
      <span class="st"></span></div>`;
  }).join("");
  for (const a of s.agents) {
    const desk = $(`desk-${a.name}`);
    if (!desk) continue;
    desk.className = `desk ${a.state}`;
    $(`bubble-${a.name}`).textContent = a.task;
  }
}

function renderPlatforms(s) {
  $("moving").textContent = `${s.kpi.in_production} videa u izradi`;
  $("platforms").innerHTML = s.pipeline.map((p) => {
    const c = (PLATFORM[p.id] || {}).c || "#fff";
    let off = "";
    if (!p.ready) {
      off = !SELECTED ? `<div class="off">Nije povezano na svim kanalima</div>`
        : p.id !== "instagram" && s.connect[p.id] ? `<a class="connect" href="/auth/${p.id}/start?channel=${SELECTED}">Poveži račun →</a>`
        : p.id === "instagram" ? `<div class="off">Upiši Instagram u ⚙ Kanali</div>`
        : `<div class="off">Nije povezano (vidi RACUNI.md)</div>`;
    }
    return `<div class="plat" style="--c:${c}">
      <div class="pn">${esc(p.name)}</div>
      <div class="pv">${p.posts} objava</div>
      <div class="ps">+${p.today} danas · ${fmt(p.views)} pregleda${p.followers ? ` · ${fmt(p.followers)} prat.` : ""}</div>${off}</div>`;
  }).join("");
}

function renderChart(s) {
  const cv = $("chart"), dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth, h = 120;
  cv.width = w * dpr; cv.height = h * dpr;
  const g = cv.getContext("2d");
  g.scale(dpr, dpr);
  g.clearRect(0, 0, w, h);
  // prirast pregleda između dva mjerenja
  const pts = s.series.slice(1).map((p, i) => Math.max(0, p.views - s.series[i].views));
  g.strokeStyle = "#2c1c52"; g.lineWidth = 1;
  for (let y = 20; y < h; y += 25) { g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); }
  if (pts.length < 2) {
    g.fillStyle = "#8f80b8"; g.font = "12px JetBrains Mono"; g.fillText("Čeka prve objave…", 8, 64);
    return;
  }
  const max = Math.max(...pts, 1);
  const xy = pts.map((v, i) => [(i / (pts.length - 1)) * w, h - 8 - (v / max) * (h - 24)]);
  const grad = g.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "#ff2bd655"); grad.addColorStop(1, "#ff2bd600");
  g.beginPath(); xy.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.lineTo(w, h); g.lineTo(0, h); g.closePath(); g.fillStyle = grad; g.fill();
  g.beginPath(); xy.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y)));
  g.strokeStyle = "#ff2bd6"; g.lineWidth = 2; g.shadowColor = "#ff2bd6"; g.shadowBlur = 10; g.stroke();
  g.shadowBlur = 0; g.fillStyle = "#ece6ff"; g.font = "11px JetBrains Mono";
  g.fillText(`+${fmt(pts[pts.length - 1])} zadnje mjerenje`, 8, 14);
}

function renderComments(s) {
  $("comments").innerHTML = s.comments.length ? s.comments.map((c) => {
    const p = PLATFORM[c.platform] || { c: "#fff", short: "?" };
    const rep = c.status === "replied" ? `<div class="rep">↳ ${esc(c.reply)}</div>` : "";
    return `<div class="cm"><div class="ic" style="background:${p.c}">${p.short}</div>
      <div>${chip(c.channel_id)}<b>@${esc(c.author)}</b> <span class="mono">${time(c.ts)}</span><p>${esc(c.text)}</p>${rep}</div></div>`;
  }).join("") : `<div class="empty">Još nema komentara.</div>`;
}

let approvalKey = null;
function renderApprovals(s) {
  $("ok-count").textContent = s.approvals.length;
  const key = s.approvals.map((a) => a.id).join(",");
  if (key === approvalKey) return; // ne diraj dok korisnik možda piše u polje
  approvalKey = key;
  const kinds = { topic: "Nova tema", publish: "Objava videa", reply: "Odgovor na komentar" };
  $("approvals").innerHTML = s.approvals.length ? s.approvals.map((a) => {
    const img = a.thumb ? `<img src="${a.thumb}" alt="">` : "";
    const extra = a.kind === "reply"
      ? `<textarea id="txt-${a.id}" rows="2">${esc(a.detail)}</textarea>`
      : `<div class="d">${esc(a.detail)}</div>`;
    const prev = a.video ? ` <a href="${a.video}" target="_blank">▶ pogledaj</a>` : "";
    return `<div class="ap ${img ? "" : "noimg"}">${img}<div>
      <div class="k">${chip(a.channel_id)}${kinds[a.kind] || a.kind}</div><div class="t">${esc(a.title)}</div>${extra}
      <div class="btns"><button class="btn ok" data-id="${a.id}" data-ok="1">Odobri</button>
      <button class="btn no" data-id="${a.id}" data-ok="0">Odbij</button>${prev}</div></div></div>`;
  }).join("") : `<div class="empty">Sve je čisto. Agenti rade dalje.</div>`;
}

function renderWeek(s) {
  const days = [];
  const start = new Date(); start.setHours(0, 0, 0, 0);
  for (let i = 0; i < 7; i++) days.push(new Date(start.getTime() + i * 86400000));
  $("week-count").textContent = `${s.week.filter((v) => v.status === "scheduled").length} zakazano`;
  $("week").innerHTML = days.map((d, i) => {
    const end = d.getTime() / 1000 + 86400;
    const items = s.week.filter((v) => v.scheduled_at >= d.getTime() / 1000 && v.scheduled_at < end);
    const label = i === 0 ? "Danas" : d.toLocaleDateString("hr-HR", { weekday: "short", day: "numeric" });
    return `<div class="day ${i === 0 ? "today" : ""}"><h3>${label}</h3>${items.map((v) => {
      const c = (STATUS[v.status] || [, "#fff"])[1];
      return `<div class="slot" style="--c:${c}"><b>${time(v.scheduled_at)}${v.format === "long" ? " · DUGI" : ""}</b><span title="${esc(v.title)}">${chip(v.channel_id)}${esc(v.title)}</span></div>`;
    }).join("")}</div>`;
  }).join("");
}

let latestId = null;
function renderLatest(s) {
  const v = s.latest;
  if (!v) { $("latest").innerHTML = `<div class="empty">Još ništa nije objavljeno.</div>`; latestId = null; return; }
  if (v.id !== latestId) {
    latestId = v.id;
    $("latest").innerHTML = `<div class="latest">
      <video class="${v.format === "long" ? "wide" : ""}" src="${v.video}" poster="${v.thumb}" muted loop playsinline autoplay controls></video>
      <div><div class="t">${esc(v.title)}</div><div class="nums" id="latest-nums"></div>
      <div class="links">${v.links.map((l) => `<a href="${esc(l.url)}" target="_blank" rel="noopener">${esc((PLATFORM[l.platform] || {}).short || l.platform)} ↗</a>`).join("")}</div>
      <div class="mono" style="margin-top:8px">objavljeno ${time(v.published_at)}</div></div></div>`;
  }
  $("latest-nums").innerHTML = `<div>Pregledi<b>${fmt(v.views)}</b></div><div>Lajkovi<b>${fmt(v.likes)}</b></div><div>Kom.<b>${fmt(v.comments)}</b></div>`;
}

function renderVideos(s) {
  $("videos").innerHTML = s.videos.length ? s.videos.map((v) => {
    const [label, c] = STATUS[v.status] || [v.status, "#fff"];
    const retry = v.status === "failed" ? ` <button class="btn no small" data-retry="${v.id}">Ponovi</button>` : "";
    const err = v.error && v.status === "failed" ? `<div class="err" title="${esc(v.error)}">${esc(v.error)}</div>` : "";
    const fmtTag = v.format === "long" ? `<span class="fmt long">DUGI</span>` : `<span class="fmt">KRATKI</span>`;
    return `<div class="vrow"><div style="min-width:0"><div class="vt">${fmtTag}${chip(v.channel_id)}${esc(v.title || v.topic)}</div>${err}</div>
      <div><span class="status" style="--c:${c}">${label}</span>${retry}</div></div>`;
  }).join("") : `<div class="empty">Scout upravo traži prve teme…</div>`;
}

function renderLog(s) {
  $("log").innerHTML = s.events.map((e) =>
    `<div><span class="ts">${time(e.ts)}</span><span class="who" style="color:${(AGENTS[e.agent] || {}).c || "#fff"}">${esc(e.agent)}</span>${chip(e.channel_id)}${esc(e.message)}</div>`).join("");
}

// ---------- petlja ----------
let last = null;
async function tick() {
  try {
    const r = await fetch(SELECTED ? `/api/state?channel=${SELECTED}` : "/api/state");
    if (!r.ok) throw new Error(r.status);
    const s = await r.json();
    last = s;
    TZ = s.timezone;
    $("demo").hidden = !s.demo;
    if (SELECTED && !s.channels.some((c) => c.id === SELECTED)) SELECTED = null;
    renderPicker(s);
    if (!$("voices").options.length) $("voices").innerHTML = s.voices.map((v) => `<option>${esc(v)}</option>`).join("");
    if ($("dlg").open) renderChannelList(s);
    renderKpis(s); renderTeam(s); renderPlatforms(s); renderChart(s); renderComments(s);
    renderApprovals(s); renderWeek(s); renderLatest(s); renderVideos(s); renderLog(s);
  } catch (e) {
    console.error(e);
  }
}

document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("button");
  if (!b) return;
  if (b.dataset.id) {
    b.disabled = true;
    const txt = $(`txt-${b.dataset.id}`);
    const r = await fetch(`/api/approvals/${b.dataset.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approve: b.dataset.ok === "1", text: txt ? txt.value : null }),
    });
    if (!r.ok) alert("Nije uspjelo: " + (await r.text()));
    approvalKey = null; tick();
  } else if (b.dataset.retry) {
    await fetch(`/api/videos/${b.dataset.retry}/retry`, { method: "POST" });
    tick();
  } else if (b.dataset.edit) {
    openForm(Number(b.dataset.edit));
  }
});

// ---------- prozor "Kanali": dodaj i uredi kanal ----------
const DAYS = [["mon", "Pon"], ["tue", "Uto"], ["wed", "Sri"], ["thu", "Čet"], ["fri", "Pet"], ["sat", "Sub"], ["sun", "Ned"]];
$("days").innerHTML = DAYS.map(([v, l]) => `<label class="ck"><input type="checkbox" name="ld" value="${v}"> ${l}</label>`).join("");
let EDITING = null;

function renderChannelList(s) {
  $("ch-list").innerHTML = s.channels.map((c) => {
    const conn = Object.entries(c.connections).map(([p, ok]) =>
      `<span class="pdot ${ok ? "on" : ""}" title="${p}: ${ok ? "povezano" : "nije povezano"}">${(PLATFORM[p] || {}).short || p}</span>`).join("");
    return `<button type="button" class="ch-item ${c.id === EDITING ? "sel" : ""}" data-edit="${c.id}" style="--c:${esc(c.color)}">
      <b>${esc(c.name)}</b>${c.active ? "" : ' <span class="mono">(pauza)</span>'}<span class="mono">${esc(c.niche || "")}</span><span>${conn}</span></button>`;
  }).join("");
}

function openForm(id) {
  EDITING = id;
  const c = chById(id) || { name: "", niche: "", language: "English", color: "#18ff8a", voice: "am_michael",
    post_times: "09:00,13:00,18:00", long_enabled: 1, long_days: "tue,thu,sat", long_time: "17:00",
    platforms: "youtube,tiktok,instagram", auto_topics: 0, auto_publish: 0, active: 1, ig_user_id: "" };
  const f = $("ch-form");
  $("form-title").textContent = id ? `Uredi: ${c.name}` : "Novi kanal";
  for (const k of ["name", "niche", "language", "color", "voice", "post_times", "long_time", "ig_user_id"]) f.elements[k].value = c[k] || "";
  for (const k of ["long_enabled", "auto_topics", "auto_publish", "active"]) f.elements[k].checked = !!c[k];
  const pf = (c.platforms || "").split(","), ld = (c.long_days || "").split(",");
  f.querySelectorAll('[name="pf"]').forEach((x) => (x.checked = pf.includes(x.value)));
  f.querySelectorAll('[name="ld"]').forEach((x) => (x.checked = ld.includes(x.value)));
  f.elements.ig_token.value = "";
  f.elements.ig_token.placeholder = c.has_ig_token ? "spremljen (ostavi prazno)" : "";
  $("form-msg").textContent = "";
  $("brand-out").innerHTML = "";
  $("extra").hidden = !id;
  if (id) renderConn(c);
  if (last) renderChannelList(last);
}

function renderConn(c) {
  const s = last || { connect: {} };
  $("conn").innerHTML = Object.entries(c.connections).map(([p, ok]) => {
    const name = { youtube: "YouTube", tiktok: "TikTok", instagram: "Instagram" }[p] || p;
    const action = ok ? `<span class="okc">✓ povezano</span>`
      : p === "instagram" ? `<span class="mono">upiši ID i token gore</span>`
      : s.connect[p] ? `<a class="btn ok small" href="/auth/${p}/start?channel=${c.id}">Poveži</a>`
      : `<span class="mono">treba ključeve u .env (RACUNI.md)</span>`;
    return `<div class="conn-row"><b>${name}</b>${action}</div>`;
  }).join("") || `<div class="mono">Nije odabrana nijedna platforma.</div>`;
}

$("manage").addEventListener("click", () => {
  if (last) renderChannelList(last);
  openForm(SELECTED || (CHANNELS[0] || {}).id || null);
  $("dlg").showModal();
  $("dlg").scrollTop = 0;
});
$("dlg-close").addEventListener("click", () => $("dlg").close());
$("ch-new").addEventListener("click", () => openForm(null));

$("ch-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target, el = f.elements;
  const body = {
    name: el.name.value.trim(), niche: el.niche.value.trim(), language: el.language.value.trim() || "English",
    color: el.color.value, voice: el.voice.value, post_times: el.post_times.value.replace(/\s/g, ""),
    long_enabled: el.long_enabled.checked, long_time: el.long_time.value || "17:00",
    long_days: [...f.querySelectorAll('[name="ld"]:checked')].map((x) => x.value).join(","),
    platforms: [...f.querySelectorAll('[name="pf"]:checked')].map((x) => x.value).join(","),
    auto_topics: el.auto_topics.checked, auto_publish: el.auto_publish.checked, active: el.active.checked,
    ig_user_id: el.ig_user_id.value.trim(), ig_token: el.ig_token.value.trim(),
  };
  const r = await fetch(EDITING ? `/api/channels/${EDITING}` : "/api/channels", {
    method: EDITING ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { $("form-msg").textContent = data.detail || "Greška"; return; }
  const id = EDITING || data.id;
  await tick();
  openForm(id);
  $("form-msg").textContent = "Spremljeno ✓";
});

$("make-brand").addEventListener("click", async () => {
  if (!EDITING) return;
  const btn = $("make-brand");
  btn.disabled = true; btn.textContent = "Radim…";
  const r = await fetch(`/api/channels/${EDITING}/branding`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tagline: $("tagline").value }),
  });
  const data = await r.json().catch(() => ({}));
  btn.disabled = false; btn.textContent = "Napravi ponovno";
  $("brand-out").innerHTML = r.ok ? data.files.map((f) =>
    `<a href="${esc(f.url)}" download target="_blank"><img src="${esc(f.url)}" alt=""><span>${esc(f.label)} ↓</span></a>`).join("")
    : `<div class="mono">${esc(data.detail || "Greška")}</div>`;
});

setInterval(() => ($("clock").textContent = new Date().toLocaleTimeString("hr-HR", { timeZone: TZ })), 1000);
window.addEventListener("resize", () => last && renderChart(last));
buildOffice();
tick();
setInterval(tick, 2500);
