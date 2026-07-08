// =====================================================================
// EcoHabit — frontend app logic (vanilla JS, no build step needed)
// =====================================================================

let CURRENT_PAGE = "home";
let CATEGORY_FILTER = "All";
let STORE_CATEGORY_FILTER = "All";

// ---------------------------------------------------------------------
// API helper
// ---------------------------------------------------------------------
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw { status: res.status, ...data };
  return data;
}

function toast(message, type = "") {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.className = "toast " + type;
  el.classList.remove("hidden");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => el.classList.add("hidden"), 3500);
}

function escapeHtml(str) {
  const d = document.createElement("div");
  d.textContent = str ?? "";
  return d.innerHTML;
}

function initials(name) {
  return (name || "?").slice(0, 2).toUpperCase();
}

function timeAgo(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "2-digit", year: "numeric" });
}

// ---------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------
function showRegister() {
  document.getElementById("login-form").classList.add("hidden");
  document.getElementById("register-form").classList.remove("hidden");
}
function showLogin() {
  document.getElementById("register-form").classList.add("hidden");
  document.getElementById("login-form").classList.remove("hidden");
}

async function doLogin() {
  const username = document.getElementById("login-username").value;
  const password = document.getElementById("login-password").value;
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ username, password }) });
    enterApp();
  } catch (e) {
    showLoginError(e.message || "Login failed.");
  }
}

async function doRegister() {
  const username = document.getElementById("register-username").value;
  const email = document.getElementById("register-email").value;
  const password = document.getElementById("register-password").value;
  try {
    const data = await api("/api/register", { method: "POST", body: JSON.stringify({ username, email, password }) });
    if (data.success) {
      toast("Account created! Log in now.", "success");
      showLogin();
    } else {
      showLoginError(data.message);
    }
  } catch (e) {
    showLoginError(e.message || "Registration failed.");
  }
}

