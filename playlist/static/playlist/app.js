/**
 * Spotify-themed Circular Doubly Linked List (CDLL) Music Playlist Manager
 * Vanilla JavaScript Frontend
 */

// Application & Playback State
let currentState = null;
let isPlaying = false;          // Single client-side state variable (never overwritten by server responses)
let playbackTimer = null;       // Reference to active progress timer interval
let currentElapsedSeconds = 0;  // Preserved when pausing to resume from exact position
let dragSourcePosition = null;

// CSRF Token Helper
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.content) return meta.content;

  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : "";
}

// Global Alert Notification Toast
function showAlert(message, isError = true) {
  const container = document.getElementById("alert-container");
  const box = document.getElementById("alert-box");
  const msg = document.getElementById("alert-message");
  const icon = document.getElementById("alert-icon");

  if (!container || !box) return;

  msg.textContent = message;
  icon.textContent = isError ? "⚠️" : "✅";
  box.className = isError ? "alert-box" : "alert-box success";
  container.style.display = "block";

  setTimeout(() => {
    container.style.display = "none";
  }, 5000);
}

function dismissAlert() {
  const container = document.getElementById("alert-container");
  if (container) container.style.display = "none";
}

// REST API Helper
async function apiCall(endpoint, method = "GET", payload = null) {
  const options = {
    method: method,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
  };

  if (payload && method !== "GET") {
    options.body = JSON.stringify(payload);
  }

  try {
    const response = await fetch(endpoint, options);
    const data = await response.json();

    if (!response.ok || data.success === false) {
      const errMsg = data.error || `Server returned error (${response.status})`;
      showAlert(errMsg, true);
      logConsole(`[ERROR] ${errMsg}`, "err");
      return null;
    }

    return data;
  } catch (err) {
    const errMsg = `Network error: ${err.message}`;
    showAlert(errMsg, true);
    logConsole(`[NETWORK ERROR] ${errMsg}`, "err");
    return null;
  }
}

