//! Stratus Application - Main Iced App
//!
//! Elm-style architecture with Message passing.

use iced::futures::{SinkExt, StreamExt};
use iced::widget::{
    column, container, horizontal_space, row, scrollable, text, text_input, Column,
};
use iced::{stream, time, Element, Length, Subscription, Task, Theme};
use std::path::PathBuf;
use std::time::Duration;
use stratus_core::{
    atc::AtcEngine, commands::CommandWriter, config::StratusConfig, speech::SpeechProxy, voice,
    Telemetry, WarmupService,
};

/// Main application state
pub struct StratusApp {
    // UI State
    input_text: String,
    comm_log: Vec<CommEntry>,

    // Core state
    telemetry: Telemetry,
    connected: bool,
    last_telemetry_time: std::time::Instant,
    ollama_status: OllamaStatus,

    // Services
    atc_engine: AtcEngine,
    cmd_writer: CommandWriter,
    warmup: WarmupService,
    pending_prompt: Option<String>,
    #[cfg(target_os = "linux")]
    speech: Option<SpeechProxy<'static>>,
    config: StratusConfig,

    // Paths
    data_dir: PathBuf,
}

#[derive(Debug, Clone)]
pub struct CommEntry {
    pub speaker: String,
    pub message: String,
}

#[derive(Debug, Clone, Default, PartialEq)]
pub enum OllamaStatus {
    #[default]
    Unknown,
    Connected,
    Disconnected,
}

/// Messages that can be sent to the application
#[derive(Debug, Clone)]
pub enum Message {
    // UI Events
    InputChanged(String),
    SendMessage,

    // Background events
    TelemetryUpdated(Result<Telemetry, String>),
    OllamaStatusChanged(bool),
    #[cfg(target_os = "linux")]
    SpeechConnected(Result<SpeechProxy<'static>, String>),
    VoiceSignalReceived(String),
    // Processing results
    ProcessingFinished(
        Result<
            (
                AtcEngine,
                String,
                Option<String>,
                Vec<stratus_core::commands::Command>,
            ),
            String,
        >,
    ), // engine, pilot_msg, atc_msg, commands

    // System
    Tick,
    CheckOllama,
}

impl StratusApp {
    /// Create new application with initial state
    pub fn new() -> (Self, Task<Message>) {
        let data_dir = Self::get_data_dir();
        let config = StratusConfig::load().unwrap_or_default();

        let atc_engine = AtcEngine::new(&config);
        let cmd_writer = CommandWriter::new(data_dir.join("stratus_commands.jsonl"));

        let warmup = WarmupService::default();

        // Start warmup service
        warmup.start();

        let app = Self {
            input_text: String::new(),
            comm_log: vec![CommEntry {
                speaker: "SYSTEM".into(),
                message: "Stratus ATC (Rust Core) initialized.".into(),
            }],
            telemetry: Telemetry::default(),
            connected: false,
            last_telemetry_time: std::time::Instant::now(),
            ollama_status: OllamaStatus::Unknown,
            atc_engine,
            cmd_writer,
            warmup,
            pending_prompt: None,
            data_dir,
            #[cfg(target_os = "linux")]
            speech: None,
            config,
        };

        // Initial tasks
        let check_ollama = Task::perform(check_ollama_available(), Message::OllamaStatusChanged);

        #[cfg(target_os = "linux")]
        let connect_speech = Task::perform(connect_speech(), Message::SpeechConnected);

        #[cfg(target_os = "linux")]
        return (app, Task::batch([check_ollama, connect_speech]));

        #[cfg(not(target_os = "linux"))]
        (app, check_ollama)
    }

    fn get_data_dir() -> PathBuf {
        dirs::data_local_dir()
            .unwrap_or_else(|| PathBuf::from("/tmp"))
            .join("StratusATC")
    }