function showLoginError(msg) {
  const el = document.getElementById("login-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}

async function doLogout() {
  await api("/api/logout", { method: "POST" });
  location.reload();
}

function enterApp() {
  document.getElementById("login-screen").classList.add("hidden");
  document.getElementById("app-shell").classList.remove("hidden");
  document.getElementById("assistant-widget").classList.remove("hidden");
  navigate("home");
  refreshSidebarEcobits();
}

// ---------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------
window.addEventListener("DOMContentLoaded", async () => {
  document.querySelectorAll(".nav-item").forEach(el => {
    el.addEventListener("click", () => navigate(el.dataset.page));
  });
  try {
    const s = await api("/api/session");
    if (s.logged_in) enterApp();
  } catch (e) { /* not logged in, stay on login screen */ }
});

async function refreshSidebarEcobits() {
  try {
    const d = await api("/api/dashboard");
    document.getElementById("sidebar-ecobits").textContent = d.user.ecobits;
  } catch (e) { /* ignore */ }
}

// ---------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------
function navigate(page) {
  CURRENT_PAGE = page;
  document.querySelectorAll(".nav-item").forEach(el => {
    el.classList.toggle("active", el.dataset.page === page);
  });
  const renderers = {
    home: renderHome, loghabit: renderLogHabit, compare: renderCompare,
    myplants: renderMyPlants, social: renderSocial, ecostore: renderEcoStore,
    leaderboard: renderLeaderboard, recyclingmap: renderRecyclingMap,
    profile: renderProfile, settings: renderSettings,
  };
  (renderers[page] || renderHome)();
}

// ---------------------------------------------------------------------
// HOME
// ---------------------------------------------------------------------
async function renderHome() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/dashboard");
  document.getElementById("sidebar-ecobits").textContent = d.user.ecobits;

  const trees = (d.user.total_co2_saved / 21) * 100; // 1 tree absorbs ~21kg CO2/year
  const treesFull = Math.floor(d.user.total_co2_saved / 21);
  const treesPct = Math.min(100, Math.round(((d.user.total_co2_saved % 21) / 21) * 100));

  el.innerHTML = `
    <div class="banner">
      <h2>Welcome back, ${escapeHtml(d.user.username)}! 🌿</h2>
      <p>Every sustainable habit you log makes our planet a little greener. Keep up the amazing work!</p>
      <button class="btn" onclick="navigate('loghabit')">🌱 Log Today's Habit →</button>
    </div>

    <div class="stat-grid">
      <div class="stat-card"><div class="stat-icon">🪙</div><div class="stat-value">${d.user.ecobits}</div><div class="stat-label">Total EcoBits</div></div>
      <div class="stat-card"><div class="stat-icon">🌍</div><div class="stat-value">${d.user.total_co2_saved.toFixed(1)} kg</div><div class="stat-label">CO2 Saved</div></div>
      <div class="stat-card"><div class="stat-icon">🎯</div><div class="stat-value">${d.habits_logged}</div><div class="stat-label">Habits Logged</div></div>
      <div class="stat-card"><div class="stat-icon">🔥</div><div class="stat-value">${d.streak} days</div><div class="stat-label">Current Streak</div></div>
    </div>

    <div class="section-title">Quick Actions</div>
    <div class="quick-grid">
      <div class="quick-card" onclick="navigate('loghabit')"><div class="qi" style="background:#10B981">🌱</div><div class="qtitle">Log Habit</div><div class="qsub">Earn EcoBits</div></div>
      <div class="quick-card" onclick="navigate('compare')"><div class="qi" style="background:#3B82F6">📈</div><div class="qtitle">Compare</div><div class="qsub">See your footprint</div></div>
      <div class="quick-card" onclick="navigate('leaderboard')"><div class="qi" style="background:#F59E0B">🏆</div><div class="qtitle">Leaderboard</div><div class="qsub">Top 10 heroes</div></div>
      <div class="quick-card" onclick="navigate('ecostore')"><div class="qi" style="background:#EC4899">🛍️</div><div class="qtitle">EcoStore</div><div class="qsub">Spend EcoBits</div></div>
    </div>

    <div class="section-title">Recent Activity</div>
    <div class="card">
      ${d.recent_logs.length === 0 ? `<p class="muted">Nothing logged yet — go log your first habit!</p>` :
        d.recent_logs.map(l => `
          <div class="activity-row">
            <div class="activity-left">
              <div class="activity-icon">${l.icon}</div>
              <div><div class="activity-name">${escapeHtml(l.habit_name)}</div><div class="activity-date">${timeAgo(l.logged_at)}</div></div>
            </div>
            <div class="activity-right">
              <div class="activity-points">+${l.ecobits_earned} EcoBits</div>
              <div class="activity-co2">-${l.co2_saved}kg CO2</div>
            </div>
          </div>`).join("")}
    </div>

    <div class="card" style="background:linear-gradient(120deg,#EAF7EE,#D5F0E0)">
      <div style="font-weight:800; margin-bottom:4px;">🔔 Your Environmental Impact</div>
      <div class="muted" style="font-size:13px; margin-bottom:8px;">${d.user.total_co2_saved.toFixed(1)} kg CO2 Saved</div>
      <div style="display:flex; justify-content:space-between; font-size:13px;">
        <span>Equivalent to planting</span><span>${treesFull} trees</span>
      </div>
      <div class="progress-track"><div class="progress-fill" style="width:${treesPct}%"></div></div>
      <div class="muted" style="font-size:12px; margin-top:8px;">💡 One tree absorbs about 21 kg of CO2 per year. Keep logging habits to grow your forest!</div>
    </div>
  `;
}

// ---------------------------------------------------------------------
// LOG HABIT
// ---------------------------------------------------------------------
async function renderLogHabit() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/habits");

  const cats = ["All", ...d.categories];
  const trustWarning = d.trust_gated
    ? `<div class="card" style="background:#FEF2F2; border:1px solid #FCA5A5;">
         ⚠️ Your trust score is low, so check-in habits (no photo) are paused for now.
         Log a few photo-verified habits below to rebuild trust.
       </div>` : "";

  el.innerHTML = `
    <div class="page-title">Log Your Eco Habit</div>
    <div class="page-subtitle">Choose a sustainable habit you did today and earn EcoBits!</div>
    <div class="card" style="background:#EAF7EE; font-size:13px;">
      🤖 Photo-verifiable habits are checked by AI. Habits that can't be photographed (like a shorter shower)
      use a quick AI honesty check-in instead.
    </div>
    ${trustWarning}
    <div class="pill-row">
      ${cats.map(c => `<div class="pill ${c === CATEGORY_FILTER ? "active" : ""}" onclick="setHabitCategory('${c}')">${c}</div>`).join("")}
    </div>
    <div id="habit-list"></div>
  `;
  renderHabitList(d.habits);
}

