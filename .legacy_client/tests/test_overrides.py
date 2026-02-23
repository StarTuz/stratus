
import pytest
from client.src.ui.main_window import MainWindow
from client.src.core.sim_data import SimTelemetry, RadioState
from tests.test_prompt_logic import base_telemetry, MockAirports, MockAirport

def test_identity_overrides(base_telemetry):
    """Verify that manual overrides take precedence over telemetry."""
    airports = MockAirports()
    airports.nearest = MockAirport("KLAX", "Los Angeles Intl")
    
    # 1. No overrides -> Uses telemetry ("N12345")
    prompt_default = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Taxiing", "", "Radio check"
    )
    assert "N12345" in prompt_default
    
    # 2. Callsign Override -> Uses override ("D-ERMI")
    overrides = {"callsign": "D-ERMI", "type": "PA28"}
    prompt_override = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Taxiing", "", "Radio check",
        overrides=overrides
    )
    
    assert "D-ERMI" in prompt_override
    assert "N12345" not in prompt_override
    assert "PA28" in prompt_override  # Checks type override too
