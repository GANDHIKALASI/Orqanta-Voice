"""Vendored text normaliser.

The modules in this directory are byte-identical copies of the source (see orqanta_voice/text/README.md); only this
__init__.py was added so they import as a package.  Use orqanta_voice.text.normalise_text rather than this package directly.
"""
from .normalize import NormalizationError, normalize, resolve_language  # noqa: F401