function setHabitCategory(cat) {
  CATEGORY_FILTER = cat;
  renderLogHabit();
}

function renderHabitList(habits) {
  const list = document.getElementById("habit-list");
  const filtered = CATEGORY_FILTER === "All" ? habits : habits.filter(h => h.category === CATEGORY_FILTER);
  list.innerHTML = filtered.map(h => `
    <div class="habit-card">
      <div class="habit-icon">${h.icon}</div>
      <div class="habit-body">
        <div class="habit-name-row"><span class="habit-name">${escapeHtml(h.name)}</span><span class="badge">${h.category}</span></div>
        <div class="habit-desc">${escapeHtml(h.desc)}</div>
        <div class="habit-meta">🪙 <b>${h.ecobits} EcoBits</b> &nbsp;&nbsp; 🌿 <b>${h.co2}kg</b> CO2 saved</div>
      </div>
      <div class="habit-action">
        <button class="btn btn-primary btn-sm" onclick='openHabitModal(${JSON.stringify(h)})'>
          ${h.verify === "photo" ? "📷 Prove it" : "💬 Check in"}
        </button>
        <div class="verify-tag">${h.verify === "photo" ? "Photo required" : "AI check-in"}</div>
      </div>
    </div>
  `).join("");
}

// ---- Habit logging modals ----
function openHabitModal(habit) {
  if (habit.verify === "photo") openPhotoModal(habit);
  else openCheckinModal(habit);
}

function closeModal() {
  const m = document.getElementById("modal-overlay");
  if (m) m.remove();
}

function openPhotoModal(habit) {
  closeModal();
  const div = document.createElement("div");
  div.id = "modal-overlay";
  div.className = "modal-overlay";
  div.innerHTML = `
    <div class="modal-box">
      <h3>${habit.icon} ${escapeHtml(habit.name)}</h3>
      <p class="muted" style="font-size:13px;">Upload a quick photo — our AI checks it plausibly matches this habit.</p>
      <div class="file-drop" onclick="document.getElementById('photo-input').click()">
        <div id="photo-preview">📷 Click to choose a photo</div>
      </div>
      <input type="file" id="photo-input" accept="image/*" class="hidden" onchange="previewPhoto(event)">
      <div class="modal-actions">
        <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="photo-submit-btn" onclick="submitPhotoHabit(${habit.id})" disabled>Submit</button>
      </div>
    </div>`;
  document.body.appendChild(div);
}

let PENDING_IMAGE_B64 = null;
function previewPhoto(evt) {
  const file = evt.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    PENDING_IMAGE_B64 = reader.result;
    document.getElementById("photo-preview").innerHTML = `<img src="${reader.result}">`;
    document.getElementById("photo-submit-btn").disabled = false;
  };
  reader.readAsDataURL(file);
}

async function submitPhotoHabit(habitId) {
  const btn = document.getElementById("photo-submit-btn");
  btn.disabled = true;
  btn.textContent = "Verifying with AI...";
  try {
    const res = await api(`/api/habits/${habitId}/log`, {
      method: "POST", body: JSON.stringify({ image_base64: PENDING_IMAGE_B64 }),
    });
    closeModal();
    toast(res.message, "success");
    renderLogHabit();
    refreshSidebarEcobits();
  } catch (e) {
    toast(e.message || "Verification failed.", "error");
    btn.disabled = false;
    btn.textContent = "Submit";
  }
}

async function openCheckinModal(habit) {
  closeModal();
  const div = document.createElement("div");
  div.id = "modal-overlay";
  div.className = "modal-overlay";
  div.innerHTML = `<div class="modal-box"><h3>${habit.icon} ${escapeHtml(habit.name)}</h3><p class="muted">Asking AI a quick honesty check-in question...</p></div>`;
  document.body.appendChild(div);
  try {
    const res = await api(`/api/habits/${habit.id}/checkin-question`, { method: "POST" });
    div.querySelector(".modal-box").innerHTML = `
      <h3>${habit.icon} ${escapeHtml(habit.name)}</h3>
      <p style="font-weight:600; font-size:14px;">${escapeHtml(res.question)}</p>
      <input type="text" id="checkin-answer" placeholder="Your answer...">
      <div class="modal-actions">
        <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="checkin-submit-btn" onclick="submitCheckinHabit(${habit.id})">Submit</button>
      </div>`;
  } catch (e) {
    div.querySelector(".modal-box").innerHTML = `
      <h3>${habit.icon} ${escapeHtml(habit.name)}</h3>
      <p style="color:#EF4444;">${escapeHtml(e.error || e.message || "Could not start check-in.")}</p>
      <div class="modal-actions"><button class="btn btn-outline" onclick="closeModal()">Close</button></div>`;
  }
}

