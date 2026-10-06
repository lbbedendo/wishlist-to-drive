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
- Execução **agendada no GitHub Actions**, sem chaves de longa duração (Workload Identity Federation)

---

## 🧩 Requisitos

- Python **3.9+**
- Chrome (o ChromeDriver é instalado automaticamente via `webdriver-manager`)
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install)
- Um projeto no Google Cloud e uma service account com acesso a uma pasta do Google Drive

O projeto **não usa chaves JSON de service account** (credenciais de longa duração). A autenticação no Google Drive é feita com credenciais de curta duração:

| Onde roda | Como autentica |
|---|---|
| Localmente | Sua conta Google personifica a service account (`gcloud auth application-default login --impersonate-service-account`) |
| GitHub Actions | Workload Identity Federation: o token OIDC do GitHub é trocado por um token temporário da service account |

Em ambos os casos o código usa as [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials) (`google.auth.default`).

---

## 🔐 Passo 1 — Configurar o Google Cloud (comum aos dois modos)

Defina as variáveis abaixo no terminal; os comandos seguintes as utilizam:

```bash
PROJECT_ID="amazon-wishlist-scraper"        # ID do seu projeto no Google Cloud
SA_NAME="wishlist-to-drive-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud auth login
gcloud config set project "$PROJECT_ID"
```

1. Ative as APIs necessárias:

   ```bash
   gcloud services enable \
     drive.googleapis.com \
     iam.googleapis.com \
     iamcredentials.googleapis.com \
     sts.googleapis.com
   ```

2. Crie a service account (**não crie chaves para ela**):

   ```bash
   gcloud iam service-accounts create "$SA_NAME" --display-name="wishlist-to-drive"
   ```

   A service account não precisa de nenhum papel (role) no projeto: o acesso ao Drive vem do compartilhamento da pasta.

3. No Google Drive, crie uma pasta e copie o ID dela (o trecho após `/folders/` na URL). Exemplo: https://drive.google.com/drive/u/0/folders/<aqui-está-o-id-da-pasta>

4. Compartilhe essa pasta com o e-mail da service account (`$SA_EMAIL`) com permissão de **Editor**.

---

## ▶️ Passo 2a — Executando localmente

1. Dê à sua conta Google permissão para personificar a service account:

   ```bash
   gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
     --member="user:seu-email@gmail.com" \
     --role="roles/iam.serviceAccountTokenCreator"
   ```

2. Gere as Application Default Credentials personificando a service account:

   ```bash
   gcloud auth application-default login --impersonate-service-account="$SA_EMAIL"
   ```

   O script passa a obter tokens temporários da service account a partir da sua sessão do `gcloud`. Nenhuma chave da service account é salva em disco.

3. Crie o ambiente virtual e instale as dependências:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. Crie o arquivo `.env` a partir do modelo e preencha `GDRIVE_FOLDER_ID`:

   ```bash
   cp .env.example .env
   ```

   ```
   GDRIVE_FOLDER_ID="SEU_FOLDER_ID_DO_GOOGLE_DRIVE"
   ```

   > Deixe `SERVICE_ACCOUNT_FILE` comentada/ausente. Se ela estiver definida, o script usa a chave JSON indicada em vez das Application Default Credentials.

