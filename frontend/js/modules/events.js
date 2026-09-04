function bindImages(){document.querySelectorAll('.profile-image').forEach(img=>{
  const selected=img.closest('.compare-selected-avatar');
  if(selected){
    const fallback=selected.querySelector('.avatar-fallback');
    const hasSrc=!!img.getAttribute('src');
    if(!hasSrc){img.style.display='none';if(fallback)fallback.style.display='grid';return}
    img.addEventListener('error',()=>{img.style.display='none';if(fallback)fallback.style.display='grid'},{once:true});
    img.addEventListener('load',()=>{img.style.display='block';if(fallback)fallback.style.display='none'},{once:true});
    return;
  }
  let wrap=img.closest('.avatar-wrap');
  if(!wrap){wrap=document.createElement('div');wrap.className='avatar-wrap';img.parentNode.insertBefore(wrap,img);wrap.appendChild(img);const fallback=document.createElement('div');fallback.className='avatar-fallback';fallback.textContent='◉';fallback.setAttribute('aria-hidden','true');wrap.appendChild(fallback)}
  if(!img.getAttribute('src')){wrap.classList.add('image-failed');return}
  img.addEventListener('error',()=>wrap.classList.add('image-failed'),{once:true});
  img.addEventListener('load',()=>wrap.classList.remove('image-failed'),{once:true});
})}
function resetViewState(){if(state.feedTimer){clearInterval(state.feedTimer);state.feedTimer=null}state.analysis=null;state.analysisError=null;state.summary=null;state.summaryPk=null;state.historyField=null;state.profiles=[];state.explore=null;state.compare=null;state.exploreRank='activity';state.feedFilter='todos'}
function startFeedAutoRefresh(){
  if(state.feedTimer){clearInterval(state.feedTimer);state.feedTimer=null}
  if(state.route!=='feed')return;
  if(state.pageConfig?.feed?.ativo===false)return;
  const segundos=Math.max(1,Number(state.pageConfig?.feed?.intervalo_segundos||2));
  state.feedTimer=setInterval(async()=>{
    if(document.hidden)return;
    try{
      const f=await api('/api/feed');
      const list=$('#feed-list');
      if(!list)return;
      list.innerHTML=f.map(feedRow).join('')||'<div class="empty">Nenhuma atividade registrada ainda.</div>';
      document.querySelectorAll('#feed-list .feed-row').forEach(row=>{
        const movimento=row.dataset.movimento==='true';
        row.style.display=state.feedFilter==='todos'?'flex':state.feedFilter==='movimento'?(movimento?'flex':'none'):(movimento?'none':'flex');
      });
      const last=$('#feed-last-refresh');if(last)last.textContent=`Última leitura: ${fmtDate(new Date())}`;
      bindImages();
    }catch(e){
      const last=$('#feed-last-refresh');
      if(last)last.textContent='Aguardando atualização…';
    }
  },segundos*1000);
}
function bind(){
  document.querySelectorAll('[data-route]').forEach(b=>b.onclick=e=>{
    e.preventDefault();
    const r=b.dataset.route;
    if(r==='compare'){state.compare=null;go('compare')}
    else if(r==='public-profile'){go('public-profile')}
    else{go(r)}
  });
  document.querySelectorAll('[data-back]').forEach(b=>b.onclick=()=>{
    state.route=b.dataset.back;
    if(state.route==='saved'){state.summary=null;state.summaryPk=null;state.historyField=null}
    go(state.route)
  });

  const input=$('#analysis-input'),btn=$('#analysis-btn');
  if(btn)btn.onclick=async()=>{
    try{
      const username=input.value.trim();
      if(!username){toast('Informe um usuário.');return}
      state.analysisError=null;state.analysis=null;
      btn.disabled=true;btn.textContent='CONSULTANDO...';
      const result=await api('/api/profile/analyze',{method:'POST',body:JSON.stringify({username})});
      if(!result||!result.perfil||!result.perfil.username)throw new Error('Não retornou dados suficientes para esse usuário.');
      state.analysis=result;
      state.profiles=await api('/api/profiles');
      render();
    }catch(e){
      state.analysis=null;state.analysisError=e.message||'Usuário não encontrado.';
      render();
    }finally{if(btn){btn.disabled=false;btn.textContent='ANALISAR'}}
  };
  const clear=$('#clear-analysis');
  if(clear)clear.onclick=()=>{state.analysis=null;state.analysisError=null;render()};
  const tryAgain=$('#analysis-try-again');
  if(tryAgain)tryAgain.onclick=()=>{state.analysis=null;state.analysisError=null;const input=$('#analysis-input');if(input){input.value='';input.focus()}render()};
  const save=$('#save-profile');
  if(save)save.onclick=async()=>{
    try{await api('/api/profile/save',{method:'POST',body:JSON.stringify({dados:state.analysis})});state.profiles=await api('/api/profiles');toast('Usuário salvo na sua conta.');render()}
    catch(e){toast(e.message)}
  };

  document.querySelectorAll('[data-summary]').forEach(b=>b.onclick=()=>{state.summaryPk=b.dataset.summary;state.route='summary';render()});
  document.querySelectorAll('[data-history]').forEach(b=>b.onclick=()=>{state.historyField=b.dataset.history;state.route='history';render()});
  const tl=$('#open-timeline');if(tl)tl.onclick=()=>{state.route='timeline';render()};
  document.querySelectorAll('[data-monitor]').forEach(b=>b.onclick=async()=>{
    try{await api(`/api/profiles/${encodeURIComponent(b.dataset.monitor)}/monitor`,{method:'POST',body:JSON.stringify({monitorando:b.dataset.enabled==='true'})});toast('Monitoramento atualizado.');render()}
    catch(e){toast(e.message)}
  });
  document.querySelectorAll('[data-remove]').forEach(b=>b.onclick=async()=>{
    if(!confirm(`Remover @${b.dataset.remove}?`))return;
    try{await api(`/api/profiles/${encodeURIComponent(b.dataset.remove)}`,{method:'DELETE'});state.profiles=await api('/api/profiles');toast('Usuário removido.');render()}
    catch(e){toast(e.message)}
  });

  const search=$('#profile-search');
  if(search)search.oninput=()=>{const q=search.value.toLowerCase();document.querySelectorAll('.profile-card').forEach(e=>e.style.display=e.dataset.username.toLowerCase().includes(q)?'grid':'none')};

  const ps=$('#public-search-input'),pb=$('#public-search-btn');
  if(pb)pb.onclick=()=>publicSearch();
  if(ps){let timer;ps.oninput=()=>{clearTimeout(timer);timer=setTimeout(()=>publicSearch(ps.value),250)};ps.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();publicSearch(ps.value)}}}

  bindPublicCards();

  document.querySelectorAll('[data-compare-from]').forEach(b=>b.onclick=()=>{
    state.compare={a:b.dataset.compareFrom||'',b:''};go('compare')
  });
  document.querySelectorAll('[data-login]').forEach(b=>b.onclick=openAuth);

  document.querySelectorAll('[data-feed-filter]').forEach(b=>b.onclick=()=>{
    const filter=b.dataset.feedFilter;state.feedFilter=filter;
    document.querySelectorAll('#feed-list .feed-row').forEach(row=>{
      const movimento=row.dataset.movimento==='true';
      row.style.display=filter==='todos'?'flex':filter==='movimento'?(movimento?'flex':'none'):(movimento?'none':'flex')
    });
    document.querySelectorAll('[data-feed-filter]').forEach(x=>x.classList.toggle('active-filter',x.dataset.feedFilter===filter));
  });

  const ranking=$('#ranking-select');
  if(ranking)ranking.onchange=()=>{state.exploreRank=ranking.value;render()};

  document.querySelectorAll('[data-compare-toggle]').forEach(button=>button.onclick=e=>{
    e.preventDefault();
    const side=button.dataset.compareToggle;
    const menu=$(`#compare-menu-${side}`);
    if(!menu)return;
    const willOpen=!menu.classList.contains('open');
    document.querySelectorAll('.compare-select-menu.open').forEach(x=>x.classList.remove('open'));
    document.querySelectorAll('[data-compare-toggle]').forEach(x=>x.setAttribute('aria-expanded','false'));
    if(willOpen){menu.classList.add('open');button.setAttribute('aria-expanded','true')}
  });
  document.querySelectorAll('[data-compare-option]').forEach(option=>option.onclick=()=>{
    const side=option.dataset.compareOption,user=option.dataset.compareUser;
    const current=state.compare||{};
    state.compare={...current,[side]:user,data:null};
    render();
  });
  const compareSwap=$('#compare-swap');
  if(compareSwap)compareSwap.onclick=()=>{
    const current=state.compare||{};
    const a=current.a,b=current.b;
    state.compare={...current,a:b,b:a,data:null};
    render();
  };
  const compareBtn=$('#compare-btn');
  if(compareBtn)compareBtn.onclick=async()=>{
    const a=String(state.compare?.a||'').trim().replace(/^@/,'');
    const b=String(state.compare?.b||'').trim().replace(/^@/,'');
    if(!a||!b){toast('Escolha os dois perfis.');return}
    if(a.toLowerCase()===b.toLowerCase()){toast('Escolha dois perfis diferentes.');return}
    try{
      compareBtn.disabled=true;compareBtn.textContent='COMPARANDO...';
      const endpoint=state.session?.autenticado?'/api/compare':'/api/public/compare';
      const url=state.session?.autenticado
        ?`${endpoint}?username_a=${encodeURIComponent(a)}&username_b=${encodeURIComponent(b)}`
        :`${endpoint}?username_a=${encodeURIComponent(a)}&username_b=${encodeURIComponent(b)}`;
      state.compare={a,b,data:await api(url)};
      history.replaceState({},'',`/comparar?a=${encodeURIComponent(a)}&b=${encodeURIComponent(b)}`);
      render();
    }catch(e){toast(e.message)}
    finally{compareBtn.disabled=false;compareBtn.textContent='⚡ COMPARAR AGORA'}
  };
  const mobileMenu=$('#mobile-menu-toggle');if(mobileMenu)mobileMenu.onclick=()=>{const open=document.body.classList.toggle('mobile-nav-open');mobileMenu.setAttribute('aria-expanded',open?'true':'false')};
  document.querySelectorAll('#main-nav button').forEach(b=>b.addEventListener('click',()=>{document.body.classList.remove('mobile-nav-open');if(mobileMenu)mobileMenu.setAttribute('aria-expanded','false')}));
  startFeedAutoRefresh();
}

window.addEventListener('popstate',()=>{detectRoute();render()});
$('#theme-toggle').onclick=()=>{state.theme=state.theme==='dark'?'light':'dark';applyTheme()};
$('#auth-btn').onclick=async()=>{if(state.session?.autenticado){await api('/api/auth/logout',{method:'POST'});state.session=await api('/api/session');resetViewState();history.pushState({},'', '/');state.route='dashboard';toast('Sessão encerrada.');render()}else openAuth()};
boot();