async function submitCheckinHabit(habitId) {
  const btn = document.getElementById("checkin-submit-btn");
  const answer = document.getElementById("checkin-answer").value;
  btn.disabled = true;
  btn.textContent = "Checking with AI...";
  try {
    const res = await api(`/api/habits/${habitId}/log`, { method: "POST", body: JSON.stringify({ answer }) });
    closeModal();
    toast(res.message, "success");
    renderLogHabit();
    refreshSidebarEcobits();
  } catch (e) {
    toast(e.message || "Not accepted.", "error");
    closeModal();
  }
}

// ---------------------------------------------------------------------
// COMPARE
// ---------------------------------------------------------------------
async function renderCompare() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/compare");
  el.innerHTML = `
    <div class="page-title">Compare Your Impact</div>
    <div class="page-subtitle">See how everyday choices stack up against each other.</div>
    <div class="plant-grid">
      ${d.comparisons.map(c => {
        const maxCo2 = Math.max(c.co2_greener, c.co2_typical, 0.01);
        return `
        <div class="card" style="text-align:left;">
          <div style="font-weight:800; margin-bottom:10px;">${escapeHtml(c.title)}</div>
          <div style="font-size:13px; margin-bottom:4px;">🟢 ${escapeHtml(c.greener)} — ${c.co2_greener}kg CO2</div>
          <div class="progress-track"><div class="progress-fill" style="width:${(c.co2_greener/maxCo2)*100}%"></div></div>
          <div style="font-size:13px; margin:10px 0 4px;">🔴 ${escapeHtml(c.typical)} — ${c.co2_typical}kg CO2</div>
          <div class="progress-track"><div class="progress-fill" style="width:${(c.co2_typical/maxCo2)*100}%; background:#EF4444;"></div></div>
          <div class="muted" style="font-size:12px; margin-top:10px;">💡 ${escapeHtml(c.tip)}</div>
        </div>`;
      }).join("")}
    </div>
  `;
}

// ---------------------------------------------------------------------
// MY PLANTS
// ---------------------------------------------------------------------
let PLANTS_TAB = "current";
async function renderMyPlants() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/plants");
  const user = (await api("/api/dashboard")).user;

  el.innerHTML = `
    <div class="banner">
      <h2>🌾 My Garden</h2>
      <p>Grow your plants by logging habits and earning EcoBits</p>
      <div style="margin-top:10px; font-weight:700;">🪙 ${user.ecobits} EcoBits</div>
    </div>
    <div class="tab-row">
      <button class="tab-btn ${PLANTS_TAB === "current" ? "active" : ""}" onclick="setPlantsTab('current')">🌱 Current Plants</button>
      <button class="tab-btn ${PLANTS_TAB === "catalog" ? "active" : ""}" onclick="setPlantsTab('catalog')">📖 Collection Book</button>
    </div>
    <div id="plants-body"></div>
  `;
  renderPlantsBody(d);
}
function setPlantsTab(tab) { PLANTS_TAB = tab; renderMyPlants(); }