5. Crie o arquivo de wishlists a partir do modelo (veja [Wishlists](#-wishlists)):

   ```bash
   cp wishlist.txt.template wishlist.txt
   ```

6. Execute:

   ```bash
   python main.py
   ```

   Durante a execução:
   - Cada wishlist é acessada, rolada até o fim e salva como HTML e JSON em `output/`.
   - Apenas os arquivos gerados nesta execução são enviados ao Google Drive; arquivos com o mesmo nome na pasta são atualizados.

7. (Opcional) Rode os testes:

   ```bash
   pip install -r requirements-dev.txt
   pytest
   ```

---

## ⏰ Passo 2b — Executando periodicamente no GitHub Actions

O workflow [`.github/workflows/wishlist-to-drive.yml`](.github/workflows/wishlist-to-drive.yml) roda o script em um agendamento cron e também pode ser disparado manualmente. A autenticação usa **Workload Identity Federation**, sem nenhuma chave armazenada no GitHub.

1. Defina as variáveis adicionais (além das do Passo 1):

   ```bash
   GITHUB_REPO="lbbedendo/wishlist-to-drive"   # <dono>/<repositório>
   POOL_ID="github"
   PROVIDER_ID="wishlist-to-drive"
   PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
   ```

2. Crie o Workload Identity Pool:

   ```bash
   gcloud iam workload-identity-pools create "$POOL_ID" \
     --location="global" \
     --display-name="GitHub Actions"
   ```

3. Crie o provider OIDC do GitHub, aceitando **apenas** tokens deste repositório:

   ```bash
   gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
     --location="global" \
     --workload-identity-pool="$POOL_ID" \
     --display-name="wishlist-to-drive" \
     --issuer-uri="https://token.actions.githubusercontent.com" \
     --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
     --attribute-condition="assertion.repository == '${GITHUB_REPO}'"
   ```

4. Permita que o workflow deste repositório personifique a service account:

   ```bash
   gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
     --role="roles/iam.workloadIdentityUser" \
     --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}"
   ```

5. Obtenha o nome completo do provider (usado no próximo passo):

   ```bash
   gcloud iam workload-identity-pools providers describe "$PROVIDER_ID" \
     --location="global" \
     --workload-identity-pool="$POOL_ID" \
     --format="value(name)"
   # projects/123456789/locations/global/workloadIdentityPools/github/providers/wishlist-to-drive
   ```

6. Configure as variáveis e o secret do repositório (em **Settings → Secrets and variables → Actions**, ou com o [GitHub CLI](https://cli.github.com/)):

   | Nome | Tipo | Valor |
   |---|---|---|
   | `GCP_WORKLOAD_IDENTITY_PROVIDER` | Variable | Saída do passo 5 |
   | `GCP_SERVICE_ACCOUNT` | Variable | E-mail da service account (`$SA_EMAIL`) |
   | `GDRIVE_FOLDER_ID` | Variable | ID da pasta do Google Drive |
   | `WISHLIST_TXT` | Secret | Conteúdo completo do seu `wishlist.txt` |

   ```bash
   gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "projects/123456789/locations/global/workloadIdentityPools/github/providers/wishlist-to-drive"
   gh variable set GCP_SERVICE_ACCOUNT --body "$SA_EMAIL"
   gh variable set GDRIVE_FOLDER_ID --body "SEU_FOLDER_ID_DO_GOOGLE_DRIVE"
   gh secret set WISHLIST_TXT < wishlist.txt
   ```

   > Sempre que editar o `wishlist.txt` local, rode `gh secret set WISHLIST_TXT < wishlist.txt` novamente.

7. Ajuste o agendamento, se quiser, na expressão cron do workflow:

   ```yaml
   on:
     schedule:
       - cron: "0 9 * * *"   # todos os dias às 09:00 UTC (06:00 em Brasília)
   ```

   O cron do GitHub Actions é **sempre em UTC**.

8. Faça o push para a branch padrão e teste disparando o workflow manualmente:

   ```bash
   gh workflow run wishlist-to-drive.yml
   gh run watch
   ```

**Observações sobre o GitHub Actions:**

- Execuções agendadas podem atrasar alguns minutos (ou, raramente, ser puladas) em horários de alta demanda.
- Em repositórios públicos, o GitHub desativa workflows agendados após **60 dias sem atividade** no repositório. Reative em **Actions → wishlist-to-drive → Enable workflow**.
- Em repositórios públicos, **os logs das execuções são públicos** e incluem os títulos das wishlists e dos livros. As URLs ficam mascaradas por virem do secret `WISHLIST_TXT`.
- A Amazon pode responder com CAPTCHA para IPs de datacenter (como os dos runners do GitHub). Nesse caso o log mostra "Nenhum livro encontrado".

### Removendo chaves antigas

Se você já criou chaves JSON para a service account, apague-as depois de validar os dois modos acima:

```bash
gcloud iam service-accounts keys list --iam-account="$SA_EMAIL" --managed-by=user
gcloud iam service-accounts keys delete KEY_ID --iam-account="$SA_EMAIL"
rm service_account.json
```

---

## 📋 Wishlists

As wishlists ficam no arquivo `wishlist.txt`, na raiz do projeto. Ele é pessoal e não é versionado; crie-o a partir do modelo `wishlist.txt.template`.

Uma wishlist por linha, com a URL completa ou apenas o ID. Linhas em branco são ignoradas e `#` inicia um comentário:

```
# Ficção
https://www.amazon.com.br/hz/wishlist/ls/XXXXXXXXXXXX
YYYYYYYYYYYY   # só o ID também funciona (usa amazon.com.br)
```

Linhas inválidas e wishlists duplicadas são ignoradas com um aviso no log.

## 🛠️ Solução de problemas

- **`storageQuotaExceeded` / "Service Accounts do not have storage quota"**: service accounts não têm cota de armazenamento própria e o Google pode recusar a criação de arquivos por elas em pastas do "Meu Drive" de contas pessoais. Use uma pasta dentro de um **Drive compartilhado** (requer Google Workspace) e adicione a service account como membro.
- **`DefaultCredentialsError`**: as Application Default Credentials não foram configuradas. Localmente, refaça o passo 2 da seção "Passo 2a — Executando localmente".
- **Nenhum livro encontrado**: abra o HTML salvo em `output/amazon_wishlist_<ID>.html` para ver o que a Amazon retornou (página de CAPTCHA, lista privada etc.).

## 🧠 Estrutura do Projeto

```
wishlist-to-drive/
├── .github/workflows/
│   └── wishlist-to-drive.yml  # Execução agendada no GitHub Actions
├── gdrive.py                  # Autenticação e upload para o Google Drive
├── main.py                    # Script principal de scraping
├── wishlists.py               # Leitura do arquivo wishlist.txt
├── tests/                     # Testes unitários (pytest)
├── requirements.txt           # Dependências Python
├── requirements-dev.txt       # Dependências de desenvolvimento (pytest)
├── wishlist.txt.template      # Modelo da lista de wishlists
├── wishlist.txt               # Suas wishlists (não versionado)
├── .env.example               # Modelo das variáveis de ambiente
├── .env                       # Variáveis de ambiente (não versionado)
└── output/                    # Arquivos HTML e JSON gerados
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