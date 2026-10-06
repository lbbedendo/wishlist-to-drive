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
- Execução **agendada no GitHub Actions**, com autenticação OAuth restrita aos arquivos criados pelo app (`drive.file`)

---

## 🧩 Requisitos

- Python **3.9+**
- Chrome (o ChromeDriver é instalado automaticamente via `webdriver-manager`)
- Uma conta Google (o Gmail pessoal funciona) e um projeto no [Google Cloud Console](https://console.cloud.google.com/)
- [GitHub CLI (`gh`)](https://cli.github.com/), para configurar a execução no GitHub Actions

### Como funciona a autenticação

O script envia os arquivos **como você**, usando **OAuth 2.0** com o escopo `drive.file`:

1. **Uma única vez**, o script `autorizar_google_drive.py` abre o navegador, você autoriza o app e ele salva um **refresh token** em `google_drive_token.json`.
2. **A cada execução** (local ou no GitHub Actions), o refresh token é trocado por um **access token de ~1 hora**, usado nas chamadas ao Drive.

Os arquivos ocupam a cota do **seu** Drive. Por isso não se usa uma service account: service accounts não têm cota de armazenamento e o Google recusa uploads delas no "Meu Drive" de contas pessoais.

Sobre o escopo `drive.file`:

- O app só enxerga e altera **arquivos e pastas que ele mesmo criou**. O resto do seu Drive fica inacessível para ele.
- Por isso a pasta de destino precisa ser **criada pelo app**: o `autorizar_google_drive.py` faz isso e imprime o ID dela. Uma pasta criada à mão no Drive não funciona (erro `appNotAuthorizedToFile`).
- Depois de criada, você pode mover ou renomear a pasta no Drive à vontade.

> ⚠️ O refresh token é uma **credencial de longa duração**: quem tiver o arquivo pode criar e alterar os arquivos deste app no seu Drive. Não versione `google_drive_token.json` nem `client_secret.json` (ambos estão no `.gitignore`). Para revogar o acesso a qualquer momento: [myaccount.google.com/permissions](https://myaccount.google.com/permissions).

---

## 🔐 Passo 1 — Criar o OAuth client no Google Cloud (uma vez)

No [Google Cloud Console](https://console.cloud.google.com/), com o seu projeto selecionado:

1. **Ative a Google Drive API**: *APIs e serviços → Biblioteca → Google Drive API → Ativar*.

2. **Configure a tela de consentimento** em *Google Auth Platform*:
   - **Branding** (todos exigidos para publicar em produção):
     - Nome do app: `wishlist-to-drive`
     - E-mail de suporte e e-mail de contato do desenvolvedor
     - Página inicial do aplicativo: URL do repositório (ex.: `https://github.com/<usuario>/wishlist-to-drive`)
     - Link da Política de Privacidade: o [`PRIVACY.md`](PRIVACY.md) do repositório (ex.: `https://github.com/<usuario>/wishlist-to-drive/blob/main/PRIVACY.md`). Ele precisa estar no GitHub antes de salvar.
     - Domínios autorizados: `github.com`
     - Deixe **logotipo** e **Termos de Serviço** em branco: um logotipo exige verificação da marca pelo Google.
   - **Público-alvo (Audience)**: tipo **Externo**. Em *Status de publicação*, clique em **Publicar app** para deixá-lo **Em produção**.

     > ⚠️ Não deixe o app em **Teste**: nesse modo o Google expira o refresh token em **7 dias** e a execução agendada passa a falhar. Como `drive.file` é um escopo não sensível, publicar não exige verificação do Google.

   - **Acesso a dados (Data access)**: *Adicionar ou remover escopos* → marque `https://www.googleapis.com/auth/drive.file` → *Atualizar* → *Salvar*.

3. **Crie o OAuth client**: *Google Auth Platform → Clientes → Criar cliente*:
   - Tipo de aplicativo: **App para computador (Desktop app)**
   - Nome: `wishlist-to-drive`
   - Clique em **Fazer download do JSON** e salve o arquivo como `client_secret.json` na raiz do projeto.

---

## ▶️ Passo 2a — Executando localmente

1. Crie o ambiente virtual e instale as dependências:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Autorize o acesso ao Google Drive (uma vez):

   ```bash
   python autorizar_google_drive.py
   ```

   - O navegador abre: entre na sua conta Google e autorize o acesso aos arquivos do app.
   - Se aparecer o aviso *"O Google não verificou este app"*, clique em *Avançado → Acessar wishlist-to-drive*. O app é seu.
   - O script salva o refresh token em `google_drive_token.json` (permissão `600`), cria a pasta `wishlist-to-drive` no seu Drive (ou reutiliza a existente) e imprime o ID dela.

   Opções: `--client-secret <arquivo>`, `--token <arquivo>` e `--pasta <nome>`.

3. Crie o arquivo `.env` a partir do modelo e preencha `GDRIVE_FOLDER_ID` com o ID impresso no passo anterior:

   ```bash
   cp .env.example .env
   ```

   ```
   GDRIVE_FOLDER_ID="ID_IMPRESSO_PELO_AUTORIZAR_GOOGLE_DRIVE"
   ```

4. Crie o arquivo de wishlists a partir do modelo (veja [Wishlists](#-wishlists)):

   ```bash
   cp wishlist.txt.template wishlist.txt
   ```

5. Execute:

   ```bash
   python main.py
   ```

   Durante a execução:
   - Cada wishlist é acessada, rolada até o fim e salva como HTML e JSON em `output/`.
   - Apenas os arquivos gerados nesta execução são enviados ao Google Drive; arquivos com o mesmo nome na pasta são atualizados.
   - Wishlists sem nenhum livro (CAPTCHA, lista privada, timeout) são salvas em `output/` para análise, mas não são enviadas ao Drive, e o script termina com código de saída 1.

6. (Opcional) Rode os testes:

   ```bash
   pip install -r requirements-dev.txt
   pytest
   ```

---

## ⏰ Passo 2b — Executando periodicamente no GitHub Actions

O workflow [`.github/workflows/wishlist-to-drive.yml`](.github/workflows/wishlist-to-drive.yml) roda o script em um agendamento cron e também pode ser disparado manualmente. Ele recria o `wishlist.txt` e o arquivo do token a partir de secrets do repositório.

1. Conclua o **Passo 2a** até o item 2: você precisa do `google_drive_token.json` e do ID da pasta.

2. Configure os secrets e a variável do repositório (em **Settings → Secrets and variables → Actions**, ou com o `gh`):

   | Nome | Tipo | Valor |
   |---|---|---|
   | `GOOGLE_DRIVE_TOKEN` | Secret | Conteúdo do `google_drive_token.json` |
   | `WISHLIST_TXT` | Secret | Conteúdo do seu `wishlist.txt` |
   | `GDRIVE_FOLDER_ID` | Variable | ID da pasta impresso pelo `autorizar_google_drive.py` |

   ```bash
   gh secret set GOOGLE_DRIVE_TOKEN < google_drive_token.json
   gh secret set WISHLIST_TXT < wishlist.txt
   gh variable set GDRIVE_FOLDER_ID --body "ID_DA_PASTA"
   ```

   > Sempre que editar o `wishlist.txt` local, rode `gh secret set WISHLIST_TXT < wishlist.txt` novamente.

3. Ajuste o agendamento, se quiser, na expressão cron do workflow:

   ```yaml
   on:
     schedule:
       - cron: "0 9 * * *"   # todos os dias às 09:00 UTC (06:00 em Brasília)
   ```

   O cron do GitHub Actions é **sempre em UTC**.

4. Faça o push para a branch padrão e teste disparando o workflow manualmente:

   ```bash
   gh workflow run wishlist-to-drive.yml
   gh run watch
   ```

**Observações sobre o GitHub Actions:**

- Execuções agendadas podem atrasar alguns minutos (ou, raramente, ser puladas) em horários de alta demanda.
- Em repositórios públicos, o GitHub desativa workflows agendados após **60 dias sem atividade** no repositório. Reative em **Actions → wishlist-to-drive → Enable workflow**.
- Em repositórios públicos, **os logs das execuções são públicos** e incluem os títulos das wishlists e dos livros. As URLs ficam mascaradas por virem do secret `WISHLIST_TXT`. Secrets não são expostos a pull requests de forks.
- A Amazon pode responder com CAPTCHA para IPs de datacenter (como os dos runners do GitHub). Nesse caso o log mostra "Nenhum livro encontrado".
- A execução **falha (código de saída 1)** se alguma wishlist vier sem livros, se algum upload falhar, se o `wishlist.txt` estiver vazio ou se o refresh token tiver sido revogado. Os arquivos das wishlists que falharam não são enviados ao Drive, para não sobrescrever a última versão boa. Ative as notificações de falha em **Settings → Notifications → Actions** no seu perfil do GitHub para ser avisado por e-mail.

### Renovando o refresh token

O refresh token não expira com o tempo (com o app **Em produção**), mas é invalidado se você revogar o acesso, se ele ficar **6 meses sem uso** ou se você autorizar o mesmo client mais de 100 vezes. Se a execução falhar com *"O refresh token do Google Drive foi revogado ou expirou"*:

```bash
python autorizar_google_drive.py                         # reutiliza a pasta existente
gh secret set GOOGLE_DRIVE_TOKEN < google_drive_token.json
```

> Não apague o OAuth client nem crie outro: com `drive.file`, o acesso aos arquivos já enviados pertence ao client que os criou. Um client novo não enxerga a pasta antiga e criaria uma pasta e arquivos novos.

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

- **`appNotAuthorizedToFile` / `File not found` na pasta**: o `GDRIVE_FOLDER_ID` aponta para uma pasta que não foi criada pelo app. Use o ID impresso pelo `autorizar_google_drive.py`.
- **"O refresh token do Google Drive foi revogado ou expirou"**: veja [Renovando o refresh token](#renovando-o-refresh-token). Se acontecer a cada ~7 dias, o app está em modo **Teste**: publique-o (Passo 1, item 2).
- **Arquivo de token não encontrado**: rode `python autorizar_google_drive.py` ou defina `GOOGLE_DRIVE_TOKEN_FILE` com o caminho correto.
- **Nenhum livro encontrado**: abra o HTML salvo em `output/amazon_wishlist_<ID>.html` para ver o que a Amazon retornou (página de CAPTCHA, lista privada etc.).

## 🧠 Estrutura do Projeto

```
wishlist-to-drive/
├── .github/workflows/
│   └── wishlist-to-drive.yml  # Execução agendada no GitHub Actions
├── autorizar_google_drive.py  # Autorização OAuth única e criação da pasta no Drive
├── gdrive.py                  # Autenticação e upload para o Google Drive
├── main.py                    # Script principal de scraping
├── wishlists.py               # Leitura do arquivo wishlist.txt
├── tests/                     # Testes unitários (pytest)
├── requirements.txt           # Dependências Python
├── requirements-dev.txt       # Dependências de desenvolvimento (pytest)
├── assets/logo.{png,svg}      # Logotipo (PNG 120x120 e fonte SVG)
├── PRIVACY.md                 # Política de privacidade (exigida pela tela de consentimento OAuth)
├── wishlist.txt.template      # Modelo da lista de wishlists
├── wishlist.txt               # Suas wishlists (não versionado)
├── .env.example               # Modelo das variáveis de ambiente
├── .env                       # Variáveis de ambiente (não versionado)
├── client_secret.json         # OAuth client baixado do Google Cloud (não versionado)
├── google_drive_token.json    # Refresh token gerado pela autorização (não versionado)
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
- [OAuth 2.0 para apps instalados](https://developers.google.com/identity/protocols/oauth2/native-app) — Autorização do Google Drive
- [Chrome Headless](https://developer.chrome.com/docs/chromium/headless) — Execução sem janela