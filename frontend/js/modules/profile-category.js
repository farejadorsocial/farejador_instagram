(function(){
  const FALLBACK_CATEGORIES=['Influenciador','Música','Ator','Atriz','Celebridade','Esporte','Futebol','Humor','Jornalismo','Empresa/Marca','Criador de conteúdo','Streamer','Outro'];
  let categories=FALLBACK_CATEGORIES.slice();
  let loading=false;

  const normalizeCategories=(data)=>{
    const list=Array.isArray(data?.categorias)?data.categorias:[];
    const valid=[...new Set(list.map(value=>String(value||'').trim()).filter(Boolean))];
    return valid.length?valid:FALLBACK_CATEGORIES.slice();
  };

  const categoryValue=()=>{
    const select=document.querySelector('#profile-category-select');
    return String(select?.value||categories[0]||'').trim();
  };

  const renderSelector=()=>{
    const button=document.querySelector('#save-profile');
    if(!button)return;
    let wrap=document.querySelector('#profile-category-control');
    if(!wrap){
      wrap=document.createElement('label');
      wrap.id='profile-category-control';
      wrap.className='analysis-category-control';
      button.parentNode.insertBefore(wrap,button);
    }
    wrap.innerHTML=`<span class="analysis-category-label">Categoria</span><select id="profile-category-select" class="analysis-category-select" aria-label="Categoria do perfil" ${loading?'disabled':''}>${categories.map(category=>`<option value="${esc(category)}">${esc(category)}</option>`).join('')}</select>`;
  };

  const saveWithCategory=async()=>{
    const button=document.querySelector('#save-profile');
    if(!button||!state.analysis)return;
    const categoria=categoryValue();
    if(!categoria){toast('Selecione uma categoria para salvar o perfil.');return;}
    const original=button.innerHTML;
    button.disabled=true;
    button.innerHTML='SALVANDO...';
    try{
      const dados=JSON.parse(JSON.stringify(state.analysis));
      dados.perfil=dados.perfil&&typeof dados.perfil==='object'?dados.perfil:{};
      dados.perfil.categoria=categoria;
      await api('/api/profile/save',{method:'POST',body:JSON.stringify({dados})});
      state.analysis=dados;
      state.profiles=await api('/api/profiles');
      toast(`Perfil salvo na categoria: ${categoria}.`);
      render();
    }catch(error){
      toast(error.message||'Não foi possível salvar o perfil.');
      button.disabled=false;
      button.innerHTML=original;
    }
  };

  const install=()=>{
    renderSelector();
    const select=document.querySelector('#profile-category-select');
    if(select&&state.analysis?.perfil?.categoria&&categories.includes(state.analysis.perfil.categoria))select.value=state.analysis.perfil.categoria;
  };

  document.addEventListener('click',event=>{
    const button=event.target.closest?.('#save-profile');
    if(!button)return;
    event.preventDefault();
    event.stopImmediatePropagation();
    saveWithCategory();
  },true);

  const observer=new MutationObserver(()=>install());
  observer.observe(document.body,{childList:true,subtree:true});

  fetch('/static/config/profile-categories.json',{cache:'no-store',credentials:'same-origin'})
    .then(response=>response.ok?response.json():null)
    .then(data=>{categories=normalizeCategories(data);loading=false;install();})
    .catch(()=>{loading=false;install();});

  loading=true;
  install();
})();
