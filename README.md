## Farejador 1.6.0

Evolução focada em análise comportamental real do histórico JSON: qualidade do histórico, sequências, oscilações, intervalos entre capturas, mudanças por campo, insights e novos rankings. O armazenamento continua em JSON e os módulos de análise são somente leitura.

# Farejador — Instagram

Aplicação web construída sobre o projeto `semLogin/instagram`, usando FastAPI no backend e HTML/CSS/JavaScript no frontend.

## Organização

- `backend/`: API, autenticação e integração com os módulos.
- `frontend/`: interface responsiva para computador e celular.
- `toolFarejador/`: módulos de extração, salvamento, monitoramento, notificações e análise.
- `dados/`: dados operacionais separados por `cliente_usuario`.
- `user/`: usuários cadastrados e sessões do sistema.
- `config/sistema/`: somente configurações globais do sistema.
- `layout/`: layouts fornecidos como referência visual.

## Identidade do cliente

O backend resolve `cliente_usuario` pela sessão autenticada. O token fica em cookie HTTP-only e aponta para o usuário cadastrado. Os dados operacionais continuam separados em `dados/<cliente_usuario>/`.

Visitantes não autenticados usam `admin` somente como fonte pública de visualização e não possuem acesso às rotas de consulta/edição.

## Monitoramento em tempo real

`monitoramento_perfis_tempo_real()` é uma função global do sistema e não recebe parâmetros. Ela fica em `toolFarejador/toolMonitoramentoSistema.py`, percorre os diretórios de monitoramento de todos os `cliente_usuario` e executa o monitoramento dos perfis ativos.

A interface de **Usuários Salvos** apenas controla o estado `monitorando` de cada perfil. Ela não inicia um monitor independente por usuário. O backend inicia uma única thread de monitoramento do sistema no startup.

## Modelo de dados usado pela interface

A interface utiliza os arquivos de `dados/<cliente_usuario>/` como fonte dos dados operacionais. Em especial:

- `perfil_salvos/<pk>.json`: perfil e conteúdo atualmente salvo pelo cliente.
- `historico/<pk>.json`: snapshots reais capturados pelo monitoramento, cada um contendo `perfil`, `hash`, `timestamp_capture` e `conteudo`.
- `monitoramento/<pk>.json`: estado `monitorando`, `sleep`, `pk`, `username` e `atualizado`.
- `notificacoes/<pk>.json`: última situação de atividade daquele perfil.
- `feed/feed.json`: consolidação das notificações do cliente.
- `resumo/<pk>.json`: timeline (`timiline`, nome mantido por compatibilidade com o modelo existente) e histórico por campo.

Para o **Resumo**, o estado atual é derivado do último snapshot de `historico`, e a variação inicial é calculada comparando o primeiro e o último snapshot. Isso evita mostrar no painel um `perfil_salvo` antigo depois que o monitoramento já capturou alterações.

A tela de **Histórico** trata corretamente os dois formatos presentes no modelo: registros iniciais usam `valor`, enquanto alterações usam `valor_anterior` e `valor_atual`.

## Remoção de perfil

A remoção usa `cliente_usuario + pk` para localizar os dados. Os campos de caminho gravados nos JSONs são apenas metadados, porque arquivos antigos podem conter caminhos absolutos de outra máquina. Ao remover um perfil são eliminados os dados derivados em `perfil_salvos`, `historico`, `monitoramento`, `notificacoes` e `resumo`; depois o `feed/feed.json` é reconstruído com as notificações restantes.

## Instalação

```bash
pip install -r requirements.txt
python run.py
```

Abra `http://127.0.0.1:8000`.

## Identificadores

O `pk` do Instagram continua sendo a chave dos arquivos de perfil. O `hash` já existente continua apenas como mecanismo de deduplicação dos snapshots do histórico. Nenhum novo `id_hash` foi criado para substituir esses identificadores.

## Evolução 1.2 — camada pública sem banco de dados

A aplicação continua usando **JSON como armazenamento**, sem alterar a lógica dos módulos de extração, histórico, monitoramento e notificações.

Foram adicionados:

- páginas públicas de perfil em `/perfil/<username>`;
- busca pública por usuário/nome;
- exploração dos perfis disponíveis;
- resumo público com crescimento e quantidade de capturas;
- seção **O que mudou?** usando a timeline real do histórico;
- comparação pública em `/comparar`;
- feed público somente leitura;
- endpoints públicos somente leitura em `/api/public/*`;
- endpoint `/api/health` para verificar a aplicação;
- limite simples de requisições para a consulta autenticada de perfis;
- gravação atômica dos principais arquivos JSON de serviço/autenticação;
- cookies configuráveis para produção;
- CORS configurável por variável de ambiente;
- execução configurável por ambiente no `run.py`.

### Variáveis opcionais de produção

