const state={session:null,route:'dashboard',profiles:[],analysis:null,analysisError:null,summary:null,summaryPk:null,historyField:null,publicProfile:null,compare:null,explore:null,exploreRank:'activity',publicUsername:null,feedFilter:'todos',feedTimer:null,pageConfig:null,displayLimits:null,theme:localStorage.getItem('farejador-theme')||'dark'};
const $=s=>document.querySelector(s);
const api=async(url,opt={})=>{const r=await fetch(url,{cache:'no-store',headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt});let d={};try{d=await r.json()}catch{}if(!r.ok)throw new Error(d.detail||'Erro na operação');return d};
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const imageUrl=v=>v?`/api/profile-image?url=${encodeURIComponent(v)}`:'';
const fmtDate=v=>v?new Date(v).toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'}):'—';
const fmtTime=v=>v?new Date(v).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'}):'—';
const fmtNumber=v=>{const n=Number(v??0);return Number.isFinite(n)?n.toLocaleString('pt-BR',{maximumFractionDigits:2}):'0'};
const limiteUI=(chave,padrao=10)=>Math.max(1,Number(state.displayLimits?.[chave]??padrao));
const formatDurationSeconds=seconds=>{
  const n=Number(seconds);
  if(!Number.isFinite(n)||n<0)return '—';
  let s=Math.round(n);
  const d=Math.floor(s/86400);s%=86400;
  const h=Math.floor(s/3600);s%=3600;
  const m=Math.floor(s/60);s%=60;
  const parts=[];
  if(d)parts.push(`${d}d`);
  if(h)parts.push(`${h}h`);
  if(m)parts.push(`${m}min`);
  if(s||!parts.length)parts.push(`${s}s`);
  return parts.join(' ');
};
const historyDisplay=v=>{
  if(!v)return '—';
  const raw=v.valor_atual!==undefined?v.valor_atual:v.valor;
  if(typeof raw==='boolean')return raw?'PRIVADO':'PÚBLICO';
  if(raw===null||raw===undefined)return '—';
  if(Array.isArray(raw))return raw.length?raw.join(', '):'Nenhum';
  return typeof raw==='number'?fmtNumber(raw):String(raw);
};
const historyPreviousDisplay=v=>{
  if(!v)return '—';
  const raw=v.valor_anterior!==undefined?v.valor_anterior:v.valor;
  if(typeof raw==='boolean')return raw?'PRIVADO':'PÚBLICO';
  if(raw===null||raw===undefined)return '—';
  if(Array.isArray(raw))return raw.length?raw.join(', '):'Nenhum';
  return typeof raw==='number'?fmtNumber(raw):String(raw);
};
const historyIntervalSeconds=(vals,index)=>{
  if(index<=0)return null;
  const a=new Date(vals[index-1]?.timestamp||vals[index-1]?.timestamp_atual||0).getTime();
  const b=new Date(vals[index]?.timestamp||vals[index]?.timestamp_atual||0).getTime();
  if(!Number.isFinite(a)||!Number.isFinite(b)||!a||!b)return null;
  return Math.max(0,(b-a)/1000);
};

const variationDirection=value=>{
  const direct=Number(value?.variacao);
  if(Number.isFinite(direct)&&direct!==0)return direct>0?'positive':'negative';
  const text=String(value?.variacao_texto??'').trim();
  if(/^\+/.test(text))return 'positive';
  if(/^-/.test(text))return 'negative';
  return 'neutral';
};

const pct=v=>`${v>0?'+':''}${Number(v||0).toLocaleString('pt-BR')}%`;
function toast(msg){const e=document.createElement('div');e.className='toast';e.textContent=msg;$('#toast').appendChild(e);setTimeout(()=>e.remove(),3200)}
function applyTheme(){document.body.classList.toggle('dark',state.theme==='dark');$('#theme-toggle').textContent=state.theme==='dark'?'☀':'☾';localStorage.setItem('farejador-theme',state.theme)}
function go(route,replace=false){state.route=route;const path=route==='dashboard'?'/':route==='public-profile'?`/perfil/${encodeURIComponent(state.publicProfile?.perfil?.username||state.publicUsername||'')}`:route==='compare'?'/comparar':route==='explore'?'/explorar':'/';if(replace)history.replaceState({},'',path);else history.pushState({},'',path);render()}
function detectRoute(){const m=location.pathname.match(/^\/perfil\/([^/]+)$/);if(m){state.route='public-profile';state.publicUsername=decodeURIComponent(m[1]);return}if(location.pathname==='/comparar'){state.route='compare';return}if(location.pathname==='/explorar'){state.route='explore';return}state.route='dashboard'}
function nav(){const auth=state.session?.autenticado;const items=auth?['dashboard|Painel','analyze|Analisar','saved|Usuários salvos','feed|Feed','explore|Explorar','compare|Comparar']:['dashboard|Início','explore|Explorar','feed|Feed','compare|Comparar'];$('#main-nav').innerHTML=items.map(x=>{let[a,b]=x.split('|');return `<button class="${state.route===a?'active':''}" data-route="${a}">${b}</button>`}).join('');$('#auth-btn').textContent=auth?`Sair · ${state.session.cliente_usuario}`:'Entrar';document.body.classList.remove('mobile-nav-open');const m=$('#mobile-menu-toggle');if(m)m.setAttribute('aria-expanded','false')}
async function boot(){
  detectRoute();
  try{
    state.session=await api('/api/session');
  }catch(e){
    // A falha de registro do visitante não pode deixar a aplicação inteira em branco.
    state.session={autenticado:false,cliente_usuario:null,modo_publico:true,publico_cliente_usuario:'admin',versao:null};
    console.error('Falha ao iniciar sessão:',e);
  }
  try{
    state.pageConfig=await api('/api/config/atualizacao-paginas');
  }catch(_){
    state.pageConfig={feed:{intervalo_segundos:2,ativo:true},paginas:{intervalo_segundos:10}};
  }
  applyTheme();
  await render();
}
