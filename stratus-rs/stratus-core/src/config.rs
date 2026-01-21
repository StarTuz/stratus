use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct StratusConfig {
    pub aircraft: AircraftConfig,
    pub model: ModelConfig,
    pub audio: AudioConfig,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AircraftConfig {
    pub callsign: String,
    pub aircraft_type: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ModelConfig {
    pub url: String,
    pub name: String,
    pub backend: String, // "BitNet" or "Ollama"
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct AudioConfig {
    pub input_device: String,
}

impl Default for StratusConfig {
    fn default() -> Self {
        Self {
            aircraft: AircraftConfig {
                callsign: "N172SP".to_string(),
                aircraft_type: "C172".to_string(),
            },
            model: ModelConfig {
                url: "http://localhost:11434".to_string(),
                name: "llama3".to_string(),
                backend: "BitNet".to_string(),
            },
            audio: AudioConfig {
                input_device: "default".to_string(),
            },
        }
    }
}

impl StratusConfig {
    pub fn load() -> Result<Self> {
        let config_path = Self::get_config_path();

        if config_path.exists() {
            let content = fs::read_to_string(config_path)?;
            let config: StratusConfig = toml::from_str(&content)?;
            Ok(config)
        } else {
            let config = Self::default();
            config.save()?;
            Ok(config)
        }
    }

    pub fn save(&self) -> Result<()> {
        let config_path = Self::get_config_path();
        if let Some(parent) = config_path.parent() {
            fs::create_dir_all(parent)?;
        }
        let content = toml::to_string_pretty(self)?;
        fs::write(config_path, content)?;
        Ok(())
    }

    fn get_config_path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("StratusATC")
            .join("config.toml")
    }
}
