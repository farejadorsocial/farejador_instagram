(function(){
  const FALLBACK_CATEGORIES=['Influenciador','Música','Ator','Atriz','Celebridade','Esporte','Futebol','Humor','Jornalismo','Empresa/Marca','Criador de conteúdo','Streamer','Outro'];
  const categoriesPromise=fetch('/static/config/profile-categories.json',{cache:'no-store',credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(data=>{
    const list=Array.isArray(data?.categorias)?data.categorias:[];
    return [...new Set(list.map(x=>String(x||'').trim()).filter(Boolean))].length?[...new Set(list.map(x=>String(x||'').trim()).filter(Boolean))]:FALLBACK_CATEGORIES;
  }).catch(()=>FALLBACK_CATEGORIES);

  const categoryIcon=(name)=>({Música:'🎵',Celebridade:'⭐',Ator:'🎭',Atriz:'🎭',Influenciador:'🎤',Esporte:'🏆',Futebol:'⚽',Humor:'😂',Jornalismo:'📰',Streamer:'🎮','Empresa/Marca':'🏢','Criador de conteúdo':'📱',Outro:'📌'}[name]||'📌');
  const categoryLabel=(name)=>name?`${categoryIcon(name)} ${name}`:'👥 Todos os perfis';

  window.exploreView=async function(){
    const endpoint=state.session.autenticado?'/api/explore':'/api/public/explore';
    const categoria=String(state.exploreCategory||'').trim();
    const url=categoria?`${endpoint}?categoria=${encodeURIComponent(categoria)}`:endpoint;
    const [d,categories]=await Promise.all([api(url),categoriesPromise]);
    state.explore=d;
    const ranks=[['activity','🔥 Mais ativos','Perfis com maior quantidade de eventos e capturas','mais_ativos'],['growth','📈 Maior crescimento percentual','Quem mais cresceu proporcionalmente','maior_crescimento'],['absolute','🚀 Maior crescimento absoluto','Quem ganhou mais seguidores em quantidade','maior_crescimento_absoluto'],['followers','👥 Mais seguidores','Maior número atual de seguidores','mais_seguidores'],['content','🎬 Mais conteúdo','Maior volume de posts, reels e destaques','mais_conteudo'],['pace','⚡ Maior ritmo','Maior ritmo recente de crescimento','maior_ritmo'],['discoveries','🔎 Mais descobertas','Mais padrões e acontecimentos encontrados','mais_descobertas']];
    if(!ranks.some(r=>r[0]===state.exploreRank))state.exploreRank='activity';
    const selected=ranks.find(r=>r[0]===state.exploreRank)||ranks[0];
    const items=d[selected[3]]||[];
    const categoryOptions=[`<option value="">👥 Todos os perfis</option>`,...categories.map(name=>`<option value="${esc(name)}" ${name.toLowerCase()===categoria.toLowerCase()?'selected':''}>${esc(categoryLabel(name))}</option>`)].join('');
    const scopeLabel=categoria?`Categoria: ${categoria}`:'Todos os perfis';
    return layout('◈ EXPLORAR',state.session.autenticado?'Explore somente os perfis salvos na sua conta':'Descubra perfis, crescimento, atividade e rankings públicos',`${publicSearchBox()}<div class="stats explore-stats">${stat('👤 Perfis',d.total_perfis)}${stat('📸 Capturas',d.total_capturas)}${stat('📈 Eventos',d.total_eventos)}</div><div class="explore-intro card"><div><div class="eyebrow">RANKING DO MOMENTO</div><b>Veja quem mais se destaca</b><p class="muted">${state.session.autenticado?'Os cálculos usam exclusivamente os dados dos usuários salvos por você.':'Os rankings usam somente o histórico público já registrado.'}</p></div><button class="primary-btn" data-route="compare">⚖ Comparar perfis</button></div><div class="section-title ranking-selector-title"><div><b>🏆 Escolha o ranking</b><small>Um ranking por vez para manter a exploração rápida.</small></div></div><div class="ranking-selector card"><div class="ranking-filter-grid"><label for="ranking-select">Ranking exibido<select id="ranking-select" class="input">${ranks.map(r=>`<option value="${r[0]}" ${r[0]===state.exploreRank?'selected':''}>${r[1]}</option>`).join('')}</select></label><label for="ranking-category-select">Categoria<select id="ranking-category-select" class="input">${categoryOptions}</select></label></div><div class="ranking-filter-status"><span>${categoryIcon(categoria||'Outro')}</span><div><b>${esc(scopeLabel)}</b><small>${categoria?'Ranking filtrado por categoria':'Ranking geral com todos os perfis'}</small></div></div><div class="ranking-selected-info"><b>${selected[1]}</b><span>${selected[2]}</span></div></div>${exploreSection(selected[1],categoria?`${selected[2]} · ${categoria}`:selected[2],items,state.exploreRank)}<div class="notice public-disclaimer">${state.session.autenticado?'Nada desta tela usa dados públicos de outros clientes.':'Os rankings podem mudar quando novas capturas forem realizadas.'}</div>`
  };

  document.addEventListener('change',event=>{
    const target=event.target;
    if(target?.id==='ranking-select'){state.exploreRank=target.value;render();}
    if(target?.id==='ranking-category-select'){state.exploreCategory=target.value;render();}
  },true);
})();
