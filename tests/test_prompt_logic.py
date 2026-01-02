
import pytest
from unittest.mock import MagicMock
from client.src.ui.main_window import MainWindow
from client.src.core.sim_data import SimTelemetry, RadioState

class MockAirport:
    def __init__(self, icao, name):
        self.icao = icao
        self.name = name

class MockAirports:
    def __init__(self):
        self.airports = {
            "KLAX": MockAirport("KLAX", "Los Angeles International Airport"),
            "KJFK": MockAirport("KJFK", "John F. Kennedy International Airport"),
            "KTRK": MockAirport("KTRK", "Truckee Tahoe Airport"),
        }
        self.nearest = None

    def find_nearest(self, lat, lon):
        return self.nearest

@pytest.fixture
def base_telemetry():
    t = SimTelemetry()
    t.connected = True
    t.tail_number = "N12345"
    t.com1 = RadioState(active="118.500")
    t.latitude = 34.0
    t.longitude = -118.0
    t.altitude_msl = 1000.0
    t.on_ground = True
    t.heading_mag = 270.0
    t.ias = 0.0
    return t

def test_dynamic_facility_name(base_telemetry):
    """Verify explicit facility names appear in the prompt."""
    airports = MockAirports()
    
    # CASE 1: Los Angeles
    airports.nearest = MockAirport("KLAX", "Los Angeles International Airport")
    prompt_la = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Taxiing", "", "Request taxi"
    )
    
    assert "Los Angeles" in prompt_la
    assert "1. INITIAL CONTACT" in prompt_la
    assert "Truckee" not in prompt_la  # Crucial regression check

    # CASE 2: New York (Simulate flying to new destination)
    airports.nearest = MockAirport("KJFK", "John F. Kennedy International Airport")
    prompt_ny = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Taxiing", "", "Request taxi"
    )
    
    assert "John F. Kennedy" in prompt_ny
    assert "Los Angeles" not in prompt_ny
    assert "Truckee" not in prompt_ny

def test_truckee_regression(base_telemetry):
    """Verify Truckee ONLY appears if we are properly at Truckee."""
    airports = MockAirports()
    
    # Not at Truckee -> No Truckee
    airports.nearest = MockAirport("KSFO", "San Francisco International")
    prompt_sf = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Taxiing", "", "Request taxi"
    )
    assert "Truckee" not in prompt_sf

    # At Truckee -> Explicit Truckee
    airports.nearest = MockAirport("KTRK", "Truckee Tahoe Airport")
    prompt_truckee = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Taxiing", "", "Request taxi"
    )
    assert "Truckee" in prompt_truckee

def test_generic_fallback(base_telemetry):
    """Verify we fall back to 'Local' or 'Generic' if no airport found."""
    airports = MockAirports()
    airports.nearest = None # Middle of ocean
    
    prompt = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Cruise", "", "Position report"
    )
    
    assert "You are Air Traffic Control at Local" in prompt
    assert "Truckee" not in prompt

def test_disconnected_state():
    """Verify prompt behavior when disconnected."""
    t = SimTelemetry()
    t.connected = False
    
    prompt = MainWindow.build_atc_prompt(
        t, MockAirports(), "Unknown", "", "Hello"
    )
    
    assert "Simulator disconnected" in prompt
    assert "Truckee" not in prompt

def test_flight_following_prompt_structure(base_telemetry):
    """Verify checks for VFR Flight Following examples in the prompt."""
    airports = MockAirports()
    airports.nearest = MockAirport("KSFO", "San Francisco International")
    
    prompt = MainWindow.build_atc_prompt(
        base_telemetry, airports, "Climb", "", "Request flight following"
    )
    
    # Verify the specific FAA examples exist
    assert "2. FLIGHT FOLLOWING REQUEST:" in prompt
    assert "squawk 4521, ident" in prompt
    assert "4. SERVICE TERMINATION" in prompt
    assert "radar service terminated" in prompt
