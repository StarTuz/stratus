use anyhow::{Context, Result};
use log::info;
use serde::Deserialize;
use std::fs;
use std::path::PathBuf;

/// Configuration for stratus-voice
#[derive(Debug, Deserialize)]
pub struct Config {
    /// Path to whisper.cpp model (optional, for fallback)
    #[serde(default = "default_whisper_model")]
    pub whisper_model: String,

    /// Path to whisper.cpp binary (optional)
    #[serde(default = "default_whisper_bin")]
    pub whisper_bin: String,
}

fn default_whisper_model() -> String {
    "whisper.cpp/models/ggml-tiny.en.bin".to_string()
}

fn default_whisper_bin() -> String {
    "whisper.cpp/main".to_string()
}

impl Config {
    /// Load configuration from default path (~/.config/stratus/voice.toml)
    /// or create a default config if one doesn't exist.
    pub fn load() -> Result<Self> {
        let config_path = Self::config_path()?;

        if !config_path.exists() {
            info!("Config not found at {:?}, creating default...", config_path);
            Self::create_default(&config_path)?;
        }

        let content = fs::read_to_string(&config_path)
            .with_context(|| format!("Failed to read config at {:?}", config_path))?;

        toml::from_str(&content)
            .with_context(|| format!("Failed to parse config at {:?}", config_path))
    }

    /// Get the PTT file path (written by X-Plane plugin)
    pub fn ptt_file() -> PathBuf {
        dirs::data_local_dir()
            .unwrap_or_else(|| PathBuf::from("/tmp"))
            .join("StratusATC")
            .join("stratus_ptt.json")
    }

    fn config_path() -> Result<PathBuf> {
        let config_dir = dirs::config_dir()
            .context("Could not determine config directory")?
            .join("stratus");

        fs::create_dir_all(&config_dir)?;
        Ok(config_dir.join("voice.toml"))
    }

    fn create_default(path: &PathBuf) -> Result<()> {
        let default_content = r#"# Stratus Voice Configuration
#
# PTT is now handled via X-Plane's keybinding system.
# Bind "stratus/ptt" in X-Plane Settings > Keyboard or Joystick.

# Optional: Path to whisper.cpp model (fallback if speechd-ng unavailable)
# whisper_model = "whisper.cpp/models/ggml-tiny.en.bin"

# Optional: Path to whisper.cpp binary
# whisper_bin = "whisper.cpp/main"
"#;
        fs::write(path, default_content)?;
        info!("Created default config at {:?}", path);
        Ok(())
    }
}
