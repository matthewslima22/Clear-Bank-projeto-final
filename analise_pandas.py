"""ClearBank — implementação alternativa com pandas (opcional).

Aplica as mesmas regras de limpeza da solução principal (desafio-final.ipynb),
calcula as mesmas métricas mensais com groupby e compara o resultado com o
relatorio.json gerado pelo notebook.

Uso (na pasta clearbank-analise/, depois de executar o notebook):
    python analise_pandas.py

Diferenças de tipos e arredondamento em relação ao notebook:
- O notebook usa Decimal (valores exatos) e só arredonda a média, na precisão dos
  valores do mês. Aqui os valores viram float64, sujeitos a erro de representação
  binária (ex.: 0.1 + 0.2 = 0.30000000000000004) e a cerca de 15-17 dígitos
  significativos: valores muito grandes (ex.: 1e30 + 0.01) perdem os centavos.
- Por isso a comparação usa tolerância de meio centavo (0.005), adequada ao
  conjunto de demonstração, cujos valores têm até 2 casas e ordem de grandeza baixa.
- IDs são int64 e datas são Timestamp (no notebook: int e datetime).
- Para que as regras de limpeza sejam idênticas, id e valor são convertidos com
  int() e Decimal() via .map: pd.to_numeric não aceita, por exemplo, "1_000" ou
  dígitos não ASCII, que o notebook aceita. As agregações usam groupby.

Esta versão NÃO substitui a implementação obrigatória com o módulo csv.
"""

import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd

LIMITE_SUSPEITO = 10000.00
COLUNAS_OBRIGATORIAS = ["id", "data", "cliente_id", "tipo", "valor", "descricao", "categoria"]
TIPOS_VALIDOS = ["credito", "debito"]
MAGNITUDE_MAXIMA = 40          # mesmos limites técnicos do notebook
CASAS_DECIMAIS_MAXIMAS = 10
TOLERANCIA = 0.005

PASTA = Path(__file__).resolve().parent
CAMINHO_CSV = PASTA / "transacoes.csv"
CAMINHO_JSON = PASTA / "relatorio.json"


def carregar_csv(caminho):
    """Lê o CSV com tudo como texto, para validar com as mesmas regras do notebook."""
    df = pd.read_csv(caminho, dtype=str, keep_default_na=False, encoding="utf-8")
    ausentes = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if ausentes:
        raise ValueError(f"colunas obrigatórias ausentes: {', '.join(ausentes)}")
    return df


def converter_id(texto):
    try:
        return int(texto)
    except ValueError:
        return None


def converter_valor(texto):
    """Mesmas regras do notebook; devolve float ou None se inválido."""
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        return None
    if not valor.is_finite() or valor <= 0 or valor.adjusted() >= MAGNITUDE_MAXIMA:
        return None
    _, digitos, expoente = valor.as_tuple()
    significativos = "".join(map(str, digitos)).rstrip("0")
    casas = max(0, -(expoente + len(digitos) - len(significativos)))
    return None if casas > CASAS_DECIMAIS_MAXIMAS else float(valor)


def validar(df):
    """Devolve (validas, quantidade_invalidas) aplicando as regras do notebook."""
    d = df[COLUNAS_OBRIGATORIAS].apply(lambda coluna: coluna.str.strip())

    ids = d["id"].map(converter_id)
    cliente_ok = d["cliente_id"] != ""
    formato_ok = d["data"].str.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
    datas = pd.to_datetime(d["data"].where(formato_ok), format="%Y-%m-%d", errors="coerce")
    data_ok = formato_ok & datas.notna()
    tipo_ok = d["tipo"].isin(TIPOS_VALIDOS)
    valores = d["valor"].map(converter_valor)

    valido = ids.notna() & cliente_ok & data_ok & tipo_ok & valores.notna()
    validas = d[valido].assign(
        id=ids[valido].astype("int64"),
        data=datas[valido],
        valor=valores[valido].astype("float64"),
    )
    validas["mes"] = validas["data"].dt.strftime("%Y-%m")
    return validas, int((~valido).sum())


