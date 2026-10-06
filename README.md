# 📦 wishlist-to-drive

**wishlist-to-drive** é um scraper automatizado em **Python + Selenium** que coleta livros de wishlists da **Amazon**, gera arquivos **HTML e JSON**, e envia automaticamente para o **Google Drive**.

Ideal para quem quer **organizar ou arquivar listas de leitura**, criar **dashboards pessoais** ou integrar os dados em outros sistemas.

---

## 🚀 Funcionalidades

- Extrai **título da wishlist** e **livros com autor e URL**  
- Gera automaticamente:
  - `amazon_wishlist_<ID>.html` — cópia da página completa  
  - `amazon_wishlist_<ID>.json` — dados estruturados dos livros  
- Envia ambos os arquivos diretamente para o **Google Drive** (atualizando o arquivo existente com o mesmo nome, sem criar duplicatas)
- Rola a página até o fim para carregar **todos os itens** de wishlists longas
- Suporte a **múltiplas wishlists** via arquivo `wishlist.txt`

---

## 🧩 Requisitos

- Python **3.9+**
- Google Cloud Service Account com acesso ao Google Drive
- Chrome e ChromeDriver (instalado automaticamente via `webdriver-manager`)

## ⚙️ Configuração

Crie um arquivo .env na raiz do projeto com as seguintes variáveis:

```
GDRIVE_FOLDER_ID="SEU_FOLDER_ID_DO_GOOGLE_DRIVE"
SERVICE_ACCOUNT_FILE="service_account.json"
```

💡 SERVICE_ACCOUNT_FILE deve apontar para o caminho do arquivo JSON da sua service account.

### Wishlists

As wishlists ficam no arquivo `wishlist.txt`, na raiz do projeto. Ele é pessoal e não é versionado; crie-o a partir do modelo:

```bash
cp wishlist.txt.template wishlist.txt
```

Uma wishlist por linha, com a URL completa ou apenas o ID. Linhas em branco são ignoradas e `#` inicia um comentário:

```
# Ficção
https://www.amazon.com.br/hz/wishlist/ls/XXXXXXXXXXXX
YYYYYYYYYYYY   # só o ID também funciona (usa amazon.com.br)
```

Linhas inválidas e wishlists duplicadas são ignoradas com um aviso no log.

## 🔐 Configurando a Service Account (Google Cloud)

1. Acesse [Google Cloud Console](https://console.cloud.google.com/welcome?project=amazon-wishlist-scraper)
2. Vá para IAM e Admin → Contas de serviço.
3. Clique em Criar conta de serviço e siga os passos:
   - Nome da conta: wishlist-to-drive
   - Função: Editor ou Drive File Creator
4. Após criada, acesse a conta e vá em Chaves → Adicionar chave → Criar nova chave.
5. Escolha o formato JSON e salve o arquivo como service_account.json na raiz do projeto.
6. No seu Google Drive, crie uma pasta e copie o ID dela (o trecho após /folders/ na URL).
7. Compartilhe essa pasta com o e-mail da sua service account (presente no JSON).

## 🧠 Estrutura do Projeto

```
wishlist-to-drive/
├── gdrive.py                # Autenticação e upload para o Google Drive
├── main.py                  # Script principal de scraping
├── wishlists.py             # Leitura do arquivo wishlist.txt
├── tests/                   # Testes unitários (pytest)
├── requirements.txt         # Dependências Python
├── requirements-dev.txt     # Dependências de desenvolvimento (pytest)
├── wishlist.txt.template    # Modelo da lista de wishlists
├── wishlist.txt             # Suas wishlists (não versionado)
├── .env                     # Variáveis de ambiente
├── service_account.json     # Credenciais da service account
└── output/                  # Arquivos HTML e JSON gerados
```

## ▶️ Executando o Script
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Durante a execução:
- Cada wishlist será acessada, rolada até o fim e salva como HTML e JSON.
- Apenas os arquivos gerados nesta execução são enviados ao Google Drive; arquivos com o mesmo nome na pasta são atualizados.

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest
```

## 📁 Output

Os arquivos gerados são salvos em output/ e enviados ao Google Drive.

Exemplo:
```
output/
├── amazon_wishlist_33CDZWIZN8JHQ.html
├── amazon_wishlist_33CDZWIZN8JHQ.json
└── amazon_wishlist_3SXT8GLB7APWA.json
```

## 🧰 Tecnologias Utilizadas

- [Selenium](https://www.selenium.dev/) — Automação do navegador
- [webdriver-manager](https://pypi.org/project/webdriver-manager/) — Instalação automática do ChromeDriver
- [python-dotenv](https://pypi.org/project/python-dotenv/) — Variáveis de ambiente
- [Google Drive API](https://developers.google.com/workspace/drive/api/guides/about-sdk) — Upload automático
- [Chrome Headless](https://developer.chrome.com/docs/chromium/headless) — Execução sem janela