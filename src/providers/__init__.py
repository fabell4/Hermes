"""Test providers package for Hermes.

Providers implement the BaseTestProvider interface and are orchestrated by
SpeedtestRunner, which tries each in order and falls back on failure.
"""

from src.providers.base import BaseTestProvider
from src.providers.ndt7 import NDT7Provider
from src.providers.ookla import OoklaProvider

__all__ = ["BaseTestProvider", "NDT7Provider", "OoklaProvider"]
