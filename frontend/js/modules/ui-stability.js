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

    // Se a análise foi bloqueada por falta de créditos, não devemos apresentar
    // o erro como se o usuário não existisse. O status vem preservado pelo
    // runtime e registrado pelo handler da análise.
    if(state.route==='analyze'&&state.analysisErrorStatus===402){
      const content=$('#content');
      const card=content?.querySelector('.friendly-empty');
      if(card){
        const icon=card.querySelector('.friendly-icon');
        const title=card.querySelector('h2');
        if(icon)icon.textContent='💳';
        if(title)title.textContent='Créditos insuficientes';
      }
    }

    // Se algum renderer anterior estiver sendo usado, força uma única renderização
    // do Explore com o filtro de categoria. O marker vem do módulo dedicado.
    if(state.route==='explore'&&window.__farejadorEnhancedExplore&&!document.querySelector('#ranking-category-select')){
      const content=$('#content');
      if(content){
        const html=await window.exploreView();
        if(state.route==='explore'){
          content.innerHTML=html;
          if(typeof bind==='function')bind();
          if(typeof bindImages==='function')bindImages();
        }
      }
    }

    // Navegação real entre telas continua podendo iniciar no topo.
    // Atualizações na mesma tela preservam exatamente a posição anterior.
    if(state.route===routeBefore&&scrollY>0){
      requestAnimationFrame(()=>{
        window.scrollTo(0,scrollY);
        requestAnimationFrame(()=>window.scrollTo(0,scrollY));
      });
    }
  };

  if(state&&!Object.prototype.hasOwnProperty.call(state,'exploreCategory'))state.exploreCategory='';
})();
