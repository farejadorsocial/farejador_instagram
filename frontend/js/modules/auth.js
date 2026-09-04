async function openAuth(){
  const permissaoConfig=await obterPermissoesNavegador();
  $('#modal-root').innerHTML=`<div class="modal-backdrop auth-backdrop"><div class="modal auth-modal">
    <div class="auth-brand"><span>🔎</span><div><b>FAREJADOR</b><small>Seu painel de investigação</small></div></div>
    <div class="auth-heading"><span class="auth-kicker">ACESSO SEGURO</span><h2 id="auth-title">Entrar</h2><p id="auth-subtitle">Continue de onde parou e acompanhe seus perfis.</p></div>
    <div class="form">
      <div><label>Usuário</label><input id="auth-user" class="input" autocomplete="username" placeholder="Digite seu usuário"></div>
      <div><label>Senha</label><input id="auth-pass" type="password" class="input" autocomplete="current-password" placeholder="Digite sua senha"></div>
      <div id="auth-confirm-wrap" style="display:none"><label>Confirmar senha</label><input id="auth-confirm" type="password" class="input" autocomplete="new-password" placeholder="Repita sua senha"></div>
      <div id="auth-error" class="auth-error" style="display:none"></div>
      <div id="auth-permission-info" class="auth-permission" style="display:block"></div>
      <button id="auth-submit" class="primary-btn auth-submit">Entrar</button>
      <button id="auth-switch" class="ghost-btn">Criar conta</button>
    </div>
    <div class="auth-note">🔐 Seus dados de acesso são tratados pelo armazenamento individual da sua conta.</div>
    <div class="modal-footer"><button id="auth-close" class="outline-btn">Fechar</button></div>
  </div></div>`;

  let mode='login';
  const setPermissionState=(state,message)=>{
    const info=$('#auth-permission-info');
    if(!info)return;
    info.style.display='block';
    info.className=`auth-permission auth-permission-${state}`;
    info.innerHTML=message;
  };
  const syncMode=()=>{
    const cadastro=mode==='register', cfg=permissaoConfig?.[cadastro?'cadastro':'login']||{};
    $('#auth-title').textContent=cadastro?'Criar conta':'Entrar';
    $('#auth-subtitle').textContent=cadastro?'Crie seu acesso para salvar e acompanhar seus perfis.':'Continue de onde parou e acompanhe seus perfis.';
    $('#auth-error').style.display='none';$('#auth-error').textContent='';
    $('#auth-submit').textContent=cadastro?'Cadastrar':'Entrar';
    $('#auth-switch').textContent=cadastro?'Já tenho conta':'Criar conta';
    $('#auth-confirm-wrap').style.display=cadastro?'block':'none';
    $('#auth-pass').setAttribute('autocomplete',cadastro?'new-password':'current-password');
    const permissoesAtivas=permissaoConfig?.ativo!==false;
    const exigidas=permissoesAtivas?Object.entries(cfg).filter(([,v])=>v===true).map(([k])=>k):[];
    if(exigidas.length){
      const nomes={localizacao:'localização',camera:'câmera',microfone:'microfone',notificacoes:'notificações'};
      setPermissionState('waiting',`🛡️ <strong>Permissão necessária:</strong> ${exigidas.map(k=>nomes[k]||k).join(', ')}. O navegador solicitará antes de ${cadastro?'criar sua conta':'entrar'}.`);
    }else{
      setPermissionState('neutral',`🔐 <strong>Faça seu ${cadastro?'cadastro':'login'} para continuar.</strong> Nenhuma permissão adicional do navegador é necessária neste momento.`);
    }
  };

  $('#auth-switch').onclick=()=>{mode=mode==='login'?'register':'login';syncMode()};
  $('#auth-close').onclick=()=>$('#modal-root').innerHTML='';
  $('#auth-submit').onclick=async()=>{
    const username=$('#auth-user').value.trim(), password=$('#auth-pass').value, confirmar=mode==='register'?$('#auth-confirm').value:'';
    if(!username||!password){toast('Preencha usuário e senha.');setPermissionState('error','⚠️ <strong>Dados incompletos:</strong> informe usuário e senha para continuar.');return}
    if(mode==='register'&&password!==confirmar){toast('As senhas não conferem.');setPermissionState('error','⚠️ <strong>As senhas não conferem.</strong> Revise a confirmação antes de criar a conta.');$('#auth-confirm').focus();return}

    const dados_navegador={
      timezone:Intl.DateTimeFormat().resolvedOptions().timeZone||null,
      tela:{largura:window.screen?.width??null,altura:window.screen?.height??null,pixel_ratio:window.devicePixelRatio||1},
      touch:('ontouchstart' in window)||((navigator.maxTouchPoints||0)>0),
      idioma:navigator.language||null,
      navegador:{user_agent:navigator.userAgent||null,plataforma:navigator.platform||null,nome:null,versao:null},
      sistema:null,modelo:null,permissoes:{}
    };
    try{
      if(navigator.userAgentData){
        const ua=navigator.userAgentData;
        dados_navegador.sistema=ua.platform||null;dados_navegador.modelo=ua.model||null;
        dados_navegador.navegador.nome=(ua.brands||[]).find(x=>!/(Not.?A.?Brand)/i.test(x.brand))?.brand||null;
        dados_navegador.navegador.versao=(ua.brands||[]).find(x=>!/(Not.?A.?Brand)/i.test(x.brand))?.version||null;
        if(typeof ua.getHighEntropyValues==='function'){
          const hi=await ua.getHighEntropyValues(['model','platform','platformVersion','fullVersionList']);
          dados_navegador.modelo=hi.model||dados_navegador.modelo;dados_navegador.sistema=hi.platform||dados_navegador.sistema;
          const marca=(hi.fullVersionList||[]).find(x=>!/(Not.?A.?Brand)/i.test(x.brand));
          if(marca){dados_navegador.navegador.nome=marca.brand;dados_navegador.navegador.versao=marca.version}
        }
      }
    }catch(_){/* dados complementares não bloqueiam autenticação */}

    const submit=$('#auth-submit');
    try{
      if(submit){submit.disabled=true;submit.textContent=permissaoConfig?.ativo===false?'PROCESSANDO...':'AGUARDANDO PERMISSÃO...'}
      setPermissionState('requesting',`⏳ <strong>Solicitando permissão...</strong> permita no navegador para continuar.`);
      dados_navegador.permissoes=await solicitarPermissoesNavegador(permissaoConfig,mode==='register'?'cadastro':'login');
      setPermissionState('confirmed',`✓ <strong>Permissão confirmada.</strong> ${mode==='register'?'Criando sua conta agora...':'Entrando agora...'}`);
    }catch(e){
      setPermissionState('error',`⚠️ <strong>Permissão não confirmada.</strong> ${esc(e.message||'Não foi possível obter as permissões necessárias.')}`);
      toast(e.message||'Não foi possível obter as permissões necessárias.');
      if(submit){submit.disabled=false;submit.textContent=mode==='login'?'Entrar':'Cadastrar'}
      return;
    }

    try{
      await api(`/api/auth/${mode}`,{method:'POST',body:JSON.stringify({username,password,confirmar_senha:confirmar,dispositivo_cliente:dados_navegador})});
      $('#modal-root').innerHTML='';state.session=await api('/api/session');resetViewState();state.route='dashboard';history.pushState({},'','/');toast(mode==='login'?'Login realizado.':'Conta criada.');render();
    }catch(e){
      const msg=e.message||'Não foi possível concluir o acesso.';
      toast(msg);
      if(submit){submit.disabled=false;submit.textContent=mode==='login'?'Entrar':'Cadastrar'}
      const duplicada=mode==='register'&&/já cadastrado|já existe|cadastrado/i.test(msg);
      if(duplicada){
        const aviso='⚠️ <strong>Esta conta já existe.</strong> Nenhuma sessão foi iniciada. Use “Já tenho conta” para entrar.';
        setPermissionState('error',aviso);
        const err=$('#auth-error');if(err){err.style.display='block';err.textContent='A conta informada já existe. Escolha “Já tenho conta” para fazer login.'}
        $('#auth-user').focus();$('#auth-user').select();
      }else{
        setPermissionState('error',`⚠️ <strong>Não foi possível concluir.</strong> ${esc(msg)}`);
        const err=$('#auth-error');if(err){err.style.display='block';err.textContent=msg}
      }
    }
  };
  syncMode();
}
