# 🤖 Bot de Gastos Inteligente (Telegram + Gemini + Supabase)

Um bot para Telegram que te ajuda a registrar e visualizar seus gastos e ganhos de forma inteligente, usando o poder da inteligência artificial (Gemini API) para categorização e análise. Gerencie suas finanças de forma conversacional e visualize seus dados em gráficos claros.

---

## ✨ Funcionalidades

* **Registro Fácil de Gastos e Ganhos:** Basta enviar mensagens em linguagem natural como:
    * `Gastei 50 no mercado hoje no pix`
    * `Recebi meu salário de 3000`
    * `Dia 4 de julho Uber no valor de 10,98 no crédito`

* **Categorização Inteligente:** O bot usa o Gemini para sugerir e aplicar automaticamente categorias para seus gastos (ex: "mercado" vira "Alimentação").

* **Confirmação e Edição:** Após o reconhecimento, o bot pede confirmação e permite corrigir qualquer campo (valor, categoria, data, forma de pagamento, descrição).

* **Gestão de Categorias:**
    * Liste suas categorias (`/categorias`).
    * Adicione novas categorias (automaticamente pelo Gemini ou via comando como `/adicionar_categoria Lazer`).
    * Defina limites de gastos para categorias (`/definir_limite Alimentacao 800`).
    * Adicione aliases (sinônimos) para categorias para um reconhecimento ainda mais inteligente (`/adicionar_alias Alimentacao mercado,supermercado`).

* **Registro de Forma de Pagamento:** Guarde como você pagou (crédito, débito, Pix, dinheiro).

* **Visualização de Dados (Gráficos):**
    * **Balanço Mensal:** Gráfico de ganhos vs. gastos (`/balanco`).
    * **Gastos por Categoria:** Gráfico de distribuição de gastos por categoria, com limites (`/gastos_por_categoria`).
    * **Gastos por Forma de Pagamento:** Gráfico de distribuição de gastos por forma de pagamento (`/total_por_pagamento`).
    * **Gastos Combinados:** Gráfico mensal detalhado por categoria e forma de pagamento (`/gastos_mensal_combinado`).
    * **Filtros Inteligentes:** Peça gráficos com filtros por data (`... de julho`, `... este mês`) ou forma de pagamento/categoria específica (`... no crédito`, `... em Moradia`).

* **Listagem Detalhada:** Veja uma lista textual de gastos por mês ou categoria (`/listar_gastos 2025-07`, `/listar_gastos Transporte`).

* **Edição e Exclusão (Funcionalidade a Ser Reativada):** O bot possui a estrutura para editar e excluir gastos específicos, permitindo total controle sobre seus registros.

---

## 🚀 Como Rodar o Projeto

Este projeto é configurado para rodar **localmente**, utilizando a **Gemini API** da Google.

### Pré-requisitos

