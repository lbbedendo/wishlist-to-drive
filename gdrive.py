import os
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

# Escopo mínimo necessário para acesso ao Google Drive
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def autenticar_com_service_account_json():
    """
    Autentica no Google Drive usando o arquivo JSON da service account
    definido via variável de ambiente SERVICE_ACCOUNT_FILE.
    """
    credentials_path = os.getenv("SERVICE_ACCOUNT_FILE")
    if not credentials_path or not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"❌ O arquivo de credenciais da service account não foi encontrado ({credentials_path!r}). "
            "Defina a variável de ambiente SERVICE_ACCOUNT_FILE com o caminho do JSON."
        )

    logging.info(f"🔐 Autenticando com service account: {credentials_path}")
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=credentials)
    return service


def buscar_arquivo_existente(service, nome_arquivo, folder_id=None):
    """Retorna o ID de um arquivo com o mesmo nome (na pasta, se informada), ou None."""
    nome_escapado = nome_arquivo.replace("\\", "\\\\").replace("'", "\\'")
    query = f"name = '{nome_escapado}' and trashed = false"
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
