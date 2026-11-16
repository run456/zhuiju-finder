// 磁力直链搜索 - 前端逻辑
const $ = (sel) => document.querySelector(sel);
let films = [];
let resources = [];
let currentFilm = null;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  clearTimeout(toast._timer); toast._timer = setTimeout(() => t.classList.remove("show"), 1800);
}
async function api(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error("HTTP " + r.status);
  return r.json();
}

function tyClass(t) {
  if (t === "magnet") return "ty-magnet";
  if (t === "quark") return "ty-quark";
  if (t === "ed2k") return "ty-ed2k";
  return "ty-other";
}

async function doSearch() {
  const q = $("#queryInput").value.trim();
  if (!q) { toast("请输入片名"); return; }
  const btn = $("#searchBtn"); btn.disabled = true; btn.textContent = "搜索中…";
  $("#emptyState").style.display = "none";
  $("#resSection").style.display = "none";
  $("#filmSection").style.display = "block";
  $("#filmArea").innerHTML = `<div class="empty">正在搜索「${esc(q)}」的影片…</div>`;
  $("#filmCount").textContent = "";
  try {
    const data = await api("/api/bd/search?q=" + encodeURIComponent(q));
    films = data.films || [];
    $("#filmCount").textContent = `(${films.length})`;
    if (!films.length) {
      $("#filmArea").innerHTML = `<div class="empty">没找到相关影片，换个片名试试</div>`;
    } else {
      $("#filmArea").innerHTML = films.map((f, i) => `
        <div class="film-card" data-id="${esc(f.id)}" data-i="${i}">
          <div class="film-idx">${i + 1}</div>
          <div class="film-title" title="${esc(f.title)}">${esc(f.title)}</div>
          <span class="film-go">选这部 →</span>
        </div>`).join("");
      $("#filmArea").querySelectorAll(".film-card").forEach(c => {
        c.onclick = () => selectFilm(c.dataset.id, c);
      });
    }
  } catch (e) {
    $("#filmArea").innerHTML = `<div class="empty">搜索失败：${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false; btn.textContent = "搜 索";
  }
}

async function selectFilm(id, cardEl) {
  $("#filmArea").querySelectorAll(".film-card").forEach(c => c.classList.remove("active"));
  if (cardEl) cardEl.classList.add("active");
  currentFilm = films.find(f => f.id === id);
  $("#resSection").style.display = "block";
  $("#resArea").innerHTML = `<div class="empty">正在获取「${esc(currentFilm ? currentFilm.title : "")}」的真实链接…</div>`;
  $("#resCount").textContent = "";
  try {
    const data = await api("/api/bd/resources?id=" + encodeURIComponent(id));
    resources = data.resources || [];
    $("#resCount").textContent = `(${resources.length}) · ${esc(currentFilm ? currentFilm.title : "")}`;
    renderResources();
  } catch (e) {
    $("#resArea").innerHTML = `<div class="empty">获取失败：${esc(e.message)}</div>`;
  }
}

function renderResources() {
  const ft = $("#typeFilter").value;
  const list = resources.filter(r => !ft || r.type === ft);
  if (!list.length) { $("#resArea").innerHTML = `<div class="empty">该类型下暂无链接</div>`; return; }
  $("#resArea").innerHTML = list.map((r, i) => `
    <div class="link-card">
      <div class="link-main">
        <div class="link-title" title="${esc(r.filename)}">${i + 1}. ${esc(r.filename)}</div>
        <div class="link-badges">
          <span class="ty-badge ${tyClass(r.type)}">${esc(r.type_label)}</span>
          ${r.size ? `<span class="size-badge">${r.size} GB</span>` : ""}
          ${r.version ? `<span class="size-badge">${esc(r.version)}</span>` : ""}
        </div>
        <div class="link-url" title="${esc(r.url)}">${esc(r.url)}</div>
      </div>
      <div class="link-actions">
        <button class="btn btn-sm btn-copy" data-copy="${encodeURIComponent(r.url)}">复制</button>
        <button class="btn btn-sm btn-open" data-open="${encodeURIComponent(r.url)}">打开 ↗</button>
      </div>
    </div>`).join("");
}

function copyText(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(() => toast("已复制"))
      .catch(() => fallbackCopy(text));
  } else fallbackCopy(text);
}
function fallbackCopy(text) {
  const ta = document.createElement("textarea"); ta.value = text;
  document.body.appendChild(ta); ta.select();
  try { document.execCommand("copy"); toast("已复制"); } catch (e) { toast("复制失败"); }
  document.body.removeChild(ta);
}

function bindEvents() {
  $("#searchBtn").addEventListener("click", doSearch);
  $("#queryInput").addEventListener("keydown", e => { if (e.key === "Enter") doSearch(); });
  $("#clearBtn").addEventListener("click", () => { $("#queryInput").value = ""; $("#queryInput").focus(); });
  document.querySelectorAll(".chip").forEach(c => c.onclick = () => { $("#queryInput").value = c.textContent; doSearch(); });
  $("#typeFilter").addEventListener("change", renderResources);
  $("#copyAllBtn").addEventListener("click", () => {
    const ft = $("#typeFilter").value;
    const list = resources.filter(r => !ft || r.type === ft);
    if (!list.length) return;
    copyText(list.map(r => r.filename + "\n" + r.url).join("\n\n"));
  });
  $("#backBtn").addEventListener("click", () => {
    $("#resSection").style.display = "none";
    $("#filmArea").querySelectorAll(".film-card").forEach(c => c.classList.remove("active"));
  });
  document.addEventListener("click", e => {
    const cp = e.target.closest("[data-copy]");
    if (cp) { copyText(decodeURIComponent(cp.dataset.copy)); return; }
    const op = e.target.closest("[data-open]");
    if (op) {
      const url = decodeURIComponent(op.dataset.open);
      if (url.startsWith("magnet:") || url.startsWith("ed2k:")) {
        copyText(url); toast("磁力链接已复制，请粘贴到下载工具");
      } else window.open(url, "_blank", "noopener");
    }
  });
}

bindEvents();
