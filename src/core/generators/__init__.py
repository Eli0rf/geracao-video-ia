"""
src/core/generators — Implementações concretas dos contratos do motor.

Cada submódulo implementa um Protocol de `src/core/interfaces.py`:

    ollama.py → OllamaScriptGenerator   (ScriptGenerator, ADR-006)
    piper.py  → PiperAudioSynthesizer   (AudioSynthesizer, ADR-006)
    (futuro) animatediff.py / wan21.py → VideoGenerator (ADR-003)

A `factory.py` resolve qual implementação usar, com fallback para os fakes
quando o serviço real está indisponível.
"""
