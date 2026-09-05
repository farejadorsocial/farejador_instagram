from datetime import datetime
import json
import os
from pathlib import Path



def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados



def salvar_dados_json(dados,caminho):
    """Grava atomicamente para o endpoint de feed nunca ler JSON parcial."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(f".{caminho.name}.tmp")
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)
        arquivo.flush()
        os.fsync(arquivo.fileno())
    temporario.replace(caminho)



def caminho_base(*caminho_final, nome_projeto="instagram"):
    """
    Retorna caminhos relativos à raiz do projeto.

    Funciona no:
    - VSCode
    - Jupyter Notebook
    - Scripts Python
    - Anaconda
    """

    # VSCode / Scripts
    try:
        caminho_atual = Path(__file__).resolve()
    except NameError:
        # Jupyter Notebook
        caminho_atual = Path.cwd().resolve()

    # Procura a raiz do projeto
    for pasta in [caminho_atual] + list(caminho_atual.parents):

        if pasta.name == nome_projeto:

            # junta os caminhos corretamente
            return pasta.joinpath(*caminho_final)

    raise FileNotFoundError(
        f"Não foi encontrada a pasta '{nome_projeto}'."
    )



def carregar_perfis_salvos(cliente_usuario):
    
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_perfil_salvos = caminho_dados_usuario(cliente_usuario, 'perfil_salvos')
    
    lista = []

    if not caminho_perfil_salvos.exists():
        return {
            'usernames': [],
            'dados_perfis': []
        }
    
    for c in caminho_perfil_salvos.glob('*.json'):
        try:
            dados = carregar_dados(c)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(dados, dict):
            lista.append(dados)
        
    lista_username = [i['perfil']['username'] for i in lista]
        
    return {
        'usernames':lista_username,
        'dados_perfis':lista
    }
    




def consultar_id_pk(valor,cliente_usuario):
    
    perfis_salvos = carregar_perfis_salvos(cliente_usuario)

    for i in perfis_salvos['dados_perfis']:

        if (
            i['perfil']['username'] == valor
            or i['perfil']['nome'] == valor
        ):
            return {
                'pk': i['perfil']['pk']
            }

    return None





def notificacao_movimento(lista_usernames,cliente_usuario):

    for username in lista_usernames:

        identificacao = consultar_id_pk(username, cliente_usuario)
        if not identificacao:
            continue

        pk = identificacao['pk']

        from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
        caminho_notificacoes = caminho_dados_usuario(
            cliente_usuario,
            'notificacoes',
            f"{pk}.json"
        )
        
        
        caminho_feed = caminho_dados_usuario(cliente_usuario, 'feed', 'feed.json')

        caminho_notificacoes.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        
        caminho_feed.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        if not caminho_notificacoes.exists():
            caminho_notificacoes.write_text(
                "{}",
                encoding="utf-8"
            )
            
        if not caminho_feed.exists():
            caminho_feed.write_text(
                "[]",
                encoding="utf-8"
            )

        notificacao = carregar_dados(caminho_notificacoes)
        notificacao['cliente_usuario'] = cliente_usuario

        caminho_historico = caminho_dados_usuario(cliente_usuario, 'historico', f'{pk}.json')

        historico = carregar_dados(caminho_historico)

        # Durante a migração, o histórico legado continua sendo a origem
        # compatível com o fluxo atual, mas cada captura também é gravada
        # no PostgreSQL. O sincronizador é idempotente e preserva o JSON.
        try:
            from backend.database.sync import sincronizar_historico
            if isinstance(historico, list):
                for item_historico in historico:
                    sincronizar_historico(cliente_usuario, item_historico)
        except Exception as erro:
            print(f"[postgres] Falha ao sincronizar histórico: {erro}")

        total_atual = len(historico)

        # Primeira execução
        if 'total' not in notificacao:

            notificacao['pk'] = pk
            notificacao['username'] = username
            notificacao['total']     = total_atual
            notificacao['movimento'] = None
            notificacao['timestamp_capture'] = datetime.now().isoformat()
            notificacao['icone']    = '👤✨'
            notificacao['texto']    = 'Novo usuário detectado'
            notificacao['mensagem'] = (
            
                f"👤✨ Novo usuário detectado: {username}"
            )

        # Houve novos registros no histórico
        elif total_atual > notificacao['total']:

            notificacao['pk'] = pk
            notificacao['username'] = username
            notificacao['total'] = total_atual
            notificacao['movimento'] = True
            notificacao['timestamp_capture'] = datetime.now().isoformat()
            notificacao['icone']    = '🚨'
            notificacao['texto']    = 'Movimento detectado no perfil do usuário'
            notificacao['mensagem'] = (
                f"🚨 Movimento detectado no perfil do usuário: {username}"
            )
            

        # Não houve novos registros
        else:

            notificacao['pk'] = pk
            notificacao['username'] = username
            notificacao['total'] = total_atual
            notificacao['movimento'] = False
            notificacao['timestamp_capture'] = datetime.now().isoformat()
            notificacao['icone']    = '💤'
            notificacao['texto']    = 'Sem movimento no perfil do usuário'
            notificacao['mensagem'] = (
                f"💤 Sem movimento no perfil do usuário: {username}"
            )
            
            
            

        salvar_dados_json(
            notificacao,
            caminho_notificacoes
        )
        
        
        caminho_notificacoes2 = caminho_dados_usuario(cliente_usuario, 'notificacoes')
        
        
        feed = []
        
        for i in sorted(caminho_notificacoes2.glob("*.json")):
            try:
                d = carregar_dados(i)
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(d, dict):
                feed.append(d)

        feed.sort(
            key=lambda item: item.get("timestamp_capture", ""),
            reverse=True,
        )
            
            
        salvar_dados_json(
            feed,
            caminho_feed
        )
        
        if notificacao['movimento']:
            return notificacao
            
        


def carregar_feed(cliente_usuario):
    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_feed = caminho_dados_usuario(cliente_usuario, 'feed', 'feed.json')

    try:
        feed = carregar_dados(caminho_feed)
    except (OSError, json.JSONDecodeError):
        return []

    return feed if isinstance(feed, list) else []


if __name__ == "__main__":

    cliente_usuario ='admin'

    lista_usernames = carregar_perfis_salvos(cliente_usuario)['usernames']

    notificacao_movimento(lista_usernames,cliente_usuario)


    feed = carregar_feed(cliente_usuario)


