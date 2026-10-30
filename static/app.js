const cards = document.querySelector('#cards');
const search = document.querySelector('#search');
const count = document.querySelector('#result-count');
const empty = document.querySelector('#empty');
const dialog = document.querySelector('#editor');
const form = document.querySelector('#company-form');
const toast = document.querySelector('#toast');
let timer;

function initials(name) {
  return name.replace(/[^\p{L}\p{N}\s]/gu, ' ').trim().split(/\s+/).slice(0, 2).map(word => word[0]).join('').toUpperCase();
}
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
}
function showToast(message) {
  toast.textContent = message; toast.classList.add('show');
  clearTimeout(timer); timer = setTimeout(() => toast.classList.remove('show'), 2500);
}
async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || data.message || 'Ocurrió un error.');
  return data;
}
function render(items) {
  count.textContent = `${items.length} ${items.length === 1 ? 'empresa encontrada' : 'empresas encontradas'}`;
  empty.hidden = items.length !== 0;
  cards.innerHTML = items.map(company => {
    const logo = `<span class="logo-link ${company.website ? '' : 'no-link'}" aria-label="${company.website ? 'Visitar sitio oficial de ' + esc(company.name) : 'Sitio oficial no registrado'}">${esc(initials(company.name))}</span>`;
    const linkedLogo = company.website ? `<a class="logo-link" href="${esc(company.website)}" target="_blank" rel="noopener noreferrer" aria-label="Visitar sitio oficial de ${esc(company.name)}">${esc(initials(company.name))}</a>` : logo;
    return `<article class="card"><div class="card-top">${linkedLogo}<div><h2>${esc(company.name)}</h2><div class="area">${esc(company.address)}</div></div></div><p class="specialty">${esc(company.specialty)}</p><div class="card-bottom"><a class="phone" href="tel:${esc(company.phone.replace(/[^+\d]/g,''))}">☎ &nbsp;${esc(company.phone)}</a><div class="actions"><button class="icon-button" data-edit="${esc(company.id)}" aria-label="Editar ${esc(company.name)}" title="Editar">✎</button><button class="icon-button delete" data-delete="${esc(company.id)}" aria-label="Eliminar ${esc(company.name)}" title="Eliminar">⌫</button></div></div></article>`;
  }).join('');
}
async function load() {
  try { render(await request(`/api/companies?q=${encodeURIComponent(search.value.trim())}`)); }
  catch (error) { count.textContent = 'No fue posible cargar el directorio'; cards.innerHTML = `<p class="error">${esc(error.message)} Revisa que MongoDB esté iniciado y vuelve a cargar.</p>`; }
}
function openNew() {
  form.reset(); document.querySelector('#company-id').value = '';
  document.querySelector('#modal-title').textContent = 'Nueva empresa';
  document.querySelector('#form-error').textContent = ''; dialog.showModal();
}
function openEdit(company) {
  form.reset(); document.querySelector('#company-id').value = company.id;
  document.querySelector('#modal-title').textContent = 'Editar empresa';
  for (const field of ['name','address','specialty','phone','website']) form.elements[field].value = company[field] || '';
  document.querySelector('#form-error').textContent = ''; dialog.showModal();
}
let lastItems = [];
const originalRender = render;
render = function(items) { lastItems = items; originalRender(items); };
search.addEventListener('input', () => { clearTimeout(search.delay); search.delay = setTimeout(load, 180); });
document.querySelector('#add').addEventListener('click', openNew);
document.querySelector('#close').addEventListener('click', () => dialog.close());
document.querySelector('#cancel').addEventListener('click', () => dialog.close());
dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
cards.addEventListener('click', async event => {
  const editId = event.target.closest('[data-edit]')?.dataset.edit;
  const deleteId = event.target.closest('[data-delete]')?.dataset.delete;
  if (editId) openEdit(lastItems.find(item => item.id === editId));
  if (deleteId) {
    const company = lastItems.find(item => item.id === deleteId);
    if (!confirm(`¿Eliminar a ${company.name} del directorio?`)) return;
    try { await request(`/api/companies/${deleteId}`, {method:'DELETE'}); showToast('Empresa eliminada.'); await load(); }
    catch (error) { showToast(error.message); }
  }
});
form.addEventListener('submit', async event => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(form).entries());
  const id = document.querySelector('#company-id').value;
  try {
    await request(id ? `/api/companies/${id}` : '/api/companies', {method:id ? 'PUT' : 'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    dialog.close(); showToast(id ? 'Cambios guardados.' : 'Empresa agregada.'); await load();
  } catch (error) { document.querySelector('#form-error').textContent = error.message; }
});
document.addEventListener('keydown', event => { if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') { event.preventDefault(); search.focus(); } });
load();