function renderPlantsBody(d) {
  const body = document.getElementById("plants-body");
  if (PLANTS_TAB === "current") {
    body.innerHTML = `<div class="plant-grid">
      ${d.my_plants.length === 0 ? `<p class="muted">No plants yet — grab one from the Collection Book!</p>` :
      d.my_plants.map(p => `
        <div class="plant-card">
          <div class="plant-emoji">${p.emoji}</div>
          <div class="plant-name">${escapeHtml(p.name)}</div>
          <div class="muted" style="font-size:12px;">Stage ${p.stage}</div>
          <div class="rarity-badge rarity-${p.rarity}">${p.rarity}</div>
          <div class="growth-label"><span>Growth Progress</span><span>${p.pct}%</span></div>
          <div class="progress-track"><div class="progress-fill" style="width:${p.pct}%"></div></div>
          <div class="muted" style="font-size:11px; margin:6px 0 10px;">${p.growth_progress}/${p.max_ecobits} EcoBits</div>
          <button class="btn btn-primary btn-block btn-sm" onclick="waterPlant(${p.id})" ${p.pct>=100?"disabled":""}>💧 Water Plant (10 EcoBits)</button>
        </div>
      `).join("")}
    </div>`;
  } else {
    body.innerHTML = `<div class="plant-grid">
      ${d.catalog.map(p => `
        <div class="plant-card">
          <div class="plant-emoji">${p.emoji}</div>
          <div class="plant-name">${escapeHtml(p.name)}</div>
          <div class="plant-desc">${escapeHtml(p.desc)}</div>
          <div class="rarity-badge rarity-${p.rarity}">${p.rarity}</div>
          ${p.free_starter
            ? `<button class="btn btn-primary btn-block btn-sm" onclick="buyPlant(${p.id})">🎁 Get Free Starter Plant</button>`
            : `<button class="btn btn-primary btn-block btn-sm" onclick="buyPlant(${p.id})" ${p.can_afford ? "" : "disabled"}>
                 ${p.can_afford ? `🪙 Buy - ${p.cost} EcoBits` : `${p.cost} EcoBits needed`}
               </button>`}
        </div>
      `).join("")}
    </div>`;
  }
}

async function buyPlant(catalogId) {
  try {
    const res = await api(`/api/plants/buy/${catalogId}`, { method: "POST" });
    toast(res.message, res.success ? "success" : "error");
    if (res.success) { refreshSidebarEcobits(); renderMyPlants(); }
  } catch (e) { toast(e.message || "Purchase failed.", "error"); }
}

async function waterPlant(plantId) {
  try {
    const res = await api(`/api/plants/${plantId}/water`, { method: "POST" });
    toast(res.message, res.success ? "success" : "error");
    if (res.success) { refreshSidebarEcobits(); renderMyPlants(); }
  } catch (e) { toast(e.message || "Could not water plant.", "error"); }
}

// ---------------------------------------------------------------------
// SOCIAL
// ---------------------------------------------------------------------
async function renderSocial() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/social/posts");
  el.innerHTML = `
    <div class="banner">
      <h2>👥 Eco Feed</h2>
      <p>Share your sustainability journey with the community</p>
    </div>
    <button class="btn btn-primary btn-block" onclick="openCreatePost()" style="margin-bottom:20px;">➤ Create Post</button>
    <div id="feed"></div>
  `;
  renderFeed(d.posts);
}

function renderFeed(posts) {
  const feed = document.getElementById("feed");
  feed.innerHTML = posts.length === 0 ? `<p class="muted">No posts yet — be the first to share!</p>` :
    posts.map(p => `
      <div class="post-card">
        <div class="post-header">
          <div class="post-avatar">${initials(p.username)}</div>
          <div>
            <span class="post-user">${escapeHtml(p.username)}</span><span class="post-type">↗ ${escapeHtml(p.post_type)}</span>
            <div class="post-date">${timeAgo(p.created_at)}</div>
          </div>
        </div>
        <div class="post-content">${escapeHtml(p.content)}</div>
        <div class="post-actions">
          <span class="${p.liked_by_viewer ? "liked" : ""}" onclick="toggleLike(${p.id})">❤️ ${p.likes} likes</span>
          <span>💬 ${p.comments.length} comments</span>
        </div>
        ${p.comments.map(c => `<div class="comment-row"><b>${escapeHtml(c.username)}</b>: ${escapeHtml(c.content)}</div>`).join("")}
        <div class="comment-input-row">
          <input type="text" id="comment-input-${p.id}" placeholder="Write a comment..." onkeydown="if(event.key==='Enter') submitComment(${p.id})">
          <button class="btn btn-primary btn-sm" onclick="submitComment(${p.id})">➤</button>
        </div>
      </div>
    `).join("");
}

