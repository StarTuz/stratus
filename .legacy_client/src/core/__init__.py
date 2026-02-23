"""
Core module for StratusATC native client.

Contains:
- sapi_interface: SAPI REST API wrappers
- sim_data: Simulator data interface (X-Plane telemetry)
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

from .sim_data import (
    SimDataInterface,
    SimTelemetry,
    RadioState,
    TransponderState
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
    "Entity",
    "SimDataInterface",
    "SimTelemetry",
    "RadioState",
    "TransponderState"
]
