"""
Autorização única do Google Drive (OAuth 2.0, fluxo de app instalado).

Abre o navegador para você autorizar o app com o escopo drive.file, salva o
refresh token em um arquivo e garante que exista uma pasta criada pelo próprio
app no Drive (com drive.file o app só consegue gravar em pastas que ele criou).

Uso:
    python autorizar_google_drive.py
    python autorizar_google_drive.py --client-secret client_secret.json --pasta wishlist-to-drive
"""
import os
import json
import argparse

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from gdrive import SCOPES, caminho_do_token, escapar_para_query

ARQUIVO_CLIENT_SECRET_PADRAO = "client_secret.json"
NOME_PASTA_PADRAO = "wishlist-to-drive"
TIPO_PASTA = "application/vnd.google-apps.folder"


def autorizar(arquivo_client_secret):
    """Executa o consentimento OAuth no navegador e retorna as credenciais."""
    flow = InstalledAppFlow.from_client_secrets_file(arquivo_client_secret, SCOPES)
    # prompt=consent garante que o Google devolva um refresh token
    return flow.run_local_server(port=0, prompt="consent")


def salvar_token(credentials, caminho):
    """Salva o refresh token no formato 'authorized_user', legível só pelo dono."""
    if not credentials.refresh_token:
        raise RuntimeError("❌ O Google não retornou um refresh token. Rode o script novamente.")

    dados = {
        "type": "authorized_user",
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "refresh_token": credentials.refresh_token,
    }
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2)


def obter_ou_criar_pasta(service, nome):
    """Retorna (id, criada) da pasta do app com esse nome, criando-a se não existir."""
    query = f"name = '{escapar_para_query(nome)}' and mimeType = '{TIPO_PASTA}' and trashed = false"
    pastas = (
        service.files()
        .list(q=query, fields="files(id)", pageSize=1, spaces="drive")
        .execute()
        .get("files", [])
    )
    if pastas:
        return pastas[0]["id"], False

    pasta = service.files().create(body={"name": nome, "mimeType": TIPO_PASTA}, fields="id").execute()
    return pasta["id"], True


def main():
    parser = argparse.ArgumentParser(description="Autoriza o acesso ao Google Drive e gera o refresh token.")
    parser.add_argument("--client-secret", default=ARQUIVO_CLIENT_SECRET_PADRAO,
                        help=f"JSON do OAuth client do tipo Desktop (padrão: {ARQUIVO_CLIENT_SECRET_PADRAO})")
    parser.add_argument("--token", default=caminho_do_token(),
                        help="Arquivo onde o refresh token será salvo (padrão: GOOGLE_DRIVE_TOKEN_FILE ou google_drive_token.json)")
    parser.add_argument("--pasta", default=NOME_PASTA_PADRAO,
                        help=f"Nome da pasta do Drive usada pelo app (padrão: {NOME_PASTA_PADRAO})")
    args = parser.parse_args()

    if not os.path.exists(args.client_secret):
        parser.error(f"arquivo {args.client_secret!r} não encontrado. Baixe o JSON do OAuth client no Google Cloud Console.")

    credentials = autorizar(args.client_secret)
    salvar_token(credentials, args.token)
    print(f"✅ Refresh token salvo em {args.token}")

    service = build("drive", "v3", credentials=credentials)
    pasta_id, criada = obter_ou_criar_pasta(service, args.pasta)
    print(f"📁 Pasta '{args.pasta}' {'criada' if criada else 'já existente'} no Drive: {pasta_id}")

    print(f"""
Próximos passos:
  1. No .env, defina:
       GDRIVE_FOLDER_ID="{pasta_id}"
  2. Para o GitHub Actions:
       gh secret set GOOGLE_DRIVE_TOKEN < {args.token}
       gh variable set GDRIVE_FOLDER_ID --body "{pasta_id}"
""")


if __name__ == "__main__":
    main()
