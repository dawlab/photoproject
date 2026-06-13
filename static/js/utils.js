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
