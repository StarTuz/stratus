use futures_util::StreamExt;
use zbus::{proxy, Result};

/// Proxy for the Stratus Voice D-Bus service.
#[proxy(
    interface = "org.stratus.ATC.Voice",
    default_service = "org.stratus.ATC.Voice",
    default_path = "/org/stratus/ATC/Voice"
)]
pub trait Voice {
    /// Start listening (PTT Press)
    fn start_listening(&self) -> Result<()>;

    /// Stop listening (PTT Release) - returns raw text
    fn stop_listening(&self) -> Result<String>;

    /// Signal emitted when speech is recognized
    #[zbus(signal)]
    fn speech_recognized(&self, text: String) -> Result<()>;
}

/// Connect to the Voice service
pub async fn connect() -> Result<VoiceProxy<'static>> {
    let connection = zbus::Connection::session().await?;
    VoiceProxy::new(&connection).await
}

/// Create a stream of valid speech events
pub async fn speech_stream() -> Result<impl futures_util::Stream<Item = String>> {
    let proxy = connect().await?;
    Ok(proxy.receive_speech_recognized().await?.map(|msg| {
        // msg.0 is zbus::message::Body (lazy decoding)
        // We deserialize it to String
        msg.0.deserialize::<String>().unwrap_or_default()
    }))
}
