(function () {
  var categoryEl = document.getElementById('fb-category');

  function showMsg(text, isErr) {
    var el = document.getElementById('fb-msg');
    el.style.display = 'block';
    el.textContent = text;
    el.style.color = isErr ? '#DC2626' : '#16A34A';
  }

  window.submitFeedback = function () {
    var btn = document.getElementById('fb-submit');
    var categoryId = Number(categoryEl.value);
    var title = document.getElementById('fb-title').value.trim();
    var content = document.getElementById('fb-content').value.trim();
    if (!categoryId) { showMsg('请选择反馈分类', true); return; }
    if (title.length < 2) { showMsg('请填写标题（至少 2 个字）', true); return; }
    if (content.length < 5) { showMsg('请填写详细内容（至少 5 个字）', true); return; }

    var payload = {
      category_id: categoryId,
      title: title,
      content: content,
      related_url: document.getElementById('fb-related_url').value.trim() || null,
      contact_info: document.getElementById('fb-contact_info').value.trim() || null
    };

    btn.disabled = true;
    btn.textContent = '提交中…';
    fetch('/api/v1/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().then(function (d) { return { ok: r.ok, d: d }; });
    }).then(function (res) {
      btn.disabled = false;
      btn.textContent = '提交反馈';
      if (!res.ok) { showMsg(res.d.detail || '提交失败', true); return; }
      var parts = ['反馈已保存，感谢你的建议！'];
      if (res.d.email_status === 'FAILED') {
        parts.push('（邮件通知失败：' + (res.d.email_error || '未知错误') + '，但你的反馈已记录）');
      } else if (res.d.email_status === 'DISABLED') {
        parts.push('（邮件通知当前未开启，反馈已记录）');
      }
      showMsg(parts.join(''), res.d.email_status === 'FAILED');
      document.getElementById('feedback-form').reset();
      setTimeout(function () { location.reload(); }, 2500);
    }).catch(function (e) {
      btn.disabled = false;
      btn.textContent = '提交反馈';
      showMsg('网络错误：' + e.message, true);
    });
  };
})();
