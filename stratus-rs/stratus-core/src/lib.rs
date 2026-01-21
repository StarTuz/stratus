//! Stratus Core - ATC Engine Library
//!
//! This crate contains the core logic for Stratus ATC:
//! - Telemetry: File-based communication with X-Plane
//! - Ollama: Local LLM client
//! - Streaming: Low-latency streaming LLM responses
//! - Warmup: Keep model hot to eliminate cold-starts
//! - ATC: Prompt building and response parsing

pub mod atc;
pub mod commands;
pub mod ollama;
#[cfg(target_os = "linux")]
pub mod speech;
pub mod streaming;
pub mod telemetry;
pub mod voice;
pub mod warmup;

#[cfg(test)]
mod atc_tests;
#[cfg(test)]
mod commands_tests;

// Re-export common types
pub use atc::AtcEngine;
pub use ollama::OllamaClient;
pub use streaming::{StreamChunk, StreamingOllama};
pub use telemetry::{Telemetry, TelemetryWatcher};
pub use warmup::{WarmupConfig, WarmupService};
