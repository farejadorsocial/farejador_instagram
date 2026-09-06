# Farejador — Instagram

Plataforma de monitoramento, histórico, descoberta e análise de perfis do Instagram.

O Farejador utiliza **FastAPI no backend, JavaScript/CSS no frontend e PostgreSQL como banco de dados oficial da aplicação**.

## Visão geral

O sistema acompanha perfis e transforma os dados coletados em histórico, indicadores e recursos de descoberta. A aplicação possui áreas públicas e autenticadas, mantendo o isolamento dos dados conforme o contexto do usuário.

Principais recursos:

- monitoramento de perfis;
- histórico de capturas e alterações;
- análise de crescimento e atividade;
- timeline de eventos;
- Feed;
- Explorar;
- Rankings;
- comparação de perfis;
- páginas públicas de perfil;
- busca e descoberta por categorias;
- autenticação e sessões de usuários;
- controle de perfis salvos;
- análises e insights derivados do histórico.

## Arquitetura

```text
farejador_instagram/
├── backend/       # API, autenticação, regras de negócio e acesso aos dados
├── frontend/      # interface web responsiva
├── toolFarejador/ # extração, monitoramento e processamento dos dados
├── config/        # configurações da aplicação
├── sistema/       # componentes e dados auxiliares do sistema
└── README.md
```

### Backend

O backend é construído com **FastAPI** e concentra as APIs, autenticação, regras de acesso e integração com os serviços do Farejador.

### Frontend

A interface utiliza HTML, CSS e JavaScript modular, com navegação entre Dashboard, Explorar, Ranking, Feed, Comparar, perfis e recursos autenticados.

### Banco de dados

O **PostgreSQL é a fonte oficial de persistência do sistema**.

Os dados da aplicação não dependem mais de uma estrutura de armazenamento baseada em arquivos JSON. Consultas, persistência e isolamento dos dados devem utilizar a camada de banco de dados definida pelo backend.

Isso permite que o projeto evolua para maior volume de dados, consultas históricas, rankings, múltiplos usuários e execução em ambiente de produção sem depender de arquivos locais como banco principal.

> Arquivos JSON que eventualmente existam no repositório podem representar configuração, dados auxiliares, fixtures ou componentes legados específicos. Eles não devem ser tratados como o banco de dados oficial da aplicação.

## Usuários e isolamento de dados

O sistema possui contexto de usuário autenticado. Os recursos privados devem trabalhar somente com os dados pertencentes ao usuário da sessão atual.

Visitantes não autenticados acessam somente os recursos públicos disponibilizados pela aplicação.

O objetivo é manter uma separação clara entre:

- dados públicos;
- dados pertencentes ao usuário autenticado;
- dados internos do sistema.

## Monitoramento

O monitoramento acompanha os perfis ativos e registra suas capturas e alterações no banco de dados.

A interface de perfis salvos controla o estado de monitoramento conforme as regras do backend. O monitoramento é executado pela infraestrutura do sistema, e não deve ser duplicado por uma sessão individual do navegador.

## Histórico e análises

O histórico é a base das análises do Farejador.

A partir das capturas armazenadas, o sistema pode calcular informações como:

- evolução de seguidores;
- crescimento percentual e absoluto;
- ritmo de crescimento;
- atividade;
- alterações de campos do perfil;
- eventos detectados;
- períodos de atividade;
- tendências;
- recordes;
- insights;
- rankings.

As análises são derivadas dos dados armazenados e não devem modificar o histórico original apenas para produzir uma visualização.

## Explorar

A área **Explorar** concentra os critérios de análise e ordenação dos perfis.

Os rankings disponíveis podem incluir:

- 🔥 Mais ativos;
- 📈 Maior crescimento percentual;
- 🚀 Maior crescimento absoluto;
- 👥 Mais seguidores;
- 🎬 Mais conteúdo;
- ⚡ Maior ritmo;
- 🔎 Mais descobertas.

A área também permite filtrar os resultados por categoria.

## Ranking

A página **Ranking** possui uma finalidade diferente da área Explorar.

Ela é dedicada à seleção de **categorias de perfis**, permitindo visualizar o ranking correspondente à categoria escolhida.

Categorias atualmente utilizadas pelo sistema incluem:

- Influenciador;
- Música;
- Ator;
- Atriz;
- Atleta;
- Esporte;
- Futebol;
- Política;
- TV;
- Humor;
- Jornalismo;
- Criador de conteúdo;
- Streamer;
- Outro.

A lista de categorias deve permanecer centralizada na configuração utilizada pela aplicação, evitando duplicação de regras entre as telas.

## Área pública

O Farejador possui endpoints e páginas públicas somente para leitura.

Entre os recursos públicos estão:

- busca de perfis;
- páginas públicas de perfil;
- Explorar;
- Ranking;
- comparação pública;
- Feed público;
- informações de crescimento e histórico disponibilizadas publicamente.

A camada pública não deve conceder acesso a dados privados de outros usuários.

## Comparador

O Comparador permite analisar perfis lado a lado utilizando indicadores derivados dos dados disponíveis, incluindo crescimento, seguidores, atividade e outros indicadores definidos pela aplicação.

Quando autenticado, o comparador deve respeitar o contexto e os perfis disponíveis para aquele usuário.

## Autenticação e sessões

A aplicação possui autenticação de usuários e gerenciamento de sessões.

A sessão utiliza cookie HTTP-only, e o backend determina o usuário associado à requisição antes de acessar dados privados.

Informações de atividade de autenticação podem ser registradas para controle e auditoria do sistema, sem armazenar senhas em texto puro.

## Segurança e produção

Configurações de produção devem ser definidas por variáveis de ambiente, evitando credenciais e segredos diretamente no código-fonte.

Exemplos de configurações utilizadas pelo projeto podem incluir:

```text
FAREJADOR_HOST=0.0.0.0
FAREJADOR_PORT=8000
FAREJADOR_RELOAD=0
FAREJADOR_COOKIE_SECURE=1
FAREJADOR_COOKIE_SAMESITE=lax
FAREJADOR_RATE_LIMIT=30
FAREJADOR_CORS_ORIGINS=https://seudominio.com
```

Em desenvolvimento local com HTTP, o cookie seguro pode precisar permanecer desativado. Em produção com HTTPS, deve ser habilitado.

O acesso ao PostgreSQL também deve ser configurado por ambiente e nunca expor credenciais no código ou no repositório.

## Execução local

Instale as dependências:

```bash
pip install -r requirements.txt
```

Execute a aplicação:

```bash
python run.py
```

Depois acesse:

```text
http://127.0.0.1:8000
```

## Saúde da aplicação

A aplicação possui endpoint de saúde para verificar se o serviço está disponível:

```text
/api/health
```

## Princípios de desenvolvimento

O desenvolvimento do Farejador deve preservar a arquitetura existente e evitar alterações desnecessárias em módulos estáveis.

Antes de alterar uma funcionalidade, deve-se verificar:

1. como o frontend atual utiliza o módulo;
2. quais endpoints do backend alimentam a funcionalidade;
3. quais regras de autenticação e isolamento estão envolvidas;
4. quais dados vêm do PostgreSQL;
5. quais outras telas dependem daquele código;
6. se a alteração mantém o comportamento existente.

Novas funcionalidades devem ser integradas ao padrão visual e estrutural do projeto, evitando telas isoladas ou componentes incompatíveis com a identidade do Farejador.

## Estado do projeto

O Farejador está em evolução contínua. A prioridade é consolidar a plataforma como um produto web estável, seguro e escalável, com o PostgreSQL como base de dados oficial e com separação clara entre coleta, persistência, análise e apresentação.
