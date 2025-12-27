/* UNDERHILL / SHIFT 1 — POC
   Intentionally crude prototype:
   - Top-down grid
   - One tile per input, slow cooldown
   - Four rooms w/ presence-based decay
   - Proximity dialogue that continues without you
   - Deterministic time events
   - Hard ending after ~10 minutes
*/

(() => {
  /** @type {HTMLCanvasElement} */
  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");

  const elClock = document.getElementById("clockValue");
  const elRoom = document.getElementById("roomBadge");
  const elHint = document.getElementById("hintText");
  const elSpeaker = document.getElementById("speaker");
  const elAlert = document.getElementById("alert");
  const elDialogue = document.getElementById("dialogueText");
  const elChoices = document.getElementById("choices");
  const mLife = document.getElementById("mLife");
  const mComms = document.getElementById("mComms");
  const mCommon = document.getElementById("mCommon");
  const mOps = document.getElementById("mOps");

  const TILE = 32;
  const GRID_W = 25;
  const GRID_H = 18; // 18 * 32 = 576

  const MOVE_COOLDOWN_MS = 210; // deliberate; every step is a delay
  const SESSION_SECONDS_DEFAULT = 10 * 60;
  const SESSION_SECONDS = (() => {
    const v = Number(new URLSearchParams(location.search).get("t"));
    if (Number.isFinite(v) && v > 20 && v <= 20 * 60) return v;
    return SESSION_SECONDS_DEFAULT;
  })();

  const COLORS = {
    wall: "#142232",
    floor: "#081420",
    corridor: "#0a1b2a",
    door: "#2b4664",
    roomLife: "#0d2331",
    roomComms: "#102035",
    roomCommon: "#14213a",
    roomOps: "#0f2630",
    player: "#eaf4ff",
    npc: "#8bdcff",
    npcHot: "#ffd36b",
    highlight: "rgba(139,220,255,0.18)",
    alert: "#ff6b6b",
  };

  /** Habitat layout (25x18)
      Legend:
      # = wall
      . = floor
      = = corridor floor (just a different tint)
      D = door (passable)
      L/C/A/O = room floor (Life/Comms/Area/Ops)
  */
  const MAP = [
    "#########################",
    "#LLLLLLL###=====###CCCC##",
    "#LLLLLLL###=====###CCCC##",
    "#LLLLLLLD==#####==DCCCC##",
    "#LLLLLLL#==#===#==#CCCC##",
    "####D####==#===#==####D##",
    "#====#====##===##====#=##",
    "#====#====##===##====#=##",
    "#====D====##===##====D=##",
    "#====#====##===##====#=##",
    "#====#====##===##====#=##",
    "#D#######==#===#==#######",
    "#AAAAAAA#==#===#==#OOOO##",
    "#AAAAAAAD==#####==DOOOO##",
    "#AAAAAAA###=====###OOOO##",
    "#AAAAAAA###=====###OOOO##",
    "#########################",
    "#########################",
  ];

  const roomDefs = [
    { id: "life", name: "Life Support", floor: "L", tint: COLORS.roomLife },
    { id: "comms", name: "Comms", floor: "C", tint: COLORS.roomComms },
    { id: "common", name: "Common Area", floor: "A", tint: COLORS.roomCommon },
    { id: "ops", name: "Planning / Ops", floor: "O", tint: COLORS.roomOps },
  ];

  const npcByRoom = {
    life: {
      id: "eng",
      name: "Engineer",
      color: COLORS.npc,
      pos: { x: 3, y: 3 },
      scriptId: "life",
    },
    comms: {
      id: "lia",
      name: "Political Liaison",
      color: COLORS.npc,
      pos: { x: 21, y: 3 },
      scriptId: "comms",
    },
    common: {
      id: "org",
      name: "Union Organizer",
      color: COLORS.npc,
      pos: { x: 3, y: 13 },
      scriptId: "common",
    },
    ops: {
      id: "sci",
      name: "Science Lead",
      color: COLORS.npc,
      pos: { x: 21, y: 13 },
      scriptId: "ops",
    },
  };

  const scripts = {
    life: [
      { t: "Your filter stack is drifting. I can hold it for a bit, but not alone." },
      {
        t: "If you want stability, I need explicit authority to restrict usage in the Common Area.",
        choices: [
          { k: "1", label: "Acknowledge. Do it.", effect: (s) => (s.commonTension += 10, s.lifeIntegrity += 6, s.lifeNotes.push("Restricted usage authorized.")) },
          { k: "2", label: "Defer. Not now.", effect: (s) => (s.lifeIntegrity -= 3, s.silences.life += 1) },
          { k: "3", label: "Shut it down. Keep it quiet.", effect: (s) => (s.commsTrust -= 6, s.lifeIntegrity += 2, s.lifeNotes.push("Told engineer to keep it quiet.")) },
        ],
        timeoutDefault: "2",
      },
      { t: "If it fails, it won’t look like a catastrophe. It’ll look like neglect." },
    ],
    comms: [
      { t: "Earth noticed the gap in our last two transmission windows." },
      {
        t: "They’re asking who’s ‘in control’ under stress. Give me something unambiguous.",
        choices: [
          { k: "1", label: "Acknowledge. We are steady.", effect: (s) => (s.commsTrust += 10, s.commonTension += 3) },
          { k: "2", label: "Defer. I’ll get back to you.", effect: (s) => (s.commsTrust -= 6, s.silences.comms += 1) },
          { k: "3", label: "Shut it down. No more Earth theatre.", effect: (s) => (s.commsTrust -= 14, s.commonTension += 6, s.silences.comms += 2) },
        ],
        timeoutDefault: "2",
      },
      { t: "They interpret silence as intent. Not neutrality." },
    ],
    common: [
      { t: "People are counting footsteps now. Who you stand with is policy." },
      {
        t: "They want a statement: are we building Mars or building Earth’s project on Mars?",
        choices: [
          { k: "1", label: "Acknowledge. Mars first.", effect: (s) => (s.commonTension += 8, s.opsProgress += 3) },
          { k: "2", label: "Defer. Keep it calm.", effect: (s) => (s.commonTension -= 4, s.silences.common += 1) },
          { k: "3", label: "Shut it down. Back to work.", effect: (s) => (s.commonTension += 14, s.commsTrust -= 4) },
        ],
        timeoutDefault: "2",
      },
      { t: "If you leave without answering, someone else will answer for you." },
    ],
    ops: [
      { t: "The plan is a sequence, not a slogan. I need time in the room to lock it." },
      {
        t: "Earth’s directive is coming. Do we pre-commit to a local timeline or wait to be told?",
        choices: [
          { k: "1", label: "Acknowledge. Pre-commit locally.", effect: (s) => (s.opsProgress += 12, s.commsTrust -= 4, s.commonTension += 4) },
          { k: "2", label: "Defer. Wait for Earth.", effect: (s) => (s.opsProgress -= 2, s.commsTrust += 6, s.silences.ops += 1) },
          { k: "3", label: "Shut it down. Stop theorizing.", effect: (s) => (s.opsProgress -= 8, s.commonTension += 6) },
        ],
        timeoutDefault: "2",
      },
      { t: "You can’t be everywhere. So we’ll become what you ignored." },
    ],
  };

  const state = {
    startedAt: performance.now(),
    nowS: 0,
    ended: false,
    endReason: "",
    regrets: /** @type {string[]} */ ([]),
    alertText: "",
    alertUntil: 0,
    blink: 0,

    // Room system state (0..100)
    lifeIntegrity: 88,
    commsTrust: 62,
    commonTension: 44,
    opsProgress: 38,

    // tracking
    lastMoveAt: 0,
    player: { x: 12, y: 8 },
    lastRoom: "corridor",

    // dialogue
    convo: /** @type {null | {
      roomId: string,
      npcId: string,
      scriptId: string,
      idx: number,
      lineStartedAt: number,
      awaiting: null | { choices: any[], timeoutDefault: string, timeoutAt: number },
      hardlock: boolean
    }} */ (null),

    // deterministic flags & counters
    flags: {
      warnedLife: false,
      warnedComms: false,
      warnedCommon: false,
      warnedOps: false,
      earthPing1: false,
      earthPing2: false,
      earthPing3: false,
      directive: false,
    },
    silences: { life: 0, comms: 0, common: 0, ops: 0 },
    lifeNotes: /** @type {string[]} */ ([]),
  };

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }
  function fmtClock(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }
  function tileAt(x, y) {
    if (x < 0 || y < 0 || x >= GRID_W || y >= GRID_H) return "#";
    const row = MAP[y] || "";
    return row[x] || "#";
  }
  function passable(ch) {
    return ch !== "#";
  }
  function roomIdAt(x, y) {
    const t = tileAt(x, y);
    const def = roomDefs.find((r) => r.floor === t);
    if (def) return def.id;
    return "corridor";
  }
  function roomName(id) {
    if (id === "corridor") return "Corridor";
    return roomDefs.find((r) => r.id === id)?.name ?? "—";
  }

  function setAlert(text, seconds = 3.5) {
    state.alertText = text;
    state.alertUntil = state.nowS + seconds;
  }

  function beginConversation(roomId) {
    const npc = npcByRoom[roomId];
    if (!npc) return;
    state.convo = {
      roomId,
      npcId: npc.id,
      scriptId: npc.scriptId,
      idx: 0,
      lineStartedAt: state.nowS,
      awaiting: null,
      hardlock: false,
    };
    elSpeaker.textContent = npc.name;
    elHint.textContent = "Choices: press 1 / 2 / 3. Walking away mid-sentence has consequences.";
    advanceLine(true);
  }

  function endConversation(reason) {
    if (!state.convo) return;
    state.convo = null;
    elSpeaker.textContent = "—";
    elChoices.innerHTML = "";
    if (reason) {
      elDialogue.textContent = reason;
    } else {
      elDialogue.textContent = "—";
    }
  }

  function currentNpcAdjacent() {
    const roomId = roomIdAt(state.player.x, state.player.y);
    if (roomId === "corridor") return null;
    const npc = npcByRoom[roomId];
    if (!npc) return null;
    const dx = Math.abs(npc.pos.x - state.player.x);
    const dy = Math.abs(npc.pos.y - state.player.y);
    if (dx + dy === 1) return { roomId, npc };
    return null;
  }

  function renderChoices(choices) {
    elChoices.innerHTML = "";
    for (const c of choices) {
      const row = document.createElement("div");
      row.className = "choice";
      const key = document.createElement("div");
      key.className = "key";
      key.textContent = c.k;
      const txt = document.createElement("div");
      txt.className = "choiceText";
      txt.textContent = c.label;
      row.appendChild(key);
      row.appendChild(txt);
      elChoices.appendChild(row);
    }
  }

  function applyEffect(effectFn) {
    effectFn(state);
    state.lifeIntegrity = clamp(state.lifeIntegrity, 0, 100);
    state.commsTrust = clamp(state.commsTrust, 0, 100);
    state.commonTension = clamp(state.commonTension, 0, 100);
    state.opsProgress = clamp(state.opsProgress, 0, 100);
  }

  function pickChoice(k) {
    if (!state.convo || !state.convo.awaiting) return false;
    const { choices } = state.convo.awaiting;
    const chosen = choices.find((c) => c.k === k) ?? null;
    if (!chosen) return false;
    applyEffect(chosen.effect);
    state.convo.awaiting = null;
    elChoices.innerHTML = "";
    setAlert("RECORDED", 1.2);
    advanceLine(false);
    return true;
  }

  function advanceLine(force) {
    if (!state.convo) return;
    const script = scripts[state.convo.scriptId] ?? [];
    if (state.convo.idx >= script.length) {
      endConversation("You step back. The room keeps moving without you.");
      return;
    }
    const line = script[state.convo.idx];
    if (!force && state.convo.awaiting) return;
    elDialogue.textContent = line.t;
    state.convo.lineStartedAt = state.nowS;
    state.convo.awaiting = null;
    if (line.choices) {
      renderChoices(line.choices);
      state.convo.awaiting = {
        choices: line.choices,
        timeoutDefault: line.timeoutDefault ?? "2",
        timeoutAt: state.nowS + 4.0,
      };
    }
    state.convo.idx += 1;
  }

  function updateConversation(dt) {
    if (!state.convo) return;

    // If player walks away mid-conversation, it bites.
    const adjacent = currentNpcAdjacent();
    const stillAdjacent = adjacent && adjacent.roomId === state.convo.roomId;
    if (!stillAdjacent) {
      const npcName = npcByRoom[state.convo.roomId]?.name ?? "Someone";
      state.regrets.push(`You walked away from ${npcName} (${roomName(state.convo.roomId)}).`);
      if (state.convo.roomId === "comms") state.commsTrust -= 8;
      if (state.convo.roomId === "life") state.lifeIntegrity -= 6;
      if (state.convo.roomId === "common") state.commonTension += 8;
      if (state.convo.roomId === "ops") state.opsProgress -= 6;
      setAlert("WALKED AWAY", 2.2);
      endConversation("The sentence finishes without you. The consequence does too.");
      return;
    }

    // Auto-advance cadence; dialogue continues even if you don't respond.
    const cadence = 3.6;
    if (state.convo.awaiting) {
      if (state.nowS >= state.convo.awaiting.timeoutAt) {
        pickChoice(state.convo.awaiting.timeoutDefault);
      }
      return;
    }
    if (state.nowS - state.convo.lineStartedAt >= cadence) {
      advanceLine(false);
    }
  }

  function updateSystems(dt) {
    const roomId = roomIdAt(state.player.x, state.player.y);
    const presence = {
      life: roomId === "life",
      comms: roomId === "comms",
      common: roomId === "common",
      ops: roomId === "ops",
    };

    // Decay/growth rates are deterministic and tuned to create pressure in ~10 minutes.
    // Presence slows decay (or enables progress) only in that room.
    const lifeDecay = presence.life ? 0.04 : 0.16;
    const commsDecay = presence.comms ? -0.06 : 0.14; // trust recovers slightly with attention; decays without
    const commonDecay = presence.common ? -0.05 : 0.15; // tension reduces if you're there; rises if not
    const opsGain = presence.ops ? 0.16 : 0.02; // planning needs presence to move meaningfully

    state.lifeIntegrity -= lifeDecay * dt;
    state.commsTrust -= commsDecay * dt;
    state.commonTension += commonDecay * dt;
    state.opsProgress += opsGain * dt;

    // Clamp
    state.lifeIntegrity = clamp(state.lifeIntegrity, 0, 100);
    state.commsTrust = clamp(state.commsTrust, 0, 100);
    state.commonTension = clamp(state.commonTension, 0, 100);
    state.opsProgress = clamp(state.opsProgress, 0, 100);

    // Warnings (deterministic, threshold-based)
    if (!state.flags.warnedLife && state.lifeIntegrity <= 55) {
      state.flags.warnedLife = true;
      setAlert("LIFE SUPPORT DRIFT", 4);
      state.regrets.push("Life Support started drifting.");
    }
    if (!state.flags.warnedComms && state.commsTrust <= 48) {
      state.flags.warnedComms = true;
      setAlert("EARTH WATCHING", 4);
      state.regrets.push("Comms trust slipped.");
    }
    if (!state.flags.warnedCommon && state.commonTension >= 62) {
      state.flags.warnedCommon = true;
      setAlert("COMMON HEATING", 4);
      state.regrets.push("The Common Area began to polarize.");
    }
    if (!state.flags.warnedOps && state.opsProgress <= 25 && state.nowS >= 120) {
      state.flags.warnedOps = true;
      setAlert("PLAN STALLING", 4);
      state.regrets.push("Ops drifted without you.");
    }
  }

  function timelineEvents() {
    // Deterministic clock pings. No RNG.
    if (!state.flags.earthPing1 && state.nowS >= 150) {
      state.flags.earthPing1 = true;
      setAlert("EARTH PING", 3);
      state.commsTrust -= 3;
      state.regrets.push("Earth pinged. Silence became a signal.");
    }
    if (!state.flags.earthPing2 && state.nowS >= 330) {
      state.flags.earthPing2 = true;
      setAlert("EARTH FOLLOW-UP", 3);
      state.commsTrust -= 4;
      state.commonTension += 2;
      state.regrets.push("Earth followed up. People noticed the delay.");
    }
    if (!state.flags.earthPing3 && state.nowS >= 510) {
      state.flags.earthPing3 = true;
      setAlert("EARTH IMPATIENT", 3);
      state.commsTrust -= 6;
      state.regrets.push("Earth got impatient.");
    }
  }

  function computeOutcome() {
    // Outcomes are coarse on purpose: no "perfect" state.
    // Convert "attention as spatial cost" into irreversible interpretation.
    const silenceScore = state.silences.life + state.silences.comms * 2 + state.silences.common + state.silences.ops;
    const abandonmentScore = state.regrets.filter((r) => r.startsWith("You walked away")).length;

    // Catastrophic systems or heavy comms degradation -> Earth control.
    if (state.commsTrust <= 32 || state.lifeIntegrity <= 24 || silenceScore >= 6) {
      return {
        title: "Terraforming greenlit — under Earth control",
        body:
          "Earth reads gaps and disorder as consent to intervention. The directive arrives pre-signed, pre-funded, and pre-owned.\n\nYou didn’t lose an argument. You lost the ability to be interpreted charitably.",
      };
    }

    // Social instability -> delay.
    if (state.commonTension >= 74 || abandonmentScore >= 3 || state.lifeIntegrity <= 42) {
      return {
        title: "Terraforming delayed — instability cited",
        body:
          "The directive arrives wrapped in ‘risk assessment’. Earth delays on paper, tightens on practice.\n\nThe habitat didn’t collapse. It just couldn’t present one coherent intent for ten uninterrupted minutes.",
      };
    }

    // Otherwise: autonomy weakened early (not a catastrophe, but a shape set).
    return {
      title: "Mars autonomy weakened — early precedent set",
      body:
        "The directive arrives ‘conditional’. Oversight clauses lock in before the first shovel hits regolith.\n\nYou kept it mostly together — but the map taught them where your attention runs out.",
    };
  }

  function endGame() {
    state.ended = true;
    state.flags.directive = true;
    const outcome = computeOutcome();
    elAlert.textContent = "DIRECTIVE";
    elSpeaker.textContent = "Earth / Directorate";

    const regrets = state.regrets.slice(-6);
    const regretText =
      regrets.length === 0
        ? "No log entries. That, too, will be interpreted."
        : regrets.map((r) => `- ${r}`).join("\n");

    elDialogue.textContent =
      `${outcome.title}\n\n` +
      `${outcome.body}\n\n` +
      `—\n` +
      `What you will replay:\n${regretText}\n\n` +
      `Refresh to run the shift again. (No pause. No save.)`;

    elChoices.innerHTML = "";
    elHint.textContent = "Shift complete. Refresh to restart.";
    setAlert("SHIFT ENDED", 9999);
  }

  function updateHUD() {
    elClock.textContent = fmtClock(state.nowS);

    const roomId = roomIdAt(state.player.x, state.player.y);
    elRoom.textContent = roomName(roomId);

    const pct = (v) => `${clamp(v, 0, 100).toFixed(1)}%`;
    mLife.style.width = pct(state.lifeIntegrity);
    mComms.style.width = pct(state.commsTrust);
    mCommon.style.width = pct(100 - state.commonTension); // show "stability"
    mOps.style.width = pct(state.opsProgress);

    // Color cues
    mLife.style.background = state.lifeIntegrity <= 35 ? "linear-gradient(90deg, #ff6b6b, rgba(255,107,107,0.35))" : "linear-gradient(90deg, #8bdcff, rgba(139,220,255,0.35))";
    mComms.style.background = state.commsTrust <= 35 ? "linear-gradient(90deg, #ff6b6b, rgba(255,107,107,0.35))" : "linear-gradient(90deg, #8bdcff, rgba(139,220,255,0.35))";
    mCommon.style.background = state.commonTension >= 70 ? "linear-gradient(90deg, #ff6b6b, rgba(255,107,107,0.35))" : "linear-gradient(90deg, #8bdcff, rgba(139,220,255,0.35))";
    mOps.style.background = state.opsProgress <= 25 ? "linear-gradient(90deg, #ffd36b, rgba(255,211,107,0.35))" : "linear-gradient(90deg, #8bdcff, rgba(139,220,255,0.35))";

    // Alert blink
    if (state.nowS < state.alertUntil) {
      const on = Math.floor(state.blink * 2) % 2 === 0;
      elAlert.textContent = on ? state.alertText : "";
    } else {
      elAlert.textContent = "";
    }
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Map
    for (let y = 0; y < GRID_H; y++) {
      for (let x = 0; x < GRID_W; x++) {
        const t = tileAt(x, y);
        let c = COLORS.floor;
        if (t === "#") c = COLORS.wall;
        if (t === "=") c = COLORS.corridor;
        if (t === ".") c = COLORS.floor;
        if (t === "D") c = COLORS.door;
        const roomDef = roomDefs.find((r) => r.floor === t);
        if (roomDef) c = roomDef.tint;

        ctx.fillStyle = c;
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);

        // subtle grid
        ctx.strokeStyle = "rgba(255,255,255,0.04)";
        ctx.strokeRect(x * TILE + 0.5, y * TILE + 0.5, TILE, TILE);
      }
    }

    // Door choke points: highlight doors slightly
    for (let y = 0; y < GRID_H; y++) {
      for (let x = 0; x < GRID_W; x++) {
        if (tileAt(x, y) !== "D") continue;
        ctx.fillStyle = "rgba(255,211,107,0.14)";
        ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
      }
    }

    // NPCs
    for (const roomId of Object.keys(npcByRoom)) {
      const npc = npcByRoom[roomId];
      const hot = (() => {
        const dx = Math.abs(npc.pos.x - state.player.x);
        const dy = Math.abs(npc.pos.y - state.player.y);
        return dx + dy === 1;
      })();
      ctx.fillStyle = hot ? COLORS.npcHot : npc.color;
      ctx.fillRect(npc.pos.x * TILE + 8, npc.pos.y * TILE + 8, TILE - 16, TILE - 16);
    }

    // Player
    ctx.fillStyle = COLORS.player;
    ctx.fillRect(state.player.x * TILE + 10, state.player.y * TILE + 10, TILE - 20, TILE - 20);

    // adjacency highlight
    const adj = currentNpcAdjacent();
    if (adj) {
      ctx.fillStyle = COLORS.highlight;
      ctx.fillRect(adj.npc.pos.x * TILE, adj.npc.pos.y * TILE, TILE, TILE);
      ctx.fillRect(state.player.x * TILE, state.player.y * TILE, TILE, TILE);
    }

    // Room labels (crude, top-left corner of rooms)
    ctx.fillStyle = "rgba(234,244,255,0.65)";
    ctx.font = "12px system-ui";
    ctx.fillText("LIFE", 2 * TILE, 2 * TILE - 10);
    ctx.fillText("COMMS", 18 * TILE, 2 * TILE - 10);
    ctx.fillText("COMMON", 2 * TILE, 14 * TILE - 10);
    ctx.fillText("OPS", 19 * TILE, 14 * TILE - 10);
  }

  function tryMove(dx, dy) {
    if (state.ended) return;
    const now = performance.now();
    if (now - state.lastMoveAt < MOVE_COOLDOWN_MS) return;
    state.lastMoveAt = now;

    const nx = state.player.x + dx;
    const ny = state.player.y + dy;
    if (!passable(tileAt(nx, ny))) return;
    state.player.x = nx;
    state.player.y = ny;

    // entering adjacency opens conversation (if none active)
    const adj = currentNpcAdjacent();
    if (!state.convo && adj) beginConversation(adj.roomId);
  }

  function onKeyDown(e) {
    if (state.ended) {
      if (e.key === "r" || e.key === "R") location.reload();
      return;
    }

    // Dialogue choice keys first
    if (e.key === "1" || e.key === "2" || e.key === "3") {
      if (pickChoice(e.key)) {
        e.preventDefault();
        return;
      }
    }

    // Movement
    const key = e.key.toLowerCase();
    if (key === "arrowup" || key === "w") tryMove(0, -1);
    if (key === "arrowdown" || key === "s") tryMove(0, 1);
    if (key === "arrowleft" || key === "a") tryMove(-1, 0);
    if (key === "arrowright" || key === "d") tryMove(1, 0);
  }

  window.addEventListener("keydown", onKeyDown, { passive: false });

  let last = performance.now();
  function loop() {
    const now = performance.now();
    let dt = (now - last) / 1000;
    last = now;
    dt = clamp(dt, 0, 0.25); // stability; still real-time pressure

    if (!state.ended) {
      state.nowS += dt;
      state.blink += dt;

      updateSystems(dt);
      timelineEvents();
      updateConversation(dt);

      if (state.nowS >= SESSION_SECONDS) {
        endGame();
      }
    } else {
      state.blink += dt;
    }

    updateHUD();
    draw();
    requestAnimationFrame(loop);
  }

  // Start: show immediate room prompt if adjacent
  const adj = currentNpcAdjacent();
  if (adj) beginConversation(adj.roomId);
  requestAnimationFrame(loop);
})();