* **Python 3.9+** instalado.
* **`pip`** (gerenciador de pacotes do Python).
* **Uma conta no Telegram** para criar seu bot.
* **Uma conta no Supabase** para o banco de dados.
* **Uma chave de API do Google Gemini** (gerada em [Google AI Studio](https://aistudio.google.com/)).

### 1. Configuração do Ambiente

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/missetubal/bot-gastos.git](https://github.com/missetubal/bot-gastos.git)
    cd bot-gastos
    ```

2.  **Crie e Ative um Ambiente Virtual:**
    É crucial usar um ambiente virtual para isolar as dependências do projeto.
    ```bash
    python3.9 -m venv venv_bot_gastos
    source venv_bot_gastos/bin/activate  # No Linux/macOS
    # Ou `.\venv_bot_gastos\Scripts\activate` no Windows
    ```

3.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure o Arquivo `.env`:**
    Crie um arquivo chamado `.env` na **raiz do projeto** (na mesma pasta que o `src/` e `requirements.txt`). Cole o conteúdo abaixo, substituindo os placeholders (`SEU_..._AQUI`) pelas suas credenciais reais.
    ***MUITO IMPORTANTE: Não compartilhe seu arquivo `.env` publicamente!***
    ```dotenv
    # .env
    TELEGRAM_BOT_TOKEN="SEU_TOKEN_DO_BOT_TELEGRAM_AQUI"
    SUPABASE_URL="https://SUA_URL_DO_PROJETO.supabase.co"
    SUPABASE_KEY="SUA_ANON_KEY_PUBLICA_AQUI"
    GOOGLE_API_KEY="SUA_CHAVE_API_DO_GEMINI_AQUI"
    ```

### 2. Configuração do Supabase

1.  **Crie um Projeto no Supabase:** Se ainda não o fez, crie um novo projeto no Supabase.
2.  **Crie as Tabelas:** No "Table Editor" do Supabase, crie as seguintes tabelas com as estruturas abaixo. Lembre-se de configurar as **Chaves Primárias (Primary Key)** como `uuid` com `gen_random_uuid()` como default, e as **Chaves Estrangeiras (Foreign Key)** corretamente.

    * **`categorias`**
        * `id` (uuid, PK, default: `gen_random_uuid()`)
        * `created_at` (timestamp with time zone, default: `now()`, Not Null)
        * `nome` (text, Not Null, Unique)
        * `limite_mensal` (double precision, Nullable)
        * `aliases` (text\[\], Nullable)

    * **`formas_pagamento`**
        * `id` (uuid, PK, default: `gen_random_uuid()`)
        * `created_at` (timestamp with time zone, default: `now()`, Not Null)
        * `nome` (text, Not Null, Unique)

    * **`ganhos`**
        * `id` (uuid, PK, default: `gen_random_uuid()`)
        * `created_at` (timestamp with time zone, default: `now()`, Not Null)
        * `valor` (double precision, Not Null)
        * `descricao` (text, Not Null)
        * `data` (date, Not Null)

    * **`gastos`**
        * `id` (uuid, PK, default: `gen_random_uuid()`)
        * `created_at` (timestamp with time zone, default: `now()`, Not Null)
        * `valor` (double precision, Not Null)
        * `categoria_id` (uuid, Not Null, FK para `categorias.id`)
        * `data` (date, Not Null)
        * `forma_pagamento_id` (uuid, Nullable, FK para `formas_pagamento.id`)
        * `descricao` (text, Nullable)

3.  **Adicione Formas de Pagamento Iniciais:** Na tabela `formas_pagamento`, adicione manualmente algumas formas de pagamento. Sugestões: `Crédito`, `Débito`, `Pix`, `Dinheiro`, `Não Informado`.

4.  **Configure as Políticas RLS (Row Level Security):** Para que seu bot possa ler e escrever nas tabelas, você precisa configurar políticas RLS para `categorias`, `formas_pagamento`, `ganhos` e `gastos`.
    * No Supabase, vá em **"Authentication" -> "Policies"**.
    * Para **cada uma das 4 tabelas (`categorias`, `formas_pagamento`, `ganhos`, `gastos`)**:
        * Clique em `New Policy`.
        * Escolha `Quickstart: Policy for full access` (ou crie manualmente `FOR ALL TO anon USING (TRUE) WITH CHECK (TRUE)`).
        * Salve a política.

### 3. Crie seu Bot no Telegram

1.  No Telegram, converse com o **`@BotFather`**.
2.  Use o comando `/newbot` e siga as instruções para dar um nome e um `username` ao seu bot.
3.  O `@BotFather` te dará um **Token de API**. Cole-o no seu arquivo `.env`.

### 4. Rodar o Bot Localmente

1.  **Limpe o cache do Python:**
    ```bash
    find . -name "__pycache__" -exec rm -rf {} +
    ```
2.  **Inicie o Bot:**
    No terminal, na pasta raiz do seu projeto (`bot-gastos`):
    ```bash
    python -m src.main
    ```

Seu bot estará rodando e pronto para interagir no Telegram!

---

## ☁️ Deploy em Produção (Opções Avançadas)

Rodar localmente é ótimo para desenvolvimento. Para ter seu bot online 24/7, você pode considerar:

* **Render.com:** Plataforma PaaS com Free Tier (pode ter limites de CPU/RAM). Requer `Procfile` e configuração de variáveis de ambiente.
* **Google Cloud Run:** Serviço serverless com Free Tier muito generoso. Exige Docker e gcloud CLI.

Para ambos, você precisaria do `Procfile` (para Render) ou `Dockerfile` (para Cloud Run) e configurar a URL do webhook do serviço no Telegram (usando o script `set_webhook.py`).

---

## 🤝 Como Contribuir

1.  Faça um fork deste repositório.
2.  Crie uma nova branch (`git checkout -b feature/sua-feature`).
3.  Faça suas alterações e commite (`git commit -m 'feat: adicionei nova funcionalidade X'`).
4.  Envie para sua branch (`git push origin feature/sua-feature`).
5.  Abra um Pull Request.
</immersive>
