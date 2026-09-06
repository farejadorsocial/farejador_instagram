/* Estabilidade de interface.
 * Remove o estado de carregamento agressivo entre renders e preserva a posição
 * da página quando uma ação atualiza a mesma tela.
 */
(function(){
  if(typeof window==='undefined'||typeof window.render!=='function')return;

  // O render original substitui #content por um loading antes de cada render.
  // Isso provoca o "piscar" visível em ações simples como monitorar/remover.
  window.uiPageLoading=function(){};

  const renderOriginal=window.render;
  window.render=async function(){
    const routeBefore=state.route;
    const scrollY=window.scrollY||window.pageYOffset||0;
    await renderOriginal.apply(this,arguments);

    // Navegação real entre telas continua podendo iniciar no topo.
    // Atualizações na mesma tela preservam exatamente a posição anterior.
    if(state.route===routeBefore&&scrollY>0){
      requestAnimationFrame(()=>{
        window.scrollTo(0,scrollY);
        requestAnimationFrame(()=>window.scrollTo(0,scrollY));
      });
    }
  };

  // Garante que a nova propriedade exista mesmo em sessões iniciadas antes
  // da implementação do filtro por categoria.
  if(state&&!Object.prototype.hasOwnProperty.call(state,'exploreCategory'))state.exploreCategory='';
})();
