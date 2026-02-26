const API_URL = 'http://localhost:8000';

let currentMotions = [];
let activeCategory = 'all';
let activeSort = 'default';
let meetings = [];
let activeMeetingCode = null;
let activeRegion = 'all';
let loadingLongTimeout = null;
let currentModalMotion = null;

// Initial load: fetch meetings and select the newest one
window.addEventListener('DOMContentLoaded', () => {
  initTimeline();
});

// Sort select listener
document.getElementById('sortSelect').addEventListener('change', (e) => {
  activeSort = e.target.value;
  renderFilteredMotions();
});

document.getElementById('retryBtn').addEventListener('click', () => {
  if (activeMeetingCode) {
    loadMeeting(activeMeetingCode);
  } else if (meetings.length > 0) {
    loadMeeting(meetings[0].meeting_code);
  }
});

document.getElementById('refreshFromCouncilBtn').addEventListener('click', () => {
  refreshFromCouncil();
});

document.getElementById('preloadAllBtn').addEventListener('click', () => {
  preloadAllMeetings();
});

async function initTimeline() {
  showLoading();
  hideError();
  hideResults();

  try {
    const response = await fetch(`${API_URL}/api/meetings`);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || 'Failed to fetch meetings');
    }

    meetings = data;
    renderRegionFilters(meetings);
    renderTimeline(meetings);

    if (meetings.length > 0) {
      // Assume API returns newest first; select the first meeting
      selectTimelineItem(meetings[0].meeting_code);
      await loadMeeting(meetings[0].meeting_code);
    }
  } catch (error) {
    console.error('Error loading meetings:', error);
    const msg = error.message || 'Could not load meetings';
    showError(msg + (msg.includes('fetch') ? ' Is the backend running at http://localhost:8000?' : ''));
  } finally {
    hideLoading();
  }
}

