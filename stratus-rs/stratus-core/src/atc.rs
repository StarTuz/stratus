//! ATC Engine - Prompt building and response handling
//!
//! Constructs context-aware prompts for the LLM based on telemetry.

use crate::commands::Command;
use crate::ollama::OllamaClient;
use crate::telemetry::Telemetry;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::sync::OnceLock;
use stratus_bitnet::BitNetClient;

static COMMAND_REGEX: OnceLock<Regex> = OnceLock::new();

const KSFO_GND: i32 = 121800; // 121.80 MHz
const KSFO_TWR: i32 = 120500; // 120.50 MHz

fn get_command_regex() -> &'static Regex {
    COMMAND_REGEX.get_or_init(|| Regex::new(r"\[([A-Z_]+)\s+(.+?)\]").unwrap())
}

/// Parse a frequency string into Hz (i32).
/// Handles multiple formats:
/// - "118500" -> 118500 (already Hz)
/// - "118.5" -> 118500 (MHz with 1 decimal)
/// - "118.50" -> 118500 (MHz with 2 decimals)
/// - "118.500" -> 118500 (MHz with 3 decimals)
fn parse_frequency(s: &str) -> i32 {
    // If it contains a decimal point, it's in MHz format
    if s.contains('.') {
        if let Ok(mhz) = s.parse::<f64>() {
            // Convert MHz to Hz (multiply by 1000)
            // X-Plane uses kHz * 100 format: 118.500 MHz = 118500
            return (mhz * 1000.0).round() as i32;
        }
    }
    // Already in Hz format or fallback
    s.parse::<i32>().unwrap_or(0)
}

/// ATC Engine - manages the conversation and prompt construction
#[derive(Debug, Clone)]
pub struct AtcEngine {
    backend: Backend,
    conversation_history: Vec<ConversationEntry>,
    callsign: String,
    aircraft_type: String,
    state: VfrState,
}

#[derive(Debug, Clone)]
pub enum Backend {
    Ollama(OllamaClient),
    BitNet(BitNetClient),
}

