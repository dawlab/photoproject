const MOODS = {
  great: { label: 'Świetny',        color: '#1b4d3e', bg: '#1b4d3e' },
  good:  { label: 'Dobry',          color: '#52b788', bg: '#52b788' },
  meh:   { label: 'Nic specjalnego', color: '#b7e4c7', bg: '#b7e4c7' },
  bad:   { label: 'Zły',            color: '#dda15e', bg: '#dda15e' },
  awful: { label: 'Okropny',        color: '#c1440e', bg: '#c1440e' },
};

// SVG face icons — each returns an <svg> string at given size
function moodSvg(key, size = 36) {
  const m = MOODS[key];
  if (!m) return '';
  const c = m.color;
  const faces = {
    great: `<circle cx="12" cy="12" r="10" fill="${c}"/>
      <path d="M7 13.5 Q12 19 17 13.5" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M8.5 9 Q9.5 7.5 10.5 9" stroke="#fff" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      <path d="M13.5 9 Q14.5 7.5 15.5 9" stroke="#fff" stroke-width="1.4" fill="none" stroke-linecap="round"/>`,
    good: `<circle cx="12" cy="12" r="10" fill="${c}"/>
      <path d="M7.5 13.5 Q12 18 16.5 13.5" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <circle cx="9.5" cy="10" r="1" fill="#fff"/>
      <circle cx="14.5" cy="10" r="1" fill="#fff"/>`,
    meh: `<circle cx="12" cy="12" r="10" fill="${c}"/>
      <line x1="8" y1="15" x2="16" y2="15" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
      <circle cx="9.5" cy="10" r="1" fill="#fff"/>
      <circle cx="14.5" cy="10" r="1" fill="#fff"/>`,
    bad: `<circle cx="12" cy="12" r="10" fill="${c}"/>
      <path d="M8 16.5 Q12 12 16 16.5" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <circle cx="9.5" cy="10" r="1" fill="#fff"/>
      <circle cx="14.5" cy="10" r="1" fill="#fff"/>`,
    awful: `<circle cx="12" cy="12" r="10" fill="${c}"/>
      <path d="M7.5 16.5 Q12 11 16.5 16.5" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/>
      <path d="M8.5 9 Q9.5 10.5 10.5 9" stroke="#fff" stroke-width="1.4" fill="none" stroke-linecap="round"/>
      <path d="M13.5 9 Q14.5 10.5 15.5 9" stroke="#fff" stroke-width="1.4" fill="none" stroke-linecap="round"/>`,
  };
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24">${faces[key] || ''}</svg>`;
}
