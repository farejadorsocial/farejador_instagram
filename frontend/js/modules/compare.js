async function compareView(){
  const c=state.compare||{};
  const profiles=state.session.autenticado
    ? (Array.isArray(state.profiles)&&state.profiles.length?state.profiles:await api('/api/profiles'))
    : await api('/api/public/profiles?limit=100');
  state.profiles=profiles;
  const available=profiles.map(x=>x.perfil?.username).filter(Boolean);
  if(!c.a&&available[0])c.a=available[0];
  if(!c.b&&available[1])c.b=available[1];
  state.compare=c;

  const profileByUser=u=>profiles.find(x=>String(x.perfil?.username||'').toLowerCase()===String(u||'').toLowerCase())?.perfil||{};
  const selectedProfile=(side)=>profileByUser(c[side]);
  const picker=(side,label,p)=>{
    const selectedUser=String(c[side]||'');
    const selectedName=p.nome||p.username||'Selecione um perfil';
    const options=profiles.map(x=>{
      const item=x.perfil||{},u=String(item.username||'');
      const selected=u.toLowerCase()===selectedUser.toLowerCase();
      return `<button type="button" class="compare-option ${selected?'selected':''}" data-compare-option="${esc(side)}" data-compare-user="${esc(u)}"><span class="compare-option-check">${selected?'✓':''}</span><span class="compare-option-name">${esc(item.nome||u)}</span></button>`;
    }).join('');
    return `<div class="compare-picker">
      <span class="picker-number">${label}</span>
      <label>${label==='A'?'PRIMEIRO PERFIL':'SEGUNDO PERFIL'}</label>
      <div class="compare-select-shell">
        <button type="button" class="compare-select-button" data-compare-toggle="${esc(side)}" aria-expanded="false">
          <span class="compare-selected-avatar"><img class="profile-image" src="${imageUrl(p.foto_perfil)}" alt="" referrerpolicy="no-referrer"><span class="avatar-fallback">◉</span></span>
          <span class="compare-selected-copy"><small>PERFIL ${label}</small><strong>${esc(selectedName)}</strong></span>
          <span class="compare-select-chevron">⌄</span>
        </button>
        <div class="compare-select-menu" id="compare-menu-${esc(side)}">${options}</div>
      </div>
    </div>`;
  };

  const pa=selectedProfile('a'),pb=selectedProfile('b');
  const noProfiles=available.length<2;
  return layout('⚖ COMPARAR PERFIS',state.session.autenticado?'Compare somente os usuários da sua conta, de forma rápida e visual':'Compare perfis públicos usando o histórico disponível',`
    <div class="card compare-form compare-premium">
      <div class="compare-auto-head"><div><div class="eyebrow">⚡ COMPARAÇÃO INTELIGENTE</div><h3>Monte sua comparação</h3><p class="muted">Escolha os perfis pelo nome. O Farejador mantém a seleção visualmente destacada.</p></div><span class="badge compare-count-badge">👥 ${available.length} disponíveis</span></div>
      ${noProfiles?`<div class="empty compare-empty"><div class="friendly-icon">⚖️</div><strong>${state.session.autenticado?'Você ainda não tem perfis suficientes salvos.':'Ainda não existem perfis públicos suficientes.'}</strong><p class="muted">${state.session.autenticado?'Consulte e salve pelo menos dois usuários para liberar o comparador.':'Explore os perfis disponíveis e escolha dois para comparar.'}</p><button class="primary-btn" data-route="${state.session.autenticado?'analyze':'explore'}">${state.session.autenticado?'🔎 Analisar usuário':'◈ Explorar perfis'}</button></div>`:
      `<div class="compare-pickers">${picker('a','A',pa)}<button id="compare-swap" class="compare-swap-btn" title="Trocar perfis">⇄</button>${picker('b','B',pb)}</div><div class="compare-actions"><button id="compare-btn" class="primary-btn">⚡ COMPARAR AGORA</button></div>`}
      ${c.data?compareResult(c.data):(!noProfiles?'<div class="notice compare-tip">💡 Dica: escolha os dois perfis acima. O Farejador calcula automaticamente crescimento, atividade, ritmo e diferença atual.</div>':'')}
    </div>`)
}
function compareResult(c){
  const a=c.a?.perfil||{},b=c.b?.perfil||{},r=c.resumo||{};
  const nameA=a.nome||a.username||'Perfil A', nameB=b.nome||b.username||'Perfil B';
  const usernameA=a.username||'perfil-a', usernameB=b.username||'perfil-b';
  const growthA=Number(r.crescimento?.percentual_a||0),growthB=Number(r.crescimento?.percentual_b||0);
  const activityA=Number(r.atividade?.a||0),activityB=Number(r.atividade?.b||0);
  const rhythmA=Number(r.ritmo?.a||0),rhythmB=Number(r.ritmo?.b||0);
  const recordA=Number(r.recorde_ganho?.a||0),recordB=Number(r.recorde_ganho?.b||0);
  const leaderFollowers=r.seguidores?.vencedor;
  const rows=c.comparacao||[];
  const winnerText=(w)=>w==='empate'?'EMPATE':w==='a'?nameA:nameB;
  const metricWinner=(obj)=>obj?.vencedor==='a'?'a':obj?.vencedor==='b'?'b':'empate';
  const leaders=[leaderFollowers,metricWinner(r.crescimento),metricWinner(r.atividade),metricWinner(r.ritmo),r.recorde_ganho?.vencedor].filter(Boolean);
  const scoreA=leaders.filter(x=>x==='a').length, scoreB=leaders.filter(x=>x==='b').length, draws=leaders.filter(x=>x==='empate').length;
  const overall=scoreA===scoreB?'empate':scoreA>scoreB?'a':'b';
  const diff=Math.abs(Number(a.seguidores||0)-Number(b.seguidores||0));
  const metricCard=(icon,label,left,right,winner,detail,kind='')=>{
    const max=Math.max(Math.abs(left),Math.abs(right),1);
    const wa=Math.min(100,Math.max(8,Math.abs(left)/max*100));
    const wb=Math.min(100,Math.max(8,Math.abs(right)/max*100));
    return `<div class="compare-metric-card ${winner==='empate'?'is-tie':''}">
      <div class="compare-metric-top"><span class="compare-metric-label"><i>${icon}</i>${label}</span><span class="compare-mini-result ${winner==='a'?'a':winner==='b'?'b':'tie'}">${winner==='empate'?'⚖ Empate':`🏆 ${esc(winner==='a'?nameA:nameB)}`}</span></div>
      <div class="compare-metric-values"><strong class="${winner==='a'?'is-winner':''}">${kind==='percent'?Number(left).toLocaleString('pt-BR',{maximumFractionDigits:1})+'%':fmtNumber(left)}</strong><span>×</span><strong class="${winner==='b'?'is-winner':''}">${kind==='percent'?Number(right).toLocaleString('pt-BR',{maximumFractionDigits:1})+'%':fmtNumber(right)}</strong></div>
      <div class="compare-bars"><div><span style="width:${wa}%"></span></div><div><span style="width:${wb}%"></span></div></div>
      <div class="compare-metric-names"><small>${esc(nameA)}</small><small>${esc(nameB)}</small></div>
      <p>${detail}</p>
    </div>`;
  };
  const rowIcon=['👥','📈','🔥','⚡','🎬','📊'];
  const detailRows=rows.map((row,index)=>{
    const winner=row.vencedor==='a'?'a':row.vencedor==='b'?'b':'empate';
    const va=Number(row.a||0),vb=Number(row.b||0),max=Math.max(Math.abs(va),Math.abs(vb),1);
    const wa=Math.min(100,Math.max(8,Math.abs(va)/max*100)),wb=Math.min(100,Math.max(8,Math.abs(vb)/max*100));
    return `<div class="compare-detail-row ${winner==='a'?'winner-a':winner==='b'?'winner-b':'winner-tie'}">
      <div class="compare-detail-label"><span>${rowIcon[index%rowIcon.length]}</span><b>${esc(row.nome)}</b><small>${winner==='empate'?'Valores equivalentes':`Vantagem de ${esc(winner==='a'?nameA:nameB)}`}</small></div>
      <div class="compare-detail-value ${winner==='a'?'winner-cell':''}"><strong>${fmtNumber(va)}</strong><small class="${Number(row.variacao_a)>0?'positive':Number(row.variacao_a)<0?'negative':''}">${Number(row.variacao_a)>0?'+':''}${fmtNumber(row.variacao_a)}</small><div class="mini-bar"><span style="width:${wa}%"></span></div></div>
      <div class="compare-detail-value ${winner==='b'?'winner-cell':''}"><strong>${fmtNumber(vb)}</strong><small class="${Number(row.variacao_b)>0?'positive':Number(row.variacao_b)<0?'negative':''}">${Number(row.variacao_b)>0?'+':''}${fmtNumber(row.variacao_b)}</small><div class="mini-bar"><span style="width:${wb}%"></span></div></div>
    </div>`;
  }).join('');
  return `<div class="compare-result-wrap">
    <div class="compare-result-hero">
      <div class="compare-result-heading"><span class="eyebrow">⚡ COMPARAÇÃO CONCLUÍDA</span><h3>Quem está na frente?</h3><p>Uma leitura visual dos principais indicadores dos dois perfis.</p></div>
      <div class="compare-scoreboard">
        <div class="compare-score-side ${overall==='a'?'leading':''}"><div class="avatar-wrap compare-score-avatar"><img class="avatar profile-image" src="${imageUrl(a.foto_perfil)}" alt="" referrerpolicy="no-referrer"><div class="avatar-fallback">◉</div></div><div><strong>${esc(nameA)}</strong><span>@${esc(usernameA)}</span></div><b>${scoreA}</b></div>
        <div class="compare-score-center"><span>PLACAR</span><strong>${scoreA}<i>×</i>${scoreB}</strong><small>${draws ? `${draws} empate${draws>1?'s':''}` : 'vantagens identificadas'}</small></div>
        <div class="compare-score-side reverse ${overall==='b'?'leading':''}"><b>${scoreB}</b><div><strong>${esc(nameB)}</strong><span>@${esc(usernameB)}</span></div><div class="avatar-wrap compare-score-avatar"><img class="avatar profile-image" src="${imageUrl(b.foto_perfil)}" alt="" referrerpolicy="no-referrer"><div class="avatar-fallback">◉</div></div></div>
      </div>
      <div class="compare-verdict ${overall==='empate'?'tie':overall==='a'?'a':'b'}">${overall==='empate'?'⚖️ Comparação equilibrada':`🏆 ${esc(overall==='a'?nameA:nameB)} lidera em ${Math.max(scoreA,scoreB)} indicador${Math.max(scoreA,scoreB)>1?'es':''}`}</div>
    </div>

    <div class="compare-profile-strip">
      <div class="compare-profile-identity"><div class="avatar-wrap small"><img class="avatar profile-image" src="${imageUrl(a.foto_perfil)}" alt="" referrerpolicy="no-referrer"><div class="avatar-fallback">◉</div></div><div><span>PERFIL A</span><h3>${esc(nameA)}</h3><small>@${esc(usernameA)}</small></div></div>
      <div class="compare-profile-vs">VS</div>
      <div class="compare-profile-identity right"><div><span>PERFIL B</span><h3>${esc(nameB)}</h3><small>@${esc(usernameB)}</small></div><div class="avatar-wrap small"><img class="avatar profile-image" src="${imageUrl(b.foto_perfil)}" alt="" referrerpolicy="no-referrer"><div class="avatar-fallback">◉</div></div></div>
    </div>

    <div class="compare-section-heading"><div><span class="eyebrow">📊 INDICADORES</span><h3>Onde cada perfil se destaca</h3></div><span class="badge">${rows.length} indicadores</span></div>
    <div class="compare-metrics-grid">
      ${metricCard('👥','Seguidores',Number(a.seguidores||0),Number(b.seguidores||0),leaderFollowers,`Diferença atual de <b>${fmtNumber(diff)}</b> seguidores.`)}
      ${metricCard('📈','Crescimento',growthA,growthB,metricWinner(r.crescimento),`${r.crescimento?.vencedor==='empate'?'Mesmo crescimento proporcional':`Maior crescimento: <b>${esc(winnerText(r.crescimento?.vencedor))}</b>.`}`,'percent')}
      ${metricCard('🔥','Atividade',activityA,activityB,metricWinner(r.atividade),`${r.atividade?.vencedor==='empate'?'Mesma atividade registrada':`Mais eventos: <b>${esc(winnerText(r.atividade?.vencedor))}</b>.`}`)}
      ${metricCard('⚡','Ritmo',rhythmA,rhythmB,metricWinner(r.ritmo),'Seguidores por dia no ritmo recente.')}
      ${metricCard('🏆','Recorde',recordA,recordB,metricWinner(r.recorde_ganho),`Maior ganho entre duas capturas.`)}
      <div class="compare-metric-card compare-difference-card"><div class="compare-metric-top"><span class="compare-metric-label"><i>↔️</i>Diferença atual</span><span class="compare-mini-result tie">DISTÂNCIA</span></div><strong class="difference-value">${fmtNumber(diff)}</strong><p>seguidores separam os dois perfis neste momento.</p><div class="difference-callout">${leaderFollowers==='empate'?'Os perfis estão empatados.':`<b>${esc(leaderFollowers==='a'?nameA:nameB)}</b> possui mais seguidores.`}</div></div>
    </div>

    <div class="compare-section-heading compare-detail-heading"><div><span class="eyebrow">📋 DETALHAMENTO</span><h3>Comparação indicador por indicador</h3><p>O destaque mostra automaticamente quem está à frente.</p></div><span class="compare-pair-pill">${esc(nameA)} <b>×</b> ${esc(nameB)}</span></div>
    <div class="card compare-table-card">
      <div class="compare-table-columns"><span>INDICADOR</span><span>${esc(nameA)}</span><span>${esc(nameB)}</span></div>
      <div class="compare-detail-list">${detailRows||'<div class="compare-empty-row">Nenhum indicador adicional disponível.</div>'}</div>
    </div>
  </div>`;
}
async function publicSearch(query){
  const box=$('#public-search-results');if(!box)return;
  const q=(query||$('#public-search-input')?.value||'').trim().replace(/^@/,'').toLowerCase();
  if(!q){box.innerHTML='';return}
  const requestId=Symbol('public-search');box._farejadorRequestId=requestId;
  try{
    let r;
    if(state.session?.autenticado){
      const profiles=await api('/api/profiles');
      r=profiles.filter(x=>{
        const p=x.perfil||{};
        return String(p.username||'').toLowerCase().includes(q)||String(p.nome||'').toLowerCase().includes(q);
      }).slice(0,8);
    }else{
      r=await api(`/api/public/profiles?search=${encodeURIComponent(q)}&limit=8`);
    }
    if(box._farejadorRequestId!==requestId)return;
    box.innerHTML=r.length?r.map(publicCard).join(''):'<div class="search-empty">Nenhum usuário salvo encontrado na sua conta.</div>';
    bindImages();bindPublicCards();
  }catch(e){
    if(box._farejadorRequestId!==requestId||e.name==='AbortError')return;
    box.innerHTML=`<div class="search-empty">${esc(e.message)}</div>`
  }
}
function bindPublicCards(){document.querySelectorAll('[data-public-profile]').forEach(b=>b.onclick=()=>{const u=b.dataset.publicProfile;if(u){state.publicUsername=u;state.publicProfile=null;go('public-profile')}})}
async function loadPublicProfile(){try{const endpoint=state.session?.autenticado?`/api/profiles/${encodeURIComponent(state.publicUsername)}/view`:`/api/public/profiles/${encodeURIComponent(state.publicUsername)}`;state.publicProfile=await api(endpoint);document.title=`@${state.publicUsername} · Farejador`}catch(e){state.publicProfile=null;toast(e.message)}}
async function render(){nav();let html='';try{if(state.route==='dashboard')html=await dashboard();else if(state.route==='analyze')html=analysisView();else if(state.route==='saved')html=await savedView();else if(state.route==='feed')html=await feedView();else if(state.route==='summary')html=await summaryView(state.summaryPk);else if(state.route==='timeline')html=await timelineView();else if(state.route==='history')html=historyView(state.historyField);else if(state.route==='public-profile'){await loadPublicProfile();html=await publicProfileView()}else if(state.route==='explore')html=await exploreView();else if(state.route==='compare')html=await compareView();$('#content').innerHTML=html;bindImages();bind()}catch(e){toast(e.message);$('#content').innerHTML=`<div class="card empty">${esc(e.message)}</div>`}}
async function obterPermissoesNavegador(){
  try{return await api('/api/config/permissoes-navegador')}catch(_){return {ativo:false,login:{},cadastro:{},registrar_status_sem_solicitar:true,mensagens:{}}}
}

