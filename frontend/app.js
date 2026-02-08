const API_URL = 'http://localhost:3000';

let currentMotions = [];

// Event listeners
document.getElementById('searchBtn').addEventListener('click', handleSearch);
document.getElementById('cityInput').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') handleSearch();
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
  
  const meetingDate = metadata.meeting_date && metadata.meeting_date !== 'Unknown' 
    ? `Meeting Date: ${metadata.meeting_date}` 
    : 'Recent Council Meeting';
  document.getElementById('meetingInfo').textContent = meetingDate;
  
  // Handle PDF document link (the actual parsed document)
  const pdfUrl = metadata.document_url;
  const pdfLinkElement = document.getElementById('pdfLink');
  const pdfLinkContainer = document.getElementById('pdfLinkContainer');
  
  if (pdfUrl && pdfUrl !== '#') {
    pdfLinkElement.href = pdfUrl;
    // Display a shortened URL or filename
    const urlParts = pdfUrl.split('/');
    const fileName = urlParts[urlParts.length - 1] || 'View Document';
    pdfLinkElement.textContent = decodeURIComponent(fileName).substring(0, 60) + (fileName.length > 60 ? '...' : '');
    pdfLinkContainer.style.display = 'flex';
  } else {
    pdfLinkContainer.style.display = 'none';
  }
  
  // Handle source page link (the repository or listing page)
  const sourceUrl = metadata.source_url;
  const sourceLinkElement = document.getElementById('sourceLink');
  const sourceLinkContainer = document.getElementById('sourceLinkContainer');
  
  if (sourceUrl && sourceUrl !== '#' && sourceUrl !== pdfUrl) {
    sourceLinkElement.href = sourceUrl;
    // Extract domain for display
    try {
      const domain = new URL(sourceUrl).hostname.replace('www.', '');
      sourceLinkElement.textContent = domain;
    } catch {
      sourceLinkElement.textContent = 'View Source Page';
    }
    sourceLinkContainer.style.display = 'flex';
  } else {
    sourceLinkContainer.style.display = 'none';
  }

  // Display motions
  const grid = document.getElementById('motionsGrid');
  grid.innerHTML = '';

  if (motions.length === 0) {
    grid.innerHTML = '<p style="grid-column: 1/-1; text-align: center; color: #666; padding: 40px;">No motions found in this meeting.</p>';
  } else {
    motions.forEach((motion, index) => {
      const card = createMotionCard(motion, index);
      grid.appendChild(card);
    });
  }

  showResults();
  
  // Scroll to results
  document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
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
