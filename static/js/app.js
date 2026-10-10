async function logout(e) {
  e.preventDefault();
  await fetch('/api/v1/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}
