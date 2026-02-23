use nix::fcntl::{flock, FlockArg};
use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::{BufRead, BufReader, Seek, SeekFrom};
use std::os::unix::io::AsRawFd;
use std::path::PathBuf;
use xplm::data::borrowed::DataRef;
use xplm::data::DataReadWrite;

#[derive(Debug, Serialize, Deserialize)]
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

pub struct CommandParser {
    command_path: PathBuf,
    pub status_path: PathBuf,
}

impl CommandParser {
    pub fn new(command_path: PathBuf, status_path: PathBuf) -> Self {
        Self {
            command_path,
            status_path,
        }
    }

    pub fn process_commands(&self) -> anyhow::Result<()> {
        if !self.command_path.exists() {
            return Ok(());
        }

        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .open(&self.command_path)?;

        flock(file.as_raw_fd(), FlockArg::LockExclusive)?;

        let mut commands = Vec::new();
        {
            let reader = BufReader::new(&file);
            for line in reader.lines() {
                let line = line?;
                if line.trim().is_empty() {
                    continue;
                }
                match serde_json::from_str::<Command>(&line) {
                    Ok(cmd) => commands.push(cmd),
                    Err(e) => log::error!("Failed to parse command: {} (line: {})", e, line),
                }
            }
        }

        for cmd in commands {
            if let Err(e) = self.execute_command(&cmd) {
                log::error!("Failed to execute command: {:?}", e);
            }
        }

        file.set_len(0)?;
        file.seek(SeekFrom::Start(0))?;

        flock(file.as_raw_fd(), FlockArg::Unlock)?;

        Ok(())
    }

    fn execute_command(&self, cmd: &Command) -> anyhow::Result<()> {
        match cmd {
            Command::SetRadio {
                target,
                param,
                value,
            } => self.handle_set_radio(target, param, *value),
            Command::SetXpdr { code, mode } => self.handle_set_xpdr(*code, *mode),
            Command::SetAp { mode, value } => self.handle_set_ap(mode, *value),
        }
    }

    fn handle_set_radio(&self, target: &str, param: &str, value: i32) -> anyhow::Result<()> {
        let dataref_path = match (target, param) {
            ("COM1", "FREQUENCY") => "sim/cockpit2/radios/actuators/com1_frequency_hz_833",
            ("COM1", "STANDBY") => "sim/cockpit2/radios/actuators/com1_standby_frequency_hz_833",
            ("COM2", "FREQUENCY") => "sim/cockpit2/radios/actuators/com2_frequency_hz_833",
            ("COM2", "STANDBY") => "sim/cockpit2/radios/actuators/com2_standby_frequency_hz_833",
            ("NAV1", "FREQUENCY") => "sim/cockpit2/radios/actuators/nav1_frequency_hz",
            ("NAV2", "FREQUENCY") => "sim/cockpit2/radios/actuators/nav2_frequency_hz",
            _ => anyhow::bail!("Unsupported radio target/param: {}/{}", target, param),
        };

        if let Ok(dr) = DataRef::<i32>::find(dataref_path) {
            if let Ok(mut drw) = dr.writeable() {
                log::info!("Setting {} to {}", dataref_path, value);
                drw.set(value);
            }
        }
        Ok(())
    }

    fn handle_set_xpdr(&self, code: i32, mode: Option<i32>) -> anyhow::Result<()> {
        if let Ok(dr_code) = DataRef::<i32>::find("sim/cockpit/radios/transponder_code") {
            if let Ok(mut drw) = dr_code.writeable() {
                drw.set(code);
            }
        }
        if let Some(m) = mode {
            if let Ok(dr_mode) = DataRef::<i32>::find("sim/cockpit/radios/transponder_mode") {
                if let Ok(mut drw) = dr_mode.writeable() {
                    drw.set(m);
                }
            }
        }
        Ok(())
    }

    fn handle_set_ap(&self, mode: &str, value: f32) -> anyhow::Result<()> {
        let dataref_path = match mode {
            "ALT" => "sim/cockpit/autopilot/altitude",
            "HDG" => "sim/cockpit/autopilot/heading_mag",
            "VS" => "sim/cockpit/autopilot/vertical_velocity",
            _ => anyhow::bail!("Unsupported AP mode: {}", mode),
        };

        if let Ok(dr) = DataRef::<f32>::find(dataref_path) {
            if let Ok(mut drw) = dr.writeable() {
                drw.set(value);
            }
        }
        Ok(())
    }
}

/// C FFI: process commands file.
///
/// # Safety
/// Caller must pass valid, non-null pointers to NUL-terminated C strings that outlive the call.
#[no_mangle]
pub unsafe extern "C" fn process_stratus_commands(
    command_path: *const i8,
    status_path: *const i8,
) -> i32 {
    use std::ffi::CStr;

    if command_path.is_null() || status_path.is_null() {
        return -1;
    }

    let c_cmd_path = CStr::from_ptr(command_path);
    let c_stat_path = CStr::from_ptr(status_path);

    let cmd_path = PathBuf::from(c_cmd_path.to_string_lossy().into_owned());
    let stat_path = PathBuf::from(c_stat_path.to_string_lossy().into_owned());

    let parser = CommandParser::new(cmd_path, stat_path);
    match parser.process_commands() {
        Ok(_) => 0,
        Err(_) => -1,
    }
}
