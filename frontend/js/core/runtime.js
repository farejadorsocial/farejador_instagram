const state={session:null,route:'dashboard',profiles:[],analysis:null,analysisError:null,summary:null,summaryPk:null,historyField:null,publicProfile:null,compare:null,explore:null,exploreRank:'activity',publicUsername:null,feedFilter:'todos',feedTimer:null,feedAbortController:null,pageConfig:null,displayLimits:null,theme:localStorage.getItem('farejador-theme')||'dark'};
const $=s=>document.querySelector(s);
const API_CACHE_TTL={'/api/session':5000,'/api/config/atualizacao-paginas':30000};
const apiCache=new Map();
const apiInflight=new Map();
function tokenLegado(){try{return localStorage.getItem('farejador_token')||localStorage.getItem('laboratorio_bet_token')||null}catch(_){return null}}
function limparTokenLegado(){try{localStorage.removeItem('farejador_token');localStorage.removeItem('laboratorio_bet_token')}catch(_){} }
function invalidarCacheApi(url){const base=String(url||'').split('?')[0];[...apiCache.keys()].filter(k=>k===base||k.startsWith(`${base}?`)).forEach(k=>apiCache.delete(k))}
const api=async(url,opt={})=>{
  const method=String(opt.method||'GET').toUpperCase(),isGet=method==='GET',baseUrl=String(url).split('?')[0],cacheTtl=isGet?Number(API_CACHE_TTL[baseUrl]||0):0,cacheKey=String(url);
  if(isGet&&cacheTtl){const cached=apiCache.get(cacheKey);if(cached&&Date.now()-cached.time<cacheTtl)return cached.data}
  if(isGet&&apiInflight.has(cacheKey))return apiInflight.get(cacheKey);
  const headers=new Headers(opt.headers||{});
  if(!headers.has('Content-Type')&&method!=='GET'&&method!=='HEAD')headers.set('Content-Type','application/json');
  const legado=tokenLegado();if(legado&&!headers.has('Authorization'))headers.set('Authorization',`Bearer ${legado}`);
  const externalSignal=opt.signal||null,controller=new AbortController(),signal=controller.signal,timeoutMs=Number(opt.timeoutMs??15000);let timeout=null,abortExternal=null;
  if(externalSignal){if(externalSignal.aborted)controller.abort();else{abortExternal=()=>controller.abort();externalSignal.addEventListener('abort',abortExternal,{once:true})}}
  if(timeoutMs>0)timeout=setTimeout(()=>controller.abort(),timeoutMs);
  const fetchOptions={...opt};delete fetchOptions.timeoutMs;delete fetchOptions.signal;
  const request=fetch(url,{cache:'no-store',credentials:'same-origin',...fetchOptions,headers,signal}).then(async r=>{
    let d={};try{d=await r.json()}catch{}
    if(!r.ok){
      if(r.status===401){limparTokenLegado();if(state.session?.autenticado){state.session={autenticado:false,cliente_usuario:null,modo_publico:true,publico_cliente_usuario:'admin',versao:state.session?.versao??null};document.dispatchEvent(new CustomEvent('farejador:session-expired'))}}
      const error=new Error(d.detail||`Erro na operação (${r.status})`);error.status=r.status;error.data=d;throw error;
    }
    if(isGet&&cacheTtl)apiCache.set(cacheKey,{time:Date.now(),data:d});
    if(!isGet)invalidarCacheApi('/api/session');
    return d;
  }).finally(()=>{if(timeout)clearTimeout(timeout);if(externalSignal&&abortExternal)externalSignal.removeEventListener('abort',abortExternal);if(apiInflight.get(cacheKey)===request)apiInflight.delete(cacheKey)});
  if(isGet)apiInflight.set(cacheKey,request);
  return request;
};
const esc=s=>String(s??'').replace(/[&<>'\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[c]));
const imageUrl=v=>v?`/api/profile-image?url=${encodeURIComponent(v)}`:'';
const fmtDate=v=>v?new Date(v).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—';
const fmtTime=v=>v?new Date(v).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}):'—';
const fmtNumber=v=>{const n=Number(v??0);return Number.isFinite(n)?n.toLocaleString('pt-BR',{maximumFractionDigits:2}):'0'};
const limiteUI=(chave,padrao=10)=>Math.max(1,Number(state.displayLimits?.[chave]??padrao));
const formatDurationSeconds=seconds=>{const n=Number(seconds);if(!Number.isFinite(n)||n<0)return '—';let s=Math.round(n);const d=Math.floor(s/86400);s%=86400;const h=Math.floor(s/3600);s%=3600;const m=Math.floor(s/60);s%=60;const parts=[];if(d)parts.push(`${d}d`);if(h)parts.push(`${h}h`);if(m)parts.push(`${m}min`);if(s||!parts.length)parts.push(`${s}s`);return parts.join(' ')};
const historyDisplay=v=>{if(!v)return '—';const raw=v.valor_atual!==undefined?v.valor_atual:v.valor;if(typeof raw==='boolean')return raw?'PRIVADO':'PÚBLICO';if(raw===null||raw===undefined)return '—';if(Array.isArray(raw))return raw.length?raw.join(', '):'Nenhum';return typeof raw==='number'?fmtNumber(raw):String(raw)};
const historyPreviousDisplay=v=>{if(!v)return '—';const raw=v.valor_anterior!==undefined?v.valor_anterior:v.valor;if(typeof raw==='boolean')return raw?'PRIVADO':'PÚBLICO';if(raw===null||raw===undefined)return '—';if(Array.isArray(raw))return raw.length?raw.join(', '):'Nenhum';return typeof raw==='number'?fmtNumber(raw):String(raw)};
const historyIntervalSeconds=(vals,index)=>{if(index<=0)return null;const a=new Date(vals[index-1]?.timestamp||vals[index-1]?.timestamp_atual||0).getTime(),b=new Date(vals[index]?.timestamp||vals[index]?.timestamp_atual||0).getTime();if(!Number.isFinite(a)||!Number.isFinite(b)||!a||!b)return null;return Math.max(0,(b-a)/1000)};
const variationDirection=value=>{const direct=Number(value?.variacao);if(Number.isFinite(direct)&&direct!==0)return direct>0?'positive':'negative';const text=String(value?.variacao_texto??'').trim();if(/^\+/.test(text))return 'positive';if(/^-/.test(text))return 'negative';return 'neutral'};
const pct=v=>`${v>0?'+':''}${Number(v||0).toLocaleString('pt-BR')}%`;
function toast(msg){const root=$('#toast');if(!root)return;const e=document.createElement('div');e.className='toast';e.textContent=msg;root.appendChild(e);setTimeout(()=>e.remove(),3200)}
function applyTheme(){document.body.classList.toggle('dark',state.theme==='dark');const toggle=$('#theme-toggle');if(toggle)toggle.textContent=state.theme==='dark'?'☀':'☾';localStorage.setItem('farejador-theme',state.theme)}
function cancelarAtualizacoes(){if(state.feedTimer){clearTimeout(state.feedTimer);state.feedTimer=null}if(state.feedAbortController){state.feedAbortController.abort();state.feedAbortController=null}}
function go(route,replace=false){cancelarAtualizacoes();state.route=route;const path=route==='dashboard'?'/':route==='public-profile'?`/perfil/${encodeURIComponent(state.publicProfile?.perfil?.username||state.publicUsername||'')}`:route==='compare'?'/comparar':route==='explore'?'/explorar':'/';if(replace)history.replaceState({},'',path);else history.pushState({},'',path);render()}
function detectRoute(){const m=location.pathname.match(/^\/perfil\/([^/]+)$/);if(m){state.route='public-profile';state.publicUsername=decodeURIComponent(m[1]);return}if(location.pathname==='/comparar'){state.route='compare';return}if(location.pathname==='/explorar'){state.route='explore';return}state.route='dashboard'}
function nav(){const auth=state.session?.autenticado,items=auth?['dashboard|Painel','analyze|Analisar','saved|Usuários salvos','feed|Feed','explore|Explorar','compare|Comparar']:['dashboard|Início','explore|Explorar','feed|Feed','compare|Comparar'];const navEl=$('#main-nav');if(navEl)navEl.innerHTML=items.map(x=>{let[a,b]=x.split('|');return `<button class=\"${state.route===a?'active':''}\" data-route=\"${a}\">${b}</button>`}).join('');const authBtn=$('#auth-btn');if(authBtn)authBtn.textContent=auth?`Sair · ${state.session.cliente_usuario}`:'Entrar';document.body.classList.remove('mobile-nav-open');const m=$('#mobile-menu-toggle');if(m)m.setAttribute('aria-expanded','false')}
async function boot(){detectRoute();try{state.session=await api('/api/session')}catch(e){state.session={autenticado:false,cliente_usuario:null,modo_publico:true,publico_cliente_usuario:'admin',versao:null};console.error('Falha ao iniciar sessão:',e)}try{state.pageConfig=await api('/api/config/atualizacao-paginas')}catch(_){state.pageConfig={feed:{intervalo_segundos:2,ativo:true},paginas:{intervalo_segundos:10}}}applyTheme();await render()}
