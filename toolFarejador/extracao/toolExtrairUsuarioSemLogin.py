from datetime import datetime
import json
import os
import hashlib
from pathlib import Path



def gerador_hash(texto):
    texto = str(texto)
    hash_ = hashlib.sha256(texto.encode()).hexdigest()
    
    return hash_



def salvar_dados_json(dados,caminho):
    with open(caminho,"w",encoding="utf-8") as arquivo:
        json.dump(dados,arquivo,ensure_ascii=False,indent=4)



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



try:
    import instaloader
except ImportError:
    instaloader = None







def extraindo_perfil(cliente_usuario,pesquisar_perfil):


    from toolFarejador.extracao.modulo_extrair_perfil import extrair_perfil

    dados_perfil = extrair_perfil(pesquisar_perfil)

    from toolFarejador.usuarios.toolDadosUsuario import caminho_dados_usuario
    caminho_log  = caminho_dados_usuario(cliente_usuario, 'log', 'perfil.json')

    caminho_log.parent.mkdir(parents=True, exist_ok=True)

    if not caminho_log.exists():
        caminho_log.write_text("[]", encoding="utf-8")

    salvar_dados_json(dados_perfil,caminho_log)
    
    return dados_perfil



if __name__ == "__main__":

    cliente_usuario  = 'admin'
    pesquisar_perfil = "yhagocinaudis"
    
    resultado = extraindo_perfil(cliente_usuario,pesquisar_perfil)