def calcular_metricas(validas):
    """Métricas mensais com groupby, nas mesmas regras do notebook."""
    v = validas.assign(
        credito=validas["valor"].where(validas["tipo"] == "credito", 0.0),
        debito=validas["valor"].where(validas["tipo"] == "debito", 0.0),
    )
    grupos = v.groupby("mes", sort=True)
    resumo = grupos.agg(
        quantidade=("valor", "size"),
        total_credito=("credito", "sum"),
        total_debito=("debito", "sum"),
        soma=("valor", "sum"),
    )
    resumo["saldo"] = resumo["total_credito"] - resumo["total_debito"]
    resumo["media_por_transacao"] = resumo["soma"] / resumo["quantidade"]
    # idxmax/idxmin devolvem a primeira ocorrência em empates, como max/min do Python.
    resumo["id_maior"] = v.loc[grupos["valor"].idxmax(), "id"].to_numpy()
    resumo["id_menor"] = v.loc[grupos["valor"].idxmin(), "id"].to_numpy()
    return resumo.drop(columns="soma")


def comparar_com_notebook(validas, invalidas, resumo, caminho_json):
    """Compara com relatorio.json; devolve a lista de divergências."""
    with open(caminho_json, encoding="utf-8") as arquivo:
        nativo = json.load(arquivo)

    divergencias = []
    verificacoes = 0

    def checar(nome, obtido, esperado, tolerancia=0.0):
        nonlocal verificacoes
        verificacoes += 1
        if isinstance(esperado, float):
            ok = abs(float(obtido) - esperado) <= tolerancia
        else:
            ok = obtido == esperado
        if not ok:
            divergencias.append(f"{nome}: pandas={obtido!r} notebook={esperado!r}")

    checar("total_validas", len(validas), nativo["total_transacoes_validas"])
    checar("total_invalidas", invalidas, nativo["total_transacoes_invalidas"])
    checar("meses", list(resumo.index), list(nativo["resumo_mensal"]))

    for mes, linha in resumo.iterrows():
        m = nativo["resumo_mensal"].get(mes)
        if m is None:
            divergencias.append(f"{mes}: ausente no notebook")
            continue
        checar(f"{mes}.quantidade", int(linha["quantidade"]), m["quantidade"])
        for campo in ("total_credito", "total_debito", "saldo", "media_por_transacao"):
            checar(f"{mes}.{campo}", linha[campo], float(m[campo]), TOLERANCIA)
        checar(f"{mes}.maior_transacao.id", int(linha["id_maior"]), m["maior_transacao"]["id"])
        checar(f"{mes}.menor_transacao.id", int(linha["id_menor"]), m["menor_transacao"]["id"])

    suspeitas = validas.loc[validas["valor"] > LIMITE_SUSPEITO, "id"].tolist()
    checar("ids_suspeitos", suspeitas, [s["id"] for s in nativo["transacoes_suspeitas"]])
    return verificacoes, divergencias


def formatar_moeda(valor):
    texto = f"{abs(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{'-' if valor < 0 else ''}R$ {texto}"


def main():
    try:
        df = carregar_csv(CAMINHO_CSV)
    except FileNotFoundError:
        print(f"[ERRO] arquivo não encontrado: {CAMINHO_CSV}")
        return 1

    validas, invalidas = validar(df)
    resumo = calcular_metricas(validas)

    print(f"Linhas lidas: {len(df)} | válidas: {len(validas)} | inválidas: {invalidas}\n")
    exibicao = resumo.copy()
    for campo in ("total_credito", "total_debito", "saldo", "media_por_transacao"):
        exibicao[campo] = exibicao[campo].map(formatar_moeda)
    print(exibicao.to_string())
    print(f"\nTipos no pandas: valor={validas['valor'].dtype}, id={validas['id'].dtype}, "
          f"data={validas['data'].dtype}")

    if not CAMINHO_JSON.exists():
        print("\nrelatorio.json não encontrado: execute o notebook antes da comparação.")
        return 1

    verificacoes, divergencias = comparar_com_notebook(validas, invalidas, resumo, CAMINHO_JSON)
    print(f"\nComparação com o notebook: {verificacoes} verificações, {len(divergencias)} divergência(s).")
    for d in divergencias:
        print(f"  - {d}")
    return 1 if divergencias else 0


if __name__ == "__main__":
    sys.exit(main())
