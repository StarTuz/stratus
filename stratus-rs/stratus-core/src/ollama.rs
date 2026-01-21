//! Ollama Client - Local LLM integration
//!
//! Communicates with Ollama REST API for ATC response generation.

use reqwest::Client;
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum OllamaError {
    #[error("HTTP request failed: {0}")]
    RequestError(#[from] reqwest::Error),
    #[error("Ollama not running or model not loaded")]
    NotAvailable,
    #[error("Invalid response: {0}")]
    InvalidResponse(String),
}

/// Request body for Ollama generate endpoint
#[derive(Debug, Serialize)]
struct GenerateRequest {
    model: String,
    prompt: String,
    stream: bool,
    options: GenerateOptions,
}

#[derive(Debug, Serialize)]
struct GenerateOptions {
    temperature: f32,
    num_predict: i32,
}

/// Response from Ollama generation (non-streaming or final)
#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct GenerateResponse {
    response: String,
    done: bool,
}

/// Ollama client for ATC response generation
#[derive(Debug, Clone)]
pub struct OllamaClient {
    client: Client,
    base_url: String,
    model: String,
}

impl OllamaClient {
    /// Create a new Ollama client
    pub fn new(model: impl Into<String>) -> Self {
        Self {
            client: Client::new(),
            base_url: "http://localhost:11434".to_string(),
            model: model.into(),
        }
    }

    /// Set custom Ollama URL
    pub fn with_url(mut self, url: impl Into<String>) -> Self {
        self.base_url = url.into();
        self
    }

    /// Set custom model
    pub fn with_model(mut self, model: impl Into<String>) -> Self {
        self.model = model.into();
        self
    }

    /// Check if Ollama is available
    pub async fn is_available(&self) -> bool {
        self.client
            .get(format!("{}/api/tags", self.base_url))
            .send()
            .await
            .is_ok()
    }

    /// Generate a response from the LLM
    pub async fn generate(&self, prompt: &str) -> Result<String, OllamaError> {
        let request = GenerateRequest {
            model: self.model.clone(),
            prompt: prompt.to_string(),
            stream: false,
            options: GenerateOptions {
                temperature: 0.7,
                num_predict: 256,
            },
        };

        let response = self
            .client
            .post(format!("{}/api/generate", self.base_url))
            .json(&request)
            .timeout(std::time::Duration::from_secs(30))
            .send()
            .await?;

        if !response.status().is_success() {
            return Err(OllamaError::NotAvailable);
        }

        let result: GenerateResponse = response.json().await?;
        Ok(result.response)
    }
}

impl Default for OllamaClient {
    fn default() -> Self {
        Self::new("llama3.2:3b")
    }
}
