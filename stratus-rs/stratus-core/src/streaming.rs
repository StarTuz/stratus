//! Streaming Ollama Client
//!
//! Provides streaming LLM responses for low-latency ATC responses.
//! Tokens are streamed and can be sent to TTS as they arrive.

use futures_util::StreamExt;
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::time::{Duration, Instant};
use thiserror::Error;
use tokio::sync::mpsc;

#[derive(Error, Debug)]
pub enum StreamError {
    #[error("HTTP request failed: {0}")]
    RequestError(#[from] reqwest::Error),
    #[error("Ollama not available")]
    NotAvailable,
    #[error("JSON parse error: {0}")]
    ParseError(#[from] serde_json::Error),
    #[error("Stream closed unexpectedly")]
    StreamClosed,
}

/// A chunk of streamed response
#[derive(Debug, Clone)]
pub struct StreamChunk {
    pub text: String,
    pub is_final: bool,
    pub latency_ms: u64,
}

/// Response from Ollama streaming endpoint (each line)
#[derive(Debug, Deserialize)]
struct StreamLine {
    response: String,
    done: bool,
}

/// Request body for Ollama generate endpoint
#[derive(Debug, Serialize)]
struct GenerateRequest {
    model: String,
    prompt: String,
    system: String,
    stream: bool,
    options: GenerateOptions,
}

#[derive(Debug, Serialize)]
struct GenerateOptions {
    temperature: f32,
    num_predict: i32,
}

use std::hash::{Hash, Hasher};

/// Streaming Ollama client for low-latency ATC responses
#[derive(Clone, Debug)]
pub struct StreamingOllama {
    client: Client,
    base_url: String,
    model: String,
    min_chunk_chars: usize,
    max_chunk_chars: usize,
}

impl PartialEq for StreamingOllama {
    fn eq(&self, other: &Self) -> bool {
        self.base_url == other.base_url
            && self.model == other.model
            && self.min_chunk_chars == other.min_chunk_chars
            && self.max_chunk_chars == other.max_chunk_chars
    }
}

impl Eq for StreamingOllama {}

impl Hash for StreamingOllama {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.base_url.hash(state);
        self.model.hash(state);
        self.min_chunk_chars.hash(state);
        self.max_chunk_chars.hash(state);
    }
}

impl StreamingOllama {
    /// Create a new streaming Ollama client
    pub fn new(model: impl Into<String>) -> Self {
        Self {
            client: Client::new(),
            base_url: "http://localhost:11434".to_string(),
            model: model.into(),
            min_chunk_chars: 20,
            max_chunk_chars: 100,
        }
    }

    /// Set custom Ollama URL
    pub fn with_url(mut self, url: impl Into<String>) -> Self {
        self.base_url = url.into();
        self
    }

    /// Set chunk size parameters
    pub fn with_chunk_size(mut self, min: usize, max: usize) -> Self {
        self.min_chunk_chars = min;
        self.max_chunk_chars = max;
        self
    }

    /// Check if Ollama is available
    pub async fn is_available(&self) -> bool {
        self.client
            .get(format!("{}/api/tags", self.base_url))
            .timeout(Duration::from_secs(2))
            .send()
            .await
            .is_ok()
    }

    /// Generate a streaming response
    ///
    /// Returns a channel receiver that yields StreamChunk as they arrive.
    /// Chunks are buffered until phrase boundaries (punctuation) or max size.
    pub async fn generate_stream(
        &self,
        prompt: &str,
    ) -> Result<mpsc::Receiver<StreamChunk>, StreamError> {
        let (tx, rx) = mpsc::channel(32);

        let system_prompt = "You are Stratus, an expert US Air Traffic Controller (TRACON). \
        You communicate using strict FAA Order 7110.65 phraseology. \
        You are concise, professional, and authoritative. \
        Do not act as a conversational assistant. Only provide ATC instructions. \
        Your output must be suitable for Text-to-Speech.";

        let request = GenerateRequest {
            model: self.model.clone(),
            prompt: prompt.to_string(),
            system: system_prompt.to_string(),
            stream: true,
            options: GenerateOptions {
                temperature: 0.3, // Lower temperature for more deterministic/professional output
                num_predict: 256,
            },
        };

        let response = self
            .client
            .post(format!("{}/api/generate", self.base_url))
            .json(&request)
            .timeout(Duration::from_secs(30))
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(StreamError::NotAvailable);
        }

        let min_chars = self.min_chunk_chars;
        let max_chars = self.max_chunk_chars;
        let start_time = Instant::now();

        // Spawn task to process stream
        tokio::spawn(async move {
            let mut buffer = String::new();
            let mut stream = response.bytes_stream();

            while let Some(chunk_result) = stream.next().await {
                let bytes = match chunk_result {
                    Ok(b) => b,
                    Err(_) => break,
                };

                // Parse each line in the chunk
                for line in String::from_utf8_lossy(&bytes).lines() {
                    if line.is_empty() {
                        continue;
                    }

                    let parsed: StreamLine = match serde_json::from_str(line) {
                        Ok(p) => p,
                        Err(_) => continue,
                    };

                    buffer.push_str(&parsed.response);

                    // Check if we should emit a chunk
                    let should_emit = parsed.done
                        || buffer.len() >= max_chars
                        || (buffer.len() >= min_chars && has_phrase_boundary(&buffer));

                    if should_emit && !buffer.is_empty() {
                        let chunk = StreamChunk {
                            text: buffer.trim().to_string(),
                            is_final: parsed.done,
                            latency_ms: start_time.elapsed().as_millis() as u64,
                        };
                        buffer.clear();

                        if tx.send(chunk).await.is_err() {
                            break;
                        }
                    }

                    if parsed.done {
                        break;
                    }
                }
            }

            // Send any remaining buffer
            if !buffer.is_empty() {
                let _ = tx
                    .send(StreamChunk {
                        text: buffer.trim().to_string(),
                        is_final: true,
                        latency_ms: start_time.elapsed().as_millis() as u64,
                    })
                    .await;
            }
        });

        Ok(rx)
    }

    /// Generate with a callback for each chunk (convenience method)
    pub async fn generate_with_callback<F>(
        &self,
        prompt: &str,
        mut on_chunk: F,
    ) -> Result<String, StreamError>
    where
        F: FnMut(StreamChunk) + Send + 'static,
    {
        let mut rx = self.generate_stream(prompt).await?;
        let mut full_response = String::new();

        while let Some(chunk) = rx.recv().await {
            full_response.push_str(&chunk.text);
            full_response.push(' ');
            on_chunk(chunk);
        }

        Ok(full_response.trim().to_string())
    }
}

/// Check if buffer ends with a phrase boundary
fn has_phrase_boundary(s: &str) -> bool {
    s.ends_with('.')
        || s.ends_with('!')
        || s.ends_with('?')
        || s.ends_with(',')
        || s.ends_with(';')
        || s.ends_with(':')
        || s.ends_with('\n')
}

impl Default for StreamingOllama {
    fn default() -> Self {
        Self::new("llama3.2:3b")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_availability_check() {
        let client = StreamingOllama::default();
        // This will fail if Ollama isn't running, which is fine for unit tests
        let _ = client.is_available().await;
    }
}
