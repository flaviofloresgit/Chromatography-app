"""
Repository interface for sample data and analysis history storage.
Decoupled from Streamlit or any web framework.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from ..models import SampleAnalysis, SampleMetadata, IdentificationResult, PeakData


class BaseSampleRepository(ABC):
    """Abstract interface for sample persistence and history."""

    @abstractmethod
    def save_sample_analysis(
        self,
        analysis: SampleAnalysis,
        raw_file_bytes: Optional[bytes] = None,
        raw_filename: str = ""
    ) -> str:
        """Saves a complete sample analysis. Returns the saved sample ID."""
        pass

    @abstractmethod
    def get_sample_analysis(self, sample_id: str) -> Optional[SampleAnalysis]:
        """Retrieves a complete sample analysis by its ID."""
        pass

    @abstractmethod
    def list_samples(self) -> List[Dict[str, Any]]:
        """Returns summary list of all analyzed samples."""
        pass

    @abstractmethod
    def delete_sample(self, sample_id: str) -> bool:
        """Deletes a sample and its associated peaks and identifications."""
        pass

    @abstractmethod
    def save_chat_message(self, sample_id: str, role: str, content: str) -> None:
        """Stores a chat message associated with a sample."""
        pass

    @abstractmethod
    def get_chat_history(self, sample_id: str) -> List[Dict[str, str]]:
        """Retrieves chat messages for a sample."""
        pass
