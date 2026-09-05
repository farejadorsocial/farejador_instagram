from datetime import datetime
import json
from pathlib import Path



def caminho_base(*caminho_final, nome_projeto="instagram"):
    """Retorna caminhos relativos à raiz do projeto."""
    try:
        caminho_atual = Path(__file__).resolve()
    except NameError:
        caminho_atual = Path.cwd().resolve()

    for pasta in [caminho_atual] + list(caminho_atual.parents):
        if pasta.name == nome_projeto:
            return pasta.joinpath(*caminho_final)

    raise FileNotFoundError(f"Não foi encontrada a pasta '{nome_projeto}'.")



def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        return json.load(f)



def salvar_dados_json(dados, caminho):
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=4)



def criando_registro_monitorar_perfil(selecionado, monitorando):
    pk = selecionado['perfil']['pk']
    username = selecionado['perfil']['username']
    nome = selecionado['perfil']['nome']

    return {
        'pk': pk,
        'username': username,
        'nome': nome,
        'sleep': 10,
        'monitorando': monitorando,
        'atualizado': datetime.now().isoformat()
    }



def _sincronizar_postgresql(cliente_usuario, dados):
    try:
        from backend.database.sync import sincronizar_monitoramento
        sincronizar_monitoramento(cliente_usuario, dados)
    except Exception as erro:
        print(f"[postgres] Falha ao sincronizar monitoramento: {erro}")



def lista_perfil_monitorados(cliente_usuario):
    lista = []

    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_monitorar = caminho_dados_usuario(cliente_usuario, 'monitoramento')

    if not caminho_monitorar.exists():
        return []

    for i in caminho_monitorar.glob("*.json"):
        try:
            dados = carregar_dados(i)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(dados, dict):
            lista.append(dados)

    return lista
    



def monitorar_perfil(cliente_usuario, selecionado, monitorando=False):
    resultado = criando_registro_monitorar_perfil(selecionado, monitorando)
    pk = resultado['pk']

    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_monitorar = caminho_dados_usuario(cliente_usuario, 'monitoramento', f'{pk}.json')
    caminho_monitorar.parent.mkdir(parents=True, exist_ok=True)

    if not caminho_monitorar.exists():
        caminho_monitorar.write_text("{}", encoding="utf-8")

    salvar_dados_json(resultado, caminho_monitorar)
    _sincronizar_postgresql(cliente_usuario, resultado)

    return resultado
