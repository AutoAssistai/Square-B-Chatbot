const messagesEl = document.getElementById('messages');
const formEl = document.getElementById('chat-form');
const inputEl = document.getElementById('user-input');
const menuListEl = document.getElementById('menu-list');

function appendMessage(role, text) {
  const wrap = document.createElement('div');
  wrap.className = `message ${role}`;
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function ensureSession() {
  let sid = localStorage.getItem('sb_session');
  if (!sid) {
    sid = crypto.randomUUID();
    localStorage.setItem('sb_session', sid);
  }
  return sid;
}

function renderSuggestions(suggestions) {
  if (!Array.isArray(suggestions) || suggestions.length === 0) return;
  const wrap = document.createElement('div');
  wrap.className = 'suggestions';
  for (const s of suggestions) {
    const card = document.createElement('div');
    card.className = 'card';

    const img = document.createElement('img');
    img.src = s.image || '/static/images/placeholder.svg';
    img.alt = s.name;

    const title = document.createElement('div');
    title.className = 'title';
    title.textContent = s.name;

    const price = document.createElement('div');
    price.className = 'price';
    price.textContent = (s.price != null) ? (s.price.toFixed(2) + ' ر.س') : '';

    const btn = document.createElement('button');
    btn.className = 'add';
    btn.textContent = 'أضف للطلب';
    btn.onclick = () => addToCart(s);

    card.appendChild(img);
    card.appendChild(title);
    card.appendChild(price);
    card.appendChild(btn);
    wrap.appendChild(card);
  }
  const msgWrap = document.createElement('div');
  msgWrap.className = 'message bot';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.appendChild(wrap);
  msgWrap.appendChild(bubble);
  messagesEl.appendChild(msgWrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

const CART = [];
function addToCart(item) {
  CART.push(item);
  updateCartBadge();
}
function updateCartBadge() {
  const el = document.getElementById('cart-badge');
  if (el) el.textContent = CART.length.toString();
}

async function sendMessage(text) {
  appendMessage('user', text);
  inputEl.value = '';
  formEl.querySelector('button').disabled = true;

  try {
    const session_id = ensureSession();
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, session_id })
    });
    if (!res.ok) throw new Error('Network response was not ok');
    const data = await res.json();
    appendMessage('bot', data.reply);
    renderSuggestions(data.suggestions);
  } catch (err) {
    appendMessage('bot', 'عذراً، حدث خطأ غير متوقع. حاول مرة أخرى لاحقاً.');
    console.error(err);
  } finally {
    formEl.querySelector('button').disabled = false;
    inputEl.focus();
  }
}

formEl.addEventListener('submit', (e) => {
  e.preventDefault();
  const text = inputEl.value.trim();
  if (!text) return;
  sendMessage(text);
});

async function loadMenu() {
  try {
    const res = await fetch('/menu');
    if (!res.ok) throw new Error('failed');
    const payload = await res.json();
    const items = Array.isArray(payload) ? payload : (payload.items || []);
    if (!Array.isArray(items) || items.length === 0) {
      menuListEl.textContent = 'لا توجد بيانات منيو حالياً.';
      return;
    }
    menuListEl.textContent = '';
    for (const item of items) {
      const div = document.createElement('div');
      div.className = 'menu-item';
      const line = document.createElement('div');
      const colorDot = document.createElement('span');
      colorDot.className = 'menu-color';
      if (item.color) colorDot.style.background = item.color;
      line.textContent = `${item.name}${item.price ? ' — ' + item.price.toFixed(2) + ' ر.س' : ''}`;
      line.appendChild(colorDot);
      div.appendChild(line);
      if (item.description) {
        const d = document.createElement('div');
        d.style.color = '#666';
        d.style.fontSize = '.9rem';
        d.textContent = item.description;
        div.appendChild(d);
      }
      menuListEl.appendChild(div);
    }
  } catch (_) {
    menuListEl.textContent = 'تعذر تحميل المنيو.';
  }
}

loadMenu();
