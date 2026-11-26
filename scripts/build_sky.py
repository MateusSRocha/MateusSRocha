"""Gera assets/sky.svg: um céu estrelado onde cada commit é uma estrela.

- cada repositório público vira uma constelação
- cada commit vira uma estrela
- estrelas recentes brilham mais; as antigas vão ficando discretas

Sem dependências externas (só biblioteca padrão do Python 3.12+).

Uso:
    python scripts/build_sky.py            # busca dados reais na API do GitHub
    python scripts/build_sky.py --demo     # usa dados fictícios (teste offline)
"""

import hashlib
import json
import math
import os
import random
import re
import sys
import urllib.request
from datetime import datetime, timezone

USUARIO = os.environ.get("GH_USER", "MateusSRocha")
NOME = os.environ.get("SKY_NAME", "Mateus")
TOKEN = os.environ.get("GITHUB_TOKEN")
SAIDA = "assets/sky.svg"

LARGURA, ALTURA = 1200, 520
HORIZONTE = 440
MAX_COMMITS_POR_REPO = 24

PADRAO = re.compile(r"^(feat|fix|docs|style|refactor|test|build|chore)(\([^)]*\))?!?:")

CORES = [
    "#4dabf7",  # azul claro
    "#228be6",  # azul médio
    "#1864ab",  # azul escuro
]


# ---------------------------------------------------------------- coleta

def chamar_api(caminho):
    pedido = urllib.request.Request(f"https://api.github.com{caminho}")
    pedido.add_header("Accept", "application/vnd.github+json")
    pedido.add_header("User-Agent", "sky-generator")
    if TOKEN:
        pedido.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(pedido, timeout=20) as resposta:
        return json.load(resposta)


def tipo_do_commit(mensagem):
    achado = PADRAO.match(mensagem)
    if achado:
        return achado.group(1)
    return "outro"


def coletar():
    """Devolve {nome_do_repo: [(data_iso, tipo), ...]} em ordem cronológica."""
    repos = chamar_api(f"/users/{USUARIO}/repos?per_page=100&type=owner")
    resultado = {}
    for repo in repos:
        if repo["fork"]:
            continue
        nome = repo["name"]
        if nome == USUARIO:
            continue
        commits = chamar_api(
            f"/repos/{USUARIO}/{nome}/commits"
            f"?author={USUARIO}&per_page={MAX_COMMITS_POR_REPO}"
        )
        estrelas = []
        for item in commits:
            data = item["commit"]["author"]["date"]
            tipo = tipo_do_commit(item["commit"]["message"])
            estrelas.append((data, tipo))
        if estrelas:
            estrelas.reverse()
            resultado[nome] = estrelas
    return resultado


def dados_demo():
    """Dados fictícios, só para testar o desenho sem internet."""
    sorteio = random.Random(7)
    nomes = {
        "EmpregaMais": 18,
        "the-project-zeta": 22,
        "lunar-landing-navigator": 15,
        "deoxys-store": 11,
        "ecopontos": 9,
        "lab-prog-2": 14,
    }
    tipos = ["feat"] * 5 + ["fix"] * 3 + ["docs"] * 2 + ["refactor", "test", "chore", "style", "build", "outro"]
    agora = datetime.now(timezone.utc).timestamp()
    resultado = {}
    for nome, quantidade in nomes.items():
        estrelas = []
        for _ in range(quantidade):
            dias = sorteio.uniform(0, 300)
            momento = datetime.fromtimestamp(agora - dias * 86400, timezone.utc)
            estrelas.append((momento.isoformat(), sorteio.choice(tipos)))
        estrelas.sort()
        resultado[nome] = estrelas
    return resultado


# -------------------------------------------------------------- geometria

def semente(texto):
    return int(hashlib.sha256(texto.encode()).hexdigest()[:12], 16)


def distribuir_centros(nomes):
    """Dá a cada repositório um centro estável, afastado dos outros."""
    centros = []
    for nome in nomes:
        sorteio = random.Random(semente(nome))
        melhor = None
        melhor_distancia = -1
        for _ in range(60):
            x = sorteio.uniform(170, LARGURA - 260)
            y = sorteio.uniform(170, HORIZONTE - 120)
            if not centros:
                melhor = (x, y)
                break
            menor = min(math.dist((x, y), c) for c in centros)
            if menor > melhor_distancia:
                melhor_distancia = menor
                melhor = (x, y)
        centros.append(melhor)
    return centros


def posicoes_da_constelacao(nome, quantidade, centro):
    sorteio = random.Random(semente(nome) + 1)
    x, y = centro
    angulo = sorteio.uniform(0, math.tau)
    pontos = []
    for _ in range(quantidade):
        pontos.append((x, y))
        angulo += sorteio.uniform(-1.1, 1.1)
        passo = sorteio.uniform(32, 56)
        x += math.cos(angulo) * passo
        y += math.sin(angulo) * passo
        x += (centro[0] - x) * 0.10
        y += (centro[1] - y) * 0.10
        x = min(max(x, 50), LARGURA - 50)
        y = min(max(y, 120), HORIZONTE - 40)
    return pontos


# ---------------------------------------------------------------- desenho

def idade_em_dias(data_iso):
    momento = datetime.fromisoformat(data_iso.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - momento).total_seconds() / 86400


