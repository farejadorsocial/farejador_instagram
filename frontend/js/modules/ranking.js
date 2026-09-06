(function(){
  const FALLBACK_CATEGORIES=['Influenciador','Música','Ator','Atriz','Esporte','Futebol','Atleta','Política','TV','Humor','Jornalismo','Criador de conteúdo','Streamer','Outro'];
  const categoriesPromise=fetch('/static/config/profile-categories.json',{cache:'no-store',credentials:'same-origin'}).then(r=>r.ok?r.json():null).then(data=>{const list=Array.isArray(data?.categorias)?data.categorias:[];const valid=[...new Set(list.map(x=>String(x||'').trim()).filter(Boolean))];return valid.length?valid:FALLBACK_CATEGORIES}).catch(()=>FALLBACK_CATEGORIES);
  const categoryIcon=name=>({Música:'🎵',Ator:'🎭',Atriz:'🎭',Influenciador:'🎤',Esporte:'🏆',Futebol:'⚽',Atleta:'🏅',Política:'🏛️',TV:'📺',Humor:'😂',Jornalismo:'📰',Streamer:'🎮','Criador de conteúdo':'📱',Outro:'📌'}[name]||'📌');

  window.rankingView=async function(){
    const endpoint=state.session.autenticado?'/api/explore':'/api/public/explore';
    const categoria=String(state.rankingCategory||'').trim();
    const url=categoria?`${endpoint}?categoria=${encodeURIComponent(categoria)}`:endpoint;
    const [d,categories]=await Promise.all([api(url),categoriesPromise]);
    state.ranking=d;
    const categoryOptions=[...categories.map(name=>`<option value="${esc(name)}" ${name.toLowerCase()===categoria.toLowerCase()?'selected':''}>${esc(`${categoryIcon(name)} ${name}`)}</option>`)].join('');
    const scope=categoria?`${categoryIcon(categoria)} ${categoria}`:'Escolha uma categoria';
    const categoryTiles=categories.map(name=>{
      const selected=name.toLowerCase()===categoria.toLowerCase();
      return `<button type="button" class="ranking-category-tile ${selected?'selected':''}" data-ranking-category="${esc(name)}"><span class="ranking-category-icon">${categoryIcon(name)}</span><span class="ranking-category-name">${esc(name)}</span><span class="ranking-category-action">Ver ranking <b>→</b></span></button>`;
    }).join('');

    return layout('🏆 RANKING','Descubra os perfis que mais se destacam em cada categoria',`
      <section class="ranking-page-head">
        <div class="ranking-page-heading">
          <div class="eyebrow">RANKING POR CATEGORIA</div>
          <h2>${esc(scope)}</h2>
          <p>${state.session.autenticado?'Compare somente os perfis salvos na sua conta.':'Compare somente os perfis disponíveis na área pública.'}</p>
        </div>
        <label class="ranking-category-select" for="ranking-page-category">
          <span>Categoria</span>
          <select id="ranking-page-category" class="input"><option value="">Todas as categorias</option>${categoryOptions}</select>
        </label>
      </section>

      <section class="ranking-category-panel">
        <div class="ranking-panel-heading">
          <div><b>Categorias</b><small>Selecione uma categoria para abrir o ranking</small></div>
          <span>${categories.length} categorias</span>
        </div>
        <div class="ranking-category-grid">${categoryTiles}</div>
      </section>

      ${categoria?`
        <section class="ranking-results-panel">
          <div class="ranking-results-heading">
            <div>
              <span class="ranking-results-kicker">RANKING SELECIONADO</span>
              <h3>${categoryIcon(categoria)} ${esc(categoria)}</h3>
              <small>Perfis ordenados pelos dados de destaque disponíveis.</small>
            </div>
            <span class="ranking-results-count">${fmtNumber(d.total_perfis)} perfis</span>
          </div>
          <div class="category-ranking-list">${renderCategoryProfiles(d)}</div>
        </section>
      `:'
        <section class="ranking-category-empty">
          <div class="ranking-empty-icon">🏆</div>
          <div><b>Escolha uma categoria</b><small>Use os cartões acima para visualizar o ranking de Influenciador, Atleta, Política, TV, Esporte e das demais categorias.</small></div>
        </section>
      '}

      <div class="notice public-disclaimer">${state.session.autenticado?'Os dados desta página pertencem somente à sua conta.':'Os dados desta página são somente da área pública.'}</div>
    `);
  };

  function renderCategoryProfiles(data){
    const candidates=data.mais_seguidores||data.mais_ativos||data.maior_crescimento||[];
    if(!candidates.length)return '<div class="ranking-no-results">Ainda não há dados suficientes para formar este ranking.</div>';
    return candidates.map((x,i)=>{
      const p=x.perfil||{};
      return `<button type="button" class="category-ranking-card" data-public-profile="${esc(p.username||'')}">
        <span class="category-ranking-position">${String(i+1).padStart(2,'0')}</span>
        <div class="avatar-wrap small ranking-result-avatar"><img class="avatar profile-image" src="${imageUrl(p.foto_perfil)}" alt="Foto de ${esc(p.nome||p.username||'perfil')}" referrerpolicy="no-referrer"><div class="avatar-fallback" aria-hidden="true">◉</div></div>
        <div class="public-profile-info">
          <div class="profile-name">${esc(p.nome||p.username||'Perfil')}</div>
          <div class="profile-meta">@${esc(p.username||'')}</div>
          <div class="profile-stats"><span>👥 ${fmtNumber(p.seguidores)}</span><span class="ranking-growth">📈 ${x.crescimento>0?'+':''}${fmtNumber(x.crescimento)}</span></div>
        </div>
        <div class="category-ranking-score"><strong>${fmtNumber(p.seguidores)}</strong><span>seguidores</span></div>
        <span class="category-ranking-arrow">→</span>
      </button>`;
    }).join('');
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