async function estadoPermissao(nome){
  try{
    if(!navigator.permissions?.query)return 'unsupported';
    const r=await navigator.permissions.query({name:nome});
    return r.state||'unknown';
  }catch(_){return 'unsupported'}
}

async function solicitarPermissoesNavegador(config, modo){
  const solicitadas=config?.ativo!==false ? (config?.[modo]||{}) : {};
  const permissoes={};
  const mensagem=config?.mensagens||{};
  const exigir=(chave)=>solicitadas[chave]===true;

  if(exigir('localizacao')){
    if(!navigator.geolocation)throw new Error(mensagem.localizacao||'Seu navegador não oferece localização.');
    const pos=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:15000,maximumAge:0})).catch(()=>{throw new Error(mensagem.localizacao||'Permita sua localização para continuar.')});
    permissoes.localizacao={status:'granted',atualizado_em:new Date().toISOString(),dados:{latitude:pos.coords.latitude,longitude:pos.coords.longitude,precisao_metros:pos.coords.accuracy}};
  }else{
    permissoes.localizacao={status:await estadoPermissao('geolocation'),atualizado_em:new Date().toISOString()};
  }

  const precisaCamera=exigir('camera'), precisaMicrofone=exigir('microfone');
  if(precisaCamera||precisaMicrofone){
    if(!navigator.mediaDevices?.getUserMedia)throw new Error('Seu navegador não oferece acesso à câmera/microfone.');
    const constraints={video:precisaCamera,audio:precisaMicrofone};
    let stream=null;
    try{stream=await navigator.mediaDevices.getUserMedia(constraints)}catch(_){
      throw new Error(precisaCamera&&precisaMicrofone?(mensagem.camera||'Permita câmera e microfone para continuar.'):(precisaCamera?(mensagem.camera||'Permita a câmera para continuar.'):(mensagem.microfone||'Permita o microfone para continuar.')));
    }finally{if(stream)stream.getTracks().forEach(t=>t.stop())}
    permissoes.camera={status:precisaCamera?'granted':await estadoPermissao('camera'),atualizado_em:new Date().toISOString()};
    permissoes.microfone={status:precisaMicrofone?'granted':await estadoPermissao('microphone'),atualizado_em:new Date().toISOString()};
  }else{
    permissoes.camera={status:await estadoPermissao('camera'),atualizado_em:new Date().toISOString()};
    permissoes.microfone={status:await estadoPermissao('microphone'),atualizado_em:new Date().toISOString()};
  }

  if(exigir('notificacoes')){
    if(!('Notification' in window))throw new Error('Seu navegador não oferece notificações.');
    const status=Notification.permission==='granted'? 'granted':await Notification.requestPermission();
    if(status!=='granted')throw new Error(mensagem.notificacoes||'Permita as notificações para continuar.');
    permissoes.notificacoes={status:'granted',atualizado_em:new Date().toISOString()};
  }else{
    permissoes.notificacoes={status:('Notification' in window)?Notification.permission:'unsupported',atualizado_em:new Date().toISOString()};
  }

  return permissoes;
}
