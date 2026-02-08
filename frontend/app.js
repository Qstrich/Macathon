const API_URL = 'http://localhost:3000';

let currentMotions = [];
let activeCategory = 'all';
let activeSort = 'default';

// Event listeners
document.getElementById('searchBtn').addEventListener('click', handleSearch);
document.getElementById('cityInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleSearch();
});

// Sort select listener
document.getElementById('sortSelect').addEventListener('change', (e) => {
  activeSort = e.target.value;
  renderFilteredMotions();
});

// Handle search
async function handleSearch() {
  const city = document.getElementById('cityInput').value.trim();
  
  if (!city) {
    alert('Please enter a city name');
    return;
  }

  showLoading();
  hideError();
  hideResults();
  activeCategory = 'all';
  activeSort = 'default';
  document.getElementById('sortSelect').value = 'default';

  try {
    const response = await fetch(`${API_URL}/api/scrape`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ city }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || 'Failed to fetch data');
    }

    if (data.success) {
      currentMotions = data.motions;
      displayResults(data);
    } else {
      throw new Error('No data received');
    }

  } catch (error) {
    console.error('Error:', error);
    showError(error.message);
  } finally {
    hideLoading();
  }
}

// Show loading state
function showLoading() {
  document.getElementById('loadingState').classList.remove('hidden');
}

function hideLoading() {
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
  const { city, metadata, motions } = data;

  // Update header
  document.getElementById('cityName').textContent = city;
  
  // Show cached badge if applicable
  let meetingInfo = metadata.meeting_date && metadata.meeting_date !== 'Unknown' 
    ? `Meeting Date: ${metadata.meeting_date}` 
    : 'Recent Council Meeting';
  
  if (data.cached) {
    meetingInfo += ' • ⚡ Cached';
  }
  
  document.getElementById('meetingInfo').textContent = meetingInfo;
  
  // Handle PDF document link
  const pdfUrl = metadata.document_url || metadata.source_url;
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
  buildCategoryFilters(motions);
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

// Escape HTML to prevent XSS
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
