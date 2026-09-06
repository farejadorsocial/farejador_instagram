(function(){
  const FALLBACK_CATEGORIES=['Influenciador','Música','Ator','Atriz','Celebridade','Esporte','Futebol','Humor','Jornalismo','Empresa/Marca','Criador de conteúdo','Streamer','Outro'];
  const categoriesPromise=fetch('/static/config/profile-categories.json',{cache:'no-store',credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(data=>{const list=Array.isArray(data?.categorias)?data.categorias:[];const valid=[...new Set(list.map(x=>String(x||'').trim()).filter(Boolean))];return valid.length?valid:FALLBACK_CATEGORIES}).catch(()=>FALLBACK_CATEGORIES);
  const categoryIcon=name=>({Música:'🎵',Celebridade:'⭐',Ator:'🎭',Atriz:'🎭',Influenciador:'🎤',Esporte:'🏆',Futebol:'⚽',Humor:'😂',Jornalismo:'📰',Streamer:'🎮','Empresa/Marca':'🏢','Criador de conteúdo':'📱',Outro:'📌'}[name]||'📌');

  window.rankingView=async function(){
    const endpoint=state.session.autenticado?'/api/explore':'/api/public/explore';
    const categoria=String(state.rankingCategory||'').trim();
    const url=categoria?`${endpoint}?categoria=${encodeURIComponent(categoria)}`:endpoint;
    const [d,categories]=await Promise.all([api(url),categoriesPromise]);
    state.ranking=d;
    const categoryOptions=[...categories.map(name=>`<option value="${esc(name)}" ${name.toLowerCase()===categoria.toLowerCase()?'selected':''}>${esc(`${categoryIcon(name)} ${name}`)}</option>`)].join('');
    const scope=categoria?`${categoryIcon(categoria)} ${categoria}`:'Selecione uma categoria';
    const rankings=categories.map(name=>{const selected=name.toLowerCase()===categoria.toLowerCase();return `<button type="button" class="ranking-category-tile ${selected?'selected':''}" data-ranking-category="${esc(name)}"><span>${categoryIcon(name)}</span><strong>${esc(name)}</strong><small>Ver ranking</small></button>`}).join('');
    return layout('🏆 RANKING','Ranking exclusivo por categoria',`<div class="card ranking-category-header"><div class="ranking-category-copy"><div class="eyebrow">RANKING POR CATEGORIA</div><h2>${esc(scope)}</h2><p class="muted">${state.session.autenticado?'Ranking formado exclusivamente pelos perfis salvos na sua conta.':'Ranking formado exclusivamente pelos perfis disponíveis na área pública.'}</p></div><label for="ranking-page-category">Categoria<select id="ranking-page-category" class="input"><option value="">Selecione uma categoria</option>${categoryOptions}</select></label></div><div class="ranking-category-grid">${rankings}</div>${categoria?`<div class="card ranking-category-result"><div class="section-title category-ranking-title"><div><b>${categoryIcon(categoria)} ${esc(categoria)}</b><small>Perfis desta categoria</small></div><span class="ranking-label">${fmtNumber(d.total_perfis)} PERFIS</span></div><div class="category-ranking-list">${renderCategoryProfiles(d)}</div></div>`:'<div class="card ranking-category-empty"><span>🏆</span><b>Escolha uma categoria</b><small>Selecione Influenciador, Atriz, Ator, Esporte, Futebol ou outra categoria para visualizar o ranking.</small></div>'}<div class="notice public-disclaimer">${state.session.autenticado?'Os dados desta página pertencem somente à sua conta.':'Os dados desta página são somente da área pública.'}</div>`);
  };

  function renderCategoryProfiles(data){
    const candidates=data.mais_seguidores||data.mais_ativos||data.maior_crescimento||[];
    if(!candidates.length)return '<div class="card empty">Ainda não há dados suficientes para formar este ranking.</div>';
    return candidates.map((x,i)=>{const p=x.perfil||{};return `<button class="card category-ranking-card" data-public-profile="${esc(p.username||'')}"><span class="category-ranking-position">${i+1}</span><div class="avatar-wrap small"><img class="avatar profile-image" src="${imageUrl(p.foto_perfil)}" alt="Foto de ${esc(p.nome||p.username||'perfil')}" referrerpolicy="no-referrer"><div class="avatar-fallback" aria-hidden="true">◉</div></div><div class="public-profile-info"><div class="profile-name">${esc(p.nome||p.username||'Perfil')}</div><div class="profile-meta">@${esc(p.username||'')}</div><div class="profile-stats"><span>👥 ${fmtNumber(p.seguidores)}</span><span>📈 ${x.crescimento>0?'+':''}${fmtNumber(x.crescimento)}</span></div></div><div class="category-ranking-score">${fmtNumber(p.seguidores)} seguidores</div></button>`}).join('');
  }

  document.addEventListener('change',event=>{if(event.target?.id!=='ranking-page-category')return;state.rankingCategory=String(event.target.value||'').trim();render()},true);
  document.addEventListener('click',event=>{const button=event.target.closest?.('[data-ranking-category]');if(!button)return;state.rankingCategory=String(button.dataset.rankingCategory||'').trim();render()},true);

  const installRoute=()=>{
    if(typeof render!=='function'){setTimeout(installRoute,0);return}
    if(window.__farejadorRankingRouteInstalled)return;
    window.__farejadorRankingRouteInstalled=true;
    const renderOriginal=render;
    render=async function(){
      if(state.route!=='ranking')return renderOriginal.apply(this,arguments);
      const content=$('#content');if(!content)return renderOriginal.apply(this,arguments);
      try{content.innerHTML=uiLoading('Carregando ranking');content.innerHTML=await window.rankingView();if(typeof bind==='function')bind();if(typeof bindImages==='function')bindImages()}
      catch(error){content.innerHTML=uiError(error?.message||'Não foi possível carregar o ranking.');if(typeof bind==='function')bind()}
    };
  };
  installRoute();
})();
