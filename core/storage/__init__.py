"""
Storage and repository layer for sample history and persistence.
"""

import os
from .repository_interface import BaseSampleRepository
from .local_repo import LocalSampleRepository
from .supabase_repo import SupabaseSampleRepository, SUPABASE_LIB_AVAILABLE


def get_repository() -> BaseSampleRepository:
    """
    Returns SupabaseSampleRepository if SUPABASE_URL and SUPABASE_KEY are provided
    and valid; otherwise seamlessly returns LocalSampleRepository.
    """
    url = os.getenv("SUPABASE_URL", "").strip()
    key = os.getenv("SUPABASE_KEY", "").strip()

    if SUPABASE_LIB_AVAILABLE and url and key and not url.startswith("https://tu-proyecto"):
        try:
            repo = SupabaseSampleRepository(url, key)
            if repo.is_connected():
                return repo
        except Exception:
            pass

    return LocalSampleRepository()


__all__ = [
    "BaseSampleRepository",
    "LocalSampleRepository",
    "SupabaseSampleRepository",
    "get_repository"
]