def mandacaru(x):
    base = HORIZONTE + 6
    cor = "#04060d"
    return (
        f'<g stroke="{cor}" fill="none" stroke-linecap="round" stroke-linejoin="round">'
        f'<path d="M{x},{base} V{base - 96}" stroke-width="12"/>'
        f'<path d="M{x - 3},{base - 38} h-24 q-11,0 -11,-11 v-30" stroke-width="9"/>'
        f'<path d="M{x + 3},{base - 56} h22 q10,0 10,-10 v-26" stroke-width="9"/>'
        f"</g>"
    )


def serra():
    return (
        f'<path d="M0,{ALTURA} V{HORIZONTE + 14} '
        f'C150,{HORIZONTE - 8} 260,{HORIZONTE + 10} 380,{HORIZONTE + 2} '
        f'S640,{HORIZONTE - 14} 760,{HORIZONTE + 4} '
        f'S1040,{HORIZONTE + 8} {LARGURA},{HORIZONTE - 4} V{ALTURA} Z" fill="#04060d"/>'
    )


def construir_svg(repos, demo):
    sorteio_fundo = random.Random(2026)
    partes = []
    partes.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {LARGURA} {ALTURA}" '
        f'width="{LARGURA}" height="{ALTURA}" role="img" '
        f'aria-label="Céu estrelado onde cada commit de {NOME} é uma estrela">'
    )
    partes.append(
        "<defs>"
        '<linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#050816"/><stop offset="0.65" stop-color="#101b3d"/>'
        '<stop offset="1" stop-color="#3a2a52"/></linearGradient>'
        "<style>"
        "text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}"
        "@keyframes pisca{0%,100%{opacity:.35}50%{opacity:1}}"
        "@keyframes cai{0%{transform:translate(0,0);opacity:0}4%{opacity:1}"
        "14%{transform:translate(-340px,170px);opacity:0}100%{transform:translate(-340px,170px);opacity:0}}"
        ".p{animation:pisca 3.4s ease-in-out infinite}"
        ".q{animation:pisca 5.1s ease-in-out infinite}"
        ".cometa{animation:cai 14s linear infinite}"
        "</style></defs>"
    )
    partes.append(f'<rect width="{LARGURA}" height="{ALTURA}" fill="url(#ceu)"/>')

    for _ in range(170):
        x = sorteio_fundo.uniform(0, LARGURA)
        y = sorteio_fundo.uniform(0, HORIZONTE)
        raio = sorteio_fundo.uniform(0.3, 1.1)
        brilho = sorteio_fundo.uniform(0.2, 0.7)
        partes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{raio:.2f}" fill="#fff" opacity="{brilho:.2f}"/>')

    partes.append(
        '<g opacity="0.92"><circle cx="1090" cy="90" r="26" fill="#f4f1de"/>'
        '<circle cx="1102" cy="84" r="24" fill="#0c1430"/></g>'
    )

    nomes = list(repos.keys())
    centros = distribuir_centros(nomes)
    total_estrelas = 0

    for nome, centro in zip(nomes, centros):
        estrelas = repos[nome]
        pontos = posicoes_da_constelacao(nome, len(estrelas), centro)
        total_estrelas += len(estrelas)

        caminho = " ".join(f"{x:.1f},{y:.1f}" for x, y in pontos)
        partes.append(
            f'<polyline points="{caminho}" fill="none" stroke="#9db4ff" '
            f'stroke-opacity="0.22" stroke-width="0.8"/>'
        )

        for indice, ((data, tipo), (x, y)) in enumerate(zip(estrelas, pontos)):
            idade = idade_em_dias(data)
            frescor = max(0.0, 1.0 - min(idade / 120, 1.0))
            raio = 1.6 + 2.2 * frescor
            cor = random.choice(CORES)
            classe = "p" if indice % 2 == 0 else "q"
            atraso = (semente(f"{nome}{indice}") % 40) / 10
            partes.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{raio * 3:.1f}" fill="{cor}" opacity="0.10"/>'
                f'<circle class="{classe}" cx="{x:.1f}" cy="{y:.1f}" r="{raio:.2f}" fill="{cor}" '
                f'style="animation-delay:-{atraso:.1f}s"/>'
            )

        # nome da constelação
        topo = min(y for _, y in pontos)
        partes.append(
            f'<text x="{centro[0]:.0f}" y="{topo - 14:.0f}" fill="#cfd8ff" font-size="11" '
            f'text-anchor="middle" opacity="0.8">{nome}</text>'
        )

    # estrela cadente
    partes.append(
        '<g class="cometa"><line x1="900" y1="60" x2="940" y2="40" stroke="#fff" '
        'stroke-width="1.6" stroke-linecap="round" opacity="0.9"/></g>'
    )

    # horizonte do sertão
    partes.append(serra())
    partes.append(mandacaru(1010))
    partes.append(mandacaru(1068).replace("V" + str(HORIZONTE + 6 - 96), "V" + str(HORIZONTE + 6 - 70)))

    # título
    hoje = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    rotulo = "dados de demonstração" if demo else f"atualizado em {hoje}"
    partes.append(
    f'<text x="40" y="76" fill="#aab6e8" font-size="13">'
    f"{total_estrelas} commits · {len(nomes)} constelações · {rotulo}</text>"
    )

    partes.append("</svg>")

    return "\n".join(partes)

def principal():
    demo = "--demo" in sys.argv
    if demo:
        repos = dados_demo()
    else:
        repos = coletar()
    if not repos:
        print("Nenhum commit encontrado; mantendo o céu anterior.")
        return
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as arquivo:
        arquivo.write(construir_svg(repos, demo))
    print(f"Céu gerado em {SAIDA}")


if __name__ == "__main__":
    principal()
