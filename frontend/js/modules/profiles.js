function profileCard(x){const p=x.perfil||{},m=x.monitoramento||{};return `<div class="card profile-card ${m.monitorando?'is-active':'is-paused'}" data-username="${esc(p.username)}"><div class="avatar-wrap"><img class="avatar profile-image" src="${imageUrl(p.foto_perfil)}" alt="Foto de ${esc(p.nome||p.username||'perfil')}" referrerpolicy="no-referrer"><div class="avatar-fallback" aria-hidden="true">◉</div></div><div><div><span class="profile-name">${esc(p.nome||p.username)}</span> <span class="badge ${m.monitorando?'good':''}">${m.monitorando?'🟢 ATIVO':'⚪ PAUSADO'}</span></div><div class="profile-meta">@${esc(p.username)} · ${p.privado?'🔒 Conta privada':'🌐 Conta pública'}</div><div class="profile-stats"><span>👥 ${fmtNumber(p.seguidores)} seguidores</span><span>➜ ${fmtNumber(p.seguindo)} seguindo</span><span>Posts ${fmtNumber(p.total_posts)}</span><span>Reels ${fmtNumber(p.total_reels)}</span></div><div class="profile-meta">${esc(p.biografia||'')}</div></div><div class="actions"><button class="ghost-btn" data-summary="${esc(p.pk)}">📊 Resumo</button><button class="ghost-btn" data-monitor="${esc(p.username)}" data-enabled="${m.monitorando?'false':'true'}">${m.monitorando?'⏸ Parar':'▶ Monitorar'}</button><button class="danger-btn" data-remove="${esc(p.username)}">🗑 Remover</button></div></div>`}
async function feedView(){
  const f=await api('/api/feed');
  state.feedFilter=state.feedFilter||'todos';
  const segundos=Number(state.pageConfig?.feed?.intervalo_segundos||2);
  return layout('📡 FEED DE MONITORAMENTO',state.session.autenticado?'Atividade dos seus perfis, atualizada continuamente':'Atividade pública registrada pelo Farejador',`
    <div class="feed-live-hero card"><div><div class="eyebrow">● LIVE MONITOR</div><h2>Central de atividades</h2><p class="muted">Cada captura chega pelo feed correspondente ao cliente. Movimentos recebem destaque imediatamente.</p></div><div class="live-pill"><i></i> AO VIVO</div></div>
    <div class="card feed-toolbar"><div class="tabs"><button class="ghost-btn ${state.feedFilter==='todos'?'active-filter':''}" data-feed-filter="todos">TODOS</button><button class="ghost-btn ${state.feedFilter==='movimento'?'active-filter':''}" data-feed-filter="movimento">⚡ MOVIMENTOS</button><button class="ghost-btn ${state.feedFilter==='normal'?'active-filter':''}" data-feed-filter="normal">CAPTURAS</button></div></div>
    <div id="feed-list" class="card feed">${f.map(feedRow).join('')||'<div class="empty">Nenhuma atividade registrada ainda.</div>'}</div>
    <div class="feed-footer"><span>📡 Atualização automática a cada ${segundos}s</span><span id="feed-last-refresh">Última leitura: ${fmtDate(new Date())}</span></div>`)
}

