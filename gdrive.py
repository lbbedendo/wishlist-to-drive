import os
import logging
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Escopo mínimo necessário: acesso apenas aos arquivos criados por este app
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

ARQUIVO_TOKEN_PADRAO = "google_drive_token.json"


def caminho_do_token():
    """Caminho do arquivo com o refresh token (GOOGLE_DRIVE_TOKEN_FILE ou o padrão)."""
    return os.getenv("GOOGLE_DRIVE_TOKEN_FILE", ARQUIVO_TOKEN_PADRAO)


def escapar_para_query(valor):
    """Escapa um valor para uso entre aspas simples em uma query do Drive."""
    return valor.replace("\\", "\\\\").replace("'", "\\'")


def carregar_credenciais(caminho=None):
    """
    Carrega as credenciais OAuth do usuário (refresh token) e obtém um access token.
    Falha cedo, com uma mensagem clara, se o token não existir ou tiver sido revogado.
    """
    caminho = caminho or caminho_do_token()
    if not os.path.exists(caminho):
        raise FileNotFoundError(
            f"❌ Arquivo de token do Google Drive não encontrado ({caminho!r}). "
            "Rode 'python autorizar_google_drive.py' para gerá-lo."
        )

    credentials = Credentials.from_authorized_user_file(caminho, SCOPES)
    try:
        credentials.refresh(Request())
    except RefreshError as e:
        raise RuntimeError(
            "❌ O refresh token do Google Drive foi revogado ou expirou. "
            "Rode 'python autorizar_google_drive.py' novamente e atualize o secret GOOGLE_DRIVE_TOKEN."
        ) from e
    return credentials


def autenticar_no_google_drive():
    """Autentica no Google Drive como o usuário que autorizou o app (OAuth)."""
    caminho = caminho_do_token()
    logging.info(f"🔐 Autenticando no Google Drive com o token OAuth: {caminho}")
    return build("drive", "v3", credentials=carregar_credenciais(caminho))


def buscar_arquivo_existente(service, nome_arquivo, folder_id=None):
    """Retorna o ID de um arquivo com o mesmo nome (na pasta, se informada), ou None."""
    query = f"name = '{escapar_para_query(nome_arquivo)}' and trashed = false"
    if folder_id:
        query += f" and '{folder_id}' in parents"

    resultado = (
        service.files()
        .list(q=query, fields="files(id)", pageSize=1, spaces="drive")
        .execute()
    )
    arquivos = resultado.get("files", [])
    return arquivos[0]["id"] if arquivos else None


def enviar_para_drive(service, arquivo_local, folder_id=None):
    """
    Envia um arquivo para o Google Drive. Se já existir um arquivo com o mesmo
    nome na pasta de destino, seu conteúdo é atualizado em vez de criar uma cópia.

    Args:
        service: objeto autenticado do Google Drive API
        arquivo_local (str): caminho do arquivo local
        folder_id (str): ID da pasta de destino no Drive (opcional)
    """
    if not os.path.exists(arquivo_local):
        logging.error(f"❌ Arquivo não encontrado: {arquivo_local}")
        return None

    nome_arquivo = os.path.basename(arquivo_local)
    logging.info(f"☁️ Iniciando upload: {nome_arquivo}")

    media = MediaFileUpload(arquivo_local, resumable=True)

    try:
        arquivo_id = buscar_arquivo_existente(service, nome_arquivo, folder_id)
        if arquivo_id:
            arquivo = (
                service.files()
                .update(fileId=arquivo_id, media_body=media, fields="id, name, webViewLink")
                .execute()
            )
            acao = "Atualizado"
        else:
            # Metadados do arquivo
            file_metadata = {"name": nome_arquivo}
            if folder_id:
                file_metadata["parents"] = [folder_id]
            arquivo = (
                service.files()
                .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
                .execute()
            )
            acao = "Criado"
        logging.info(
            f"✅ {acao} no Drive: {arquivo.get('name')} "
            f"({arquivo.get('id')}) - Link: {arquivo.get('webViewLink')}"
        )
        return arquivo
    except Exception as e:
        logging.error(f"⚠️ Erro ao enviar '{nome_arquivo}' para o Drive: {e}")
        return None
