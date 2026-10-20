# ClearBank — Análise Financeira com Python

Desafio final da disciplina **Análise de Dados e Inteligência de Negócios com IA**, da Pós-Graduação em IA e Automação da Rocketseat.

O notebook lê um extrato de transações em CSV e executa estas etapas:

1. valida e limpa os registros;
2. calcula métricas financeiras por mês;
3. sinaliza transações acima de R$ 10.000,00;
4. exporta o resultado para `relatorio.json`.

A solução principal usa apenas a biblioteca padrão do Python (`csv`, `datetime`, `decimal`, `json`).

## Estrutura

```
├── desafio-final.ipynb   # notebook principal, salvo com as saídas
├── transacoes.csv        # dados de entrada (fictícios)
├── relatorio.json        # relatório gerado pelo notebook
├── grafico.png           # saldo mensal (opcional)
├── analise_pandas.py     # versão alternativa com pandas (opcional)
└── README.md
```

## Como executar

**Requisito:** Python 3.10 ou superior.

### Google Colab

1. Abra o [Google Colab](https://colab.research.google.com) e vá em *Arquivo → Fazer upload de notebook*. Escolha `desafio-final.ipynb`.
2. No painel *Arquivos* (ícone de pasta, à esquerda), envie o `transacoes.csv`.
3. Rode tudo em *Ambiente de execução → Executar tudo*.

`relatorio.json` e `grafico.png` aparecem no mesmo painel.

### Localmente

```bash
pip install notebook matplotlib
jupyter notebook desafio-final.ipynb
```

O notebook procura o `transacoes.csv` na pasta em que foi aberto e grava os arquivos de saída nessa mesma pasta.

### Versão com pandas (opcional)

Rode depois do notebook, porque o script compara os resultados com o `relatorio.json`:

```bash
pip install pandas
python analise_pandas.py
```

## Regras aplicadas

**Formato do CSV:** UTF-8, com o cabeçalho `id,data,cliente_id,tipo,valor,descricao,categoria`.

| Campo | Regra |
|---|---|
| `id` | obrigatório e inteiro |
| `cliente_id` | não pode ser vazio |
| `data` | formato `AAAA-MM-DD` e data existente |
| `tipo` | `credito` ou `debito` |
| `valor` | numérico, finito e maior que zero |
| `descricao`, `categoria` | opcionais |

- Linhas inválidas são contadas, ficam registradas com o motivo da rejeição e não interrompem o processamento.
- **Transação suspeita:** valor estritamente maior que `LIMITE_SUSPEITO = 10000.00`. Um valor de exatamente R$ 10.000,00 não é sinalizado. Isso é só um alerta por valor, não uma classificação de fraude.

**Métricas por mês:**

- quantidade de transações;
- total de créditos e total de débitos;
- saldo (créditos − débitos);
- média por transação (soma dos valores ÷ quantidade);
- maior e menor transação.

**Precisão:** os valores usam `Decimal` e não são arredondados, nem na exibição nem no JSON (ex.: `R$ 10.000,004`). Só a média é arredondada. Há dois limites técnicos para evitar estouro numérico: valores menores que 10⁴⁰ e com até 10 casas decimais.

**Duplicidades:** o desafio não define regra de deduplicação. Por isso, IDs repetidos são mantidos e aparecem apenas como aviso.

## Resultado com os dados de exemplo

| Mês | Créditos | Débitos | Saldo |
|---|---|---|---|
| 2026-01 | R$ 18.500,00 | R$ 1.016,40 | R$ 17.483,60 |
| 2026-02 | R$ 16.700,50 | R$ 10.330,74 | R$ 6.369,76 |
| 2026-03 | R$ 8.480,30 | R$ 11.314,21 | -R$ 2.833,91 |

- **Linhas:** 27 lidas, 17 válidas e 10 inválidas.
- **Período:** 84 dias.
- **Suspeitas:** 3 transações.

## Testes

O próprio notebook contém 101 verificações com `assert`. Elas cobrem:

- cada regra de validação;
- arquivo inexistente, vazio, com cabeçalho errado, com BOM ou em outra codificação;
- ausência de transações válidas e ausência de suspeitas;
- o limite exato de suspeição;
- valores extremos;
- a conferência do `relatorio.json` com o que é exibido.

Todas passaram em Python 3.10 e 3.13.

## Limitações

- O valor deve usar ponto decimal (`1500.00`); o formato `1.500,00` é rejeitado.
- O arquivo precisa estar em UTF-8.
- O limite de suspeição é fixo.
