use anyhow::Result;
use nix::fcntl::{Flock, FlockArg};
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::Write;
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

        let file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.command_path)?;

        // Lock for appending
        let mut file = Flock::lock(file, FlockArg::LockExclusive).map_err(|(f, e)| {
            anyhow::anyhow!(
                "Failed to lock file: {} (FD: {:?})",
                e,
                std::os::unix::io::AsRawFd::as_raw_fd(&f)
            )
        })?;

        for cmd in commands {
            let line = serde_json::to_string(cmd)?;
            writeln!(file, "{}", line)?;
        }

        Ok(())
    }
}
