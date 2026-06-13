async function loadProfile(heroId, photosCountId, galCountId) {
  const [{ data: p }, { count: total_photos }, { count: total_galleries }, { data: days }] = await Promise.all([
    sb.from('profile').select('*').eq('id', 1).single(),
    sb.from('photos').select('*', { count: 'exact', head: true }),
    sb.from('galleries').select('*', { count: 'exact', head: true }),
    sb.from('photos').select('day').order('day', { ascending: false }),
  ]);

  if (photosCountId) document.getElementById(photosCountId).textContent = total_photos ?? '–';
  if (galCountId)    document.getElementById(galCountId).textContent    = total_galleries ?? '–';

  const hero = document.getElementById(heroId);
  if (!hero || !p) return;

  let streak = 0;
  if (days && days.length) {
    streak = 1;
    for (let i = 0; i < days.length - 1; i++) {
      if (days[i].day - days[i + 1].day === 1) streak++;
      else break;
    }
  }

  const avatar = p.avatar
    ? `<img src="${photoUrl(p.avatar)}" class="profile-avatar" alt="avatar">`
    : `<div class="profile-avatar profile-avatar--placeholder">${(p.name || '?')[0].toUpperCase()}</div>`;

  const meta = [];
  if (p.location) meta.push(`<span class="profile-meta-item"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>${p.location}</span>`);
  if (p.website) {
    const label = p.website.replace(/^https?:\/\//, '').replace(/\/$/, '');
    meta.push(`<span class="profile-meta-item"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg><a href="${p.website}" target="_blank" rel="noopener">${label}</a></span>`);
  }

  hero.innerHTML = `
    <div class="profile-inner">
      ${avatar}
      <div class="profile-body">
        <div class="profile-top">
          <h1 class="profile-name">${p.name || 'Moje 365'}</h1>
          ${p.follow_url
            ? `<a href="${p.follow_url}" target="_blank" rel="noopener" class="btn-follow btn-follow--active">${p.follow_label || 'Obserwuj'}</a>`
            : `<button class="btn-follow" disabled>${p.follow_label || 'Obserwuj'}</button>`}
        </div>
        ${meta.length ? `<div class="profile-meta">${meta.join('')}</div>` : ''}
        ${p.bio ? `<p class="profile-bio">${p.bio}</p>` : ''}
        ${streak > 1 ? `<p class="profile-stats">Ciąg: ${streak}</p>` : ''}
      </div>
    </div>`;
}
