"""
StratusATC X-Plane Plugin

A bidirectional adapter for Stratus ATC native Mac/Linux client.

Features:
- Exports telemetry (position, attitude, frequencies, transponder) to JSON
- Reads command files to set frequencies/transponder in the sim
- Updates every 0.5 seconds via FlightLoop

Data Exchange:
  ~/.local/share/StratusATC/stratus_telemetry.json  (plugin writes, client reads)
  ~/.local/share/StratusATC/stratus_commands.json   (client writes, plugin reads)
"""

import os
import json
import time
from typing import Optional

try:
    import xp
except ImportError:
    # For development/testing outside X-Plane
    xp = None

# Import the overlay module
try:
    import overlay
except ImportError:
    overlay = None


class PythonInterface:
    """X-Plane Python Plugin Interface."""
    
    def XPluginStart(self):
        self.Name = "StratusATC Adapter"
        self.Sig = "com.stratusatc.adapter"
        self.Desc = "Bidirectional adapter for Stratus ATC client"
        
        self.running = True
        self.last_command_time = 0
        
        # Initialize In-Sim Overlay (optional - may fail if ImGui not available)
        if overlay:
            if overlay.init_overlay():
                xp.log("[StratusATC] In-sim overlay initialized")
            else:
                xp.log("[StratusATC] In-sim overlay disabled (ImGui not available)")
        
        # Data directory
        self.data_dir = os.path.expanduser("~/.local/share/StratusATC")
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        # File paths for data exchange
        self.telemetry_file = os.path.join(self.data_dir, "stratus_telemetry.json")
        self.commands_file = os.path.join(self.data_dir, "stratus_commands.json")
        
        # Initialize DataRefs
        self._init_datarefs()
        
        # Register flight loop callback
        self.flight_loop_id = xp.createFlightLoop(self._flight_loop_callback)
        xp.scheduleFlightLoop(self.flight_loop_id, 0.5)  # Every 0.5 seconds
        
        xp.log(f"[StratusATC] Plugin started. Data dir: {self.data_dir}")
        return self.Name, self.Sig, self.Desc
    
    def XPluginStop(self):
        self.running = False
        if hasattr(self, 'flight_loop_id'):
            xp.destroyFlightLoop(self.flight_loop_id)
        
        # Cleanup Overlay
        if overlay:
            overlay.cleanup_overlay()
            
        xp.log("[StratusATC] Plugin stopped")
    
    def XPluginEnable(self):
        return 1
    
    def XPluginDisable(self):
        if overlay:
            overlay.hide()
    
    def XPluginReceiveMessage(self, inFromWho, inMessage, inParam):
        pass
    
    def _init_datarefs(self):
        """Initialize all DataRefs we'll be using."""
        
        # =====================================================================
        # Position & Attitude
        # =====================================================================
        self.dr_lat = xp.findDataRef("sim/flightmodel/position/latitude")
        self.dr_lon = xp.findDataRef("sim/flightmodel/position/longitude")
        self.dr_alt_msl = xp.findDataRef("sim/flightmodel/position/elevation")
        self.dr_alt_agl = xp.findDataRef("sim/flightmodel/position/y_agl")
        self.dr_hdg_mag = xp.findDataRef("sim/flightmodel/position/mag_psi")
        self.dr_hdg_true = xp.findDataRef("sim/flightmodel/position/psi")
        self.dr_pitch = xp.findDataRef("sim/flightmodel/position/theta")
        self.dr_roll = xp.findDataRef("sim/flightmodel/position/phi")
        self.dr_on_ground = xp.findDataRef("sim/flightmodel/failures/onground_any")
        
        # =====================================================================
        # Speed
        # =====================================================================
        self.dr_ias = xp.findDataRef("sim/flightmodel/position/indicated_airspeed")
        self.dr_tas = xp.findDataRef("sim/flightmodel/position/true_airspeed")
        self.dr_gs = xp.findDataRef("sim/flightmodel/position/groundspeed")
        self.dr_vs = xp.findDataRef("sim/flightmodel/position/vh_ind_fpm")
        
        # =====================================================================
        # COM Radios (833 kHz spacing for X-Plane 12)
        # =====================================================================
        self.dr_com1_active = xp.findDataRef("sim/cockpit2/radios/actuators/com1_frequency_hz_833")
        self.dr_com1_standby = xp.findDataRef("sim/cockpit2/radios/actuators/com1_standby_frequency_hz_833")
        self.dr_com2_active = xp.findDataRef("sim/cockpit2/radios/actuators/com2_frequency_hz_833")
        self.dr_com2_standby = xp.findDataRef("sim/cockpit2/radios/actuators/com2_standby_frequency_hz_833")
        
        # COM Power (0 = off, 1 = on)
        self.dr_com1_power = xp.findDataRef("sim/cockpit2/radios/actuators/com1_power")
        self.dr_com2_power = xp.findDataRef("sim/cockpit2/radios/actuators/com2_power")
        
        # =====================================================================
        # NAV Radios
        # =====================================================================
        self.dr_nav1_active = xp.findDataRef("sim/cockpit2/radios/actuators/nav1_frequency_hz")
        self.dr_nav1_standby = xp.findDataRef("sim/cockpit2/radios/actuators/nav1_standby_frequency_hz")
        self.dr_nav2_active = xp.findDataRef("sim/cockpit2/radios/actuators/nav2_frequency_hz")
        self.dr_nav2_standby = xp.findDataRef("sim/cockpit2/radios/actuators/nav2_standby_frequency_hz")
        
        # =====================================================================
        # Transponder
        # =====================================================================
        self.dr_xpdr_code = xp.findDataRef("sim/cockpit/radios/transponder_code")
        self.dr_xpdr_mode = xp.findDataRef("sim/cockpit/radios/transponder_mode")
        # Mode: 0=off, 1=standby, 2=on, 3=test, 4=alt (mode C/S)
        
        self.dr_xpdr_id = xp.findDataRef("sim/cockpit2/radios/indicators/transponder_id")
        
        # =====================================================================
        # Aircraft Info
        # =====================================================================
        self.dr_tailnum = xp.findDataRef("sim/aircraft/view/acf_tailnum")
        self.dr_livery_path = xp.findDataRef("sim/aircraft/view/acf_livery_path")
        self.dr_icao = xp.findDataRef("sim/aircraft/view/acf_ICAO")
        
        # =====================================================================
        # Autopilot
        # =====================================================================
        self.dr_ap_alt = xp.findDataRef("sim/cockpit2/autopilot/altitude_dial_ft")
        self.dr_ap_hdg = xp.findDataRef("sim/cockpit/autopilot/heading_mag")
        self.dr_ap_vs = xp.findDataRef("sim/cockpit/autopilot/vertical_velocity")
        
        xp.log("[StratusATC] DataRefs initialized")
    
    def _flight_loop_callback(self, sinceLast, elapsedTime, counter, refCon):
        """Called every 0.5 seconds to update telemetry and process commands."""
        if not self.running:
            return 0  # Stop the flight loop
        
        try:
            # Export telemetry
            self._write_telemetry()
            
            # Process any incoming commands
            self._process_commands()
            
        except Exception as e:
            xp.log(f"[StratusATC] Error in flight loop: {e}")
        
        return 0.5  # Call again in 0.5 seconds
    
    def _hz_to_freq_str(self, khz: int) -> str:
        """
        Convert frequency from 833 kHz DataRef to string like '121.500'.
        
        The sim/cockpit2/radios/actuators/com*_frequency_hz_833 DataRefs
        actually return frequency in kHz (e.g., 135055 = 135.055 MHz).
        """
        if khz == 0:
            return "---"
        mhz = khz / 1000.0
        return f"{mhz:.3f}"
    
    def _freq_str_to_hz(self, freq_str: str) -> int:
        """
        Convert frequency string like '121.500' to kHz for 833 DataRefs.
        """
        try:
            mhz = float(freq_str)
            return int(mhz * 1000)
        except ValueError:
            return 0
    
    def _get_xpdr_mode_str(self, mode: int) -> str:
        """Convert transponder mode int to string."""
        modes = {0: "OFF", 1: "STBY", 2: "ON", 3: "TEST", 4: "ALT"}
        return modes.get(mode, "UNK")

    def _get_best_tail_number(self) -> str:
        """
        Get the best available tail number.
        
        Strategy:
        1. Try standard acf_tailnum.
        2. If that fails or is generic, try to parse from livery path.
        """
        # 1. Standard dataref (from .acf or livery.cfg)
        tail = xp.getDatas(self.dr_tailnum).strip()
        livery_path = xp.getDatas(self.dr_livery_path)
        
        # DEBUG: Unconditional log to see what's happening
        xp.log(f"[StratusATC] DEBUG: tail='{tail}', livery_path='{livery_path}'")
        
        # 2. Check for generic/invalid tail numbers
        # Sometimes unconfigured planes return just the ICAO type or empty string
        is_suspicious = (
            not tail or 
            tail == xp.getDatas(self.dr_icao) or 
            len(tail) < 3 or
            tail == "N1234"
        )
        
        if not is_suspicious:
            return tail
            
        # 3. Fallback: Try to get from livery folder name
        # Path example: "Aircraft/Heavy Metal/B738/.../N123AB/"
        try:
            livery_path = xp.getDatas(self.dr_livery_path)
            xp.log(f"[StratusATC] Generic tail '{tail}' detected. Checking livery path: '{livery_path}'")
            
            if livery_path:
                # Get the storage folder name (often the tail number)
                # Remove trailing slash if present
                if livery_path.endswith(os.path.sep):
                    livery_path = livery_path[:-1]
                
                folder_name = os.path.basename(livery_path)
                xp.log(f"[StratusATC] Extracted folder name: '{folder_name}'")
                
                # Heuristic: If folder name looks like a registration (3-7 chars), use it
                if 3 <= len(folder_name) <= 10:
                    return folder_name
        except Exception as e:
            xp.log(f"[StratusATC] Error parsing livery path: {e}")
            pass
            
        return tail if tail else "UNKNOWN"

    
    def _write_telemetry(self):
        """Write current aircraft state to telemetry file."""
        
        # Read all values
        com1_hz = xp.getDatai(self.dr_com1_active)
        com1_stby_hz = xp.getDatai(self.dr_com1_standby)
        com1_power = xp.getDatai(self.dr_com1_power)
        
        com2_hz = xp.getDatai(self.dr_com2_active)
        com2_stby_hz = xp.getDatai(self.dr_com2_standby)
        com2_power = xp.getDatai(self.dr_com2_power)
        
        xpdr_code = xp.getDatai(self.dr_xpdr_code)
        xpdr_mode = xp.getDatai(self.dr_xpdr_mode)
        
        # Build telemetry dictionary
        telemetry = {
            # Position
            "latitude": xp.getDataf(self.dr_lat),
            "longitude": xp.getDataf(self.dr_lon),
            "altitude_msl": xp.getDataf(self.dr_alt_msl) * 3.28084,  # meters to feet
            "altitude_agl": xp.getDataf(self.dr_alt_agl) * 3.28084,
            "heading_mag": xp.getDataf(self.dr_hdg_mag),
            "heading_true": xp.getDataf(self.dr_hdg_true),
            "pitch": xp.getDataf(self.dr_pitch),
            "roll": xp.getDataf(self.dr_roll),
            "on_ground": xp.getDatai(self.dr_on_ground) > 0,
            
            # Speed
            "ias": xp.getDataf(self.dr_ias),  # knots
            "tas": xp.getDataf(self.dr_tas) * 1.94384,  # m/s to knots
            "groundspeed": xp.getDataf(self.dr_gs) * 1.94384,
            "vertical_speed": xp.getDataf(self.dr_vs),  # fpm
            
            # COM Radios
            "com1": {
                "active": self._hz_to_freq_str(com1_hz),
                "standby": self._hz_to_freq_str(com1_stby_hz),
                "active_hz": com1_hz,
                "standby_hz": com1_stby_hz,
                "power": com1_power > 0
            },
            "com2": {
                "active": self._hz_to_freq_str(com2_hz),
                "standby": self._hz_to_freq_str(com2_stby_hz),
                "active_hz": com2_hz,
                "standby_hz": com2_stby_hz,
                "power": com2_power > 0
            },
            
            # Transponder
            "transponder": {
                "code": f"{xpdr_code:04d}",
                "code_int": xpdr_code,
                "mode": self._get_xpdr_mode_str(xpdr_mode),
                "mode_int": xpdr_mode
            },
            
            # NAV Radios
            "nav1": {
                "active": xp.getDatai(self.dr_nav1_active) / 100.0,
                "standby": xp.getDatai(self.dr_nav1_standby) / 100.0
            },
            "nav2": {
                "active": xp.getDatai(self.dr_nav2_active) / 100.0,
                "standby": xp.getDatai(self.dr_nav2_standby) / 100.0
            },
            
            # Autopilot
            "autopilot": {
                "altitude": xp.getDataf(self.dr_ap_alt),
                "heading": xp.getDataf(self.dr_ap_hdg),
                "vertical_speed": xp.getDataf(self.dr_ap_vs)
            },
            
            # Aircraft Info
            "tail_number": self._get_best_tail_number(),
            "icao_type": xp.getDatas(self.dr_icao),
            
            # Metadata
            "timestamp": time.time(),
            "sim": "xplane12"
        }
        
        # Atomic write (write to tmp, then rename)
        tmp_file = self.telemetry_file + ".tmp"
        try:
            with open(tmp_file, 'w') as f:
                json.dump(telemetry, f, indent=2)
            os.rename(tmp_file, self.telemetry_file)
        except Exception as e:
            xp.log(f"[StratusATC] Error writing telemetry: {e}")
    
    def _process_commands(self):
        """Read and execute any pending commands from the client."""
        
        if not os.path.exists(self.commands_file):
            return
        
        try:
            # Check if file was modified since last check
            mtime = os.path.getmtime(self.commands_file)
            if mtime <= self.last_command_time:
                return  # No new commands
            
            self.last_command_time = mtime
            
            with open(self.commands_file, 'r') as f:
                commands = json.load(f)
            
            # Process each command
            for cmd in commands.get("commands", []):
                self._execute_command(cmd)
            
            # Clear the commands file after processing
            os.remove(self.commands_file)
            
        except json.JSONDecodeError as e:
            xp.log(f"[StratusATC] Invalid command JSON: {e}")
        except Exception as e:
            xp.log(f"[StratusATC] Error processing commands: {e}")
    
    def _execute_command(self, cmd: dict):
        """Execute a single command."""
        cmd_type = cmd.get("type")
        
        if cmd_type == "set_com1_active":
            freq_hz = self._freq_str_to_hz(cmd.get("frequency", ""))
            if freq_hz > 0:
                xp.setDatai(self.dr_com1_active, freq_hz)
                xp.log(f"[StratusATC] Set COM1 active: {cmd.get('frequency')}")
        
        elif cmd_type == "set_com1_standby":
            freq_hz = self._freq_str_to_hz(cmd.get("frequency", ""))
            if freq_hz > 0:
                xp.setDatai(self.dr_com1_standby, freq_hz)
                xp.log(f"[StratusATC] Set COM1 standby: {cmd.get('frequency')}")
        
        elif cmd_type == "swap_com1":
            # Swap active and standby
            active = xp.getDatai(self.dr_com1_active)
            standby = xp.getDatai(self.dr_com1_standby)
            xp.setDatai(self.dr_com1_active, standby)
            xp.setDatai(self.dr_com1_standby, active)
            xp.log("[StratusATC] Swapped COM1")
        
        elif cmd_type == "set_com2_active":
            freq_hz = self._freq_str_to_hz(cmd.get("frequency", ""))
            if freq_hz > 0:
                xp.setDatai(self.dr_com2_active, freq_hz)
                xp.log(f"[StratusATC] Set COM2 active: {cmd.get('frequency')}")
        
        elif cmd_type == "set_com2_standby":
            freq_hz = self._freq_str_to_hz(cmd.get("frequency", ""))
            if freq_hz > 0:
                xp.setDatai(self.dr_com2_standby, freq_hz)
                xp.log(f"[StratusATC] Set COM2 standby: {cmd.get('frequency')}")
        
        elif cmd_type == "swap_com2":
            active = xp.getDatai(self.dr_com2_active)
            standby = xp.getDatai(self.dr_com2_standby)
            xp.setDatai(self.dr_com2_active, standby)
            xp.setDatai(self.dr_com2_standby, active)
            xp.log("[StratusATC] Swapped COM2")
        
        elif cmd_type == "set_transponder":
            code = cmd.get("code")
            if code:
                try:
                    code_int = int(code)
                    if 0 <= code_int <= 7777:
                        xp.setDatai(self.dr_xpdr_code, code_int)
                        xp.log(f"[StratusATC] Set transponder: {code}")
                except ValueError:
                    pass
        
        elif cmd_type == "set_transponder_mode":
            mode = cmd.get("mode")
            mode_map = {"OFF": 0, "STBY": 1, "ON": 2, "TEST": 3, "ALT": 4}
            if mode in mode_map:
                xp.setDatai(self.dr_xpdr_mode, mode_map[mode])
                xp.log(f"[StratusATC] Set transponder mode: {mode}")
        
        else:
            xp.log(f"[StratusATC] Unknown command type: {cmd_type}")
