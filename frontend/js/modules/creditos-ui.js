let creditosUIInicializado=false;

async function atualizarSaldoCreditos(){
  const alvo=document.querySelector('#creditos-saldo');
  if(!state.session?.autenticado){if(alvo)alvo.textContent='—';return}
  try{
    const conta=await api('/api/creditos');
    if(alvo)alvo.textContent=fmtNumber(conta.saldo);
    document.dispatchEvent(new CustomEvent('farejador:creditos-atualizados',{detail:conta}));
  }catch(e){
    if(alvo)alvo.textContent='—';
    console.error('Falha ao carregar créditos:',e);
  }
}

function fecharModalCreditos(){
  const root=document.querySelector('#modal-root');
  if(root)root.innerHTML='';
}

async function abrirCreditos(){
  if(!state.session?.autenticado){openAuth();return}
  const root=document.querySelector('#modal-root');
  if(!root)return;
  root.innerHTML=`<div class="modal-backdrop creditos-backdrop"><div class="modal creditos-modal">
    <div class="creditos-header"><div><span class="creditos-kicker">SEU SALDO</span><h2>Créditos do Farejador</h2><p>Use créditos para analisar, salvar e monitorar perfis.</p></div><button class="icon-btn" id="creditos-close" aria-label="Fechar">×</button></div>
    <div class="creditos-saldo-box"><span>Saldo atual</span><strong id="creditos-modal-saldo">…</strong><small>1 análise = 1 crédito · Salvar = 10 · Monitorar 30 dias = 10</small></div>
    <div class="creditos-pacotes" id="creditos-pacotes"><div class="creditos-loading">Carregando pacote…</div></div>
    <div id="creditos-feedback" class="creditos-feedback" hidden></div>
    <div class="modal-footer"><button class="outline-btn" id="creditos-fechar-footer">Fechar</button></div>
  </div></div>`;

  document.querySelector('#creditos-close').onclick=fecharModalCreditos;
  document.querySelector('#creditos-fechar-footer').onclick=fecharModalCreditos;
  root.querySelector('.creditos-backdrop').onclick=e=>{if(e.target===e.currentTarget)fecharModalCreditos()};

  try{
    const [conta,pacotes]=await Promise.all([api('/api/creditos'),api('/api/pagamentos/pacotes')]);
    const saldo=document.querySelector('#creditos-modal-saldo');
    if(saldo)saldo.textContent=fmtNumber(conta.saldo);
    const lista=document.querySelector('#creditos-pacotes');
    lista.innerHTML=(pacotes.pacotes||[]).map(p=>`<button class="creditos-pacote" data-pacote="${esc(p.id)}">
      <span class="pacote-tag">PACOTE</span><strong>${fmtNumber(p.creditos)} créditos</strong><span class="pacote-preco">R$ ${Number(p.valor||0).toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2})}</span><small>Comprar agora</small>
    </button>`).join('')||'<div class="creditos-loading">Nenhum pacote disponível no momento.</div>';
    lista.querySelectorAll('[data-pacote]').forEach(btn=>btn.onclick=()=>comprarCreditos(btn.dataset.pacote));
  }catch(e){
    const lista=document.querySelector('#creditos-pacotes');
    if(lista)lista.innerHTML='<div class="creditos-feedback error">Não foi possível carregar os pacotes.</div>';
    console.error(e);
  }
}

async function comprarCreditos(pacote){
  const feedback=document.querySelector('#creditos-feedback');
  const botoes=[...document.querySelectorAll('[data-pacote]')];
  botoes.forEach(b=>b.disabled=true);
  if(feedback){feedback.hidden=false;feedback.className='creditos-feedback';feedback.textContent='Preparando seu pagamento…'}
  try{
    const chave=`checkout-${state.session?.cliente_usuario||'usuario'}-${pacote}-${crypto.randomUUID?.()||Date.now()}`;
    const resultado=await api('/api/pagamentos/checkout',{method:'POST',body:JSON.stringify({pacote,idempotency_key:chave})});
    if(!resultado.checkout_url)throw new Error('O checkout não está disponível no momento.');
    window.location.href=resultado.checkout_url;
  }catch(e){
    if(feedback){feedback.hidden=false;feedback.className='creditos-feedback error';feedback.textContent=e.message||'Não foi possível iniciar o pagamento.'}
    botoes.forEach(b=>b.disabled=false);
  }
}

function atualizarBotaoCreditos(){
  const btn=document.querySelector('#creditos-btn');
  if(!btn)return;
  btn.onclick=abrirCreditos;
  atualizarSaldoCreditos();
}

if(!creditosUIInicializado){
  creditosUIInicializado=true;
  document.addEventListener('click',e=>{
    if(e.target?.closest?.('#creditos-btn')){e.preventDefault();abrirCreditos()}
  });
  document.addEventListener('farejador:creditos-atualizados',e=>{
    const modalSaldo=document.querySelector('#creditos-modal-saldo');
    if(modalSaldo&&e.detail)modalSaldo.textContent=fmtNumber(e.detail.saldo);
  });
  document.addEventListener('farejador:session-expired',()=>fecharModalCreditos());
  setTimeout(atualizarBotaoCreditos,0);
}
