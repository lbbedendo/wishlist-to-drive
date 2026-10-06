import logging
import pathlib

import pytest

from wishlists import URL_BASE_WISHLIST, carregar_urls_wishlists, interpretar_linha

RAIZ_DO_PROJETO = pathlib.Path(__file__).resolve().parent.parent


def criar_arquivo(tmp_path, conteudo):
    caminho = tmp_path / "wishlist.txt"
    caminho.write_text(conteudo, encoding="utf-8")
    return caminho


def test_carrega_urls_na_ordem_do_arquivo(tmp_path):
    caminho = criar_arquivo(tmp_path, (
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL\n"
        "https://www.amazon.com.br/hz/wishlist/ls/KLAFDOWZS758\n"
        "https://www.amazon.com.br/hz/wishlist/ls/2K7QKYF9WDWAS\n"
    ))

    assert carregar_urls_wishlists(caminho) == [
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL",
        "https://www.amazon.com.br/hz/wishlist/ls/KLAFDOWZS758",
        "https://www.amazon.com.br/hz/wishlist/ls/2K7QKYF9WDWAS",
    ]


def test_ignora_linhas_vazias_e_comentarios(tmp_path):
    caminho = criar_arquivo(tmp_path, (
        "# Ficção\n"
        "\n"
        "   \n"
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL   # comentário no fim\n"
        "    # comentário indentado\n"
        "  https://www.amazon.com.br/hz/wishlist/ls/KLAFDOWZS758  \n"
    ))

    assert carregar_urls_wishlists(caminho) == [
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL",
        "https://www.amazon.com.br/hz/wishlist/ls/KLAFDOWZS758",
    ]


def test_id_sozinho_vira_url_completa(tmp_path):
    caminho = criar_arquivo(tmp_path, "2K7QKYF9WDWAS\n")

    assert carregar_urls_wishlists(caminho) == [f"{URL_BASE_WISHLIST}2K7QKYF9WDWAS"]


def test_mantem_url_com_parametros_e_outro_dominio(tmp_path):
    url = "https://www.amazon.com/hz/wishlist/ls/1HZGW7568A6D1?ref_=wl_share"
    caminho = criar_arquivo(tmp_path, f"{url}\n")

    assert carregar_urls_wishlists(caminho) == [url]


def test_remove_duplicatas_pelo_id(tmp_path, caplog):
    caminho = criar_arquivo(tmp_path, (
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL\n"
        "1R0U6P2463LWL\n"
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL?ref_=x\n"
    ))

    with caplog.at_level(logging.WARNING):
        urls = carregar_urls_wishlists(caminho)

    assert urls == ["https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL"]
    assert "duplicada" in caplog.text
    assert f"{caminho}:2" in caplog.text


def test_ignora_linhas_invalidas_com_aviso(tmp_path, caplog):
    caminho = criar_arquivo(tmp_path, (
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL\n"
        "isso não é uma wishlist\n"
        "https://www.amazon.com.br/dp/B000000000\n"
        "https://www.amazon.com.br/hz/wishlist/ls/KLAFDOWZS758\n"
    ))

    with caplog.at_level(logging.WARNING):
        urls = carregar_urls_wishlists(caminho)

    assert urls == [
        "https://www.amazon.com.br/hz/wishlist/ls/1R0U6P2463LWL",
        "https://www.amazon.com.br/hz/wishlist/ls/KLAFDOWZS758",
    ]
    assert f"{caminho}:2" in caplog.text
    assert f"{caminho}:3" in caplog.text


def test_arquivo_so_com_comentarios_retorna_lista_vazia(tmp_path):
    caminho = criar_arquivo(tmp_path, "# nada aqui ainda\n\n")

    assert carregar_urls_wishlists(caminho) == []


def test_arquivo_inexistente_lanca_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        carregar_urls_wishlists(tmp_path / "nao_existe.txt")


def test_template_versionado_e_valido():
    urls = carregar_urls_wishlists(RAIZ_DO_PROJETO / "wishlist.txt.template")

    assert urls == [
        "https://www.amazon.com.br/hz/wishlist/ls/XXXXXXXXXXXX",
        f"{URL_BASE_WISHLIST}YYYYYYYYYYYY",
    ]


@pytest.mark.parametrize("linha", ["", "\n", "   \n", "# comentário\n", "  # indentado\n"])
def test_interpretar_linha_sem_conteudo_retorna_none(linha):
    assert interpretar_linha(linha) is None


@pytest.mark.parametrize("linha", ["abc123", "https://www.amazon.com.br/", "wishlist/ls/ABC"])
def test_interpretar_linha_invalida_lanca_value_error(linha):
    with pytest.raises(ValueError):
        interpretar_linha(linha)
