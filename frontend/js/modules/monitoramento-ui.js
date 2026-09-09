/* Regras visuais do monitoramento pago: durante os 30 dias somente o Resumo fica disponível. */
(function(){
  const texto=v=>String(v??'').trim();
  const diasRestantes=fim=>{
    if(!fim)return 0;
    const ms=new Date(fim).getTime()-Date.now();
    if(!Number.isFinite(ms)||ms<=0)return 0;
    return Math.max(1,Math.ceil(ms/86400000));
  };

  window.profileCard=function(x){
    const p=x?.perfil||{},m=x?.monitoramento||{};
    const ativo=!!m.monitorando;
    const dias=ativo?diasRestantes(m.fim_monitoramento):0;
    const fim=ativo&&m.fim_monitoramento?new Date(m.fim_monitoramento):null;
    const fimLabel=fim&&!Number.isNaN(fim.getTime())?fim.toLocaleDateString('pt-BR'):'—';
    const status=ativo?`🟢 MONITORANDO · ${dias} ${dias===1?'dia':'dias'}`:'⚪ NÃO MONITORADO';
    const acoes=ativo
      ? `<button class="ghost-btn" data-summary="${esc(p.pk)}">📊 Resumo</button>`
      : `<button class="ghost-btn" data-summary="${esc(p.pk)}">📊 Resumo</button><button class="ghost-btn" data-monitor="${esc(p.username)}" data-enabled="true">▶ Monitorar · 10 créditos</button><button class="danger-btn" data-remove="${esc(p.username)}">🗑 Remover</button>`;
    const detalhe=ativo
      ? `<div class="monitoring-cycle"><strong>Monitoramento ativo</strong><span>Até ${esc(fimLabel)} · ${dias} ${dias===1?'dia restante':'dias restantes'}</span><small>Durante o ciclo, este usuário não pode ser removido nem ter o monitoramento interrompido.</small></div>`
      : '';
    return `<div class="card profile-card ${ativo?'is-active':'is-paused'}" data-username="${esc(p.username)}"><div class="avatar-wrap"><img class="avatar profile-image" src="${imageUrl(p.foto_perfil)}" alt="Foto de ${esc(p.nome||p.username||'perfil')}" referrerpolicy="no-referrer"><div class="avatar-fallback" aria-hidden="true">◉</div></div><div><div><span class="profile-name">${esc(p.nome||p.username)}</span> <span class="badge ${ativo?'good':''}">${status}</span></div><div class="profile-meta">@${esc(p.username)} · ${p.privado?'🔒 Conta privada':'🌐 Conta pública'}</div><div class="profile-stats"><span>👥 ${fmtNumber(p.seguidores)} seguidores</span><span>➜ ${fmtNumber(p.seguindo)} seguindo</span><span>Posts ${fmtNumber(p.total_posts)}</span><span>Reels ${fmtNumber(p.total_reels)}</span></div><div class="profile-meta">${esc(p.biografia||'')}</div>${detalhe}</div><div class="actions">${acoes}</div></div>`;
  };
})();
