import configparser
import os
from .base import IATCProvider
from .local import LocalSpeechProvider


def get_provider(config_path: str = "config.ini") -> IATCProvider:
    """
    Factory function to return the configured ATC provider.
    
    Currently only the local provider (Ollama + speechd-ng) is supported.
    """
    # Config is reserved for future provider options
    return LocalSpeechProvider()
