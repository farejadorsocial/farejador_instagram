from backend.core import auth

def preparar_usuarios(): return auth.preparar_usuarios()
def register(username, password, dados_acesso=None): return auth.register(username, password, dados_acesso)
def login(username, password, dados_acesso=None): return auth.login(username, password, dados_acesso)
def logout(token): return auth.logout(token)
def get_user(token): return auth.get_user(token)
