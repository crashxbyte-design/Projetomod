"""Módulo de internacionalização (stub) para a UI EliteBR.

A interface usa strings PT-BR nativas, portanto este módulo apenas
retorna o valor padrão fornecido pelo chamador.
"""
from __future__ import annotations

# Dicionário opcional para chaves customizadas (pode ficar vazio)
_translations: dict[str, str] = {}


def get(key: str, default: str = "") -> str:
    """Retorna a tradução para *key* ou *default* se não encontrada."""
    return _translations.get(key, default)


def set_translations(mapping: dict[str, str]) -> None:
    """Substitui o dicionário de traduções."""
    global _translations
    _translations = dict(mapping)