function renderAdvancedLineChart(points, options={}){
  const valid=(Array.isArray(points)?points:[]).map(v=>({
    timestamp:v?.timestamp,
    value:Number(v?.value)
  })).filter(v=>Number.isFinite(v.value));
  if(!valid.length)return '<div class="chart-empty"><span>◌</span><b>Ainda não há dados suficientes</b><small>Novas capturas aparecerão aqui automaticamente.</small></div>';

  const values=valid.map(v=>v.value);
  const min=Math.min(...values),max=Math.max(...values),range=max-min||1;
  const width=Math.max(620, Math.max(1,valid.length-1)*78+36);
  const height=250,padX=18,top=24,bottom=38;
  const plotH=height-top-bottom;
  const step=valid.length===1?0:(width-padX*2)/(valid.length-1);
  const pointsXY=valid.map((v,i)=>{
    const x=valid.length===1?width/2:padX+i*step;
    const y=top+((max-v.value)/range)*plotH;
    return {...v,x,y};
  });
  const linePath=pointsXY.map((p,i)=>`${i?'L':'M'} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ');
  const areaPath=`M ${pointsXY[0].x.toFixed(2)} ${height-bottom} ${pointsXY.map(p=>`L ${p.x.toFixed(2)} ${p.y.toFixed(2)}`).join(' ')} L ${pointsXY[pointsXY.length-1].x.toFixed(2)} ${height-bottom} Z`;
  const labelEvery=Math.max(1,Math.ceil(valid.length/8));
  const labels=pointsXY.map((p,i)=>{
    const show=i===0||i===valid.length-1||i%labelEvery===0;
    if(!show)return '';
    const time=fmtTime(p.timestamp);
    return `<g class="chart-x-label"><text x="${p.x.toFixed(2)}" y="${height-9}" text-anchor="middle">${esc(time)}</text></g>`;
  }).join('');
  const dots=pointsXY.map((p,i)=>{
    const maxIndex=values.indexOf(max);
    const minIndex=values.indexOf(min);
    const showValue=valid.length<=6||i===0||i===valid.length-1||i===maxIndex||i===minIndex;
    const title=`${fmtDate(p.timestamp)} · ${fmtNumber(p.value)}${options.intervalLabel?.[i]?` · ${formatDurationSeconds(options.intervalLabel[i])} desde a captura anterior`:''}`;
    return `<g class="chart-point-group"><title>${esc(title)}</title><circle class="chart-hit" cx="${p.x.toFixed(2)}" cy="${p.y.toFixed(2)}" r="10"></circle><circle class="chart-dot" cx="${p.x.toFixed(2)}" cy="${p.y.toFixed(2)}" r="4"></circle>${showValue?`<text class="chart-value" x="${p.x.toFixed(2)}" y="${Math.max(13,p.y-11).toFixed(2)}" text-anchor="middle">${esc(fmtNumber(p.value))}</text>`:''}</g>`;
  }).join('');
  const mid=Math.round((max+min)/2);
  return `<div class="advanced-chart" role="img" aria-label="${esc(options.ariaLabel||'Evolução dos registros')}">
    <div class="advanced-chart-axis"><span>${fmtNumber(max)}</span><span>${fmtNumber(mid)}</span><span>${fmtNumber(min)}</span></div>
    <div class="advanced-chart-area">
      <div class="chart-scroll">
        <svg class="advanced-line-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" focusable="false">
          <g class="chart-grid-lines"><line x1="0" y1="${top}" x2="${width}" y2="${top}"></line><line x1="0" y1="${top+plotH/2}" x2="${width}" y2="${top+plotH/2}"></line><line x1="0" y1="${height-bottom}" x2="${width}" y2="${height-bottom}"></line></g>
          <path class="chart-area-fill" d="${areaPath}"></path>
          <path class="chart-line" d="${linePath}"></path>
          ${dots}${labels}
        </svg>
      </div>
    </div>
  </div>`;
}

async function summaryView(pk){
  state.summary=await api(`/api/profiles/${encodeURIComponent(pk)}/summary`);
  const s=state.summary,d=s.deltas||{},timeline=Array.isArray(s.timeline)?s.timeline.slice().reverse().slice(0,limiteUI('atividade_recente',8)):[];
  const h=s.historico||{};
  const bioVals=Array.isArray(h.biografia)?h.biografia:[];
  const privacyVals=Array.isArray(h.privado)?h.privado:[];
  const currentBio=historyDisplay(bioVals[bioVals.length-1]);
  const currentPrivacy=historyDisplay(privacyVals[privacyVals.length-1])||(s.perfil?.privado?'PRIVADO':'PÚBLICO');
  const bioChanges=bioVals.filter((v,i)=>i>0&&historyDisplay(v)!==historyDisplay(bioVals[i-1]));
  const privacyChanges=privacyVals.filter((v,i)=>i>0&&historyDisplay(v)!==historyDisplay(privacyVals[i-1]));

  const numericCard=(label,k,icon)=>{
    const v=d[k]||{},delta=Number(v.variacao||0);
    return `<div class="history-summary-card ${k==='seguidores'?'featured':''}" data-history-field="${esc(k)}"><div class="history-summary-card-top"><span class="history-summary-title">${icon||''} ${label}</span><span class="history-card-arrow">↗</span></div><strong>${fmtNumber(v.atual??0)}</strong><span class="muted ${delta>0?'positive':delta<0?'negative':''}">${delta>0?'↑ +':delta<0?'↓ ':'— '}${fmtNumber(delta)} desde o início</span><button class="ghost-btn" data-history="${k}">Ver histórico</button></div>`;
  };
  const textCard=(label,field,value,count,icon)=>{
    return `<div class="history-summary-card history-summary-text-card" data-history-field="${esc(field)}"><div class="history-summary-card-top"><span class="history-summary-title">${icon||''} ${label}</span><span class="history-card-arrow">↗</span></div><strong title="${esc(value)}">${esc(value)}</strong><span class="muted">${count} alteração${count===1?'':'ões'} registrada${count===1?'':'s'}</span><button class="ghost-btn" data-history="${field}">Ver histórico</button></div>`;
  };

  const cards=[
    numericCard('Seguidores','seguidores','👥'),
    numericCard('Seguindo','seguindo','➜'),
    numericCard('Posts','total_posts','📝'),
    numericCard('Reels','total_reels','🎬'),
    numericCard('Destaques','total_destaques','✨'),
    textCard('Biografia','biografia',currentBio,bioChanges.length,'✏️'),
    textCard('Privacidade','privado',currentPrivacy,privacyChanges.length,'🔐')
  ].join('');

  const followerVals=Array.isArray(h.seguidores)?h.seguidores:[];
  const points=followerVals.map(v=>({timestamp:v.timestamp,value:Number(historyValue(v))})).filter(x=>Number.isFinite(x.value));
  const nums=points.map(x=>x.value);
  const min=nums.length?Math.min(...nums):0,max=nums.length?Math.max(...nums):1,range=max-min||1;
  const chart=renderAdvancedLineChart(points,{ariaLabel:'Evolução dos seguidores',intervalLabel:followerVals.map((_,i)=>historyIntervalSeconds(followerVals,i))});

  const intervalValues=timeline.map(t=>Number(t.tempo_desde_anterior?.segundos)).filter(Number.isFinite);
  const avgInterval=intervalValues.length?intervalValues.reduce((a,b)=>a+b,0)/intervalValues.length:null;
  const minInterval=intervalValues.length?Math.min(...intervalValues):null;
  const maxInterval=intervalValues.length?Math.max(...intervalValues):null;

  const eventRows=timeline.slice(0,8).map((t,i)=>{
    const intervalo=t.tempo_desde_anterior?.segundos;
    const categoria=t.categoria==='rede'?'📈 Rede':t.categoria==='perfil'?'✏️ Perfil':'◉ Evento';
    const variacao=t.variacao_texto?esc(t.variacao_texto):'';
    const categoriaClass=t.categoria==='rede'?'rede':t.categoria==='perfil'?'perfil':'evento';
    const direcao=variationDirection(t);
    return `<div class="summary-activity-row activity-${categoriaClass} activity-${direcao}"><div class="summary-activity-time"><b>${fmtTime(t.timestamp)}</b><small>${fmtDate(t.timestamp).split(',')[0]}</small></div><div class="summary-activity-icon">${t.categoria==='rede'?'📈':t.categoria==='perfil'?'✏️':'◉'}</div><div class="summary-activity-main"><div class="summary-activity-heading"><b>${esc(t.titulo||t.descricao||t.evento||'Alteração')}</b><span class="activity-dot"></span></div><span>${esc(t.descricao||'')}</span><div class="summary-activity-meta"><em>${categoria}</em>${variacao?`<em>${variacao}</em>`:''}${intervalo!=null?`<em>⏱ ${formatDurationSeconds(intervalo)} depois da anterior</em>`:'<em>Primeiro registro</em>'}</div></div></div>`;
  }).join('');

  return layout('📊 RESUMO DO PERFIL',`${esc(s.perfil?.nome||'')} · @${esc(s.perfil?.username||'')}`,`
    <div class="profile-head card"><div class="avatar-wrap"><img class="avatar profile-image" src="${imageUrl(s.perfil?.foto_perfil)}" alt="Foto" referrerpolicy="no-referrer"><div class="avatar-fallback">◉</div></div><div><div class="profile-name">${esc(s.perfil?.nome||s.perfil?.username||'')}</div><div class="profile-meta">@${esc(s.perfil?.username||'')}</div></div><div class="actions profile-head-actions"><button class="primary-btn public-page-btn" data-public-profile="${esc(s.perfil?.username||'')}">🌐 Ver página pública</button></div></div>
    <div class="section-title">Indicadores</div>
    <div class="history-summary-grid">${cards}</div>
    <div class="section-title">📈 Evolução dos seguidores</div>
    <div class="card history-chart-card deep-chart"><div class="history-current"><div><span class="history-summary-title">Histórico das capturas</span><strong>${fmtNumber(d.seguidores?.atual??0)}</strong></div><span class="history-variation ${Number(d.seguidores?.variacao||0)>0?'positive':Number(d.seguidores?.variacao||0)<0?'negative':''}">${Number(d.seguidores?.variacao||0)>0?'+':''}${fmtNumber(d.seguidores?.variacao||0)} desde o início</span></div>${chart}</div>
    <div class="history-meta-grid">${stat('📚 Capturas',s.capturas??0)}${stat('⏱ Intervalo médio',avgInterval!=null?formatDurationSeconds(avgInterval):'—')}${stat('⚡ Menor intervalo',minInterval!=null?formatDurationSeconds(minInterval):'—')}${stat('🕰 Maior intervalo',maxInterval!=null?formatDurationSeconds(maxInterval):'—')}</div>
    <div class="section-title">Atividade recente</div>
    <div class="card table-list">${eventRows||'<div class="empty">Ainda não existem alterações suficientes para a atividade recente.</div>'}</div>
    <div class="section-title">Resumo de atividade</div>
    <div class="stats">${stat('🔴 Eventos',s.eventos??0)}${stat('📸 Capturas',s.capturas??0)}${stat('🌐 Rede',timeline.filter(x=>x.categoria==='rede').length)}${stat('✏️ Perfil',timeline.filter(x=>x.categoria==='perfil').length)}</div>
  `,'saved');
}
async function timelineView(){const s=state.summary||{};const timeline=Array.isArray(s.timeline)?s.timeline.slice().reverse().slice(0,limiteUI('timeline',10)):[];return layout('TIMELINE DE ATIVIDADES',`${esc(s.perfil?.nome||'')} · @${esc(s.perfil?.username||'')}`,`<div class="card"><div class="tabs"><button class="ghost-btn active-filter">TODOS</button><button class="ghost-btn">REDE</button><button class="ghost-btn">PERFIL</button></div><div class="timeline">${timeline.map(t=>`<div class="timeline-item"><div class="timeline-time">${fmtDate(t.timestamp)}</div><b>${esc(t.titulo||t.descricao||'Alteração')}</b><div class="muted">${esc(t.descricao||t.mensagem||'')}</div>${t.variacao_texto?`<div class="history-variation">${esc(t.variacao_texto)}</div>`:''}</div>`).join('')||'<div class="empty">Sem eventos.</div>'}</div></div>`, 'summary')}
function historyValue(v){if(!v)return undefined;return v.valor_atual!==undefined?v.valor_atual:v.valor}
function historyLabel(v){return historyDisplay(v)}
function historyView(field){
  const vals=Array.isArray(state.summary?.historico?.[field])?state.summary.historico[field]:[];
  const numericPoints=vals.map(v=>({timestamp:v.timestamp,value:Number(historyValue(v))})).filter(x=>Number.isFinite(x.value));
  const numbers=numericPoints.map(x=>x.value);
  const max=numbers.length?Math.max(...numbers):1,min=numbers.length?Math.min(...numbers):0,range=max-min||1;
  const initial=numbers[0],final=numbers[numbers.length-1],delta=typeof initial==='number'&&typeof final==='number'?final-initial:0;
  const intervalos=vals.map((v,i)=>historyIntervalSeconds(vals,i)).filter(Number.isFinite);
  const avgInterval=intervalos.length?intervalos.reduce((a,b)=>a+b,0)/intervalos.length:null;
  const minInterval=intervalos.length?Math.min(...intervalos):null;
  const maxInterval=intervalos.length?Math.max(...intervalos):null;
  const chart=numericPoints.length?renderAdvancedLineChart(numericPoints,{ariaLabel:`Evolução de ${field}`,intervalLabel:vals.map((_,i)=>historyIntervalSeconds(vals,i))}):'<div class="history-text">Este campo não possui uma série numérica. A evolução abaixo mostra cada registro e o tempo decorrido desde a captura anterior.</div>';
  const rows=vals.slice().reverse().map((v,reverseIndex)=>{
    const originalIndex=vals.length-1-reverseIndex;
    const intervalo=historyIntervalSeconds(vals,originalIndex);
    const before=v.valor_anterior!==undefined?historyPreviousDisplay(v):null;
    const after=historyDisplay(v);
    const transition=before!==null?`<b>${esc(before)} <i>→</i> ${esc(after)}</b>`:`<b>${esc(after)}</b>`;
    const numericBefore=before!==null?Number(String(before).replace(/\./g,'').replace(',','.')):NaN;
    const numericAfter=Number(String(after).replace(/\./g,'').replace(',','.'));
    const rowState=Number.isFinite(numericBefore)&&Number.isFinite(numericAfter)?(numericAfter>numericBefore?'positive':numericAfter<numericBefore?'negative':'neutral'):'neutral';
    return `<div class="event history-event-row ${rowState}"><div class="history-event-date"><b>${fmtTime(v.timestamp)}</b><small>${fmtDate(v.timestamp).split(',')[0]}</small></div><div class="history-event-marker"></div><div class="history-event-content"><div>${transition}</div><small class="muted">${esc(v.descricao||v.tipo||'Registro')}</small></div><div class="history-event-interval">${intervalo!=null?`⏱ ${formatDurationSeconds(intervalo)}`:'Inicial'}</div></div>`;
  }).join('');
  return layout(`HISTÓRICO — ${field.toUpperCase()}`,`${esc(state.summary?.perfil?.nome||'')} · @${esc(state.summary?.perfil?.username||'')}`,`
    <div class="card history-chart-card deep-chart"><div class="history-current"><div><span class="history-summary-title">Estado atual</span><strong>${esc(historyLabel(vals[vals.length-1]))}</strong></div><span class="history-variation ${delta>0?'positive':delta<0?'negative':''}">${numericPoints.length?(delta>0?`↑ +${fmtNumber(delta)} NO PERÍODO`:delta<0?`↓ ${fmtNumber(delta)} NO PERÍODO`:'— 0 NO PERÍODO'):`${vals.length} registros`}</span></div>${chart}</div>
    <div class="history-meta-grid">${stat('📚 Registros',vals.length)}${stat('⏱ Intervalo médio',avgInterval!=null?formatDurationSeconds(avgInterval):'—')}${stat('⚡ Menor intervalo',minInterval!=null?formatDurationSeconds(minInterval):'—')}${stat('🕰 Maior intervalo',maxInterval!=null?formatDurationSeconds(maxInterval):'—')}</div>
    <div class="section-title">Evolução dos registros</div><div class="card table-list">${rows||'<div class="empty">Nenhum registro.</div>'}</div>
  `,'summary');
}
function publicDelta(d,campo){return Number(d?.[campo]?.variacao||0)}
function publicMetricCard(label,d,campo){const v=d?.[campo]||{};const delta=Number(v.variacao||0);return `<div class="public-metric"><span>${label}</span><strong>${fmtNumber(v.atual??0)}</strong><small class="${delta>0?'positive':delta<0?'negative':''}">${delta>0?'↑ +':delta<0?'↓ ': '— '}${fmtNumber(delta)} desde a primeira captura</small></div>`}
async function publicProfileView(){
  const privateMode=!!state.session?.autenticado;
  const p=state.publicProfile;
  if(!p)return layout('Perfil','Não encontrado','<div class="card empty">Perfil não encontrado.</div>');
  const x=p.perfil||{},tl=Array.isArray(p.timeline)?p.timeline:[],an=p.analise||{};
  const deltaFollowers=publicDelta(p.deltas,'seguidores');
  const series=an.serie_seguidores?.length?an.serie_seguidores:(p.series?.seguidores||[]);
  const profileHistory=p.historico_perfil||{},privacy=profileHistory.privado||[],verified=profileHistory.verificado||[];
  const lastEvent=tl.length?tl[tl.length-1]:null;
  const periods=an.periodos||{},trend=an.tendencia||{},records=an.recordes||{},activity=an.atividade||{},projection=an.projecao||{};
  const insights=(an.insights||[]).slice(0,limiteUI('descobertas',10)),heatmap=(an.heatmap||[]).slice(-limiteUI('mapa_atividade',28)),quality=an.qualidade||{},behavior=an.comportamento||{};
  const sequence=behavior.sequencia||{},oscillation=behavior.oscilacao_seguidores||{},intervals=behavior.intervalos||{},fieldChanges=behavior.mudancas_por_campo||{};
  const maxHeat=Math.max(1,...heatmap.map(v=>Number(v.eventos)||0));
  const chartValues=series.map(v=>Number(v.valor)).filter(Number.isFinite);
  const chartMin=chartValues.length?Math.min(...chartValues):0,chartMax=chartValues.length?Math.max(...chartValues):1,chartRange=chartMax-chartMin||1;
  const followerChart=series.length?renderAdvancedLineChart(series.map(v=>({timestamp:v.timestamp,value:v.valor})),{ariaLabel:'Seguidores ao longo das capturas'}):'<div class="empty">Ainda não existem capturas suficientes para montar a evolução.</div>';
  const periodCard=(label,key)=>{const d=periods[key]||{},v=Number(d.variacao||0),pctv=Number(d.percentual||0),rate=Number(d.por_dia||0);return `<div class="period-card"><span>${label}</span><strong class="${v>0?'positive':v<0?'negative':''}">${v>0?'+':''}${fmtNumber(v)}</strong><small>${pctv>0?'+':''}${pctv.toLocaleString('pt-BR',{maximumFractionDigits:2})}% · ${rate>0?'+':''}${rate.toLocaleString('pt-BR',{maximumFractionDigits:1})}/dia</small></div>`};
  const historyCard=(label,field,formatter=historyLabel)=>{const vals=p.historico?.[field]||[],last=vals[vals.length-1];return `<div class="card public-history-card"><span class="history-summary-title">${label}</span><strong>${esc(formatter(last))}</strong><span class="muted">${vals.length} registro${vals.length===1?'':'s'}</span></div>`};
  const privacyLabel=privacy.length?historyLabel(privacy[privacy.length-1]):(x.privado?'PRIVADO':'PÚBLICO');
  const verificationLabel=verified.length?historyLabel(verified[verified.length-1]):(x.verificado?'VERIFICADO':'NÃO VERIFICADO');
  const insightCards=insights.map(i=>`<div class="card deep-insight"><div class="insight-icon">${i.icone||'💡'}</div><div><b>${esc(i.titulo||'Insight')}</b><p>${esc(i.texto||'')}</p></div></div>`).join('');
  const heat=heatmap.map(h=>{const level=Math.min(4,Math.ceil((Number(h.eventos)||0)/maxHeat*4));return `<div class="heat-cell level-${level}" title="${esc(h.data)} · ${fmtNumber(h.eventos)} evento(s)"></div>`}).join('');
  const recordCard=(icon,label,value,sub)=>`<div class="record-card"><span>${icon}</span><small>${label}</small><strong>${value}</strong><em>${sub||''}</em></div>`;
  const behaviorCards=`${sequence.maior_sequencia_queda>=2?recordCard('📉','Sequência de perdas',fmtNumber(sequence.maior_sequencia_queda),'quedas consecutivas'):''}${sequence.maior_sequencia_ganho>=2?recordCard('🚀','Sequência de ganhos',fmtNumber(sequence.maior_sequencia_ganho),'ganhos consecutivos'):''}${oscillation.ocorrencias?recordCard('🔄','Oscilações',fmtNumber(oscillation.ocorrencias),'reversões detectadas'):''}${fieldChanges.seguindo?recordCard('👥','Mudanças no seguindo',fmtNumber(fieldChanges.seguindo),'entre capturas'):''}`;
  const rate=Number(projection.ritmo_diario||0),projectionText=projection.seguidores_estimados!=null?fmtNumber(Math.round(projection.seguidores_estimados)):'—';
  const changeRows=tl.slice().reverse().slice(0,limiteUI('mudancas',10)).map(t=>{const intervalo=t.tempo_desde_anterior?.segundos;const cat=t.categoria==='rede'?'rede':t.categoria==='perfil'?'perfil':'evento';const direcao=variationDirection(t);return `<div class="change-item change-${cat} change-${direcao}"><div class="change-icon">${t.categoria==='rede'?'📈':t.categoria==='perfil'?'✏️':'◉'}</div><div class="change-body"><div class="change-title-row"><b>${esc(t.titulo||t.descricao||'Alteração')}</b><time>${fmtDate(t.timestamp)}</time></div><div class="muted">${esc(t.descricao||'')}</div>${t.variacao_texto?`<span class="history-variation">${esc(t.variacao_texto)}</span>`:''}${intervalo!=null?`<small class="change-interval">⏱ ${formatDurationSeconds(intervalo)} desde a captura anterior</small>`:''}</div></div>`}).join('');

  return layout(`@${esc(x.username||'perfil')}`,privateMode?'Seu perfil salvo · evolução, comportamento, histórico e descobertas':'Inteligência de perfil · evolução, comportamento, histórico e descobertas',`
    <div class="card public-profile-hero premium-hero"><div class="avatar-wrap large"><img class="avatar profile-image" src="${imageUrl(x.foto_perfil)}" alt="Foto de ${esc(x.nome||x.username||'perfil')}" referrerpolicy="no-referrer"><div class="avatar-fallback">◉</div></div><div><div class="eyebrow">FAREJADOR · PERFIL ANALISADO</div><h2>${esc(x.nome||x.username||'')}</h2><div class="profile-meta">@${esc(x.username||'')} · ${x.privado?'🔒 Privado':'🌐 Público'} ${x.verificado?'· ✓ Verificado':''}</div><p class="bio">${esc(x.biografia||'Sem biografia disponível.')}</p><div class="profile-live-line">${lastEvent?`● Última alteração registrada ${fmtDate(lastEvent.timestamp)}`:'● Aguardando histórico'}</div></div><div class="actions"><button class="primary-btn" data-compare-from="${esc(x.username||'')}">⚖ Comparar</button><span class="badge ${x.monitorando?'good':''}">${x.monitorando?'🟢 Monitorando':'⚪ Não monitorado'}</span></div></div>
    <div class="public-kpi-grid">${publicMetricCard('Seguidores',p.deltas,'seguidores')}${publicMetricCard('Seguindo',p.deltas,'seguindo')}${publicMetricCard('Posts',p.deltas,'total_posts')}${publicMetricCard('Reels',p.deltas,'total_reels')}</div>
    <div class="profile-insight-grid"><div class="card insight-card"><span>📈 Ritmo atual</span><strong>${rate>0?'+':''}${rate.toLocaleString('pt-BR',{maximumFractionDigits:1})}</strong><small>seguidores por dia, baseado no histórico recente</small></div><div class="card insight-card"><span>⚡ Tendência</span><strong>${trend.direcao==='acelerando'?'Acelerando':trend.direcao==='desacelerando'?'Desacelerando':trend.direcao==='queda_acelerando'?'Queda acelerando':trend.direcao==='recuperando'?'Recuperando':'Estável'}</strong><small>${Number(trend.aceleracao_percentual||0)>0?'+':''}${Number(trend.aceleracao_percentual||0).toLocaleString('pt-BR',{maximumFractionDigits:0})}% contra a parte anterior do histórico</small></div><div class="card insight-card"><span>🔥 Atividade</span><strong>${fmtNumber(activity.score||0)}</strong><small>${fmtNumber(activity.eventos||0)} eventos + ${fmtNumber(an.capturas||0)} capturas registradas</small></div><div class="card insight-card"><span>📚 Histórico</span><strong>${fmtNumber(an.capturas||p.capturas||0)}</strong><small>${an.primeira_captura?`desde ${fmtDate(an.primeira_captura)}`:'capturas disponíveis'}</small></div></div>
    <div class="section-title profile-section-title"><div><b>📈 Crescimento</b><small>Veja como o perfil se movimentou em diferentes janelas</small></div></div><div class="period-grid">${periodCard('Últimos 7 dias','7')}${periodCard('Últimos 30 dias','30')}${periodCard('Últimos 90 dias','90')}${periodCard('Todo histórico','total')}</div>
    <div class="card history-chart-card deep-chart"><div class="history-current"><div><span class="history-summary-title">Seguidores ao longo das capturas</span><strong>${fmtNumber(x.seguidores||0)}</strong></div><span class="history-variation ${deltaFollowers>0?'positive':deltaFollowers<0?'negative':''}">${deltaFollowers>0?'+':''}${fmtNumber(deltaFollowers)} desde o início</span></div>${followerChart}</div>
    <div class="section-title profile-section-title"><div><b>🧠 O que o histórico revela</b><small>Insights calculados somente a partir dos registros disponíveis</small></div></div><div class="deep-insight-grid">${insightCards||'<div class="card empty">Ainda não há dados suficientes para gerar insights.</div>'}</div>
    <div class="section-title profile-section-title"><div><b>🏆 Recordes do perfil</b><small>Momentos de maior movimento encontrados no histórico</small></div></div><div class="record-grid">${recordCard('🚀','Maior ganho',`+${fmtNumber(records.maior_ganho||0)}`,'entre duas capturas')}${recordCard('📉','Maior queda',fmtNumber(records.maior_queda||0),'entre duas capturas')}${recordCard('🔥','Eventos',fmtNumber(activity.eventos||0),'alterações detectadas')}${recordCard('✏️','Mudanças de bio',fmtNumber((behavior.mudancas_por_campo?.biografia)||0),'registradas')}</div>
    <div class="section-title profile-section-title"><div><b>🔎 Padrões detectados</b><small>Comportamentos encontrados diretamente nas capturas</small></div></div><div class="record-grid behavior-grid">${behaviorCards||'<div class="card empty">Ainda não há padrões repetidos suficientes para destacar.</div>'}</div>
    <div class="section-title profile-section-title"><div><b>🔥 Mapa de atividade</b><small>Quanto mais intenso, mais eventos foram registrados naquele dia</small></div></div><div class="card heatmap-card"><div class="heatmap-legend"><span>menos</span><i class="level-1"></i><i class="level-2"></i><i class="level-3"></i><i class="level-4"></i><span>mais</span></div><div class="heatmap">${heat||'<span class="muted">Ainda não existem eventos suficientes.</span>'}</div></div>
    <div class="section-title profile-section-title"><div><b>💡 Descobertas</b><small>Pequenos detalhes que passam despercebidos em uma tabela</small></div></div><div class="discovery-grid"><div class="card discovery-card"><span>🔮 PROJEÇÃO</span><strong>${projectionText}</strong><p>${projection.seguidores_estimados!=null?'estimativa para 30 dias mantendo o ritmo recente.':'Ainda não há histórico suficiente para projetar.'}</p></div><div class="card discovery-card"><span>📊 RITMO</span><strong>${rate?`${rate>0?'+':''}${rate.toLocaleString('pt-BR',{maximumFractionDigits:1})}/dia`:'—'}</strong><p>${quality.rotulo||'Histórico disponível'}</p></div><div class="card discovery-card"><span>⏱️ INTERVALO</span><strong>${intervals.min_segundos!=null?formatDurationSeconds(intervals.min_segundos):'—'}</strong><p>${intervals.min_segundos!=null?'menor intervalo entre capturas':'intervalos ainda não calculáveis'}</p></div><div class="card discovery-card"><span>📚 OBSERVAÇÃO</span><strong>${quality.dias_observados?quality.dias_observados.toLocaleString('pt-BR',{maximumFractionDigits:1})+'d':'—'}</strong><p>${fmtNumber(quality.capturas||0)} capturas no período observado</p></div></div>
    <div class="section-title">🚨 O que mudou?</div><div class="card change-list">${changeRows||'<div class="empty">Ainda não há alterações suficientes para gerar a lista de mudanças.</div>'}</div>
    <div class="section-title">🔐 Estado do perfil</div><div class="public-history-grid">${historyCard('Privacidade','privado')}${historyCard('Verificação','verificado')}${historyCard('Memorializado','memorializado')}</div>
    <div class="profile-status-strip"><span>Privacidade: <b>${esc(privacyLabel)}</b></span><span>Verificação: <b>${esc(verificationLabel)}</b></span><span>Último evento: <b>${lastEvent?fmtDate(lastEvent.timestamp):'—'}</b></span></div>
    <div class="section-title">📚 Histórico do perfil</div><div class="public-history-grid">${historyCard('Seguidores','seguidores')}${historyCard('Seguindo','seguindo')}${historyCard('Posts','total_posts')}${historyCard('Reels','total_reels')}${historyCard('Destaques','total_destaques')}</div>
    <div class="profile-bottom-actions"><button class="primary-btn" data-compare-from="${esc(x.username||'')}">⚖ Comparar este perfil</button>${privateMode?'<button class="ghost-btn" data-route="saved">★ Voltar aos meus usuários</button>':'<button class="ghost-btn" data-login="1">🔔 Criar conta e monitorar</button>'}</div>
  `);
}
