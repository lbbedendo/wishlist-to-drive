# Política de Privacidade — wishlist-to-drive

*Última atualização: 6 de outubro de 2026*

O **wishlist-to-drive** é um script pessoal e de código aberto que coleta os livros de wishlists públicas da Amazon e salva o resultado no Google Drive do próprio usuário. Ele não é um serviço hospedado: roda apenas no computador do usuário ou no GitHub Actions do repositório dele.

## Dados do Google acessados

- O app solicita somente o escopo **`https://www.googleapis.com/auth/drive.file`**.
- Com esse escopo, o app só consegue ver e alterar **arquivos e pastas que ele mesmo criou** no Google Drive do usuário. Ele não tem acesso ao restante do Drive, ao Gmail, aos contatos ou a qualquer outro dado da conta Google.
- O app cria uma pasta (por padrão, `wishlist-to-drive`) e grava nela arquivos HTML e JSON com o conteúdo das wishlists.

## Outros dados processados

- Páginas **públicas** de wishlists da Amazon informadas pelo usuário, das quais são extraídos o título da lista e o título, autor e link de cada livro.
- Esses dados são gravados localmente na pasta `output/` e enviados ao Google Drive do usuário.

## Armazenamento das credenciais

- A autorização gera um *refresh token* OAuth, salvo no arquivo local `google_drive_token.json` (legível apenas pelo dono do arquivo) e, se o usuário configurar a execução agendada, em um *secret* criptografado do GitHub Actions do repositório do próprio usuário.
- Nenhuma credencial é enviada ao autor do projeto ou a terceiros.

## Compartilhamento

- Os dados **não são vendidos, compartilhados ou transferidos** a terceiros, nem usados para publicidade.
- Os dados trafegam apenas entre o ambiente de execução do usuário, a Amazon (leitura das páginas públicas) e a API do Google Drive.
- Em repositórios públicos, os **logs do GitHub Actions são públicos** e incluem os títulos das wishlists e dos livros. As URLs das wishlists ficam mascaradas.

## Uso de dados do Google (Limited Use)

O uso e a transferência de informações recebidas das APIs do Google seguem a [Política de Dados do Usuário dos Serviços de API do Google](https://developers.google.com/terms/api-services-user-data-policy), incluindo os requisitos de Uso Limitado.

## Revogação e exclusão

- O acesso pode ser revogado a qualquer momento em [myaccount.google.com/permissions](https://myaccount.google.com/permissions).
- Para apagar os dados, exclua a pasta criada pelo app no Google Drive, a pasta `output/` e o arquivo `google_drive_token.json` locais e, se houver, o secret `GOOGLE_DRIVE_TOKEN` do repositório no GitHub.

## Contato

Dúvidas sobre esta política: abra uma issue em [github.com/lbbedendo/wishlist-to-drive/issues](https://github.com/lbbedendo/wishlist-to-drive/issues).

---

## Summary (English)

wishlist-to-drive is a personal, open-source script. It requests only the `drive.file` scope, so it can access only the files and folders it creates in the user's own Google Drive. It reads public Amazon wishlist pages and stores the extracted book data locally and in the user's Drive. The OAuth refresh token is stored only in a local file and, optionally, in an encrypted GitHub Actions secret in the user's own repository. No data is sold, shared with third parties, or used for advertising. Use of information received from Google APIs adheres to the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy), including the Limited Use requirements. Access can be revoked at any time at [myaccount.google.com/permissions](https://myaccount.google.com/permissions). Contact: [GitHub issues](https://github.com/lbbedendo/wishlist-to-drive/issues).
