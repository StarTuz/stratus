"""
Core module for SayIntentions.AI native client.

Contains:
- sapi_interface: SAPI REST API wrappers
"""

from .sapi_interface import (
    ISapiService,
    SapiService,
    MockSapiService,
    create_sapi_service,
    SapiResponse,
    CommEntry,
    WeatherData,
    ParkingInfo,
    Channel,
    Entity
)

__all__ = [
    "ISapiService",
    "SapiService", 
    "MockSapiService",
    "create_sapi_service",
    "SapiResponse",
    "CommEntry",
    "WeatherData",
    "ParkingInfo",
    "Channel",
    "Entity"
]
