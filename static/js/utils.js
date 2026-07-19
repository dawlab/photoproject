function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    return new Date(isoStr).toLocaleDateString('pl-PL', {
      day: 'numeric', month: 'short', year: 'numeric'
    });
  } catch { return ''; }
}

// Returns the best available date string for a photo object
function photoDate(p) {
  return formatDate(p.shot_at || p.created_at);
}

// Fills the photo/gallery counters in .page-tabs
async function loadCounts(photosCountId, galCountId) {
  const [{ count: totalPhotos }, { count: totalGalleries }] = await Promise.all([
    sb.from('photos').select('*', { count: 'exact', head: true }),
    sb.from('galleries').select('*', { count: 'exact', head: true }),
  ]);
  if (photosCountId) document.getElementById(photosCountId).textContent = totalPhotos ?? '–';
  if (galCountId)    document.getElementById(galCountId).textContent    = totalGalleries ?? '–';
}
