// ============================================================
// Green Flame Tech Jekyll Theme — main.js
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  addCopyButtons();
  addAnchorLinks();
  highlightActiveSidebarLink();
  addCodeLanguageLabels();
});

function updateCopyButtonState(btn, copied) {
  if (copied) {
    btn.textContent = 'Copied!';
    btn.setAttribute('aria-label', 'Copied! Code is in your clipboard');
    btn.classList.add('copied');
  } else {
    btn.textContent = 'Copy unavailable';
    btn.setAttribute('aria-label', 'Copy unavailable in this browser');
  }

  globalThis.setTimeout(() => {
    btn.textContent = 'Copy';
    btn.setAttribute('aria-label', 'Copy code to clipboard');
    btn.classList.remove('copied');
  }, 2000);
}

async function copyTextToClipboard(text) {
  if (globalThis.navigator?.clipboard?.writeText) {
    await globalThis.navigator.clipboard.writeText(text);
    return true;
  }
  return false;
}

function addCopyButtons() {
  document.querySelectorAll('pre > code').forEach(codeEl => {
    const pre = codeEl.parentElement;

    const wrapper = document.createElement('div');
    wrapper.className = 'code-block-wrapper';
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);

    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.setAttribute('aria-label', 'Copy code to clipboard');

    btn.addEventListener('click', async () => {
      const text = codeEl.innerText;
      const copied = await copyTextToClipboard(text).catch(() => false);
      updateCopyButtonState(btn, copied);
    });

    wrapper.appendChild(btn);
  });
}

function addAnchorLinks() {
  document.querySelectorAll('.prose h2, .prose h3').forEach(heading => {
    if (!heading.id) return;
    const anchor = document.createElement('a');
    anchor.href = `#${heading.id}`;
    anchor.className = 'anchor';
    anchor.setAttribute('aria-hidden', 'true');
    anchor.textContent = '#';
    heading.appendChild(anchor);
  });
}

function highlightActiveSidebarLink() {
  const currentPath = globalThis.location.pathname;
  document.querySelectorAll('.sidebar a').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });
}

function addCodeLanguageLabels() {
  document.querySelectorAll('pre > code[class*="language-"]').forEach(codeEl => {
    const lang = [...codeEl.classList]
      .find(c => c.startsWith('language-'))
      ?.replace('language-', '');
    if (lang) {
      codeEl.parentElement.dataset.lang = lang;
    }
  });
}
