
import pytest
from unittest.mock import MagicMock
from client.src.core.copilot import CoPilot

class TestCoPilot:
    @pytest.fixture
    def sim_data(self):
        sim = MagicMock()
        # Mock telemetry read return for "current" state check
        sim.read_telemetry.return_value.com1.active = "120.000"
        return sim

    @pytest.fixture
    def copilot(self, sim_data):
        cp = CoPilot(sim_data)
        cp.set_enabled(True)
        return cp

    def test_frequency_parsing(self, copilot, sim_data):
        # 1. Standard frequency
        text = "Contact Tower on 118.5 now."
        actions = copilot.process_atc_instruction(text)
        
        assert len(actions) == 1
        assert "Tuned COM1 to 118.5" in actions[0]
        sim_data.set_com1_active.assert_called_with("118.5")

    def test_frequency_decimal_parsing(self, copilot, sim_data):
        # 2. Frequency with 3 decimals
        text = "Contact Ground 121.750"
        actions = copilot.process_atc_instruction(text)
        
        assert "Tuned COM1 to 121.750" in actions[0]
        sim_data.set_com1_active.assert_called_with("121.750")

    def test_ignore_out_of_band(self, copilot, sim_data):
        # 3. Frequency like 108.0 (NAV) should be ignored
        text = "Tune VOR 110.5"
        actions = copilot.process_atc_instruction(text)
        assert len(actions) == 0
        sim_data.set_com1_active.assert_not_called()

    def test_squawk_parsing(self, copilot, sim_data):
        # 4. Standard squawk
        text = "Squawk 4521 and ident."
        actions = copilot.process_atc_instruction(text)
        
        assert "Set Transponder to 4521" in actions[0]
        sim_data.set_transponder_code.assert_called_with("4521")

    def test_squawk_keyword_required(self, copilot, sim_data):
        # 5. Just a 4 digit number (e.g. altitude) shouldn't trigger squawk
        text = "Climb to 4500 feet"
        actions = copilot.process_atc_instruction(text)
        
        assert len(actions) == 0
        sim_data.set_transponder_code.assert_not_called()

    def test_disabled_state(self, copilot, sim_data):
        # 6. Disabled shouldn't do anything
        copilot.set_enabled(False)
        text = "Contact Tower 118.5"
        actions = copilot.process_atc_instruction(text)
        
        assert len(actions) == 0
        sim_data.set_com1_active.assert_not_called()