    /// Handle messages (Elm-style update)
    pub fn update(&mut self, message: Message) -> Task<Message> {
        match message {
            Message::InputChanged(text) => {
                self.input_text = text;
                Task::none()
            }
            Message::SendMessage => {
                if !self.input_text.trim().is_empty() {
                    let pilot_msg = self.input_text.clone();
                    self.input_text.clear();

                    // Route through VoiceSignal mechanism to unify logic
                    return Task::done(Message::VoiceSignalReceived(pilot_msg));
                }
                Task::none()
            }
            Message::VoiceSignalReceived(text) => {
                if text.trim().is_empty() {
                    return Task::none();
                }

                // Add pilot message log
                self.comm_log.push(CommEntry {
                    speaker: "PILOT".into(),
                    message: text.clone(),
                });

                self.comm_log.push(CommEntry {
                    speaker: "ATC".into(),
                    message: "Processing...".into(),
                });

                // Spawn ATC processing task
                let mut engine = self.atc_engine.clone();
                let telemetry = self.telemetry.clone();
                let pilot_msg = text.clone();
                let writer = self.cmd_writer.clone(); // Can we clone? CommandWriter needs Clone. It's just a PathBuf.

                Task::perform(
                    async move {
                        // Process input
                        let (response, commands) = engine
                            .process_pilot_input(&pilot_msg, &telemetry)
                            .await
                            .map_err(|e| e.to_string())?;

                        // Write commands SIDE EFFECT (or we return them to main thread to write?)
                        // Main thread has cmd_writer access too. But we can write here if we clone writer.
                        // Let's return commands to valid Elm architecture?
                        // Actually executing side effects in Task is fine.

                        // Write commands
                        if !commands.is_empty() {
                            // We need CommandWriter to be passed in or just use path provided?
                            // CommandWriter is just a wrapper around PathBuf.
                            // Assuming we can instantiate or just write manually?
                            // Better: return commands and let update handle writing.
                        }

                        Ok((engine, pilot_msg, response, commands))
                    },
                    Message::ProcessingFinished,
                )
            }
            Message::ProcessingFinished(result) => {
                match result {
                    Ok((new_engine, _pilot, response_opt, commands)) => {
                        self.atc_engine = new_engine;

                        if let Some(response) = response_opt {
                            // Update log with real response
                            if let Some(last) = self.comm_log.last_mut() {
                                if last.speaker == "ATC" {
                                    last.message = response.clone();
                                }
                            }

                            // Execute Commands
                            if !commands.is_empty() {
                                if let Err(e) = self.cmd_writer.write(&commands) {
                                    eprintln!("Failed to write commands: {}", e);
                                }
                            }

                            // Speak response
                            #[cfg(target_os = "linux")]
                            if let Some(client) = &self.speech {
                                let t = response.clone();
                                let c = client.clone();
                                return Task::perform(
                                    async move {
                                        let _ = c.speak(&t).await;
                                    },
                                    |_| Message::Tick,
                                );
                            }
                        } else {
                            // Radio Silence: Remove the "Processing..." entry
                            if let Some(last) = self.comm_log.last() {
                                if last.speaker == "ATC" && last.message == "..." {
                                    self.comm_log.pop();
                                }
                            }
                        }
                    }
                    Err(e) => {
                        if let Some(last) = self.comm_log.last_mut() {
                            if last.speaker == "ATC" {
                                last.message = format!("[Error: {}]", e);
                            }
                        }
                    }
                }

                Task::none()
            }
            Message::TelemetryUpdated(result) => {
                match result {
                    Ok(telemetry) => {
                        self.telemetry = telemetry.clone();
                        self.atc_engine.update_state(&telemetry);
                        self.connected = true;
                        self.last_telemetry_time = std::time::Instant::now();
                    }
                    Err(_) => {
                        // Check if connection is stale (no update in 5 seconds)
                        if self.last_telemetry_time.elapsed() > Duration::from_secs(5) {
                            self.connected = false;
                        }
                    }
                }
                Task::none()
            }
            Message::OllamaStatusChanged(available) => {
                self.ollama_status = if available {
                    OllamaStatus::Connected
                } else {
                    OllamaStatus::Disconnected
                };
                Task::none()
            }
            Message::Tick => {
                // Read telemetry file
                let path = self.data_dir.join("stratus_telemetry.json");
                Task::perform(read_telemetry_file(path), Message::TelemetryUpdated)
            }
            Message::CheckOllama => {
                Task::perform(check_ollama_available(), Message::OllamaStatusChanged)
            }
            #[cfg(target_os = "linux")]
            Message::SpeechConnected(result) => {
                if let Ok(proxy) = result {
                    self.speech = Some(proxy);
                }
                Task::none()
            }
        }
    }

    /// Render the view
    pub fn view(&self) -> Element<'_, Message> {
        let header = self.view_header();
        let main_content = self.view_main();
        let footer = self.view_footer();

        let content = column![header, main_content, footer]
            .spacing(10)
            .padding(20);

        container(content)
            .width(Length::Fill)
            .height(Length::Fill)
            .into()
    }

    fn view_header(&self) -> Element<'_, Message> {
        let status_text = if self.connected {
            text("● Connected to X-Plane").color([0.3, 0.9, 0.3])
        } else {
            text("○ Waiting for X-Plane...").color([0.6, 0.6, 0.6])
        };

        let ollama_text = match self.ollama_status {
            OllamaStatus::Connected => text("🧠 Ollama Ready").color([0.3, 0.9, 0.3]),
            OllamaStatus::Disconnected => text("⚠ Ollama Offline").color([0.9, 0.6, 0.3]),
            OllamaStatus::Unknown => text("? Checking Ollama...").color([0.6, 0.6, 0.6]),
        };

        let header_row = row![
            text("STRATUS ATC").size(24),
            horizontal_space(),
            status_text,
            text(" | "),
            ollama_text,
        ]
        .spacing(10);

