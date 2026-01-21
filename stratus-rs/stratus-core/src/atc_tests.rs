//! Unit tests for AtcEngine command parsing

use crate::atc::AtcEngine;
use crate::commands::Command;

#[cfg(test)]
mod atc_tests {
    use super::*;

    fn make_engine() -> AtcEngine {
        let config = crate::config::StratusConfig::default();
        AtcEngine::new(&config)
    }

    #[test]
    fn test_parse_set_radio_command() {
        let engine = make_engine();
        let raw = "N12345, contact Tower on 118.5. [SET_RADIO COM1 FREQUENCY 118500]";
        let (speech, commands) = engine.parse_response(raw);

        assert_eq!(speech, "N12345, contact Tower on 118.5.");
        assert_eq!(commands.len(), 1);

        match &commands[0] {
            Command::SetRadio {
                target,
                param,
                value,
            } => {
                assert_eq!(target, "COM1");
                assert_eq!(param, "FREQUENCY");
                assert_eq!(*value, 118500);
            }
            _ => panic!("Expected SetRadio command"),
        }
    }

    #[test]
    fn test_parse_squawk_command() {
        let engine = make_engine();
        let raw = "Squawk 4521. [SET_XPDR 4521]";
        let (speech, commands) = engine.parse_response(raw);

        assert_eq!(speech, "Squawk 4521.");
        assert_eq!(commands.len(), 1);

        match &commands[0] {
            Command::SetXpdr { code, .. } => {
                assert_eq!(*code, 4521);
            }
            _ => panic!("Expected SetXpdr command"),
        }
    }

    #[test]
    fn test_parse_autopilot_command() {
        let engine = make_engine();
        let raw = "Climb and maintain 5000. [SET_AP ALT 5000]";
        let (speech, commands) = engine.parse_response(raw);

        assert_eq!(speech, "Climb and maintain 5000.");
        assert_eq!(commands.len(), 1);

        match &commands[0] {
            Command::SetAp { mode, value } => {
                assert_eq!(mode, "ALT");
                assert!((value - 5000.0).abs() < 0.01);
            }
            _ => panic!("Expected SetAp command"),
        }
    }

    #[test]
    fn test_parse_multiple_commands() {
        let engine = make_engine();
        let raw =
            "Squawk 1200,contact ground 121.9. [SET_XPDR 1200] [SET_RADIO COM1 FREQUENCY 121900]";
        let (speech, commands) = engine.parse_response(raw);

        assert_eq!(speech, "Squawk 1200,contact ground 121.9.");
        assert_eq!(commands.len(), 2);
    }

    #[test]
    fn test_parse_no_commands() {
        let engine = make_engine();
        let raw = "Roger, cleared to land runway 28L.";
        let (speech, commands) = engine.parse_response(raw);

        assert_eq!(speech, "Roger, cleared to land runway 28L.");
        assert!(commands.is_empty());
    }

    #[test]
    fn test_parse_frequency_with_decimal() {
        let engine = make_engine();
        // LLM outputs 118.5 (MHz format)
        let raw = "[SET_RADIO COM1 FREQUENCY 118.5]";
        let (_, commands) = engine.parse_response(raw);

        match &commands[0] {
            Command::SetRadio { value, .. } => {
                // 118.5 MHz = 118500 Hz (correctly converted!)
                assert_eq!(*value, 118500);
            }
            _ => panic!("Expected SetRadio command"),
        }
    }

    #[test]
    fn test_parse_robustness_whitespace() {
        let engine = make_engine();
        let raw = "[  SET_RADIO   COM1   FREQUENCY   121.8  ]";
        let (_, commands) = engine.parse_response(raw);
        assert_eq!(commands.len(), 1);
        if let Command::SetRadio { value, .. } = &commands[0] {
            assert_eq!(*value, 121800);
        }
    }

    #[test]
    fn test_parse_robustness_trailing_text() {
        let engine = make_engine();
        let raw = "[SET_XPDR 1200]and some text";
        let (speech, commands) = engine.parse_response(raw);
        assert_eq!(commands.len(), 1);
        assert_eq!(speech, "and some text");
    }
}
