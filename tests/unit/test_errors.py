"""
Testes para exceções de domínio e utilitários (src/core/errors.py).
"""

import pytest

from src.core.errors import (
    AssemblyError,
    GenerationError,
    GenerationTimeoutError,
    ModelUnavailableError,
    is_out_of_memory_error,
)


class TestHierarchy:
    def test_all_errors_inherit_generation_error(self) -> None:
        assert issubclass(ModelUnavailableError, GenerationError)
        assert issubclass(GenerationTimeoutError, GenerationError)
        assert issubclass(AssemblyError, GenerationError)


class TestIsOutOfMemoryError:
    @pytest.mark.parametrize(
        "exc",
        [
            RuntimeError("MPS backend out of memory"),
            RuntimeError("CUDA out of memory. Tried to allocate 2.00 GiB"),
            RuntimeError("DefaultCPUAllocator: not enough memory"),
        ],
    )
    def test_detects_message_based_oom(self, exc: Exception) -> None:
        assert is_out_of_memory_error(exc) is True

    def test_detects_oom_exception_class(self) -> None:
        class OutOfMemoryError(Exception):
            pass

        assert is_out_of_memory_error(OutOfMemoryError()) is True

    @pytest.mark.parametrize(
        "exc",
        [ValueError("prompt inválido"), RuntimeError("disco cheio"), KeyError("x")],
    )
    def test_other_errors_are_not_oom(self, exc: Exception) -> None:
        assert is_out_of_memory_error(exc) is False
