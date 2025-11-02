import os
import re
import json
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

# Configurações iniciais
DIRETORIO_OUTPUT = "output"
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
    """Salva o HTML da página atual."""
    filename = f"{DIRETORIO_OUTPUT}/amazon_wishlist_{wishlist_id}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    logging.info(f"📄 HTML salvo como: {filename}")


def salvar_json(dados):
    """Salva os dados extraídos em formato JSON."""
    filename = f"{DIRETORIO_OUTPUT}/amazon_wishlist_{dados['wishlist_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    logging.info(f"📄 JSON salvo como: {filename}")


def esperar_carregar_livros(driver):
    """Aguarda o carregamento dos livros e realiza scroll para garantir renderização completa."""
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.a-size-base a[title]"))
        )
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    except TimeoutException:
        logging.warning("⚠️ Timeout esperando os livros carregarem.")
        return False
    return True


def extrair_dados_da_wishlist(driver, url):
    """Extrai dados da wishlist da Amazon."""
    logging.info(f"📥 Acessando: {url}")
    driver.get(url)

    wishlist_id = extrair_id_da_url(url)
    criar_diretorio_output()

    if not esperar_carregar_livros(driver):
        salvar_html(driver, wishlist_id)
        return {
            "wishlist_id": wishlist_id,
            "titulo": "Desconhecido",
            "livros": []
        }

    salvar_html(driver, wishlist_id)
    titulo_wishlist = extrair_titulo_da_wishlist(driver)

    livros = []
    elementos = driver.find_elements(By.CSS_SELECTOR, "h2.a-size-base a[title]")

    for link in elementos:
        try:
            titulo = link.get_attribute("title").strip()
            href = link.get_attribute("href").strip()

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
    }


def enviar_arquivos_para_google_drive():
    """Envia todos os arquivos de saída para o Google Drive."""
    from os import listdir
    from os.path import isfile, join
    from gdrive import autenticar_com_service_account_json, enviar_para_drive

    gdrive_folder_id = os.getenv("GDRIVE_FOLDER_ID")
    if not gdrive_folder_id:
        logging.warning("⚠️ GDRIVE_FOLDER_ID não definido. Pulando upload para o Google Drive.")
        return

    diretorio = f"./{DIRETORIO_OUTPUT}"
    arquivos = [join(diretorio, f) for f in listdir(diretorio) if isfile(join(diretorio, f))]
    if not arquivos:
        logging.info("Nenhum arquivo encontrado para upload.")
        return

    gdrive_service = autenticar_com_service_account_json()
    for arquivo in arquivos:
        enviar_para_drive(gdrive_service, arquivo, gdrive_folder_id)
        logging.info(f"☁️ Enviado para o Google Drive: {arquivo}")


def main():
    """Função principal."""
    urls_str = os.getenv("AMAZON_LIST_URLS")
    if not urls_str:
        logging.error("❌ Variável AMAZON_LIST_URLS não encontrada.")
        return

    urls = [url.strip() for url in urls_str.split(",") if url.strip()]
    driver = configurar_driver()

    for url in urls:
        dados = extrair_dados_da_wishlist(driver, url)
        if dados["livros"]:
            logging.info(f"📚 Livros encontrados em '{dados['titulo']}':")
            for livro in dados["livros"]:
                logging.info(f" - {livro['titulo']} ({livro['autor']})")
        else:
            logging.warning(f"❌ Nenhum livro encontrado em '{dados['titulo']}'.")
        salvar_json(dados)

    driver.quit()


if __name__ == "__main__":
    main()
    enviar_arquivos_para_google_drive()