        // Add warmup status indicator
        let warmup_status = if self.warmup.is_running() {
            if self.warmup.is_paused() {
                text("🔥 Warmup Paused").size(12).color([0.9, 0.9, 0.3])
            } else {
                text("🔥 Warmup Active").size(12).color([0.3, 0.9, 0.3])
            }
        } else {
            text("❄ Warmup Stopped").size(12).color([0.6, 0.6, 0.6])
        };

        column![header_row, row![horizontal_space(), warmup_status]]
            .spacing(5)
            .into()
    }

    fn view_main(&self) -> Element<'_, Message> {
        let telemetry_panel = self.view_telemetry();
        let comm_panel = self.view_comm_log();

        row![telemetry_panel, comm_panel]
            .spacing(20)
            .height(Length::Fill)
            .into()
    }

    fn view_telemetry(&self) -> Element<'_, Message> {
        let alt_ft = (self.telemetry.position.altitude_msl_m * 3.28084) as i32;
        let hdg = self.telemetry.orientation.heading_mag as i32;
        let spd = (self.telemetry.speed.ground_speed_mps * 1.94384) as i32;
        let ias = self.telemetry.speed.ias_kts as i32;

        let content = column![
            text("TELEMETRY").size(16),
            text(format!("ALT: {} ft", alt_ft)),
            text(format!("HDG: {}°", hdg)),
            text(format!("GS: {} kts", spd)),
            text(format!("IAS: {} kts", ias)),
            text(format!("XPDR: {:04}", self.telemetry.transponder.code)),
            text(format!(
                "COM1: {:.3}",
                self.telemetry.radios.com1_hz as f64 / 1_000_000.0
            )),
        ]
        .spacing(8)
        .padding(10);

        container(content).width(200).height(Length::Fill).into()
    }

    fn view_comm_log(&self) -> Element<'_, Message> {
        let entries: Vec<Element<'_, Message>> = self
            .comm_log
            .iter()
            .map(|entry| {
                let color = match entry.speaker.as_str() {
                    "PILOT" => [0.5, 0.8, 1.0],
                    "ATC" => [0.3, 1.0, 0.5],
                    "SYSTEM" => [0.7, 0.7, 0.7],
                    _ => [1.0, 1.0, 1.0],
                };
                text(format!("{}: {}", entry.speaker, entry.message))
                    .color(color)
                    .into()
            })
            .collect();

        let log = Column::with_children(entries).spacing(4);

        let scroll = scrollable(log).height(Length::Fill);

        let input = text_input("Type message...", &self.input_text)
            .on_input(Message::InputChanged)
            .on_submit(Message::SendMessage)
            .padding(10);

        column![text("COMMUNICATIONS").size(16), scroll, input,]
            .spacing(10)
            .width(Length::Fill)
            .into()
    }

    fn view_footer(&self) -> Element<'_, Message> {
        let lat = self.telemetry.position.latitude;
        let lon = self.telemetry.position.longitude;

        row![
            text(format!("Position: {:.4}°, {:.4}°", lat, lon)).size(12),
            horizontal_space(),
            text("Stratus ATC v0.2.0 (Rust)").size(12),
        ]
        .into()
    }

    /// Get the theme
    pub fn theme(&self) -> Theme {
        Theme::Dark
    }

    /// Subscriptions for background tasks
    pub fn subscription(&self) -> Subscription<Message> {
        // Poll telemetry every 500ms
        let telemetry_tick = time::every(Duration::from_millis(500)).map(|_| Message::Tick);

        // Check Ollama every 10 seconds
        let ollama_check = time::every(Duration::from_secs(10)).map(|_| Message::CheckOllama);

        let mut subs = vec![telemetry_tick, ollama_check];

        // Listen for Voice Signals
        #[cfg(target_os = "linux")]
        {
            let voice_sub = Subscription::run(|| {
                stream::channel(100, |mut output| async move {
                    match voice::speech_stream().await {
                        Ok(mut stream) => {
                            while let Some(text) = stream.next().await {
                                let _ = output.send(Message::VoiceSignalReceived(text)).await;
                            }
                        }
                        Err(e) => {
                            eprintln!("Voice stream error: {}", e);
                        }
                    }
                    std::future::pending().await
                })
            });
            subs.push(voice_sub);
        }

        Subscription::batch(subs)
    }
}

// Async helper functions

async fn read_telemetry_file(path: PathBuf) -> Result<Telemetry, String> {
    let content = tokio::fs::read_to_string(&path)
        .await
        .map_err(|e| e.to_string())?;

    serde_json::from_str(&content).map_err(|e| e.to_string())
}

async fn check_ollama_available() -> bool {
    reqwest::get("http://localhost:11434/api/tags")
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}

#[cfg(target_os = "linux")]
async fn connect_speech() -> Result<SpeechProxy<'static>, String> {
    stratus_core::speech::connect()
        .await
        .map_err(|e| e.to_string())
}