```text
FAREJADOR_HOST=0.0.0.0
FAREJADOR_PORT=8000
FAREJADOR_RELOAD=0
FAREJADOR_COOKIE_SECURE=1
FAREJADOR_COOKIE_SAMESITE=lax
FAREJADOR_RATE_LIMIT=30
FAREJADOR_CORS_ORIGINS=https://seudominio.com
```

Durante testes locais, `FAREJADOR_COOKIE_SECURE=0` deve permanecer desligado quando o acesso for feito por HTTP. Em HTTPS, use `FAREJADOR_COOKIE_SECURE=1`.

Para executar testes sem iniciar a thread global de monitoramento:

```text
FAREJADOR_DISABLE_MONITOR=1
```

A camada pública é somente leitura e utiliza os dados do `admin` já existentes como fonte pública. Ela não cria uma segunda estrutura de dados e não altera os JSONs de monitoramento.

## Evolução 1.3 — Explorar e rankings públicos

Mantendo JSON como armazenamento e sem alterar os módulos centrais, a aplicação ganhou uma camada de descoberta pública:

- página `/explorar`;
- endpoint somente leitura `/api/public/explore`;
- ranking de maior crescimento proporcional de seguidores;
- ranking de maior número de seguidores;
- ranking de perfis mais ativos com base em eventos/capturas já registrados;
- ranking de maior volume de conteúdo;
- navegação pública entre rankings e páginas de perfil;
- filtro do feed usando o campo real `movimento`, em vez de inferência pelo texto exibido;
- layout responsivo para os novos rankings.

Os rankings não criam nenhum JSON novo. Eles são calculados sob demanda a partir de `perfil_salvos`, `historico` e da timeline já existente. Perfis com histórico incompleto continuam aparecendo sem derrubar a página.


## Evolução 1.5

- Página pública de perfil ampliada com evolução, histórico e timeline.
- Histórico de biografia com comparação Antes/Depois.
- Histórico de privacidade, verificação e memorialização.
- Gráfico de evolução de seguidores usando as capturas existentes.
- Comparador com líderes, crescimento proporcional, atividade e diferença de seguidores.
- Rankings separados por crescimento percentual e absoluto.
- Ranking de atividade recalculado a partir dos eventos/capturas existentes.
- Nenhuma migração de JSON para banco de dados.
- Nenhuma alteração no formato dos arquivos de histórico existentes.


## Evolução 1.5

A página pública de perfil ganhou uma camada de análise somente leitura em `toolFarejador/toolAnalisePerfil.py`, com períodos de crescimento, ritmo diário, tendência, recordes, heatmap de atividade, insights e projeção matemática. Nenhum JSON existente é alterado por essas análises.


## Estrutura do sistema

```text
sistema/
├── dados/
│   └── publico/       # cópia somente-leitura derivada de dados/admin
├── config/
│   └── monitoramento_perfis.json
└── user/
    ├── usuarios.json
    └── sessoes.json
```

`dados/admin` continua sendo a fonte de verdade. A função
`toolFarejador.toolSistemaPublico.sincronizar_dados_publicos()` espelha
os dados administrativos para `sistema/dados/publico`, permitindo que
as rotas públicas não dependam diretamente dos arquivos administrativos.


## Evolução 1.8
- Feed com visual de monitoramento ao vivo e atualização automática.
- Rankings do Explorer exibidos individualmente por seletor, com "Mais ativos" como padrão.
- Explorer, Feed, Comparar e perfil respeitam o `cliente_usuario` quando autenticado.
- Comparador com seleção guiada de usuários salvos.
- Tratamento amigável para análises sem resultado.
- Registro de atividade de autenticação em `sistema/user/atividade`.


## Evolução 1.9 — modelo completo de usuário e sessões

Cada usuário cadastrado possui uma pasta individual:

```text
sistema/user/<cliente_usuario>/
├── usuario.json
├── sessoes.json
├── atividades.json
└── dados/
```

`usuario.json` guarda identidade e estado da conta. `sessoes.json` guarda cada sessão com status, IP, origem, navegador, sistema, modelo quando o navegador fornecer essa informação, idioma, timezone e características básicas da tela. `atividades.json` registra cadastro, login e logout sem armazenar a senha em texto puro.

No cadastro a interface solicita **senha + confirmação da senha** e o backend também valida a confirmação, portanto não é apenas uma validação visual.

A origem de acesso utiliza o cabeçalho HTTP `Referer` quando disponível e captura `utm_source`, `utm_medium` e `utm_campaign` quando esses parâmetros estiverem presentes. O IP é obtido pelo backend; `X-Forwarded-For` somente é aceito quando `FAREJADOR_TRUST_PROXY=1`.

O navegador fornece informações complementares sem acesso a arquivos, câmera, microfone ou outros recursos privados. O modelo exato do dispositivo pode ficar `null` quando o navegador não o disponibilizar.

O armazenamento continua exclusivamente em JSON.
