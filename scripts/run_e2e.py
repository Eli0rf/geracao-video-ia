#!/usr/bin/env python3
"""
scripts/run_e2e.py — Teste End-to-End do pipeline de geração de vídeo.

Dispara um job com `model="fake"`, polia o status via GET /jobs/{id} e
valida se o .mp4 gerado no host (outputs/videos/) possui > 0 bytes.

Dependências: apenas a biblioteca padrão (urllib, json, pathlib).
"""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_SECONDS = 300
MODEL = "fake"
PROMPT = "E2E: tela preta gerada via ffmpeg lavfi"
DURATION = 2
WIDTH = 848
HEIGHT = 480

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = PROJECT_ROOT / "outputs" / "videos"


def http(method: str, path: str, payload: dict | None = None) -> tuple[dict, int]:
    """Envia um pedido HTTP e retorna (payload_decodificado, status)."""
    url = f"{BASE_URL}{path}"
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        url, data=body, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw), response.status
    except urllib.error.HTTPError as exc:
        msg = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"HTTP {exc.code} em {path}: {msg}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Erro de rede em {path}: {exc.reason}") from exc


def wait_for_job(job_id: str, timeout: int = TIMEOUT_SECONDS) -> dict:
    """Polling do job até completed/failed ou timeout."""
    deadline = time.monotonic() + timeout
    while True:
        _, job = http("GET", f"/api/v1/jobs/{job_id}")
        if job["status"] in ("completed", "failed"):
            return job
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Job {job_id} não concluiu em {timeout}s")
        time.sleep(2)


def validate_output() -> bool:
    """Verifica se há algum .mp4 real no host (> 0 bytes)."""
    if not OUTPUTS_DIR.is_dir():
        print(f"[E2E] FAIL: o diretório {OUTPUTS_DIR} não existe.")
        print("         Execute: docker compose up -d --build")
        return False

    mp4s = sorted(OUTPUTS_DIR.glob("*.mp4"))
    if not mp4s:
        print(f"[E2E] FAIL: nenhum .mp4 encontrado em {OUTPUTS_DIR}")
        return False

    ok = True
    for mp4 in mp4s:
        size = mp4.stat().st_size
        if size <= 0:
            print(f"[E2E] FAIL: {mp4} tem 0 bytes")
            ok = False
        else:
            print(f"[E2E] OK: {mp4} ({size} bytes)")
    return ok


def main() -> int:
    print(
        f"[E2E] POST /jobs: model={MODEL}, prompt={PROMPT!r}, "
        f"duration={DURATION}s, {WIDTH}x{HEIGHT}"
    )
    status, body = http(
        "POST",
        "/api/v1/jobs",
        {
            "prompt": PROMPT,
            "model": MODEL,
            "duration_seconds": DURATION,
            "width": WIDTH,
            "height": HEIGHT,
        },
    )
    print(f"[E2E] POST /jobs → {status} {json.dumps(body)}")

    if status != 202:
        print(f"[E2E] FAIL: erro ao criar job (status {status})")
        return 1

    job_id = body.get("id")
    if not job_id:
        print(f"[E2E] FAIL: resposta inesperada sem 'id': {body}")
        return 1

    print(f"[E2E] Espionando job {job_id} (timeout {TIMEOUT_SECONDS}s)...")
    job = wait_for_job(job_id)
    print(f"[E2E] Job {job_id} → status={job['status']}")

    if job["status"] != "completed":
        print(f"[E2E] FAIL: job não concluiu: {job.get('error_message')}")
        return 1

    output_url = job.get("output_url")
    print(f"[E2E] output_url: {output_url}")

    if not validate_output():
        print("[E2E] RESULTADO: FAIL — nenhum .mp4 válido gerado.")
        return 1

    print("[E2E] RESULTADO: PASS — .mp4 real gerado em outputs/videos/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
