import os
import re
import json
import time
import pathlib
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from wishlists import ARQUIVO_WISHLISTS, carregar_urls_wishlists

# Configurações iniciais
DIRETORIO_OUTPUT = "output"
SELETOR_LIVROS = "h2.a-size-base a[title]"
MAX_SCROLLS = 50
MAX_SCROLLS_SEM_PROGRESSO = 3
PAUSA_SCROLL_SEGUNDOS = 2
load_dotenv()

# Logging configurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

def configurar_driver():
    """Configura o driver do Chrome em modo headless."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)


def extrair_id_da_url(url):
    """Extrai o ID da wishlist da URL."""
    match = re.search(r'/wishlist/ls/([A-Z0-9]+)', url)
    return match.group(1) if match else "unknown"


def extrair_titulo_da_wishlist(driver):
    """Tenta extrair o título da wishlist."""
    try:
        elemento = driver.find_element(By.ID, "profile-list-name")
        return elemento.text.strip()
    except NoSuchElementException:
        return "Desconhecido"


def criar_diretorio_output():
    """Cria o diretório de saída, se não existir."""
    pathlib.Path(f"./{DIRETORIO_OUTPUT}").mkdir(parents=True, exist_ok=True)


def salvar_html(driver, wishlist_id):
    """Salva o HTML da página atual e retorna o caminho do arquivo."""
    filename = f"{DIRETORIO_OUTPUT}/amazon_wishlist_{wishlist_id}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info(f"📄 HTML salvo como: {filename}")
    return filename


def salvar_json(dados):
    """Salva os dados extraídos em formato JSON e retorna o caminho do arquivo."""
    filename = f"{DIRETORIO_OUTPUT}/amazon_wishlist_{dados['wishlist_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    logging.info(f"📄 JSON salvo como: {filename}")
    return filename


def esperar_carregar_livros(driver):
    """Aguarda o carregamento dos primeiros livros da wishlist."""
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, SELETOR_LIVROS))
        )
    except TimeoutException:
        logging.warning("⚠️ Timeout esperando os livros carregarem.")
        return False
    return True


def carregar_todos_os_livros(driver):
    """
    Rola a página até o fim repetidamente para que a Amazon carregue todas as
    páginas da wishlist (scroll infinito). Para quando o marcador de fim de lista
    aparece ou quando a quantidade de itens deixa de aumentar.
    """
    total_anterior = len(driver.find_elements(By.CSS_SELECTOR, SELETOR_LIVROS))
    sem_progresso = 0

    for _ in range(MAX_SCROLLS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(PAUSA_SCROLL_SEGUNDOS)

        if driver.find_elements(By.ID, "endOfListMarker"):
            break

        total_atual = len(driver.find_elements(By.CSS_SELECTOR, SELETOR_LIVROS))
        if total_atual > total_anterior:
            total_anterior = total_atual
            sem_progresso = 0
        else:
            sem_progresso += 1
            if sem_progresso >= MAX_SCROLLS_SEM_PROGRESSO:
                break
    else:
        logging.warning(f"⚠️ Limite de {MAX_SCROLLS} scrolls atingido; a lista pode estar incompleta.")

    total = len(driver.find_elements(By.CSS_SELECTOR, SELETOR_LIVROS))
    logging.info(f"🔄 {total} itens carregados após scroll.")


def extrair_dados_da_wishlist(driver, url):
    """Extrai dados da wishlist da Amazon. Retorna (dados, caminho_do_html)."""
    logging.info(f"📥 Acessando: {url}")
    driver.get(url)

    wishlist_id = extrair_id_da_url(url)
    criar_diretorio_output()

    if not esperar_carregar_livros(driver):
        arquivo_html = salvar_html(driver, wishlist_id)
        return {
            "wishlist_id": wishlist_id,
            "titulo": "Desconhecido",
            "livros": []
        }, arquivo_html

    carregar_todos_os_livros(driver)
    arquivo_html = salvar_html(driver, wishlist_id)
    titulo_wishlist = extrair_titulo_da_wishlist(driver)

    livros = []
    urls_vistas = set()
    elementos = driver.find_elements(By.CSS_SELECTOR, SELETOR_LIVROS)

    for link in elementos:
        try:
            titulo = link.get_attribute("title").strip()
            href = link.get_attribute("href").strip()
            if href in urls_vistas:
                continue
            urls_vistas.add(href)

            # Busca o autor associado ao item
            container = link.find_element(By.XPATH, '../../..')
            try:
                autor_element = container.find_element(By.CSS_SELECTOR, "span[id^='item-byline-']")
                autor = autor_element.text.strip()
            except NoSuchElementException:
                autor = "Desconhecido"

            livros.append({
                "titulo": titulo,
                "autor": autor,
                "url": href
            })
        except Exception as e:
            logging.warning(f"⚠️ Erro ao extrair um item: {e}")
            continue

    return {
        "wishlist_id": wishlist_id,
        "titulo": titulo_wishlist,
        "livros": livros
    }, arquivo_html


def enviar_arquivos_para_google_drive(arquivos):
    """Envia para o Google Drive os arquivos gerados nesta execução."""
    from gdrive import autenticar_no_google_drive, enviar_para_drive

    gdrive_folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if not gdrive_folder_id:
        logging.warning("⚠️ GDRIVE_FOLDER_ID não definido. Pulando upload para o Google Drive.")
        return

    if not arquivos:
        logging.info("Nenhum arquivo encontrado para upload.")
        return

    gdrive_service = autenticar_no_google_drive()
    for arquivo in arquivos:
        enviar_para_drive(gdrive_service, arquivo, gdrive_folder_id)
        logging.info(f"☁️ Enviado para o Google Drive: {arquivo}")


def main():
    """Função principal. Retorna a lista de arquivos gerados nesta execução."""
    try:
        urls = carregar_urls_wishlists(ARQUIVO_WISHLISTS)
    except FileNotFoundError:
        logging.error(
            f"❌ Arquivo {ARQUIVO_WISHLISTS} não encontrado. "
            f"Copie {ARQUIVO_WISHLISTS}.template para {ARQUIVO_WISHLISTS} e adicione suas wishlists."
        )
        return []

    if not urls:
        logging.error(f"❌ Nenhuma wishlist encontrada em {ARQUIVO_WISHLISTS}.")
        return []

    logging.info(f"📋 {len(urls)} wishlists carregadas de {ARQUIVO_WISHLISTS}.")
    driver = configurar_driver()
    arquivos_gerados = []

    for url in urls:
        dados, arquivo_html = extrair_dados_da_wishlist(driver, url)
        arquivos_gerados.append(arquivo_html)
        if dados["livros"]:
            logging.info(f"📚 Livros encontrados em '{dados['titulo']}':")
            for livro in dados["livros"]:
                logging.info(f" - {livro['titulo']} ({livro['autor']})")
        else:
            logging.warning(f"❌ Nenhum livro encontrado em '{dados['titulo']}'.")
        arquivos_gerados.append(salvar_json(dados))

    driver.quit()
    return arquivos_gerados


if __name__ == "__main__":
    arquivos = main()
    enviar_arquivos_para_google_drive(arquivos)
