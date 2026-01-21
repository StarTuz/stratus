//! Unit tests for CommandWriter

use crate::commands::{Command, CommandWriter};
use std::fs;
use tempfile::tempdir;

#[cfg(test)]
mod commands_tests {
    use super::*;

    #[test]
    fn test_write_single_command() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("commands.jsonl");
        let writer = CommandWriter::new(&path);

        let commands = vec![Command::SetXpdr {
            code: 1234,
            mode: None,
        }];
        writer.write(&commands).unwrap();

        let content = fs::read_to_string(&path).unwrap();
        assert!(content.contains("SET_XPDR"));
        assert!(content.contains("1234"));
    }

    #[test]
    fn test_write_multiple_commands() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("commands.jsonl");
        let writer = CommandWriter::new(&path);

        let commands = vec![
            Command::SetXpdr {
                code: 4521,
                mode: None,
            },
            Command::SetRadio {
                target: "COM1".to_string(),
                param: "FREQUENCY".to_string(),
                value: 118500,
            },
        ];
        writer.write(&commands).unwrap();

        let content = fs::read_to_string(&path).unwrap();
        let lines: Vec<&str> = content.lines().collect();
        assert_eq!(lines.len(), 2);
    }

    #[test]
    fn test_write_empty_commands() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("commands.jsonl");
        let writer = CommandWriter::new(&path);

        // Should not create file if no commands
        writer.write(&[]).unwrap();
        assert!(!path.exists());
    }

    #[test]
    fn test_command_serialization() {
        let cmd = Command::SetAp {
            mode: "ALT".to_string(),
            value: 5000.0,
        };
        let json = serde_json::to_string(&cmd).unwrap();
        assert!(json.contains("SET_AP"));
        assert!(json.contains("ALT"));
        assert!(json.contains("5000"));
    }

    #[test]
    fn test_append_mode() {
        let dir = tempdir().unwrap();
        let path = dir.path().join("commands.jsonl");
        let writer = CommandWriter::new(&path);

        // First write
        writer
            .write(&[Command::SetXpdr {
                code: 1200,
                mode: None,
            }])
            .unwrap();
        // Second write (should append)
        writer
            .write(&[Command::SetXpdr {
                code: 4521,
                mode: None,
            }])
            .unwrap();

        let content = fs::read_to_string(&path).unwrap();
        let lines: Vec<&str> = content.lines().collect();
        assert_eq!(lines.len(), 2);
        assert!(lines[0].contains("1200"));
        assert!(lines[1].contains("4521"));
    }
}