function openCreatePost() {
  closeModal();
  const div = document.createElement("div");
  div.id = "modal-overlay";
  div.className = "modal-overlay";
  div.innerHTML = `
    <div class="modal-box">
      <h3>Create Post</h3>
      <textarea id="post-content" rows="4" placeholder="Share your sustainability journey..."></textarea>
      <div class="modal-actions">
        <button class="btn btn-outline" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" onclick="submitPost()">Post</button>
      </div>
    </div>`;
  document.body.appendChild(div);
}

async function submitPost() {
  const content = document.getElementById("post-content").value;
  try {
    await api("/api/social/posts", { method: "POST", body: JSON.stringify({ content, post_type: "Progress" }) });
    closeModal();
    renderSocial();
  } catch (e) { toast(e.message || "Could not post.", "error"); }
}

async function toggleLike(postId) {
  await api(`/api/social/posts/${postId}/like`, { method: "POST" });
  renderSocial();
}

async function submitComment(postId) {
  const input = document.getElementById(`comment-input-${postId}`);
  const content = input.value;
  if (!content.trim()) return;
  try {
    await api(`/api/social/posts/${postId}/comment`, { method: "POST", body: JSON.stringify({ content }) });
    renderSocial();
  } catch (e) { toast(e.message || "Could not comment.", "error"); }
}

