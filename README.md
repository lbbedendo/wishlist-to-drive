# 📦 wishlist-to-drive

**wishlist-to-drive** é um scraper automatizado em **Python + Selenium** que coleta livros de wishlists da **Amazon**, gera arquivos **HTML e JSON**, e envia automaticamente para o **Google Drive**.

Ideal para quem quer **organizar ou arquivar listas de leitura**, criar **dashboards pessoais** ou integrar os dados em outros sistemas.

---

## 🚀 Funcionalidades

- Extrai **título da wishlist** e **livros com autor e URL**  
- Gera automaticamente:
  - `amazon_wishlist_<ID>.html` — cópia da página completa  
  - `amazon_wishlist_<ID>.json` — dados estruturados dos livros  
- Envia ambos os arquivos diretamente para o **Google Drive**
- Suporte a **múltiplas wishlists** via variável de ambiente

---

## 🧩 Requisitos

- Python **3.9+**
- Google Cloud Service Account com acesso ao Google Drive
- Chrome e ChromeDriver (instalado automaticamente via `webdriver-manager`)

Instale as dependências:

```bash
pip install -r requirements.txt
```
## ⚙️ Configuração

Crie um arquivo .env na raiz do projeto com as seguintes variáveis:

```
AMAZON_LIST_URLS="https://www.amazon.com.br/hz/wishlist/ls/XXXXXXXXXXXX, https://www.amazon.com.br/hz/wishlist/ls/YYYYYYYYYYYY"
GDRIVE_FOLDER_ID="SEU_FOLDER_ID_DO_GOOGLE_DRIVE"
SERVICE_ACCOUNT_FILE="service_account.json"
```

💡 AMAZON_LIST_URLS pode conter múltiplas URLs separadas por vírgula.
💡 SERVICE_ACCOUNT_FILE deve apontar para o caminho do arquivo JSON da sua service account.

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
├── requirements.txt         # Dependências Python
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
- Cada wishlist será acessada e salva como HTML e JSON.
- Os arquivos serão automaticamente enviados para o Google Drive.

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
- python-dotenv — Variáveis de ambiente
- Google Drive API — Upload automático
- Chrome Headless — Execução sem janela