use anyhow::{Context, Result};
use dbus::blocking::Connection;
use log::{debug, error, info};
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;
use std::thread;
use std::time::Duration;

#[derive(Debug, Deserialize)]
struct PttState {
    ptt: bool,
    #[serde(default)]
    timestamp: i64,
}

pub struct PTTMonitor {
    ptt_file: PathBuf,
    dbus_conn: Connection,
    last_state: bool,
}

impl PTTMonitor {
    pub fn new(ptt_file: impl Into<PathBuf>) -> Result<Self> {
        let conn = Connection::new_session().context("Failed to connect to Session Bus")?;
        Ok(Self {
            ptt_file: ptt_file.into(),
            dbus_conn: conn,
            last_state: false,
        })
    }

    /// Monitor the PTT file for state changes.
    /// This replaces the evdev-based PTT hook - now we watch a file written by X-Plane.
    pub fn listen(&mut self) -> Result<()> {
        info!("Monitoring PTT file: {:?}", self.ptt_file);

        let proxy = self.dbus_conn.with_proxy(
            "org.stratus.ATC.Voice",
            "/org/stratus/ATC/Voice",
            Duration::from_secs(5),
        );

        loop {
            // Check file state
            if let Ok(content) = fs::read_to_string(&self.ptt_file) {
                if let Ok(state) = serde_json::from_str::<PttState>(&content) {
                    // Detect state changes
                    if state.ptt && !self.last_state {
                        debug!("PTT DOWN (from X-Plane)");
                        let _: std::result::Result<(), _> = proxy
                            .method_call("org.stratus.ATC.Voice", "StartListening", ())
                            .map_err(|e| error!("Failed to call StartListening: {}", e));
                    } else if !state.ptt && self.last_state {
                        debug!("PTT UP (from X-Plane)");
                        let _: std::result::Result<(), _> = proxy
                            .method_call("org.stratus.ATC.Voice", "StopListening", ())
                            .map_err(|e| error!("Failed to call StopListening: {}", e));
                    }
                    self.last_state = state.ptt;
                }
            }

            // Poll at 50ms for low latency
            thread::sleep(Duration::from_millis(50));
        }
    }
}
