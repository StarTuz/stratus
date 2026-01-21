use anyhow::Result;
use nix::fcntl::{flock, FlockArg};
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
use std::os::unix::io::AsRawFd;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(tag = "op")]
pub enum Command {
    #[serde(rename = "SET_RADIO")]
    SetRadio {
        target: String,
        param: String,
        value: i32,
    },
    #[serde(rename = "SET_XPDR")]
    SetXpdr {
        code: i32,
        #[serde(default)]
        mode: Option<i32>,
    },
    #[serde(rename = "SET_AP")]
    SetAp { mode: String, value: f32 },
}

#[derive(Clone)]
pub struct CommandWriter {
    command_path: PathBuf,
}

impl CommandWriter {
    pub fn new(command_path: impl Into<PathBuf>) -> Self {
        Self {
            command_path: command_path.into(),
        }
    }

    pub fn write(&self, commands: &[Command]) -> Result<()> {
        if commands.is_empty() {
            return Ok(());
        }

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.command_path)?;

        // Lock for appending
        flock(file.as_raw_fd(), FlockArg::LockExclusive)?;

        for cmd in commands {
            let line = serde_json::to_string(cmd)?;
            writeln!(file, "{}", line)?;
        }

        flock(file.as_raw_fd(), FlockArg::Unlock)?;

        Ok(())
    }
}
