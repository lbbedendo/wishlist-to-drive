import re
import logging

ARQUIVO_WISHLISTS = "wishlist.txt"
URL_BASE_WISHLIST = "https://www.amazon.com.br/hz/wishlist/ls/"

REGEX_URL_WISHLIST = re.compile(r"^https?://\S+/wishlist/ls/([A-Z0-9]+)")
REGEX_ID_WISHLIST = re.compile(r"^[A-Z0-9]+$")


def interpretar_linha(linha):
    """
    Converte uma linha do arquivo de wishlists em (id, url).
    Retorna None para linhas vazias ou só com comentário.
    Lança ValueError se a linha não for uma URL de wishlist nem um ID.
    """
    conteudo = linha.split("#", 1)[0].strip()
    if not conteudo:
        return None

    match = REGEX_URL_WISHLIST.match(conteudo)
    if match:
        return match.group(1), conteudo

    if REGEX_ID_WISHLIST.match(conteudo):
        return conteudo, f"{URL_BASE_WISHLIST}{conteudo}"

    raise ValueError(f"linha inválida: {conteudo!r}")


def carregar_urls_wishlists(caminho=ARQUIVO_WISHLISTS):
    """
    Lê o arquivo de wishlists (uma URL ou ID por linha; '#' inicia comentário)
    e retorna a lista de URLs, sem duplicatas e na ordem do arquivo.
    Linhas inválidas são ignoradas com um aviso.
    """
    urls = []
    ids_vistos = set()

    with open(caminho, encoding="utf-8") as f:
        for numero, linha in enumerate(f, start=1):
            try:
                resultado = interpretar_linha(linha)
            except ValueError as e:
                logging.warning(f"⚠️ {caminho}:{numero}: {e}. Ignorando.")
                continue

            if resultado is None:
                continue

            wishlist_id, url = resultado
            if wishlist_id in ids_vistos:
                logging.warning(f"⚠️ {caminho}:{numero}: wishlist {wishlist_id} duplicada. Ignorando.")
                continue

            ids_vistos.add(wishlist_id)
            urls.append(url)

    return urls