// ---------------------------------------------------------------------
// ECOSTORE
// ---------------------------------------------------------------------
async function renderEcoStore() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/store");
  const cats = ["All", ...d.categories.filter(c => c !== "My Plants")];

  el.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
      <div>
        <div class="page-title">EcoStore</div>
        <div class="page-subtitle">Spend your EcoBits on rewards and make an even bigger impact!</div>
      </div>
      <div class="stat-card" style="min-width:140px;"><div class="stat-icon">🪙</div><div class="stat-value">${d.ecobits}</div><div class="stat-label">Your Balance</div></div>
    </div>
    <div class="pill-row">
      <div class="pill" onclick="navigate('myplants')">🌾 My Plants</div>
      ${cats.map(c => `<div class="pill ${c===STORE_CATEGORY_FILTER?"active":""}" onclick="setStoreCategory('${c}')">${c}</div>`).join("")}
    </div>
    <div id="store-grid" class="store-grid"></div>
  `;
  renderStoreGrid(d.items);
}

function setStoreCategory(cat) { STORE_CATEGORY_FILTER = cat; renderEcoStore(); }

function catClass(cat) { return "cat-" + cat.replace(/\s+/g, "-"); }

function renderStoreGrid(items) {
  const grid = document.getElementById("store-grid");
  const filtered = STORE_CATEGORY_FILTER === "All" ? items : items.filter(i => i.category === STORE_CATEGORY_FILTER);
  const emojiFor = { "Digital Badges": "🏅", "Donations": "❤️", "Eco Products": "📦", "Experiences": "⭐" };
  grid.innerHTML = filtered.map(i => `
    <div class="store-card">
      <div class="store-banner ${catClass(i.category)}">${emojiFor[i.category] || "🎁"}<span class="cat-tag">${i.category}</span></div>
      <div class="store-body">
        <div class="store-name">${escapeHtml(i.name)}</div>
        <div class="store-desc">${escapeHtml(i.desc)}</div>
        <div class="store-footer">
          <span class="price-tag">🪙 ${i.cost}</span>
          ${i.owned ? `<button class="btn btn-outline btn-sm" disabled>Owned ✓</button>` :
            `<button class="btn btn-primary btn-sm" onclick="buyStoreItem(${i.id})" ${i.can_afford ? "" : "disabled"}>${i.can_afford ? "Buy" : "Need more"}</button>`}
        </div>
      </div>
    </div>
  `).join("");
}

async function buyStoreItem(itemId) {
  try {
    const res = await api(`/api/store/buy/${itemId}`, { method: "POST" });
    toast(res.message, res.success ? "success" : "error");
    if (res.success) { refreshSidebarEcobits(); renderEcoStore(); }
  } catch (e) { toast(e.message || "Purchase failed.", "error"); }
}

// ---------------------------------------------------------------------
// LEADERBOARD
// ---------------------------------------------------------------------
async function renderLeaderboard() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/leaderboard");
  const top3 = d.leaderboard.slice(0, 3);
  const rest = d.leaderboard.slice(3);
  const podiumOrder = [top3[1], top3[0], top3[2]].filter(Boolean); // silver, gold, bronze visually

  el.innerHTML = `
    <div style="text-align:center; margin-bottom:10px;">
      <div style="font-size:40px;">🏆</div>
      <div style="font-size:24px; font-weight:800;">Eco Champions</div>
      <div class="muted">Top 10 environmental heroes making a difference</div>
    </div>
    <div class="podium">
      ${top3.map((u, i) => {
        const rank = i + 1;
        return `<div class="podium-card podium-${rank}">
          <div class="podium-avatar">${initials(u.username)}</div>
          ${rank===1 ? "👑" : rank===2 ? "🥈" : "🥉"}
          <div class="podium-name">${escapeHtml(u.username)}${u.username===d.me ? " (you)" : ""}</div>
          <div class="podium-points">${u.ecobits}</div>
          <div class="podium-sub">EcoBits</div>
        </div>`;
      }).join("")}
    </div>
    ${rest.map((u, i) => `
      <div class="rank-row">
        <div class="rank-num">#${i+4}</div>
        <div class="rank-avatar">${initials(u.username)}</div>
        <div>
          <div class="rank-name">${escapeHtml(u.username)}${u.username===d.me ? " (you)" : ""}</div>
          <div class="rank-sub">🌿 ${u.total_co2_saved.toFixed(1)}kg saved &nbsp; 🔥 ${u.streak} day streak</div>
        </div>
        <div class="rank-points">${u.ecobits} EcoBits</div>
      </div>
    `).join("")}
  `;
}

// ---------------------------------------------------------------------
// RECYCLING MAP
// ---------------------------------------------------------------------
async function renderRecyclingMap() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/recycling");
  el.innerHTML = `
    <div class="banner">
      <h2>📍 Recycling Locations</h2>
      <p>Find the nearest recycling center or public bin near you</p>
    </div>
    <div id="map"></div>
    <div class="loc-grid">
      ${d.locations.map(l => `
        <div class="loc-row">
          <div class="loc-icon">♻️</div>
          <div><div class="loc-name">${escapeHtml(l.name)}</div><div class="loc-type">${escapeHtml(l.type)}</div></div>
        </div>
      `).join("")}
    </div>
  `;
  setTimeout(() => {
    const map = L.map("map").setView([31.9, 34.9], 8);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors" }).addTo(map);
    d.locations.forEach(l => L.marker([l.lat, l.lng]).addTo(map).bindPopup(`<b>${escapeHtml(l.name)}</b><br>${escapeHtml(l.type)}`));
  }, 0);
}

// ---------------------------------------------------------------------
// PROFILE
// ---------------------------------------------------------------------
let PROFILE_TAB = "history";
async function renderProfile() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const d = await api("/api/profile");
  el.innerHTML = `
    <div class="profile-header">
      <div class="profile-header-inner">
        <div class="profile-avatar">${initials(d.user.username)}</div>
        <div class="profile-info">
          <div class="profile-username">${escapeHtml(d.user.username)}</div>
          <div class="profile-email">${escapeHtml(d.user.email || "No email set")}</div>
        </div>
        <button class="btn btn-outline btn-sm" onclick="doLogout()">🚪 Logout</button>
      </div>
    </div>
    <div class="stat-grid">
      <div class="stat-card"><div class="stat-icon">🪙</div><div class="stat-value">${d.user.ecobits}</div><div class="stat-label">Total EcoBits</div></div>
      <div class="stat-card"><div class="stat-icon">🌍</div><div class="stat-value">${d.user.total_co2_saved.toFixed(1)} kg</div><div class="stat-label">CO2 Saved</div></div>
      <div class="stat-card"><div class="stat-icon">🎯</div><div class="stat-value">${d.habits_logged}</div><div class="stat-label">Habits Logged</div></div>
      <div class="stat-card"><div class="stat-icon">🔥</div><div class="stat-value">${d.streak} days</div><div class="stat-label">Current Streak</div></div>
    </div>
    <div class="stat-card" style="margin-bottom:20px;">🛡️ Trust Score: <b>${d.user.trust_score}/100</b> <span class="muted" style="font-size:12px;">(used for AI honesty check-ins on non-photo habits)</span></div>
    <div class="tab-row">
      <button class="tab-btn ${PROFILE_TAB==="history"?"active":""}" onclick="setProfileTab('history')">🕓 Habit History</button>
      <button class="tab-btn ${PROFILE_TAB==="purchases"?"active":""}" onclick="setProfileTab('purchases')">🏅 Purchases</button>
    </div>
    <div id="profile-body"></div>
  `;
  window._profileData = d;
  renderProfileBody(d);
}
function setProfileTab(tab) { PROFILE_TAB = tab; renderProfileBody(window._profileData); }

function renderProfileBody(d) {
  const body = document.getElementById("profile-body");
  if (PROFILE_TAB === "history") {
    body.innerHTML = `<div class="card">
      ${d.logs.length === 0 ? `<p class="muted">No habits logged yet.</p>` : d.logs.map(l => `
        <div class="activity-row">
          <div class="activity-left">
            <div class="activity-icon">${l.icon}</div>
            <div><div class="activity-name">${escapeHtml(l.habit_name)}</div><div class="activity-date">${timeAgo(l.logged_at)}</div></div>
          </div>
          <div class="activity-right">
            <div class="activity-points">+${l.ecobits_earned}</div>
            <div class="activity-co2">-${l.co2_saved}kg CO2</div>
          </div>
        </div>
      `).join("")}
    </div>`;
  } else {
    body.innerHTML = `<div class="card">
      ${d.purchases.length === 0 ? `<p class="muted">No purchases yet.</p>` : d.purchases.map(p => `
        <div class="activity-row">
          <div class="activity-left"><div class="activity-icon">🏅</div><div><div class="activity-name">${escapeHtml(p.name)}</div><div class="activity-date">${timeAgo(p.purchased_at)}</div></div></div>
          <div class="activity-right"><div class="activity-points">-${p.cost} EcoBits</div></div>
        </div>
      `).join("")}
    </div>`;
  }
}

// ---------------------------------------------------------------------
// SETTINGS
// ---------------------------------------------------------------------
async function renderSettings() {
  const el = document.getElementById("content");
  el.innerHTML = `<p class="muted">Loading...</p>`;
  const [langs, profile] = await Promise.all([api("/api/languages"), api("/api/profile")]);
  const current = profile.user.language;
  el.innerHTML = `
    <div class="page-title">Settings</div>
    <div class="card">
      <div style="font-weight:800; margin-bottom:2px;">🌐 Language Preferences</div>
      <div class="muted" style="font-size:13px; margin-bottom:16px;">Choose your preferred language</div>
      ${langs.languages.map(l => `
        <div class="lang-option ${l.code===current?"active":""}" onclick="setLanguage('${l.code}')">
          <div class="lang-flag">${l.flag}</div>
          <div><div class="lang-name">${l.name}</div><div class="lang-native">${l.native}</div></div>
          ${l.code===current ? `<span class="lang-check">✓</span>` : ""}
        </div>
      `).join("")}
      <p class="muted" style="font-size:12px; margin-top:10px;">
        Note: this saves your preference, but full interface translation isn't wired up yet in this build —
        it's a good next feature to add.
      </p>
    </div>
  `;
}

async function setLanguage(code) {
  await api("/api/settings/language", { method: "POST", body: JSON.stringify({ language: code }) });
  renderSettings();
}

// ---------------------------------------------------------------------
// AI ASSISTANT WIDGET
// ---------------------------------------------------------------------
function toggleAssistant() {
  document.getElementById("assistant-panel").classList.toggle("hidden");
}

async function sendAssistantMessage() {
  const input = document.getElementById("assistant-input");
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  const msgs = document.getElementById("assistant-messages");
  msgs.insertAdjacentHTML("beforeend", `<div class="assistant-msg assistant-msg-user">${escapeHtml(message)}</div>`);
  msgs.insertAdjacentHTML("beforeend", `<div class="assistant-msg assistant-msg-bot" id="assistant-typing">Thinking...</div>`);
  msgs.scrollTop = msgs.scrollHeight;
  try {
    const res = await api("/api/assistant", { method: "POST", body: JSON.stringify({ message }) });
    document.getElementById("assistant-typing").outerHTML = `<div class="assistant-msg assistant-msg-bot">${escapeHtml(res.reply)}</div>`;
  } catch (e) {
    document.getElementById("assistant-typing").outerHTML = `<div class="assistant-msg assistant-msg-bot">Sorry, something went wrong.</div>`;
  }
  msgs.scrollTop = msgs.scrollHeight;
}
