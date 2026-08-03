#!/usr/bin/env python3
"""Generate a self-contained interactive Agent Explorer (docs/explorer/index.html)
from the real agent frontmatter in .github/agents/*.agent.md.

Run:  python3 docs/explorer/generate.py
No dependencies; output is a single static HTML file (works via file:// and GitHub Pages).
"""
import glob, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AGENT_DIR = os.path.join(ROOT, ".github", "agents")

BUILTIN_TOOLS = {"read", "edit", "search", "execute", "agent", "todo"}
STATUS_STOP = {"DO", "NOT", "MUST", "ALWAYS", "NEVER", "AND", "OR", "THE", "DFS", "DTS",
               "SRQ", "SIR", "TDD", "MCP", "PR", "RED", "GREEN", "OWASP", "JQL", "JSON",
               "WIP", "URL", "API", "P7", "T7", "GTS", "VET", "QA", "CM", "HTTP", "YAML"}

ROLE_ORDER = {"orchestrator": 0, "planner": 1, "architect": 2, "spec-author": 3, "tester": 4,
              "developer": 5, "reviewer": 6, "builder": 7, "pr-author": 8, "knowledge": 9}
PIPELINE = ["Plan", "Architect", "Spec", "Test", "Develop", "Review", "Build", "PR"]
ROLE_PHASE = {"planner": 0, "architect": 1, "spec-author": 2, "tester": 3,
              "developer": 4, "reviewer": 5, "builder": 6, "pr-author": 7}
PHASE_LABEL = {"planner": "planning", "architect": "the architecture-review gate",
               "spec-author": "spec authoring (on demand)", "tester": "the RED/GREEN test phase",
               "developer": "the develop phase", "reviewer": "review", "builder": "the build gate",
               "pr-author": "PR authoring", "knowledge": "knowledge queries"}

SYSTEMS = {
    "p7": {"label": "P7", "name": "Pricing & Risk", "fill": "#E3ECFB", "ink": "#3F6FB5"},
    "t7": {"label": "T7", "name": "Trading System", "fill": "#DBF0EE", "ink": "#2E8E84"},
    "generic": {"label": "Generic", "name": "All systems", "fill": "#ECE7FA", "ink": "#6E5BB8"},
}
GROUP_LABEL = {"generic": "Generic · router & clarifier",
               "p7": "P7 · Pricing & Risk Management", "t7": "T7 · Trading System"}
GROUP_ORDER = {"generic": 0, "p7": 1, "t7": 2}

# curated, grounded invocation examples for the user-invocable agents
INVOKE_EXAMPLES = {
    "gts-orchestrator": ["/gts-orchestrator Fix the SMP Type-B reason code on cancel in T7",
                          "/gts-orchestrator Add a validation rule to the P7 pricing engine"],
    "gts-prompt-clarifier": ["/gts-prompt-clarifier rebase my branch and rerun the failing tests"],
    "p7-orchestrator": ["/p7-orchestrator Add a validation rule to the pricing-engine request handler"],
    "t7-orchestrator": ["/t7-orchestrator Reject expired orders in the Matcher on new-order entry"],
    "p7-sdlc-reviewer": ["/p7-sdlc-reviewer Review the diff on this branch"],
}
# how an orchestrator typically dispatches each internal role (representative instruction)
DISPATCH = {
    "planner": "Analyze this request and produce a plan with tasks, affected files and acceptance criteria.",
    "architect": "Review this plan against architecture, boundaries and build order — approve, revise or block.",
    "tester": "Write failing tests for each acceptance criterion; confirm they fail (RED).",
    "developer": "Implement the minimal code to make the failing tests pass (GREEN).",
    "reviewer": "Review these changed files for correctness, security, performance and patterns.",
    "builder": "Build the affected components in dependency order.",
    "pr-author": "Write the PR title, description and changelog; link the Jira ticket.",
    "spec-author": "Author the DFS/DTS/SRQ from the approved plan.",
    "knowledge": "Where is the Matcher and who owns it?",
}


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] in "\"'" and v[-1] == v[0]:
        v = v[1:-1]
    # some agent frontmatter stores escaped unicode (e.g. \u2192) as literal text
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), v)


