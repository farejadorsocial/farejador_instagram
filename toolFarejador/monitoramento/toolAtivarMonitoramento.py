from datetime import datetime
import json
import os
from pathlib import Path



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





def carregar_dados(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    return dados



def salvar_dados_json(dados,caminho):
    with open(caminho,"w",encoding="utf-8") as arquivo:
        json.dump(dados,arquivo,ensure_ascii=False,indent=4)



def criando_registro_monitorar_perfil(selecionado,monitorando):

    pk       = selecionado['perfil']['pk']
    username = selecionado['perfil']['username']
    nome     = selecionado['perfil']['nome']

    registro = {
                'pk':pk,
                'username':username,
                'nome':nome,
                'sleep':10,
                'monitorando':monitorando,
                'atualizado':datetime.now().isoformat()
            }
    
    return registro



def _sincronizar_postgresql(cliente_usuario, dados):
    """Replica a escrita no PostgreSQL sem remover o JSON legado."""
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
        pass
        return []

    for i in caminho_monitorar.glob("*.json"):
        try:
            dados = carregar_dados(i)
        except (OSError, json.JSONDecodeError):
            continue

        if isinstance(dados, dict):
            lista.append(dados)

    return lista
    




def monitorar_perfil(cliente_usuario,selecionado,monitorando=False):
    
    resultado = criando_registro_monitorar_perfil(selecionado,monitorando)
    pk = resultado['pk']

    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_monitorar = caminho_dados_usuario(cliente_usuario, 'monitoramento', f'{pk}.json')
    caminho_monitorar.parent.mkdir(parents=True,exist_ok=True)

    if not caminho_monitorar.exists():
        caminho_monitorar.write_text("{}",encoding="utf-8")

    salvar_dados_json(resultado,caminho_monitorar)
    _sincronizar_postgresql(cliente_usuario, resultado)
    
    return resultado



selecionado = {'perfil': {'pk': 65832742299,
  'id': None,
  'username': 'thallyta.isabelly',
  'nome': '𝐓',
  'biografia': '𝘴𝘦 𝘩á 𝘢𝘭𝘨𝘰 𝘣𝘰𝘮\n𝘦𝘮 𝘮𝘪𝘮,é 𝘑𝘦𝘴𝘶𝘴',
  'privado': True,
  'verificado': False,
  'memorializado': None,
  'seguidores': 356,
  'seguindo': 391,
  'total_posts': 0,
  'total_reels': 0,
  'total_destaques': 0,
  'pronomes': [],
  'links': [],
  'foto_perfil': 'https://instagram.fbsb3-1.fna.fbcdn.net/v/t51.82787-19/732875430_17950316778198300_1037440013426501176_n.jpg?stp=dst-jpg_s320x320_tt6&efg=eyJ2ZW5jb2RlX3RhZyI6InByb2ZpbGVfcGljLmRqYW5nby4xMDgwLmMyIn0&_nc_ht=instagram.fbsb3-1.fna.fbcdn.net&_nc_cat=100&_nc_oc=Q6cZ2gHmfe2vL5SXcHiA8KYwMghChd7hiT7RgoqSwWZtoe3tan5bo2WClC49ElVSikpRqlhQtMeRUEeLCNTMbNqQs-sR&_nc_ohc=Lu6hNXF87wMQ7kNvwGpLXYK&_nc_gid=Mni6IxfaQrMeuW_WkWpf6A&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AQFgcVnjUabcJ0ynU6W57G-796aKCpND0kIoivU8lQBXIw&oe=6A90A7CD&_nc_sid=8b3546'},
 'conteudo': {'posts': [],
  'reels': [],
  'destaques': [],
  'erro_destaques': {'tipo': 'AttributeError',
   'mensagem': "'Profile' object has no attribute 'get_highlights'"}},
 'caminho_perfil_salvo': 'C:\\Users\\YHAGO\\OneDrive\\projeto\\farejador\\rede_social\\semLogin\\instagram\\dados\\admin\\perfil_salvos\\65832742299.json',
 'caminho_historico_salvo': 'C:\\Users\\YHAGO\\OneDrive\\projeto\\farejador\\rede_social\\semLogin\\instagram\\dados\\admin\\historico\\65832742299.json'}

if __name__ == "__main__":

    cliente_usuario  = 'admin'

    monitorar = monitorar_perfil(cliente_usuario,selecionado,monitorando=True)

    lista_monitoramento_perfil = lista_perfil_monitorados(cliente_usuario)