// Format Seconds to MM:SS
function formatTime(seconds) {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${String(m).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}

// CHANGE 2: Single Play/Pause Toggle Function
function togglePlay() {
  if (!isPlaying) {
    // START / RESUME PLAYBACK
    isPlaying = true;
    startProgressTimer();
    logConsole("[PLAYBACK] Playing started / resumed.", "ok");
  } else {
    // PAUSE PLAYBACK: Freeze progress bar (elapsed time is preserved, NOT reset)
    isPlaying = false;
    stopProgressTimer();
    logConsole(`[PLAYBACK] Paused at ${formatTime(currentElapsedSeconds)}.`, "sys");
  }

  updatePlayerUI();
}

// Start or Resume Progress Timer (Guaranteed Single Interval)
function startProgressTimer() {
  // Guarantee: only one interval exists at any time
  if (playbackTimer) {
    clearInterval(playbackTimer);
    playbackTimer = null;
  }

  const fillEl = document.getElementById("progress-fill");
  const elapsedEl = document.getElementById("time-elapsed");

  // Determine current song duration
  const totalSeconds = (currentState && currentState.current_track)
    ? currentState.current_track.duration
    : 180;

  playbackTimer = setInterval(() => {
    currentElapsedSeconds += 1;

    if (elapsedEl) {
      elapsedEl.textContent = formatTime(currentElapsedSeconds);
    }
    if (fillEl) {
      const percent = Math.min(100, (currentElapsedSeconds / totalSeconds) * 100);
      fillEl.style.width = `${percent}%`;
    }

    // Auto-advance when song ends (Structural circular loop!)
    if (currentElapsedSeconds >= totalSeconds) {
      stopProgressTimer();
      currentElapsedSeconds = 0;
      logConsole("[AUTO-LOOP] Track finished. Auto-advancing to next track...", "sys");
      handleNext();
    }
  }, 1000);
}

// Stop Progress Timer Without Resetting Elapsed Position
function stopProgressTimer() {
  if (playbackTimer) {
    clearInterval(playbackTimer);
    playbackTimer = null;
  }
}

// Update Player UI (Button icon, badge, equalizer) based on isPlaying
function updatePlayerUI() {
  const playBtn = document.getElementById("btn-play");
  const badge = document.getElementById("playback-badge");
  const statusText = document.getElementById("playback-status-text");

  if (playBtn) {
    if (isPlaying) {
      playBtn.classList.add("is-playing");
      playBtn.setAttribute("aria-label", "Pause");
      playBtn.title = "Pause";
    } else {
      playBtn.classList.remove("is-playing");
      playBtn.setAttribute("aria-label", "Play");
      playBtn.title = "Play";
    }
  }

  if (badge) {
    if (isPlaying) {
      badge.classList.add("is-playing");
      if (statusText) statusText.textContent = "Playing";
    } else {
      badge.classList.remove("is-playing");
      if (statusText) statusText.textContent = "Paused";
    }
  }
}

// Update UI on State Changes (Does NOT overwrite isPlaying)
function applyState(state) {
  if (!state) return;
  currentState = state;

  const current = state.current_track;

  // 1. Now Playing Metadata
  const titleEl = document.getElementById("now-title");
  const artistEl = document.getElementById("now-artist");
  const idEl = document.getElementById("now-id");
  const posEl = document.getElementById("now-pos");
  const totalCountEl = document.getElementById("total-count");
  const timeTotalEl = document.getElementById("time-total");
  const timeElapsedEl = document.getElementById("time-elapsed");
  const fillEl = document.getElementById("progress-fill");

  if (totalCountEl) totalCountEl.textContent = state.total_tracks || 0;

  if (current) {
    if (titleEl) titleEl.textContent = current.title;
    if (artistEl) artistEl.textContent = current.artist;
    if (idEl) idEl.textContent = current.id;
    if (posEl) posEl.textContent = (current.position !== undefined) ? current.position : findTrackPosition(current.id);
    if (timeTotalEl) timeTotalEl.textContent = current.formatted_duration;
  } else {
    if (titleEl) titleEl.textContent = "Playlist is Empty";
    if (artistEl) artistEl.textContent = "Add tracks to begin";
    if (idEl) idEl.textContent = "-";
    if (posEl) posEl.textContent = "-";
    if (timeTotalEl) timeTotalEl.textContent = "00:00";
  }

  // Update progress bar percentage based on currentElapsedSeconds
  if (current && timeElapsedEl && fillEl) {
    timeElapsedEl.textContent = formatTime(currentElapsedSeconds);
    const percent = Math.min(100, (currentElapsedSeconds / current.duration) * 100);
    fillEl.style.width = `${percent}%`;
  }

  // Synchronize button and equalizer with client-side isPlaying
  updatePlayerUI();

  // If isPlaying is true, ensure timer is running for current track
  if (isPlaying && current) {
    startProgressTimer();
  }

  // 2. Bidirectional Context Panels
  renderContextPanels(state);

  // 3. Full Playlist Table
  renderPlaylistTable(state.tracks, current ? current.id : null);

  // 4. SVG Ring Visualization
  renderRingVisualizer(state.tracks, current ? current.id : null);
}

function findTrackPosition(trackId) {
  if (!currentState || !currentState.tracks) return "-";
  const found = currentState.tracks.find(t => t.id === trackId);
  return found ? found.position : "-";
}

// Bidirectional Context Rendering
function renderContextPanels(state) {
  const prevContainer = document.getElementById("prev-track-content");
  const upContainer = document.getElementById("upcoming-track-content");

  // Previous Track
  if (prevContainer) {
    if (state.previous_track && state.total_tracks > 1) {
      const p = state.previous_track;
      prevContainer.innerHTML = `
        <div class="context-item">
          <div>
            <strong>${p.title}</strong><small>${p.artist}</small>
          </div>
          <div>
            <button class="btn-pill" style="padding: 0.3rem 0.8rem; font-size: 0.75rem;" onclick="handlePlayById(${p.id})">Play</button>
          </div>
        </div>
        <p style="font-size:0.75rem; color:var(--text-muted); margin-top:0.35rem;">
          Pointer: <code>current.prev</code>
        </p>
      `;
    } else {
      prevContainer.innerHTML = '<p class="empty-text">No previous track</p>';
    }
  }

  // Up Next Tracks (Up to 3)
  if (upContainer) {
    if (state.upcoming_tracks && state.upcoming_tracks.length > 0) {
      let html = "";
      state.upcoming_tracks.forEach((track, i) => {
        const stepLabel = i === 0 ? "next" : (i === 1 ? "+2" : "+3");
        html += `
          <div class="context-item">
            <div>
              <strong>${track.title}</strong><small>${track.artist}</small>
              <span style="font-size:0.7rem; color:var(--green); margin-left:6px;">(${stepLabel})</span>
            </div>
            <div>
              <button class="btn-pill" style="padding: 0.3rem 0.8rem; font-size: 0.75rem;" onclick="handlePlayById(${track.id})">Play</button>
            </div>
          </div>
        `;
      });
      upContainer.innerHTML = html;
    } else {
      upContainer.innerHTML = '<p class="empty-text">No upcoming tracks</p>';
    }
  }
}

// Playlist Table Rendering with Drag & Drop
function renderPlaylistTable(tracks, currentId) {
  const tbody = document.getElementById("table-body");
  if (!tbody) return;

  if (!tracks || tracks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center empty-text">No tracks in playlist. Add a track below!</td></tr>';
    return;
  }

  let html = "";
  tracks.forEach(t => {
    const isCurr = (t.id === currentId);
    const rowClass = isCurr ? "playlist-row current-track-row" : "playlist-row";
    const playIndicator = isCurr ? "🔊" : "⋮⋮";

    html += `
      <tr class="${rowClass}" draggable="true" data-position="${t.position}" data-id="${t.id}">
        <td><strong style="color:var(--text-secondary);">${t.position}</strong></td>
        <td class="drag-handle" title="Drag to reorder" style="cursor:grab; color:var(--text-muted);">${playIndicator}</td>
        <td>
          <span class="row-title">${t.title}</span>
          ${isCurr ? '<span class="row-now-playing-dot" title="Now Playing"></span>' : ''}
          ${t.position === 1 ? '<span class="row-head-badge">HEAD</span>' : ''}
        </td>
        <td style="color:var(--text-secondary);">${t.artist}</td>
        <td style="color:var(--text-muted);">${t.formatted_duration}</td>
        <td style="text-align: right;">
          <div class="table-actions">
            <button class="btn-pill" style="padding: 0.3rem 0.8rem; font-size: 0.75rem;" onclick="handlePlayById(${t.id})">Play</button>
            <button class="btn-pill btn-danger" onclick="handleDelete(${t.id})">Delete</button>
          </div>
        </td>
      </tr>
    `;
  });
  tbody.innerHTML = html;

  attachDragAndDropHandlers();
}

function attachDragAndDropHandlers() {
  const rows = document.querySelectorAll(".playlist-row");
  rows.forEach(row => {
    row.addEventListener("dragstart", (e) => {
      dragSourcePosition = parseInt(row.getAttribute("data-position"), 10);
      row.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    row.addEventListener("dragend", () => {
      row.classList.remove("dragging");
    });

    row.addEventListener("dragover", (e) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
    });

    row.addEventListener("drop", async (e) => {
      e.preventDefault();
      const targetPos = parseInt(row.getAttribute("data-position"), 10);
      if (dragSourcePosition && targetPos && dragSourcePosition !== targetPos) {
        logConsole(`[DRAG-DROP] Moving track from position ${dragSourcePosition} to ${targetPos}...`, "sys");
        const data = await apiCall("/api/move/", "POST", {
          pos_a: dragSourcePosition,
          pos_b: targetPos,
        });
        if (data) {
          applyState(data);
          showAlert(`Track moved to position ${targetPos}`, false);
          logConsole(`[SUCCESS] CDLL move(${dragSourcePosition}, ${targetPos}) completed.`, "ok");
        }
      }
      dragSourcePosition = null;
    });
  });
}

// Circular Ring Visualizer (SVG)
function renderRingVisualizer(tracks, currentId) {
  const svg = document.getElementById("ring-svg");
  if (!svg) return;
  svg.innerHTML = "";

  if (!tracks || tracks.length === 0) {
    svg.innerHTML = `<text x="300" y="260" fill="#727272" text-anchor="middle" font-size="16">Playlist is Empty</text>`;
    return;
  }

  const cx = 300;
  const cy = 260;
  const radius = 145;
  const n = tracks.length;

  // Arrow markers definition
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
  defs.innerHTML = `
    <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#727272" />
    </marker>
    <marker id="loop-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#1DB954" />
    </marker>
  `;
  svg.appendChild(defs);

  // Calculate coordinates of all nodes along circular perimeter
  const points = tracks.map((track, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
      angle: angle,
      track: track,
      index: i,
    };
  });

  // Draw circular link paths between nodes
  if (n > 1) {
    for (let i = 0; i < n; i++) {
      const p1 = points[i];
      const p2 = points[(i + 1) % n];
      const isLoopBack = (i === n - 1); // Tail -> Head wrap-around link!

      const midAngle = (2 * Math.PI * (i + 0.5)) / n - Math.PI / 2;
      const bendRadius = radius * 0.82;
      const qx = cx + bendRadius * Math.cos(midAngle);
      const qy = cy + bendRadius * Math.sin(midAngle);

      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("d", `M ${p1.x} ${p1.y} Q ${qx} ${qy} ${p2.x} ${p2.y}`);
      path.setAttribute("fill", "none");
      // Muted arrows between neighbors; Green arrow from last to first
      path.setAttribute("stroke", isLoopBack ? "#1DB954" : "#727272");
      path.setAttribute("stroke-width", isLoopBack ? "3" : "2");
      path.setAttribute("stroke-dasharray", isLoopBack ? "5,5" : "none");
      path.setAttribute("marker-end", isLoopBack ? "url(#loop-arrow)" : "url(#arrow)");
      svg.appendChild(path);

      if (isLoopBack) {
        // Offset label toward the center so the dashed line does not intersect text
        const dx = cx - qx;
        const dy = cy - qy;
        const dist = Math.hypot(dx, dy) || 1;
        const badgeX = qx + (dx / dist) * 26;
        const badgeY = qy + (dy / dist) * 26;

        // Background pill badge
        const badge = document.createElementNS("http://www.w3.org/2000/svg", "rect");
        badge.setAttribute("x", badgeX - 62);
        badge.setAttribute("y", badgeY - 11);
        badge.setAttribute("width", "124");
        badge.setAttribute("height", "22");
        badge.setAttribute("rx", "11");
        badge.setAttribute("fill", "#181818");
        badge.setAttribute("stroke", "#1DB954");
        badge.setAttribute("stroke-width", "1.5");
        svg.appendChild(badge);

        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", badgeX);
        label.setAttribute("y", badgeY + 4);
        label.setAttribute("fill", "#1DB954");
        label.setAttribute("font-size", "11");
        label.setAttribute("font-weight", "bold");
        label.setAttribute("text-anchor", "middle");
        label.textContent = "Tail ➔ Head (Wrap)";
        svg.appendChild(label);
      }
    }
  }

  // Draw Node Circles and Labels
  points.forEach((p) => {
    const isCurrent = (p.track.id === currentId);
    const isHead = (p.index === 0);
    const nodeR = isCurrent ? 26 : 22;

    const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.style.cursor = "pointer";
    g.onclick = () => handlePlayById(p.track.id);

    // Node Circle
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    circle.setAttribute("r", nodeR);

    if (isCurrent) {
      circle.setAttribute("fill", "#1DB954");
      circle.setAttribute("stroke", "#FFFFFF");
      circle.setAttribute("stroke-width", "3");
    } else if (isHead) {
      circle.setAttribute("fill", "#282828");
      circle.setAttribute("stroke", "#FFFFFF");
      circle.setAttribute("stroke-width", "2.5");
    } else {
      circle.setAttribute("fill", "#282828");
      circle.setAttribute("stroke", "#727272");
      circle.setAttribute("stroke-width", "2");
    }
    g.appendChild(circle);

    // Position Number inside Circle
    const textPos = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textPos.setAttribute("x", p.x);
    textPos.setAttribute("y", p.y + 5);
    textPos.setAttribute("text-anchor", "middle");
    textPos.setAttribute("fill", isCurrent ? "#000000" : "#FFFFFF");
    textPos.setAttribute("font-size", "14");
    textPos.setAttribute("font-weight", "bold");
    textPos.textContent = p.track.position;
    g.appendChild(textPos);

    // Track Title Label - Placed strictly OUTSIDE circles to eliminate overlap
    const cos = Math.cos(p.angle);
    const sin = Math.sin(p.angle);

    let lx = p.x;
    let ly = p.y;
    let anchor = "middle";

    if (cos > 0.35) {
      // Right side nodes (e.g. Node 2, 3): Text starts to the right of node and flows rightward
      lx = p.x + nodeR + 12;
      ly = p.y + 1;
      anchor = "start";
    } else if (cos < -0.35) {
      // Left side nodes (e.g. Node 5, 6): Text ends to the left of node and flows leftward
      lx = p.x - nodeR - 12;
      ly = p.y + 1;
      anchor = "end";
    } else if (sin < 0) {
      // Top nodes (e.g. Node 1): Text sits directly above node
      lx = p.x;
      ly = p.y - nodeR - 12;
      anchor = "middle";
    } else {
      // Bottom nodes (e.g. Node 4): Text sits directly below node
      lx = p.x;
      ly = p.y + nodeR + 18;
      anchor = "middle";
    }

    const textLabel = document.createElementNS("http://www.w3.org/2000/svg", "text");
    textLabel.setAttribute("x", lx);
    textLabel.setAttribute("y", ly);
    textLabel.setAttribute("text-anchor", anchor);
    textLabel.setAttribute("dominant-baseline", (anchor === "middle") ? "auto" : "central");
    textLabel.setAttribute("fill", isCurrent ? "#1DB954" : "#FFFFFF");
    textLabel.setAttribute("font-size", isCurrent ? "14" : "13");
    textLabel.setAttribute("font-weight", isCurrent ? "bold" : "600");

    const displayTitle = p.track.title.length > 18 ? p.track.title.slice(0, 17) + "…" : p.track.title;
    textLabel.textContent = displayTitle;
    g.appendChild(textLabel);

    svg.appendChild(g);
  });

  // Center Ring Label
  const centerText = document.createElementNS("http://www.w3.org/2000/svg", "text");
  centerText.setAttribute("x", cx);
  centerText.setAttribute("y", cy - 10);
  centerText.setAttribute("text-anchor", "middle");
  centerText.setAttribute("fill", "#1DB954");
  centerText.setAttribute("font-size", "18");
  centerText.setAttribute("font-weight", "bold");
  centerText.textContent = "CDLL Ring";
  svg.appendChild(centerText);

  const centerSub = document.createElementNS("http://www.w3.org/2000/svg", "text");
  centerSub.setAttribute("x", cx);
  centerSub.setAttribute("y", cy + 12);
  centerSub.setAttribute("text-anchor", "middle");
  centerSub.setAttribute("fill", "#FFFFFF");
  centerSub.setAttribute("font-size", "13");
  centerSub.setAttribute("font-weight", "500");
  centerSub.textContent = `${n} Nodes Connected`;
  svg.appendChild(centerSub);

  const centerHint = document.createElementNS("http://www.w3.org/2000/svg", "text");
  centerHint.setAttribute("x", cx);
  centerHint.setAttribute("y", cy + 30);
  centerHint.setAttribute("text-anchor", "middle");
  centerHint.setAttribute("fill", "#727272");
  centerHint.setAttribute("font-size", "11");
  centerHint.textContent = "O(1) Circular Links";
  svg.appendChild(centerHint);
}

// Next Track Handler (Resets elapsed time to 0, KEEPS current isPlaying value)
async function handleNext() {
  currentElapsedSeconds = 0;
  stopProgressTimer();

  logConsole("[CDLL] Advancing: current = current.next (O(1))...", "sys");
  const data = await apiCall("/api/next/", "POST");
  if (data) {
    applyState(data);
    // If it was playing, keep playing the new track from 0; if paused, stay paused
    if (isPlaying) {
      startProgressTimer();
    }
    logConsole(`[NEXT] Now playing: '${data.current_track ? data.current_track.title : "None"}'`, "ok");
  }
}

// Previous Track Handler (Resets elapsed time to 0, KEEPS current isPlaying value)
async function handlePrev() {
  currentElapsedSeconds = 0;
  stopProgressTimer();

  logConsole("[CDLL] Rewinding: current = current.prev (O(1))...", "sys");
  const data = await apiCall("/api/prev/", "POST");
  if (data) {
    applyState(data);
    // If it was playing, keep playing the new track from 0; if paused, stay paused
    if (isPlaying) {
      startProgressTimer();
    }
    logConsole(`[PREV] Rewound to: '${data.current_track ? data.current_track.title : "None"}'`, "ok");
  }
}

// Switch to a specific track by ID
async function handlePlayById(trackId) {
  currentElapsedSeconds = 0;
  stopProgressTimer();
  isPlaying = true; // User specifically clicked Play on a track

  logConsole(`[NAVIGATE] Switching to Track ID ${trackId}...`, "sys");
  const data = await apiCall("/api/play/", "POST", {
    track_id: trackId,
  });
  if (data) {
    applyState(data);
    startProgressTimer();
    showAlert(`Playing: ${data.current_track ? data.current_track.title : ""}`, false);
    logConsole(`[PLAYING] Started '${data.current_track ? data.current_track.title : ""}'`, "ok");
  }
}

// Add Track Form Handler
async function handleAddTrack(event) {
  event.preventDefault();
  const title = document.getElementById("add-title").value;
  const artist = document.getElementById("add-artist").value;
  const duration = document.getElementById("add-duration").value;
  const position = document.getElementById("add-position") ? document.getElementById("add-position").value : null;

  const payload = {
    title: title,
    artist: artist,
    duration: parseInt(duration, 10),
  };
  if (position && position.trim() !== "") {
    payload.position = parseInt(position, 10);
  }

  logConsole(`[INSERT] Adding track '${title}' at pos ${payload.position || "end"}...`, "sys");
  const data = await apiCall("/api/insert/", "POST", payload);
  if (data) {
    applyState(data);
    showAlert(`Track '${title}' added to playlist!`, false);
    logConsole(`[SUCCESS] Track '${title}' inserted into CDLL.`, "ok");
    document.getElementById("add-track-form").reset();
  }
}

// Delete Track Handler
async function handleDelete(trackId) {
  if (!confirm(`Are you sure you want to delete Track ID ${trackId}?`)) return;

  logConsole(`[DELETE] Deleting Track ID ${trackId} from CDLL...`, "sys");
  const data = await apiCall("/api/delete/", "POST", { id: trackId });
  if (data) {
    currentElapsedSeconds = 0;
    applyState(data);
    showAlert(`Track ${trackId} removed.`, false);
    logConsole(`[SUCCESS] Track ID ${trackId} unlinked from CDLL.`, "ok");
  }
}

// Move Track Handler (used by hidden form or drag/drop)
async function handleMoveTrack(event) {
  if (event) event.preventDefault();
  const fromEl = document.getElementById("move-from");
  const toEl = document.getElementById("move-to");
  if (!fromEl || !toEl) return;

  const posA = parseInt(fromEl.value, 10);
  const posB = parseInt(toEl.value, 10);

  logConsole(`[MOVE] Moving node from position ${posA} to ${posB}...`, "sys");
  const data = await apiCall("/api/move/", "POST", { pos_a: posA, pos_b: posB });
  if (data) {
    applyState(data);
    showAlert(`Track moved from position ${posA} to ${posB}.`, false);
    logConsole(`[SUCCESS] Relinked pointers for pos ${posA} -> ${posB}.`, "ok");
  }
}

// CLI Console Logger & Handler (Change 2 Rule 6: calls togglePlay())
function logConsole(text, type = "user") {
  const output = document.getElementById("console-output");
  if (!output) return;
  const line = document.createElement("div");
  line.className = `cli-line ${type}`;
  line.textContent = text;
  output.appendChild(line);
  output.scrollTop = output.scrollHeight;
}

async function handleConsoleSubmit(event) {
  if (event) event.preventDefault();
  const input = document.getElementById("console-input");
  if (!input) return;
  const raw = input.value.trim();
  if (!raw) return;

  logConsole(`cdll> ${raw}`, "user");
  input.value = "";

  const parts = raw.split(/\s+/);
  const cmd = parts[0].toLowerCase();

  switch (cmd) {
    case "help":
      logConsole("Available CDLL Commands:", "sys");
      logConsole("  play [id]             - Toggle play/pause (calls togglePlay) or jump to ID", "sys");
      logConsole("  pause                 - Pause playback", "sys");
      logConsole("  next                  - O(1) advance: current = current.next", "sys");
      logConsole("  prev                  - O(1) rewind: current = current.prev", "sys");
      logConsole("  insert <t> <a> <sec>  - Insert song node into CDLL", "sys");
      logConsole("  delete <id>           - Delete node and bridge neighbors", "sys");
      logConsole("  move <pos_a> <pos_b>  - Relink node from pos_a to pos_b", "sys");
      logConsole("  clear                 - Clear console", "sys");
      break;

    case "clear":
      const output = document.getElementById("console-output");
      if (output) output.innerHTML = "";
      break;

    case "play":
      if (parts[1]) {
        await handlePlayById(parseInt(parts[1], 10));
      } else {
        // Change 2 Rule 6: CLI 'play' calls the same togglePlay() function!
        togglePlay();
      }
      break;

    case "pause":
      if (isPlaying) {
        togglePlay();
      }
      break;

    case "next":
      await handleNext();
      break;

    case "prev":
      await handlePrev();
      break;

    case "delete":
      if (parts[1]) {
        await handleDelete(parseInt(parts[1], 10));
      } else {
        logConsole("[ERROR] Usage: delete <track_id>", "err");
      }
      break;

    case "move":
      if (parts.length >= 3) {
        const posA = parseInt(parts[1], 10);
        const posB = parseInt(parts[2], 10);
        const data = await apiCall("/api/move/", "POST", { pos_a: posA, pos_b: posB });
        if (data) {
          applyState(data);
          logConsole(`[SUCCESS] Moved node from ${posA} to ${posB}.`, "ok");
        }
      } else {
        logConsole("[ERROR] Usage: move <pos_a> <pos_b>", "err");
      }
      break;

    case "insert":
      const remaining = raw.slice(cmd.length).trim();
      const tokens = remaining.match(/(?:[^\s"]+|"[^"]*")+/g);
      if (!tokens || tokens.length < 3) {
        logConsole("[ERROR] Usage: insert <title> <artist> <duration_sec> [position]", "err");
      } else {
        const title = tokens[0].replace(/"/g, "");
        const artist = tokens[1].replace(/"/g, "");
        const duration = parseInt(tokens[2], 10);
        const position = tokens[3] ? parseInt(tokens[3], 10) : null;
        const payload = { title, artist, duration };
        if (position) payload.position = position;

        const data = await apiCall("/api/insert/", "POST", payload);
        if (data) {
          applyState(data);
          logConsole(`[SUCCESS] Inserted '${title}' at pos ${position || "end"}.`, "ok");
        }
      }
      break;

    default:
      logConsole(`[ERROR] Unknown command '${cmd}'. Type 'help' for command list.`, "err");
      break;
  }
}

// Initial Page Load
document.addEventListener("DOMContentLoaded", async () => {
  logConsole("[SYSTEM] Initializing Spotify CDLL Playlist...", "sys");
  const data = await apiCall("/api/state/");
  if (data) {
    applyState(data);
    logConsole(`[SYSTEM] Loaded ${data.total_tracks} tracks. Current: '${data.current_track ? data.current_track.title : "None"}'`, "ok");
  }
});
