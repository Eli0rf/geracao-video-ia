#!/usr/bin/env python3
"""
validate.py — Agente validador usando API Gemini.

Uso:
    python scripts/validate.py --code path/to/file.py
    python scripts/validate.py --code path/to/file.py --spec "descrição da task"
    python scripts/validate.py --stdin  (lê código do stdin)

Retorna:
    Exit 0 — aprovado
    Exit 1 — rejeitado (problemas encontrados)
    Exit 2 — erro de configuração/rede

Variáveis de ambiente necessárias:
    GEMINI_API_KEY — chave da API Gemini (em .env)
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Carrega .env se existir (sem dependência de python-dotenv para portabilidade)
def _load_env(env_path: Path) -> None:
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            # Não sobrescreve variáveis já definidas no ambiente
            if key.strip() not in os.environ:
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


# Carrega .env do diretório raiz do projeto
_project_root = Path(__file__).parent.parent
_load_env(_project_root / ".env")


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("❌ GEMINI_API_KEY não encontrada.", file=sys.stderr)
        print("   Configure em .env: GEMINI_API_KEY=sua_chave", file=sys.stderr)
        sys.exit(2)
    return key


def build_review_prompt(code: str, spec: str, filename: str) -> str:
    return f"""Você é um engenheiro sênior revisando código Python gerado por IA.

Analise o código abaixo e verifique os 5 eixos:

1. **Corretude lógica** — o código faz o que a spec descreve? Há bugs?
2. **Edge cases** — inputs inválidos, nulos, vazios, limites estão tratados?
3. **Segurança** — há exposição de dados sensíveis, injeção ou falhas de validação?
4. **Retrocompatibilidade** — quebra contratos ou interfaces existentes?
5. **Qualidade** — nomenclatura clara, sem complexidade desnecessária?

---

**Arquivo:** `{filename}`

**Spec / contexto da task:**
{spec if spec else "(nenhuma spec fornecida — avaliar o código por si só)"}

**Código:**
```python
{code}
```

---

Responda APENAS em JSON válido, sem texto fora do JSON:

{{
  "verdict": "approved" | "rejected" | "warning",
  "summary": "uma linha descrevendo o resultado geral",
  "issues": [
    {{
      "axis": "corretude | edge_cases | segurança | retrocompat | qualidade",
      "severity": "critical | major | minor | nit",
      "description": "descrição clara do problema",
      "suggestion": "como corrigir"
    }}
  ],
  "approved_aspects": ["o que está correto e bem feito"]
}}

Se não houver issues, retorne lista vazia em "issues".
"""


def call_gemini(prompt: str, api_key: str) -> dict:
    """Chama a API Gemini REST diretamente (sem SDK para zero dependências extras).
    
    Tenta os modelos em ordem até um funcionar:
      1. gemini-3.8-flash (mais recente)
      2. gemini-2.5-flash (estável)
      3. gemini-1.5-flash (fallback confiável)
    """
    try:
        import urllib.request
        import urllib.error
        import time
    except ImportError:
        print("❌ urllib não disponível.", file=sys.stderr)
        sys.exit(2)

    models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(payload).encode("utf-8")

    last_error = ""
    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            # Sucesso — extrai resposta
            try:
                raw_text = body["candidates"][0]["content"]["parts"][0]["text"]
                print(f"   (modelo usado: {model})", file=sys.stderr)
                return json.loads(raw_text)
            except (KeyError, IndexError, json.JSONDecodeError) as e:
                print(f"❌ Resposta inesperada do modelo {model}: {e}", file=sys.stderr)
                sys.exit(2)

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            if e.code in (404, 503, 429):
                # Modelo indisponível/sobrecarregado — tenta próximo
                last_error = f"HTTP {e.code} em {model}"
                print(f"   ⚠ {model} indisponível ({e.code}), tentando próximo...", file=sys.stderr)
                if e.code == 429:
                    time.sleep(2)  # Rate limit — pequena espera
                continue
            else:
                print(f"❌ Erro na API Gemini (HTTP {e.code}): {error_body}", file=sys.stderr)
                sys.exit(2)
        except urllib.error.URLError as e:
            print(f"❌ Falha de conexão com a API Gemini: {e.reason}", file=sys.stderr)
            sys.exit(2)
        except TimeoutError:
            print(f"   ⚠ Timeout em {model}, tentando próximo...", file=sys.stderr)
            continue

    print(f"❌ Todos os modelos Gemini indisponíveis. Último erro: {last_error}", file=sys.stderr)
    sys.exit(2)


def format_output(result: dict, filename: str) -> tuple[str, int]:
    """Formata o resultado para exibição e retorna (output, exit_code)."""
    verdict = result.get("verdict", "rejected")
    summary = result.get("summary", "")
    issues = result.get("issues", [])
    approved_aspects = result.get("approved_aspects", [])

    lines = []

    # Cabeçalho
    icons = {"approved": "✅", "warning": "⚡", "rejected": "⚠️"}
    labels = {"approved": "APROVADO", "warning": "APROVADO COM RESSALVAS", "rejected": "REJEITADO"}
    icon = icons.get(verdict, "⚠️")
    label = labels.get(verdict, "REJEITADO")

    lines.append(f"\n{icon} VALIDADOR: {label} — {filename}")
    lines.append(f"   {summary}")

    # Issues
    if issues:
        severity_order = {"critical": 0, "major": 1, "minor": 2, "nit": 3}
        sorted_issues = sorted(issues, key=lambda x: severity_order.get(x.get("severity", "nit"), 3))

        lines.append("\n   Problemas encontrados:")
        for issue in sorted_issues:
            sev = issue.get("severity", "nit").upper()
            axis = issue.get("axis", "")
            desc = issue.get("description", "")
            suggestion = issue.get("suggestion", "")
            lines.append(f"   [{sev}] ({axis}) {desc}")
            if suggestion:
                lines.append(f"          → {suggestion}")

    # Aspectos aprovados
    if approved_aspects:
        lines.append("\n   Pontos positivos:")
        for aspect in approved_aspects:
            lines.append(f"   ✓ {aspect}")

    lines.append("")

    exit_code = 0 if verdict in ("approved", "warning") else 1
    return "\n".join(lines), exit_code


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Valida código Python usando a API Gemini como revisor."
    )
    parser.add_argument(
        "--code", "-c",
        type=Path,
        help="Caminho para o arquivo de código a revisar",
    )
    parser.add_argument(
        "--spec", "-s",
        type=str,
        default="",
        help="Descrição da task ou spec (contexto para o revisor)",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Lê código do stdin em vez de arquivo",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Retorna resultado bruto em JSON",
    )
    args = parser.parse_args()

    # Lê o código
    if args.stdin:
        code = sys.stdin.read()
        filename = "<stdin>"
    elif args.code:
        if not args.code.exists():
            print(f"❌ Arquivo não encontrado: {args.code}", file=sys.stderr)
            sys.exit(2)
        code = args.code.read_text(encoding="utf-8")
        filename = str(args.code)
    else:
        parser.print_help()
        sys.exit(2)

    if not code.strip():
        print("❌ Código vazio — nada para validar.", file=sys.stderr)
        sys.exit(2)

    # Chama Gemini
    api_key = get_api_key()
    prompt = build_review_prompt(code, args.spec, filename)

    print(f"🔍 Validando {filename} com Gemini...", file=sys.stderr)
    result = call_gemini(prompt, api_key)

    # Saída
    if args.output_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        exit_code = 0 if result.get("verdict") in ("approved", "warning") else 1
    else:
        output, exit_code = format_output(result, filename)
        print(output)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
