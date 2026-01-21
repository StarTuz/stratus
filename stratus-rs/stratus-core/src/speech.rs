use zbus::{proxy, Result};

/// Proxy for the SpeechD-NG D-Bus service.
///
/// Service: `org.speech.Service`
/// Path: `/org/speech/Service`
/// Interface: `org.speech.Service`
#[proxy(
    interface = "org.speech.Service",
    default_service = "org.speech.Service",
    default_path = "/org/speech/Service"
)]
pub trait Speech {
    /// Speak the given text using the default voice.
    fn speak(&self, text: &str) -> Result<()>;

    /// Listen for speech using VAD (Voice Activity Detection).
    /// Returns the transcribed text.
    fn listen_vad(&self) -> Result<String>;

    /// Check if the service is alive.
    /// Should return "pong".
    fn ping(&self) -> Result<String>;
}

/// Connect to the speech service.
pub async fn connect() -> Result<SpeechProxy<'static>> {
    let connection = zbus::Connection::session().await?;
    SpeechProxy::new(&connection).await
}