#[derive(Debug, Clone)]
pub struct ConversationEntry {
    pub speaker: Speaker,
    pub message: String,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum Speaker {
    Pilot,
    Atc,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum VfrState {
    Parked,
    Taxiing,
    HoldingShort,
    TakeoffRoll,
    Departure,
    InPattern(PatternLeg),
    Approach,
    Landing,
    ClearOfRunway,
}

#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
pub enum PatternLeg {
    Upwind,
    Crosswind,
    Downwind,
    Base,
    Final,
}

impl VfrState {
    pub fn as_str(&self) -> &str {
        match self {
            VfrState::Parked => "Parked / At Gate",
            VfrState::Taxiing => "Taxiing",
            VfrState::HoldingShort => "Holding Short",
            VfrState::TakeoffRoll => "Takeoff Roll",
            VfrState::Departure => "Departure",
            VfrState::InPattern(leg) => match leg {
                PatternLeg::Upwind => "In Pattern (Upwind)",
                PatternLeg::Crosswind => "In Pattern (Crosswind)",
                PatternLeg::Downwind => "In Pattern (Downwind)",
                PatternLeg::Base => "In Pattern (Base)",
                PatternLeg::Final => "In Pattern (Final)",
            },
            VfrState::Approach => "On Approach",
            VfrState::Landing => "Landing",
            VfrState::ClearOfRunway => "Clear of Runway",
        }
    }
}

impl AtcEngine {
    /// Create a new ATC engine
    pub fn new(callsign: impl Into<String>, aircraft_type: impl Into<String>) -> Self {
        // Default to BitNet for efficiency if available, or fallback to Ollama if explicitly configured
        let backend = match BitNetClient::new() {
            Ok(client) => Backend::BitNet(client),
            Err(e) => {
                tracing::warn!(
                    "Failed to initialize BitNet backend: {}. Falling back to Ollama.",
                    e
                );
                Backend::Ollama(OllamaClient::default())
            }
        };

        Self {
            backend,
            conversation_history: Vec::new(),
            callsign: callsign.into(),
            aircraft_type: aircraft_type.into(),
            state: VfrState::Parked,
        }
    }

    /// Set the Ollama model (forcing Ollama backend)
    pub fn with_model(mut self, model: impl Into<String>) -> Self {
        self.backend = match self.backend {
            Backend::Ollama(client) => Backend::Ollama(client.with_model(model)),
            Backend::BitNet(_) => Backend::Ollama(OllamaClient::new(model)),
        };
        self
    }

    /// Set the Ollama URL (forcing Ollama backend)
    pub fn with_url(mut self, url: impl Into<String>) -> Self {
        self.backend = match self.backend {
            Backend::Ollama(client) => Backend::Ollama(client.with_url(url)),
            Backend::BitNet(_) => Backend::Ollama(OllamaClient::default().with_url(url)),
        };
        self
    }

    /// Build the ATC system prompt
    fn build_system_prompt(&self, telemetry: &Telemetry) -> String {
        let altitude_ft = (telemetry.position.altitude_msl_m * 3.28084) as i32;
        let heading = telemetry.orientation.heading_mag as i32;
        let ground_speed_kts = (telemetry.speed.ground_speed_mps * 1.94384) as i32;

        format!(
            r#"You are an FAA Air Traffic Controller. Respond with proper ATC phraseology.

AIRCRAFT: {callsign} ({aircraft_type})
POSITION: {state} at {altitude_ft} ft MSL, heading {heading}°, {ground_speed_kts} kts
SQUAWK: {squawk:04}

RULES:
1. Use standard FAA phraseology.
2. Be concise - real ATC is brief.
3. Include callsign in every transmission.
4. If unclear, ask pilot to "say again".
5. YOU ARE AWARE OF THE FLIGHT PHASE: {state}. Do not clear for takeoff if not at the runway. Do not clear for landing if not in the pattern.

Respond using standard phraseology. You may append machine readable commands in brackets if necessary, e.g. [SET_RADIO COM1 120.5].
Supported commands:
- [SET_RADIO target param value] (e.g. [SET_RADIO COM1 FREQUENCY 118.5])
- [SET_XPDR code] (e.g. [SET_XPDR 1200])
- [SET_AP mode value] (e.g. [SET_AP ALT 5000])"#,
            callsign = self.callsign,
            aircraft_type = self.aircraft_type,
            state = self.state.as_str(),
            altitude_ft = altitude_ft,
            heading = heading,
            ground_speed_kts = ground_speed_kts,
            squawk = telemetry.transponder.code,
        )
    }

    /// Update the current flight state based on telemetry
    pub fn update_state(&mut self, telemetry: &Telemetry) {
        let speed_kts = (telemetry.speed.ground_speed_mps * 1.94384) as f32;
        let alt_agl_ft = (telemetry.position.altitude_agl_m * 3.28084) as f32;
        let on_ground = telemetry.state.on_ground;

        let mut last_state = self.state;
        loop {
            self.state = match self.state {
                VfrState::Parked if !on_ground => VfrState::Departure, // Jump to departure if we start in air
                VfrState::Parked if speed_kts > 2.0 && on_ground => VfrState::Taxiing,
                VfrState::Taxiing if speed_kts < 1.0 && on_ground => VfrState::HoldingShort,
                VfrState::Taxiing if speed_kts > 40.0 && on_ground => VfrState::TakeoffRoll, // Immediate takeoff
                VfrState::HoldingShort if speed_kts > 5.0 && on_ground => VfrState::TakeoffRoll,
                VfrState::TakeoffRoll if !on_ground => VfrState::Departure,
                VfrState::Departure if alt_agl_ft > 300.0 => {
                    VfrState::InPattern(PatternLeg::Upwind)
                }
                VfrState::InPattern(PatternLeg::Upwind) if alt_agl_ft > 700.0 => {
                    VfrState::InPattern(PatternLeg::Crosswind)
                }
                VfrState::InPattern(PatternLeg::Crosswind) if alt_agl_ft > 900.0 => {
                    VfrState::InPattern(PatternLeg::Downwind)
                }
                VfrState::InPattern(PatternLeg::Downwind)
                    if speed_kts < 90.0 && alt_agl_ft < 1200.0 =>
                {
                    VfrState::Approach
                }
                VfrState::Approach if alt_agl_ft < 50.0 => VfrState::Landing,
                VfrState::Landing if on_ground && speed_kts < 30.0 => VfrState::ClearOfRunway,
                VfrState::ClearOfRunway if speed_kts < 2.0 => VfrState::Parked,
                _ => self.state, // Stay in current state
            };

            if self.state == last_state {
                break;
            }
            last_state = self.state;
        }
    }

    /// Get the expected frequency for the current state
    pub fn expected_frequency(&self) -> i32 {
        match self.state {
            VfrState::Parked | VfrState::Taxiing | VfrState::HoldingShort => KSFO_GND,
            _ => KSFO_TWR, // For simplicity, we use tower for all other phases for now
        }
    }

    /// Process pilot input and generate ATC response
    pub async fn process_pilot_input(
        &mut self,
        pilot_message: &str,
        telemetry: &Telemetry,
    ) -> Result<(Option<String>, Vec<Command>), crate::ollama::OllamaError> {
        // Enforce radio frequency
        let active_freq = telemetry.radios.com1_hz;
        let expected_freq = self.expected_frequency();

        if active_freq != expected_freq {
            // Monitored Frequencies check (GND and TWR)
            let monitored_freqs = vec![KSFO_GND, KSFO_TWR];
            if monitored_freqs.contains(&active_freq) {
                let redirect_msg = match expected_freq {
                    KSFO_GND => format!(
                        "{} {}, you are on Tower frequency, contact Ground on {:.3}.",
                        self.aircraft_type,
                        self.callsign,
                        KSFO_GND as f64 / 1_000_000.0
                    ),
                    KSFO_TWR => format!(
                        "{} {}, you are on Ground frequency, contact Tower on {:.3}.",
                        self.aircraft_type,
                        self.callsign,
                        KSFO_TWR as f64 / 1_000_000.0
                    ),
                    _ => "(RADIO REDIRECT)".to_string(),
                };
                return Ok((Some(redirect_msg), vec![]));
            }

            // Radio Silence: If not on a monitored frequency, return None.
            return Ok((None, vec![]));
        }

        // Add pilot message to history
        self.conversation_history.push(ConversationEntry {
            speaker: Speaker::Pilot,
            message: pilot_message.to_string(),
            timestamp: chrono::Utc::now().timestamp(),
        });

        // Update logical state from telemetry before building prompt
        self.update_state(telemetry);

        // Build the full prompt
        let system_prompt = self.build_system_prompt(telemetry);
        let history = self.format_history();

        let full_prompt =
            format!("{system_prompt}\n\nCONVERSATION:\n{history}\nPILOT: {pilot_message}\nATC:",);

        // Get LLM response
        let raw_response = match &self.backend {
            Backend::Ollama(ollama) => ollama
                .generate(&full_prompt)
                .await
                .map_err(|e| e.to_string())?,
            Backend::BitNet(bitnet) => bitnet
                .generate(&full_prompt)
                .await
                .map_err(|e| e.to_string())?,
        };
        let (speech_text, commands) = self.parse_response(&raw_response);

        // Add ATC response to history
        self.conversation_history.push(ConversationEntry {
            speaker: Speaker::Atc,
            message: speech_text.clone(),
            timestamp: chrono::Utc::now().timestamp(),
        });

        // Keep history manageable
        if self.conversation_history.len() > 20 {
            self.conversation_history.drain(0..2);
        }

        Ok((Some(speech_text), commands))
    }

    pub fn parse_response(&self, raw: &str) -> (String, Vec<Command>) {
        let regex = get_command_regex();
        let mut commands = Vec::new();
        let mut clean_text = raw.to_string();

        // Extract commands
        for cap in regex.captures_iter(raw) {
            let full_match = &cap[0]; // e.g., [SET_RADIO COM1 123.4]
            let op = &cap[1]; // SET_RADIO
            let args_str = &cap[2]; // COM1 123.4

            // Remove from text
            clean_text = clean_text.replace(full_match, "");

            // Parse Command
            // This is a naive parser, assuming LLM follows format closely.
            // Ideally we'd use a robust parser or grammar.
            let parts: Vec<&str> = args_str.split_whitespace().collect();

            let command = match op {
                "SET_RADIO" if parts.len() >= 3 => {
                    // Parse frequency value, handling both formats:
                    // - Integer Hz: 118500 (already correct)
                    // - Decimal MHz: 118.5 or 118.50 or 118.500
                    let val_str = parts[2];
                    let val = parse_frequency(val_str);
                    Some(Command::SetRadio {
                        target: parts[0].to_string(),
                        param: parts[1].to_string(),
                        value: val,
                    })
                }
                "SET_XPDR" if parts.len() >= 1 => {
                    let code = parts[0].parse::<i32>().unwrap_or(1200);
                    Some(Command::SetXpdr { code, mode: None })
                }
                "SET_AP" if parts.len() >= 2 => {
                    let val = parts[1].parse::<f32>().unwrap_or(0.0);
                    Some(Command::SetAp {
                        mode: parts[0].to_string(),
                        value: val,
                    })
                }
                _ => None,
            };

            if let Some(cmd) = command {
                commands.push(cmd);
            }
        }

        (clean_text.trim().to_string(), commands)
    }

    /// Format conversation history for the prompt
    fn format_history(&self) -> String {
        self.conversation_history
            .iter()
            .map(|entry| {
                let speaker = match entry.speaker {
                    Speaker::Pilot => "PILOT",
                    Speaker::Atc => "ATC",
                };
                format!("{}: {}", speaker, entry.message)
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    /// Get current VFR state
    pub fn state(&self) -> VfrState {
        self.state
    }

    /// Get conversation history
    pub fn history(&self) -> &[ConversationEntry] {
        &self.conversation_history
    }

    pub fn clear_history(&mut self) {
        self.conversation_history.clear();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::telemetry::Telemetry;

    #[tokio::test]
    async fn test_radio_frequency_enforcement() {
        let mut engine = AtcEngine::new("N172SP", "C172");
        let mut telemetry = Telemetry::default();

        // At parked state, expected is GND (121.80)
        // Tune to a random unmonitored frequency (e.g. 118.5)
        telemetry.radios.com1_hz = 118500;

        let (response, _) = engine
            .process_pilot_input("Request taxi", &telemetry)
            .await
            .unwrap();
        // Should be total silence (None)
        assert!(response.is_none());

        // Tune to Tower (Monitored but incorrect for Parked/GND)
        telemetry.radios.com1_hz = KSFO_TWR;
        let (response, _) = engine
            .process_pilot_input("Request taxi", &telemetry)
            .await
            .unwrap();
        // Should be a professional redirect
        assert!(response.is_some());
        assert!(response.unwrap().contains("contact Ground"));

        // Tune to Ground (Correct)
        telemetry.radios.com1_hz = KSFO_GND;
        let (response, _) = engine
            .process_pilot_input("Request taxi", &telemetry)
            .await
            .unwrap();
        // Should be a normal response (Some)
        assert!(response.is_some());
        assert!(!response.unwrap().contains("contact Ground"));
    }
}