async function refreshFromCouncil() {
  const btn = document.getElementById('refreshFromCouncilBtn');
  btn.disabled = true;
  setLoadingMessage('Fetching latest meetings from council… This may take 2+ minutes.');
  showLoading();
  document.getElementById('loadingSubtextLong')?.classList.add('hidden');
  hideError();
  try {
    const response = await fetch(`${API_URL}/api/refresh`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Refresh failed (${response.status})`);
    }
    const response2 = await fetch(`${API_URL}/api/meetings`);
    const listData = await response2.json();
    if (!response2.ok) throw new Error(listData.detail || 'Failed to fetch list');
    meetings = listData;
    renderRegionFilters(meetings);
    renderTimeline(meetings);
    if (meetings.length > 0 && !activeMeetingCode) {
      selectTimelineItem(meetings[0].meeting_code);
      await loadMeeting(meetings[0].meeting_code);
    }
  } catch (error) {
    console.error('Refresh failed:', error);
    showError(error.message || 'Refresh from council failed');
  } finally {
    hideLoading();
    btn.disabled = false;
  }
}

async function preloadAllMeetings() {
  const btn = document.getElementById('preloadAllBtn');
  btn.disabled = true;
  setLoadingMessage('Preloading all meetings… This may take several minutes.');
  showLoading();
  document.getElementById('loadingSubtextLong')?.classList.add('hidden');
  hideError();
  try {
    const response = await fetch(`${API_URL}/api/prewarm`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `Prewarm failed (${response.status})`);
    }
    const response2 = await fetch(`${API_URL}/api/meetings`);
    const listData = await response2.json();
    if (!response2.ok) throw new Error(listData.detail || 'Failed to fetch list');
    meetings = listData;
    renderRegionFilters(meetings);
    renderTimeline(meetings);
  } catch (error) {
    console.error('Prewarm failed:', error);
    showError(error.message || 'Preload all meetings failed');
  } finally {
    hideLoading();
    btn.disabled = false;
  }
}

function setLoadingMessage(text) {
  const el = document.querySelector('.loading-text');
  if (el) el.textContent = text;
}

function renderRegionFilters(meetingsList) {
  const container = document.getElementById('regionFilters');
  if (!container) return;

  container.innerHTML = '';

  if (!meetingsList || meetingsList.length === 0) {
    return;
  }

  const regions = Array.from(
    new Set(meetingsList.map((m) => m.region || 'City-wide')),
  ).sort();

  const allButton = document.createElement('button');
  allButton.className = 'filter-btn' + (activeRegion === 'all' ? ' active' : '');
  allButton.textContent = 'All regions';
  allButton.addEventListener('click', () => {
    activeRegion = 'all';
    renderRegionFilters(meetings);
    renderTimeline(meetings);
  });
  container.appendChild(allButton);

  regions.forEach((region) => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn' + (activeRegion === region ? ' active' : '');
    btn.textContent = region;
    btn.addEventListener('click', () => {
      activeRegion = region;
      renderRegionFilters(meetings);
      renderTimeline(meetings);
    });
    container.appendChild(btn);
  });
}

function renderTimeline(meetingsList) {
  const container = document.getElementById('timelineList');
  container.innerHTML = '';

  const filtered =
    activeRegion === 'all'
      ? meetingsList
      : meetingsList.filter((m) => (m.region || 'City-wide') === activeRegion);

  if (!filtered || filtered.length === 0) {
    container.innerHTML = '<p class="timeline-empty">No recent meetings found.</p>';
    return;
  }

  filtered.forEach((meeting) => {
    const item = document.createElement('button');
    item.className = 'timeline-item';
    item.dataset.meetingCode = meeting.meeting_code;

    const isUncached =
      meeting.detail_cached === false ||
      (meeting.detail_cached !== true &&
        (!meeting.motion_count || meeting.motion_count === 0) &&
        (!meeting.topics || meeting.topics.length === 0));

    const motionCountText = isUncached
      ? '—'
      : `${meeting.motion_count || 0} decisions`;

    const topicsPills =
      isUncached
        ? ''
        : (meeting.topics || [])
            .slice(0, 5)
            .map(
              (topic) =>
                `<span class="timeline-topic-pill">${escapeHtml(
                  topic.charAt(0).toUpperCase() + topic.slice(1)
                )}</span>`
            )
            .join('');

    item.innerHTML = `
      <div class="timeline-marker"></div>
      <div class="timeline-content">
        <div class="timeline-date">${escapeHtml(meeting.date || '')}</div>
        <div class="timeline-title">${escapeHtml(meeting.title || '')}</div>
        <div class="timeline-meta">
          <span class="timeline-motion-count">${escapeHtml(motionCountText)}</span>
          <div class="timeline-topics">${topicsPills}</div>
        </div>
      </div>
    `;

    item.addEventListener('click', async () => {
      if (activeMeetingCode === meeting.meeting_code) return;
      selectTimelineItem(meeting.meeting_code);
      await loadMeeting(meeting.meeting_code);
    });

    container.appendChild(item);
  });
}

function selectTimelineItem(meetingCode) {
  activeMeetingCode = meetingCode;

  document.querySelectorAll('.timeline-item').forEach((el) => {
    if (el.dataset.meetingCode === meetingCode) {
      el.classList.add('active');
    } else {
      el.classList.remove('active');
    }
  });
}

async function loadMeeting(meetingCode) {
  setLoadingMessage('Fetching council meeting data...');
  showLoading();
  document.getElementById('loadingSubtextLong')?.classList.add('hidden');
  if (loadingLongTimeout) clearTimeout(loadingLongTimeout);
  loadingLongTimeout = setTimeout(() => {
    document.getElementById('loadingSubtextLong')?.classList.remove('hidden');
  }, 2000);
  hideError();
  hideResults();
  activeCategory = 'all';
  activeSort = 'default';
  document.getElementById('sortSelect').value = 'default';

  const url = `${API_URL}/api/meetings/${encodeURIComponent(meetingCode)}`;
  try {
    const response = await fetch(url);
    let data;
    try {
      data = await response.json();
    } catch (_) {
      // Server returned non-JSON (e.g. HTML error page)
      throw new Error(response.ok ? 'Invalid response from server' : `Server error (${response.status}). Is the backend running on port 8000?`);
    }

    if (!response.ok) {
      const msg = Array.isArray(data.detail) ? data.detail.map((x) => x.msg || x).join(', ') : (data.detail || data.message || `Error ${response.status}`);
      throw new Error(msg);
    }

    currentMotions = data.motions || [];
    displayResults(data);

    // Update the meeting in the list so motion count and topics show without refresh
    const motions = data.motions || [];
    const topics = [...new Set(motions.map((m) => m.category).filter(Boolean))].sort();
    const idx = meetings.findIndex((m) => m.meeting_code === data.meeting_code);
    if (idx !== -1) {
      meetings[idx] = {
        ...meetings[idx],
        motion_count: motions.length,
        topics,
        detail_cached: true,
      };
      renderTimeline(meetings);
    }
  } catch (error) {
    console.error('Error loading meeting:', error);
    const message = error.message || 'Could not load meeting';
    showError(message);
  } finally {
    hideLoading();
  }
}

// Show loading state
function showLoading() {
  document.getElementById('loadingState').classList.remove('hidden');
}

function hideLoading() {
  if (loadingLongTimeout) {
    clearTimeout(loadingLongTimeout);
    loadingLongTimeout = null;
  }
  document.getElementById('loadingSubtextLong')?.classList.add('hidden');
  document.getElementById('loadingState').classList.add('hidden');
}

// Show error state
function showError(message) {
  document.getElementById('errorMessage').textContent = message;
  document.getElementById('errorState').classList.remove('hidden');
}

function hideError() {
  document.getElementById('errorState').classList.add('hidden');
}

// Show/hide results
function showResults() {
  document.getElementById('resultsSection').classList.remove('hidden');
}

function hideResults() {
  document.getElementById('resultsSection').classList.add('hidden');
}

// Display results
function displayResults(data) {
  const { meeting_code, title, date, source_url, motions } = data;

  // Update header
  document.getElementById('cityName').textContent = 'Toronto City Council';

  const meetingInfo =
    (date && date !== 'Unknown date'
      ? `Meeting Date: ${date}`
      : 'Recent Council Meeting') + (title ? ` • ${title}` : '');

  document.getElementById('meetingInfo').textContent = meetingInfo;

  // Handle source document link
  const pdfUrl = source_url;
  const banner = document.getElementById('sourceDocBanner');
  const pdfLinkElement = document.getElementById('pdfLink');
  const pdfLinkBtn = document.getElementById('pdfLinkBtn');
  
  if (pdfUrl && pdfUrl !== '#') {
    // Build a human-readable link label
    let linkLabel = 'Council Meeting Minutes';
    try {
      const hostname = new URL(pdfUrl).hostname.replace('www.', '');
      if (hostname.includes('escribemeetings')) {
        const cityPart = hostname.split('.')[0].replace('pub-', '');
        linkLabel = `${cityPart.charAt(0).toUpperCase() + cityPart.slice(1)} Council Minutes — eSCRIBE Portal`;
      } else {
        linkLabel = hostname;
      }
    } catch {}
    
    pdfLinkElement.href = pdfUrl;
    pdfLinkElement.textContent = linkLabel;
    pdfLinkBtn.href = pdfUrl;
    banner.classList.remove('hidden');
  } else {
    banner.classList.add('hidden');
  }

  // Build category filter buttons from actual data
  buildCategoryFilters(motions || []);
  document.getElementById('filterBar').classList.remove('hidden');

  // Render motions with current filters
  renderFilteredMotions();

  showResults();
  
  // Scroll to results
  document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
}

// Build category filter buttons from motion data
function buildCategoryFilters(motions) {
  const container = document.getElementById('categoryFilters');
  const categories = [...new Set(motions.map(m => m.category?.toLowerCase()).filter(Boolean))];
  categories.sort();

  container.innerHTML = '<button class="filter-btn active" data-category="all">All</button>';
  categories.forEach(cat => {
    const btn = document.createElement('button');
    btn.className = 'filter-btn';
    btn.dataset.category = cat;
    btn.textContent = cat.charAt(0).toUpperCase() + cat.slice(1);
    const count = motions.filter(m => m.category?.toLowerCase() === cat).length;
    btn.innerHTML = `${cat.charAt(0).toUpperCase() + cat.slice(1)} <span class="filter-count">${count}</span>`;
    container.appendChild(btn);
  });

  // Attach click handlers
  container.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCategory = btn.dataset.category;
      renderFilteredMotions();
    });
  });
}

// Render motions with current filter + sort
function renderFilteredMotions() {
  let filtered = [...currentMotions];

  // Filter by category
  if (activeCategory !== 'all') {
    filtered = filtered.filter(m => m.category?.toLowerCase() === activeCategory);
  }

  // Sort
  if (activeSort === 'category') {
    filtered.sort((a, b) => (a.category || '').localeCompare(b.category || ''));
  } else if (activeSort === 'status') {
    const order = { PASSED: 0, AMENDED: 1, DEFERRED: 2, FAILED: 3 };
    filtered.sort((a, b) => (order[a.status] ?? 4) - (order[b.status] ?? 4));
  } else if (activeSort === 'title') {
    filtered.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
  }

  // Update count
  const total = currentMotions.length;
  const shown = filtered.length;
  document.getElementById('resultsCount').textContent = activeCategory === 'all'
    ? `${total} decision${total !== 1 ? 's' : ''}`
    : `${shown} of ${total} decisions`;

  // Render grid
  const grid = document.getElementById('motionsGrid');
  grid.innerHTML = '';

  if (filtered.length === 0) {
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px;">No decisions in this category.</p>';
  } else {
    filtered.forEach((motion, index) => {
      const card = createMotionCard(motion, index);
      grid.appendChild(card);
    });
  }
}

// Create motion card
function createMotionCard(motion, index) {
  const card = document.createElement('div');
  card.className = 'motion-card';
  card.onclick = () => openModal(motion);

  const statusClass = `status-${motion.status.toLowerCase()}`;
  const categoryClass = `category-${motion.category.toLowerCase()}`;

  card.innerHTML = `
    <div class="card-header">
      <span class="card-category ${categoryClass}">${motion.category}</span>
      <span class="card-status ${statusClass}">${motion.status}</span>
    </div>
    <h3 class="card-title">${escapeHtml(motion.title)}</h3>
    <p class="card-summary">${escapeHtml(motion.summary)}</p>
    ${motion.impact_tags && motion.impact_tags.length > 0 ? `
      <div class="card-tags">
        ${motion.impact_tags.map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
      </div>
    ` : ''}
  `;

  return card;
}

// Open modal with full details
function openModal(motion) {
  currentModalMotion = motion;
  const modal = document.getElementById('modal');
  const categoryClass = `category-${motion.category.toLowerCase()}`;
  const statusClass = `status-${motion.status.toLowerCase()}`;

  document.getElementById('modalCategory').className = `modal-category ${categoryClass}`;
  document.getElementById('modalCategory').textContent = motion.category;
  
  document.getElementById('modalTitle').textContent = motion.title;
  document.getElementById('modalSummary').textContent = motion.summary;
  
  document.getElementById('modalStatus').innerHTML = `
    <span class="card-status ${statusClass}">${motion.status}</span>
  `;

  if (motion.impact_tags && motion.impact_tags.length > 0) {
    document.getElementById('modalTags').innerHTML = motion.impact_tags
      .map(tag => `<span class="tag">${escapeHtml(tag)}</span>`)
      .join('');
  } else {
    document.getElementById('modalTags').innerHTML = '';
  }

  if (motion.full_text) {
    document.getElementById('modalFullText').innerHTML = `
      <h4>Full Text:</h4>
      ${escapeHtml(motion.full_text)}
    `;
  } else {
    document.getElementById('modalFullText').innerHTML = '';
  }

  modal.classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

// Close modal
function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow = 'auto';
}

// Close modal on background click
document.getElementById('modal').addEventListener('click', (e) => {
  if (e.target.id === 'modal') {
    closeModal();
  }
});

// Report modal
function openReportModal() {
  if (!activeMeetingCode || !currentModalMotion) return;
  document.getElementById('reportForm').classList.remove('hidden');
  document.getElementById('reportConfirmation').classList.add('hidden');
  document.getElementById('reportReason').value = '';
  document.getElementById('reportComment').value = '';
  document.getElementById('reportModal').classList.remove('hidden');
}

function closeReportModal() {
  document.getElementById('reportModal').classList.add('hidden');
}

document.getElementById('reportMotionBtn').addEventListener('click', (e) => {
  e.stopPropagation();
  openReportModal();
});

document.getElementById('reportModalClose').addEventListener('click', closeReportModal);
document.getElementById('reportCancelBtn').addEventListener('click', closeReportModal);

document.getElementById('reportModal').addEventListener('click', (e) => {
  if (e.target.id === 'reportModal') closeReportModal();
});

document.getElementById('reportForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const reason = document.getElementById('reportReason').value;
  const comment = document.getElementById('reportComment').value.trim() || null;
  if (!reason) return;
  try {
    const response = await fetch(`${API_URL}/api/reports`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        meeting_code: activeMeetingCode,
        motion_id: currentModalMotion.id,
        reason,
        comment,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || 'Report failed');
    document.getElementById('reportForm').classList.add('hidden');
    document.getElementById('reportConfirmation').classList.remove('hidden');
    setTimeout(closeReportModal, 1500);
  } catch (err) {
    console.error('Report submit failed:', err);
    alert(err.message || 'Could not submit report');
  }
});

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
