/* Compatibilidade de clique do login: o botão do topo pode ser recriado pelo render/nav. */
(function(){
  if(window.__farejadorAuthDelegated)return;
  window.__farejadorAuthDelegated=true;
  document.addEventListener('click',event=>{
    const button=event.target?.closest?.('#auth-btn');
    if(!button)return;
    if(state.session?.autenticado)return;
    event.preventDefault();
    try{ openAuth(); }catch(error){
      console.error('Falha ao abrir autenticação:',error);
      toast(error?.message||'Não foi possível abrir a tela de login.');
    }
  });
})();
