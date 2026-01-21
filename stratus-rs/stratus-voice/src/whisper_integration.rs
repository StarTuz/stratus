use anyhow::{Context, Result};
use dbus::blocking::Connection;
use log::{error, info, warn};
use std::fs::File;
use std::io::Write;
use std::process::Command;
use std::time::Duration;
use tempfile::NamedTempFile;

/// Whisper transcription backend abstraction.
/// Prefers speechd-ng D-Bus, falls back to whisper.cpp subprocess.
pub struct WhisperTranscriber {
    backend: TranscriberBackend,
}

enum TranscriberBackend {
    SpeechdNg {
        connection: Connection,
    },
    WhisperCpp {
        model_path: String,
        binary_path: String,
    },
}

impl WhisperTranscriber {
    /// Creates a new transcriber, automatically detecting the best backend.
    /// Priority: speechd-ng D-Bus > whisper.cpp subprocess
    pub fn new(whisper_model: &str, whisper_binary: &str) -> Self {
        // Try speechd-ng first
        if let Ok(backend) = Self::try_speechd_ng() {
            info!("Using speechd-ng D-Bus backend for STT");
            return Self { backend };
        }

        // Fall back to whisper.cpp subprocess
        warn!("speechd-ng not available, falling back to whisper.cpp subprocess");
        Self {
            backend: TranscriberBackend::WhisperCpp {
                model_path: whisper_model.to_string(),
                binary_path: whisper_binary.to_string(),
            },
        }
    }

    fn try_speechd_ng() -> Result<TranscriberBackend> {
        let conn = Connection::new_session().context("Failed to connect to session bus")?;

        // Check if speechd-ng is running
        let proxy = conn.with_proxy(
            "org.speech.Service",
            "/org/speech/Service",
            Duration::from_secs(2),
        );

        // Ping to verify service is alive
        let result: Result<(String,), _> = proxy.method_call("org.speech.Service", "Ping", ());
        match result {
            Ok((response,)) if response == "pong" => {
                info!("Connected to speechd-ng successfully");
                Ok(TranscriberBackend::SpeechdNg { connection: conn })
            }
            Ok((response,)) => {
                anyhow::bail!("speechd-ng Ping returned unexpected: {}", response);
            }
            Err(e) => {
                anyhow::bail!("speechd-ng not available: {}", e);
            }
        }
    }

    /// Transcribes audio data to text.
    /// For speechd-ng: audio_data is ignored (it captures from mic internally via ListenVad)
    /// For whisper.cpp: audio_data is written to temp WAV and processed
    pub fn transcribe(&self, audio_data: &[i16], sample_rate: u32) -> Result<String> {
        match &self.backend {
            TranscriberBackend::SpeechdNg { connection } => self.transcribe_via_speechd(connection),
            TranscriberBackend::WhisperCpp {
                model_path,
                binary_path,
            } => self.transcribe_via_subprocess(audio_data, sample_rate, model_path, binary_path),
        }
    }

    fn transcribe_via_speechd(&self, conn: &Connection) -> Result<String> {
        let proxy = conn.with_proxy(
            "org.speech.Service",
            "/org/speech/Service",
            Duration::from_secs(10),
        );

        info!("Calling speechd-ng ListenVad...");
        let result: Result<(String,), _> = proxy.method_call("org.speech.Service", "ListenVad", ());

        match result {
            Ok((text,)) => {
                info!("Transcribed via speechd-ng: '{}'", text);
                Ok(text)
            }
            Err(e) => {
                error!("speechd-ng ListenVad failed: {}", e);
                anyhow::bail!("STT failed: {}", e)
            }
        }
    }

    fn transcribe_via_subprocess(
        &self,
        audio_data: &[i16],
        sample_rate: u32,
        model_path: &str,
        binary_path: &str,
    ) -> Result<String> {
        // Write audio to temporary WAV file
        let mut temp_file = NamedTempFile::new().context("Failed to create temp file")?;
        let temp_path = temp_file.path().to_path_buf();

        write_wav_header(
            temp_file.as_file_mut(),
            audio_data.len() as u32,
            sample_rate,
        )?;

        // Convert i16 to bytes (little endian)
        let mut byte_data = Vec::with_capacity(audio_data.len() * 2);
        for sample in audio_data {
            byte_data.extend_from_slice(&sample.to_le_bytes());
        }
        temp_file.write_all(&byte_data)?;

        info!("Running whisper.cpp on {} samples...", audio_data.len());

        let output = Command::new(binary_path)
            .arg("-m")
            .arg(model_path)
            .arg("-f")
            .arg(&temp_path)
            .arg("-nt") // No timestamps
            .output()
            .context("Failed to execute whisper binary")?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            error!("whisper.cpp failed: {}", stderr);
            anyhow::bail!("Whisper process exited with error");
        }

        let stdout = String::from_utf8_lossy(&output.stdout);
        let text = stdout.trim().to_string();

        info!("Transcribed via whisper.cpp: '{}'", text);
        Ok(text)
    }

    /// Returns which backend is active
    pub fn backend_name(&self) -> &'static str {
        match &self.backend {
            TranscriberBackend::SpeechdNg { .. } => "speechd-ng",
            TranscriberBackend::WhisperCpp { .. } => "whisper.cpp",
        }
    }
}

fn write_wav_header(file: &mut File, num_samples: u32, sample_rate: u32) -> Result<()> {
    let num_channels: u32 = 1;
    let bits_per_sample: u32 = 16;
    let byte_rate = sample_rate * num_channels * bits_per_sample / 8;
    let block_align = num_channels * bits_per_sample / 8;
    let subchunk2_size = num_samples * num_channels * bits_per_sample / 8;
    let chunk_size = 36 + subchunk2_size;

    file.write_all(b"RIFF")?;
    file.write_all(&chunk_size.to_le_bytes())?;
    file.write_all(b"WAVE")?;
    file.write_all(b"fmt ")?;
    file.write_all(&16u32.to_le_bytes())?;
    file.write_all(&1u16.to_le_bytes())?;
    file.write_all(&(num_channels as u16).to_le_bytes())?;
    file.write_all(&sample_rate.to_le_bytes())?;
    file.write_all(&byte_rate.to_le_bytes())?;
    file.write_all(&(block_align as u16).to_le_bytes())?;
    file.write_all(&(bits_per_sample as u16).to_le_bytes())?;
    file.write_all(b"data")?;
    file.write_all(&subchunk2_size.to_le_bytes())?;

    Ok(())
}
