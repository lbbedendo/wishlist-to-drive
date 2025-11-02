import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Escopo mínimo necessário para acesso ao Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def autenticar_com_service_account_json():
    """
    Autentica no Google Drive usando o arquivo 'service_account.json'
    definido via variável de ambiente GOOGLE_APPLICATION_CREDENTIALS.
    """
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path or not os.path.exists(credentials_path):
        raise FileNotFoundError(
            "❌ O arquivo de credenciais 'service_account.json' não foi encontrado. "
            "Defina a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS com o caminho completo."
        )

    logging.info(f"🔐 Autenticando com service account: {credentials_path}")
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)
    return service


def enviar_para_drive(service, arquivo_local, folder_id=None):
    """
    Envia um arquivo para o Google Drive.

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

    # Metadados do arquivo
    file_metadata = {"name": nome_arquivo}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(arquivo_local, resumable=True)

    try:
        arquivo = (
            service.files()
            .create(body=file_metadata, media_body=media, fields="id, name, webViewLink")
            .execute()
        )
        logging.info(
            f"✅ Upload concluído: {arquivo.get('name')} "
            f"({arquivo.get('id')}) - Link: {arquivo.get('webViewLink')}"
        )
        return arquivo
    except Exception as e:
        logging.error(f"⚠️ Erro ao enviar '{nome_arquivo}' para o Drive: {e}")
        return None
