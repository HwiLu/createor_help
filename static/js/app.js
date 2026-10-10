async function logout(e) {
  e.preventDefault();
  await fetch('/api/v1/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text);
  }
  return new Promise(function (resolve, reject) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.top = '-9999px';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      resolve();
    } catch (err) {
      reject(err);
    } finally {
      document.body.removeChild(ta);
    }
  });
}

document.addEventListener('click', function (e) {
  const btn = e.target.closest('.copy-btn');
  if (!btn) return;
  e.preventDefault();
  e.stopPropagation();

  const text = btn.getAttribute('data-copy') || '';
  const originalTitle = btn.getAttribute('title') || '';
  const originalSvg = btn.querySelector('svg') ? btn.querySelector('svg').outerHTML : '';

  copyText(text).then(function () {
    btn.classList.add('copied');
    btn.setAttribute('title', '已复制');
    if (originalSvg) {
      btn.querySelector('svg').outerHTML =
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';
    }
    window.setTimeout(function () {
      btn.classList.remove('copied');
      btn.setAttribute('title', originalTitle);
      if (originalSvg && btn.querySelector('svg')) {
        btn.querySelector('svg').outerHTML = originalSvg;
      }
    }, 1200);
  }).catch(function () {
    btn.setAttribute('title', '复制失败，请手动复制');
    window.setTimeout(function () {
      btn.setAttribute('title', originalTitle);
    }, 1200);
  });
});