def parse_list(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        v = v[1:-1]
    return [unquote(x) for x in v.split(",") if x.strip()]


def parse_frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    fm_raw, body = m.group(1), m.group(2)
    fm = {}
    for line in fm_raw.splitlines():
        km = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s?(.*)$", line)
        if km:
            fm[km.group(1)] = km.group(2)
    return fm, body


def extract_statuses(body):
    toks = re.findall(r"^\s*(?:\||-)\s*\*\*([A-Z][A-Z0-9_]{2,})\*\*", body, re.M)
    out = []
    for t in toks:
        if t in STATUS_STOP or t in out:
            continue
        out.append(t)
    return out[:10]


def role_info(name):
    """Return (role, role_label, type_note)."""
    if name == "gts-orchestrator":
        return ("orchestrator", "Generic router",
                "Routes each request to the right system orchestrator — implements nothing itself.")
    if name == "gts-prompt-clarifier":
        return ("clarifier", "Prompt clarifier",
                "Runs before the pipeline: resolves ambiguity and enriches the request, then hands to the router.")
    if name.endswith("-orchestrator"):
        return ("orchestrator", "System orchestrator",
                "Coordinates its system's whole SDLC pipeline — delegates every step, writes no code.")
    m = re.match(r"^(?:p7|t7)-sdlc-(.+)$", name)
    role = m.group(1) if m else name
    labels = {"pr-author": "PR Author", "spec-author": "Spec Author", "knowledge": "Knowledge"}
    return (role, labels.get(role, role.replace("-", " ").title()), "")


def invoke_of(name, system, role, invocable):
    if invocable:
        return {"mode": "command", "examples": INVOKE_EXAMPLES.get(name) or [f"/{name}"],
                "note": "", "dispatch": ""}
    orch = "p7-orchestrator" if system == "p7" else "t7-orchestrator" if system == "t7" else ""
    phase = PHASE_LABEL.get(role, "its phase")
    note = (f"Internal — you don't call it directly. The {orch} dispatches it during {phase}."
            if orch else f"Internal — dispatched during {phase}.")
    return {"mode": "internal", "examples": [], "note": note, "dispatch": DISPATCH.get(role, "")}


def model_kind(model):
    ml = (model or "").lower()
    if "opus" in ml:
        return ("Opus", "#C2862B")
    if "mini" in ml:
        return ("GPT-5 mini", "#3E9460")
    if "sonnet" in ml:
        return ("Sonnet", "#3F6FB5")
    return (model or "—", "#8A92A0")


agents = []
for path in sorted(glob.glob(os.path.join(AGENT_DIR, "*.agent.md"))):
    text = open(path, encoding="utf-8").read()
    fm, body = parse_frontmatter(text)
    name = fm.get("name", os.path.basename(path).replace(".agent.md", ""))
    tools = parse_list(fm.get("tools", "[]"))
    servers, seen = [], set()
    for t in tools:
        ns = t.split("/")[0]
        if ns in BUILTIN_TOOLS or ns in seen:
            continue
        seen.add(ns)
        servers.append(ns)
    skills = [s.split("/")[-1] for s in parse_list(fm.get("skills", "[]"))]
    skills_common = parse_list(fm.get("skills_common", "[]"))
    delegates = parse_list(fm.get("agents", "[]"))
    system = fm.get("system", "").strip() or ("p7" if name.startswith("p7") else
                                              "t7" if name.startswith("t7") else "generic")
    role, role_label, type_note = role_info(name)
    invocable = unquote(fm.get("user-invocable", "false")).lower() == "true"
    mk_label, mk_ink = model_kind(fm.get("model", ""))
    if role in ("orchestrator", "router"):
        in_group = 0
    elif role == "clarifier":
        in_group = 1
    else:
        in_group = ROLE_ORDER.get(role, 99) + 1
    agents.append({
        "name": name,
        "system": system,
        "group": GROUP_LABEL[system],
        "groupOrder": GROUP_ORDER[system],
        "inGroup": in_group,
        "role": role,
        "roleLabel": role_label,
        "typeNote": type_note,
        "phase": ROLE_PHASE.get(role, -1),
        "description": unquote(fm.get("description", "")),
        "argHint": unquote(fm.get("argument-hint", "")),
        "userInvocable": invocable,
        "model": unquote(fm.get("model", "")),
        "modelLabel": mk_label,
        "modelInk": mk_ink,
        "skills": skills,
        "skillsCommon": skills_common,
        "servers": servers,
        "delegates": delegates,
        "statuses": extract_statuses(body),
        "invoke": invoke_of(name, system, role, invocable),
    })

agents.sort(key=lambda a: (a["groupOrder"], a["inGroup"], a["name"]))
group_order = []
for a in agents:
    if a["group"] not in group_order:
        group_order.append(a["group"])

DEFAULT = "t7-sdlc-developer"

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GTS AI SDLC · Agent Explorer</title>
<style>
  :root{
    --ink:#1F2733; --body:#5B6472; --muted:#8A92A0; --faint:#AEB6C0;
    --line:#E4E9EF; --bg:#F4F7FB; --card:#FFFFFF; --hair:#EEF1F5;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);line-height:1.5;
    font-family:Inter,'SF Pro Display',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}
  a{color:#3F6FB5;text-decoration:none} a:hover{text-decoration:underline}
  .hero{background:linear-gradient(135deg,#5E54C8 0%,#3F6FB5 52%,#2E8E84 100%);color:#fff;padding:34px 24px 30px}
  .hero-in{max-width:1180px;margin:0 auto}
  .hero .eyebrow{font-size:12.5px;font-weight:700;letter-spacing:2.5px;opacity:.85}
  .hero h1{margin:8px 0 6px;font-size:30px;font-weight:800;letter-spacing:-.4px}
  .hero .sub{margin:0;font-size:15px;opacity:.94;max-width:860px}
  .wrap{max-width:1180px;margin:0 auto;padding:22px 24px 56px}
  .controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:2px 0 18px}
  .search{flex:1 1 240px;min-width:200px;display:flex;align-items:center;gap:8px;
    border:1px solid var(--line);border-radius:10px;padding:9px 12px;background:#fff}
  .search input{border:0;outline:0;font-size:14px;width:100%;color:var(--ink);background:transparent}
  .chips{display:flex;flex-wrap:wrap;gap:6px}
  .chip{border:1px solid var(--line);background:#fff;color:var(--body);border-radius:999px;
    padding:6px 13px;font-size:12.5px;font-weight:600;cursor:pointer;transition:.12s}
  .chip:hover{border-color:#c7cfd8}
  .chip.on{background:#1F2733;color:#fff;border-color:#1F2733}
  .legend{display:flex;flex-wrap:wrap;gap:13px;font-size:11.5px;color:var(--muted);margin-left:auto}
  .legend .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:1px}
  .layout{display:grid;grid-template-columns:344px 1fr;gap:20px;align-items:start}
  .card{background:var(--card);border:1px solid var(--line);border-radius:14px;box-shadow:0 1px 3px rgba(15,23,42,.05)}
  .list{padding:12px;max-height:80vh;overflow:auto}
  .group{font-size:11px;font-weight:700;letter-spacing:.8px;color:var(--muted);text-transform:uppercase;margin:14px 8px 8px}
  .group:first-child{margin-top:4px}
  .agent{display:block;width:100%;text-align:left;border:0;background:transparent;border-radius:10px;
    padding:9px 12px 9px 16px;cursor:pointer;position:relative;transition:.1s}
  .agent:hover{background:#F1F5FA}
  .agent.sel{background:#EAF1FA}
  .agent .bar{position:absolute;left:4px;top:10px;bottom:10px;width:4px;border-radius:2px}
  .agent .an{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12.5px;font-weight:600}
  .agent .ar{font-size:11.5px;color:var(--muted);margin-top:2px}
  .agent .sb{position:absolute;right:10px;top:11px;font-size:10px;font-weight:800;padding:2px 8px;border-radius:999px}
  .detail{padding:22px 24px;position:sticky;top:16px}
  .dhead{display:flex;align-items:flex-start;gap:12px;flex-wrap:wrap}
  .dname{font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:21px;font-weight:700}
  .badges{display:flex;gap:6px;flex-wrap:wrap;margin-left:auto}
  .b{font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;white-space:nowrap}
  .b.inv{background:#E8F2EC;color:#3E8C61}
  .b.noinv{background:#F1F3F6;color:#8A92A0}
  .reach{margin-top:7px;font-size:12.5px;color:var(--muted)}
  .drole{font-size:15px;font-weight:700;margin:14px 0 2px}
  .dtype{color:var(--body);font-size:13.5px;margin:2px 0}
  .ddesc{color:var(--body);font-size:13.5px;line-height:1.55;margin:8px 0 0}
  .sect{font-size:11px;font-weight:700;letter-spacing:.8px;color:var(--faint);text-transform:uppercase;margin:20px 0 9px}
  .pchips,.tchips{display:flex;flex-wrap:wrap;gap:7px}
  .pill{font-size:12px;font-weight:600;padding:6px 11px;border-radius:999px;border:1px solid;cursor:default}
  .pill.sk{background:#F0EBFB;border-color:#E0D6F4;color:#5B49A6;cursor:pointer}
  .pill.sk.sys{background:#EAF5F3;border-color:#CFE9E5;color:#2E7D74}
  .pill.sk:hover{filter:brightness(.97);text-decoration:none}
  .pill.srv{background:#fff;border-color:#D9DEE5;color:#46505E;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11.5px}
  .pill.st{background:#FBF1DC;border-color:#EFE0C2;color:#9A6A1E;font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:11px}
  .pill.go{cursor:pointer}
  .none{color:var(--muted);font-size:13px;font-style:italic}
  .cmd{background:#1F2733;color:#E9EEF5;border-radius:8px;padding:9px 12px;margin:7px 0;
    font-family:'SF Mono',ui-monospace,Menlo,monospace;font-size:12px;overflow-x:auto;white-space:nowrap}
  .cmd .sl{color:#7DE3D0;font-weight:700}
  .inote{color:var(--body);font-size:13px;margin:2px 0 6px}
  .disp{color:var(--muted);font-size:12.5px;font-style:italic}
  .meta{display:flex;flex-wrap:wrap;gap:22px;margin-top:8px}
  .meta .k{font-size:11px;font-weight:700;letter-spacing:.6px;color:var(--faint);text-transform:uppercase}
  .meta .v{font-size:13.5px;font-weight:600;margin-top:3px;display:flex;align-items:center;gap:7px}
  .mdot{width:9px;height:9px;border-radius:50%}
  .pipe{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:6px}
  .pstep{display:flex;align-items:center;gap:5px}
  .pnode{width:9px;height:9px;border-radius:50%;background:#DCE1E8}
  .pstep.on .pnode{background:#2E8E84;box-shadow:0 0 0 4px rgba(46,142,132,.15)}
  .pstep .pl{font-size:11px;color:var(--muted)}
  .pstep.on .pl{color:#2E7D74;font-weight:700}
  .parrow{color:#CBD2DA;font-size:11px}
  .xnote{background:#EEF3FA;border:1px solid #DCE6F3;border-radius:10px;padding:9px 12px;
    font-size:12.5px;color:var(--body);margin-bottom:14px;display:flex;gap:10px;align-items:center}
  .xnote b{color:var(--ink)}
  .xnote button{margin-left:auto;border:0;background:#1F2733;color:#fff;border-radius:8px;padding:5px 10px;font-size:11.5px;font-weight:600;cursor:pointer}
  footer{margin-top:26px;color:var(--muted);font-size:12px;text-align:center}
  @media(max-width:820px){.layout{grid-template-columns:1fr}.list{max-height:none}.detail{position:static}}
</style>
</head>
<body>
<header class="hero"><div class="hero-in">
  <div class="eyebrow">GTS AI SDLC</div>
  <h1>Agent Playground</h1>
  <p class="sub">Pick an agent to see what it does, what it can touch, the status it returns, and how to invoke it — the whole team, P7 and T7 side by side.</p>
</div></header>
<main class="wrap">
  <div class="controls">
    <label class="search">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#9AA1AB" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3" stroke-linecap="round"/></svg>
      <input id="q" type="search" placeholder="Search agents, roles, skills…" autocomplete="off">
    </label>
    <div class="chips" id="sysChips"></div>
    <div class="legend" id="legend"></div>
  </div>
  <div class="layout">
    <aside class="list card" id="list"></aside>
    <section class="detail card" id="detail"></section>
  </div>
  <footer id="foot"></footer>
</main>
<script>
const AGENTS = /*__AGENTS__*/;
const GROUPS = /*__GROUPS__*/;
const SYS = /*__SYS__*/;
const PIPE = /*__PIPE__*/;
let sel = "/*__DEFAULT__*/";
let fSys = "all", fSkill = null, q = "";

const $ = s => document.querySelector(s);
const esc = s => (s||"").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const byName = n => AGENTS.find(a => a.name === n);
function go(n){ if(byName(n)){ sel=n; try{history.replaceState(null,"","#"+n)}catch(e){} render(); } }

function legend(){
  const s = Object.entries(SYS).map(([k,v]) =>
    `<span><span class="dot" style="background:${v.ink}"></span>${v.label}</span>`).join("");
  $("#legend").innerHTML = s +
    `<span><span class="dot" style="background:#C2862B"></span>Opus</span>` +
    `<span><span class="dot" style="background:#3F6FB5"></span>Sonnet</span>` +
    `<span><span class="dot" style="background:#3E9460"></span>GPT-5 mini</span>`;
}
function chipBar(el, opts, cur, on){
  el.innerHTML = opts.map(o =>
    `<button class="chip ${o.v===cur?'on':''}" data-v="${o.v}">${o.t}</button>`).join("");
  el.querySelectorAll(".chip").forEach(b => b.onclick = () => on(b.dataset.v));
}
function match(a){
  if(fSys!=="all" && a.system!==fSys) return false;
  if(fSkill && !(a.skills.includes(fSkill) || a.skillsCommon.includes(fSkill))) return false;
  if(q){
    const hay = (a.name+" "+a.roleLabel+" "+a.description+" "+a.skills.join(" ")+" "+
      a.skillsCommon.join(" ")+" "+a.servers.join(" ")).toLowerCase();
    if(!hay.includes(q)) return false;
  }
  return true;
}
function renderList(){
  const shown = AGENTS.filter(match);
  let html = "";
  for(const g of GROUPS){
    const items = shown.filter(a => a.group === g);
    if(!items.length) continue;
    html += `<div class="group">${esc(g)}</div>`;
    for(const a of items){
      const sv = SYS[a.system];
      html += `<button class="agent ${a.name===sel?'sel':''}" data-n="${a.name}">
        <span class="bar" style="background:${sv.ink}"></span>
        <span class="sb" style="background:${sv.fill};color:${sv.ink}">${sv.label}</span>
        <div class="an">${esc(a.name)}</div>
        <div class="ar">${esc(a.roleLabel)} · ${esc(a.modelLabel)}</div>
      </button>`;
    }
  }
  if(!html) html = `<div class="none" style="padding:12px">No agents match.</div>`;
  const el = $("#list"); el.innerHTML = html;
  el.querySelectorAll(".agent").forEach(b => b.onclick = () => go(b.dataset.n));
}
function pipeStrip(active){
  let h = `<div class="pipe">`;
  PIPE.forEach((p,i) => {
    h += `<span class="pstep ${i===active?'on':''}"><span class="pnode"></span><span class="pl">${p}</span></span>`;
    if(i<PIPE.length-1) h += `<span class="parrow">›</span>`;
  });
  return h + `</div>`;
}
function pipe(a){
  if(a.role==="orchestrator")
    return `<div class="dtype">Coordinates every phase below — never runs one itself.</div>` + pipeStrip(-1);
  if(a.phase<0) return "";
  return pipeStrip(a.phase);
}
function invokeBlock(iv){
  if(iv.mode==="command"){
    return iv.examples.map(e=>{
      const sp=e.indexOf(" "), cmd=sp>0?e.slice(0,sp):e, rest=sp>0?e.slice(sp):"";
      return `<div class="cmd"><span class="sl">${esc(cmd)}</span>${esc(rest)}</div>`;
    }).join("");
  }
  return `<div class="inote">${esc(iv.note)}</div>` +
    (iv.dispatch?`<div class="disp">e.g. “${esc(iv.dispatch)}”</div>`:"");
}
function renderDetail(){
  const a = byName(sel) || AGENTS[0];
  const sv = SYS[a.system];
  const invBadge = a.userInvocable
    ? `<span class="b inv">call it directly</span>` : `<span class="b noinv">internal</span>`;
  let x = "";
  if(fSkill){
    const users = AGENTS.filter(z => z.skills.includes(fSkill)||z.skillsCommon.includes(fSkill)).length;
    x = `<div class="xnote">Filtering by skill <b>${esc(fSkill)}</b> — used by <b>${users}</b> agents.
         <button id="clr">clear</button></div>`;
  }
  const sysSkills = a.skills.length
    ? `<div class="pchips">`+a.skills.map(s=>`<span class="pill sk sys" data-sk="${esc(s)}">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">none</span>`;
  const comSkills = a.skillsCommon.length
    ? `<div class="pchips">`+a.skillsCommon.map(s=>`<span class="pill sk" data-sk="${esc(s)}">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">none</span>`;
  const servers = a.servers.length
    ? `<div class="tchips">`+a.servers.map(s=>`<span class="pill srv">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">no external tool servers — pure reasoning / built-ins</span>`;
  const statuses = a.statuses.length
    ? `<div class="tchips">`+a.statuses.map(s=>`<span class="pill st">${esc(s)}</span>`).join("")+`</div>`
    : `<span class="none">—</span>`;
  const delegates = a.delegates.length
    ? `<div class="tchips">`+a.delegates.map(s=>`<span class="pill srv go" data-go="${esc(s)}">${esc(s)}</span>`).join("")+`</div>`
    : "";
  const reach = `Reach: <b>${a.skills.length+a.skillsCommon.length}</b> skills · <b>${a.servers.length}</b> tool servers`;
  $("#detail").innerHTML = x + `
    <div class="dhead">
      <div>
        <div class="dname">${esc(a.name)}</div>
        <div class="reach">${reach}</div>
      </div>
      <div class="badges">
        <span class="b" style="background:${sv.fill};color:${sv.ink}">${sv.label} · ${sv.name}</span>
        ${invBadge}
      </div>
    </div>
    <div class="drole">${esc(a.roleLabel)}</div>
    ${a.typeNote?`<div class="dtype">${esc(a.typeNote)}</div>`:""}
    ${pipe(a)}
    <div class="sect">What it does</div>
    <div class="ddesc">${esc(a.description)}</div>
    <div class="sect">Invoke it</div>
    ${invokeBlock(a.invoke)}
    <div class="sect">System skills</div>${sysSkills}
    <div class="sect">Common skills</div>${comSkills}
    <div class="sect">Tool / MCP servers</div>${servers}
    <div class="sect">Status codes it returns</div>${statuses}
    ${delegates?`<div class="sect">Delegates to</div>${delegates}`:""}
    <div class="meta">
      <div><div class="k">Model</div><div class="v"><span class="mdot" style="background:${a.modelInk}"></span>${esc(a.model)}</div></div>
    </div>`;
  const clr = $("#clr"); if(clr) clr.onclick = () => { fSkill=null; render(); };
  $("#detail").querySelectorAll("[data-sk]").forEach(el =>
    el.onclick = () => { fSkill = el.dataset.sk; render(); });
  $("#detail").querySelectorAll("[data-go]").forEach(el =>
    el.onclick = () => { fSkill=null; go(el.dataset.go); });
}
function render(){
  renderList(); renderDetail();
  document.querySelectorAll("#sysChips .chip").forEach(b=>b.classList.toggle("on",b.dataset.v===fSys));
}
function init(){
  legend();
  chipBar($("#sysChips"),
    [{v:"all",t:"All"},{v:"generic",t:"Generic"},{v:"p7",t:"P7"},{v:"t7",t:"T7"}],
    fSys, v => { fSys=v; render(); });
  $("#q").oninput = e => { q = e.target.value.trim().toLowerCase(); render(); };
  const fromHash = decodeURIComponent((location.hash || "").replace(/^#/, ""));
  if(fromHash && byName(fromHash)) sel = fromHash;
  window.addEventListener("hashchange", () => {
    const n = decodeURIComponent(location.hash.replace(/^#/, ""));
    if(byName(n)){ sel = n; render(); }
  });
  $("#foot").innerHTML = `${AGENTS.length} agents · generated from <code>.github/agents/*.agent.md</code> — ` +
    `regenerate with <code>python3 docs/explorer/generate.py</code>`;
  render();
}
init();
</script>
</body>
</html>
"""

html = (TEMPLATE
        .replace("/*__AGENTS__*/", json.dumps(agents, ensure_ascii=False))
        .replace("/*__GROUPS__*/", json.dumps(group_order, ensure_ascii=False))
        .replace("/*__SYS__*/", json.dumps(SYSTEMS, ensure_ascii=False))
        .replace("/*__PIPE__*/", json.dumps(PIPELINE, ensure_ascii=False))
        .replace("/*__DEFAULT__*/", DEFAULT))

out = os.path.join(HERE, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"wrote {out}  ({len(agents)} agents, {len(html)} bytes)")
