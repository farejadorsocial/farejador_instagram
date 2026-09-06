(function(){
  const FALLBACK_CATEGORIES=['Influenciador','Música','Ator','Atriz','Celebridade','Esporte','Futebol','Humor','Jornalismo','Empresa/Marca','Criador de conteúdo','Streamer','Outro'];
  const RANKINGS=[
    ['activity','🔥 Mais ativos','Maior quantidade de eventos e capturas','mais_ativos','pontos'],
    ['growth','📈 Maior crescimento percentual','Maior crescimento proporcional no período','maior_crescimento','percentual'],
    ['absolute','🚀 Maior crescimento absoluto','Maior ganho de seguidores em quantidade','maior_crescimento_absoluto','absoluto'],
    ['followers','👥 Mais seguidores','Maior número atual de seguidores','mais_seguidores','seguidores'],
    ['content','🎬 Mais conteúdo','Maior volume de posts, reels e destaques','mais_conteudo','conteudo'],
    ['pace','⚡ Maior ritmo','Maior velocidade recente de crescimento','maior_ritmo','ritmo'],
    ['discoveries','🔎 Mais descobertas','Mais padrões e acontecimentos encontrados','mais_descobertas','descobertas']
  ];

  const categoriesPromise=fetch('/static/config/profile-categories.json',{cache:'no-store',credentials:'same-origin'})
    .then(r=>r.ok?r.json():null)
    .then(data=>{
      const list=Array.isArray(data?.categorias)?data.categorias:[];
      const valid=[...new Set(list.map(x=>String(x||'').trim()).filter(Boolean))];
      return valid.length?valid:FALLBACK_CATEGORIES;
    })
    .catch(()=>FALLBACK_CATEGORIES);

  const categoryIcon=name=>({Música:'🎵',Celebridade:'⭐',Ator:'🎭',Atriz:'🎭',Influenciador:'🎤',Esporte:'🏆',Futebol:'⚽',Humor:'😂',Jornalismo:'📰',Streamer:'🎮','Empresa/Marca':'🏢','Criador de conteúdo':'📱',Outro:'📌'}[name]||'📌');
  const metricValue=(x,tipo)=>{if(tipo==='growth')return Number(x.crescimento_percentual||0);if(tipo==='absolute')return Number(x.crescimento||0);if(tipo==='followers')return Number(x.seguidores||0);if(tipo==='activity')return Number(x.atividade_score||x.atividade||0);if(tipo==='pace')return Number(x.ritmo_diario||0);if(tipo==='discoveries')return Number(x.descobertas||0);return Number(x.conteudo||0)};
  const metricLabel=(x,tipo)=>{const v=metricValue(x,tipo);if(tipo==='growth')return `${v>0?'+':''}${v.toLocaleString('pt-BR',{maximumFractionDigits:1})}%`;if(tipo==='absolute')return `${v>0?'+':''}${fmtNumber(v)}`;if(tipo==='followers')return `${fmtNumber(v)} seguidores`;if(tipo==='activity')return `${fmtNumber(v)} pontos`;if(tipo==='pace')return `${v>0?'+':''}${v.toLocaleString('pt-BR',{maximumFractionDigits:1})}/dia`;if(tipo==='discoveries')return `${fmtNumber(v)} descobertas`;return `${fmtNumber(v)} itens`};
  const description=(x,tipo)=>{if(tipo==='growth')return `Variação proporcional · ${x.crescimento>0?'+':''}${fmtNumber(x.crescimento)} seguidores`;if(tipo==='absolute')return `Crescimento absoluto · ${x.crescimento>0?'+':''}${fmtNumber(x.crescimento)} seguidores`;if(tipo==='followers')return `Crescimento no período · ${x.crescimento>0?'+':''}${fmtNumber(x.crescimento)} (${Number(x.crescimento_percentual||0).toLocaleString('pt-BR',{maximumFractionDigits:1})}%)`;if(tipo==='activity')return `${fmtNumber(x.eventos)} eventos · ${fmtNumber(x.capturas)} capturas`;if(tipo==='pace')return `Ritmo recente · ${x.ritmo_diario>0?'+':''}${Number(x.ritmo_diario||0).toLocaleString('pt-BR',{maximumFractionDigits:1})} seguidores/dia`;if(tipo==='discoveries')return `${fmtNumber(x.descobertas)} padrões/insights encontrados`;return `${fmtNumber(x.perfil?.total_posts||0)} posts · ${fmtNumber(x.perfil?.total_reels||0)} reels`};
  const card=(x,rank,tipo)=>{const p=x.perfil||{};return `<button class="card category-ranking-card" data-public-profile="${esc(p.username||'')}"><span class="category-ranking-position">${rank}</span><div class="avatar-wrap small"><img class="avatar profile-image" src="${imageUrl(p.foto_perfil)}" alt="Foto de ${esc(p.nome||p.username||'perfil')}" referrerpolicy="no-referrer"><div class="avatar-fallback" aria-hidden="true">◉</div></div><div class="public-profile-info"><div class="profile-name">${esc(p.nome||p.username||'Perfil')}</div><div class="profile-meta">@${esc(p.username||'')}</div><div class="profile-stats"><span>👥 ${fmtNumber(p.seguidores)}</span><span>📈 ${x.crescimento>0?'+':''}${fmtNumber(x.crescimento)}</span></div><small class="category-ranking-description">${esc(description(x,tipo))}</small></div><div class="category-ranking-score">${esc(metricLabel(x,tipo))}</div></button>`};
  const section=(title,subtitle,items,tipo)=>`<section class="category-ranking-section"><div class="section-title category-ranking-title"><div><b>${title}</b><small>${subtitle}</small></div><span class="ranking-label">TOP ${(items||[]).length}</span></div><div class="category-ranking-list">${(items||[]).map((x,i)=>card(x,i+1,tipo)).join('')||'<div class="card empty">Ainda não há dados suficientes nesta categoria.</div>'}</div></section>`;

  window.rankingView=async function(){
    const endpoint=state.session.autenticado?'/api/explore':'/api/public/explore';
    const categoria=String(state.rankingCategory||'').trim();
    const url=categoria?`${endpoint}?categoria=${encodeURIComponent(categoria)}`:endpoint;
    const [d,categories]=await Promise.all([api(url),categoriesPromise]);
    state.ranking=d;
    const selectedCategory=categoria||'';
    const categoryOptions=[`<option value="">👥 Todas as categorias</option>`,...categories.map(name=>`<option value="${esc(name)}" ${name.toLowerCase()===selectedCategory.toLowerCase()?'selected':''}>${esc(`${categoryIcon(name)} ${name}`)}</option>`)].join('');
    const scope=selectedCategory?`${categoryIcon(selectedCategory)} ${selectedCategory}`:'👥 Todas as categorias';
    const sections=RANKINGS.map(r=>section(r[1],r[2],d[r[3]]||[],r[0])).join('');
    return layout('🏆 RANKING','Rankings organizados por categoria',`<div class="card ranking-category-header"><div class="ranking-category-copy"><div class="eyebrow">RANKING POR CATEGORIA</div><h2>${esc(scope)}</h2><p class="muted">${state.session.autenticado?'Veja exclusivamente os perfis salvos na sua conta.':'Veja exclusivamente os perfis disponíveis na área pública.'}</p></div><label for="ranking-page-category">Categoria<select id="ranking-page-category" class="input">${categoryOptions}</select></label></div><div class="stats ranking-page-stats">${stat('👤 Perfis',d.total_perfis)}${stat('📸 Capturas',d.total_capturas)}${stat('📈 Eventos',d.total_eventos)}</div><div class="ranking-page-grid">${sections}</div><div class="notice public-disclaimer">${state.session.autenticado?'Nada desta tela usa dados de outros clientes.':'Os rankings públicos podem mudar quando novas capturas forem realizadas.'}</div>`);
  };

  document.addEventListener('change',event=>{if(event.target?.id!=='ranking-page-category')return;state.rankingCategory=String(event.target.value||'').trim();render()},true);

  // O módulo é carregado antes de events/ui-stability. Interceptamos apenas a nova rota
  // e deixamos todas as demais rotas seguirem exatamente pelo renderizador existente.
  const installRoute=()=>{
    if(typeof render!=='function'){setTimeout(installRoute,0);return}
    if(window.__farejadorRankingRouteInstalled)return;
    window.__farejadorRankingRouteInstalled=true;
    const renderOriginal=render;
    render=async function(){
      if(state.route!=='ranking')return renderOriginal.apply(this,arguments);
      const content=$('#content');
      if(!content)return renderOriginal.apply(this,arguments);
      try{
        content.innerHTML=uiLoading('Carregando ranking');
        content.innerHTML=await window.rankingView();
        if(typeof bind==='function')bind();
        if(typeof bindImages==='function')bindImages();
      }catch(error){
        content.innerHTML=uiError(error?.message||'Não foi possível carregar o ranking.');
        if(typeof bind==='function')bind();
      }
    };
  };
  installRoute();
})();
