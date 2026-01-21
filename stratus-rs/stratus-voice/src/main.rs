mod audio_capture;
mod config;
mod ptt_hook;
mod whisper_integration;

use audio_capture::AudioPipeline;
use config::Config;
use dbus::ffidisp::Connection;
use dbus_tree::{Factory, MTFn, MethodErr, MethodInfo};
use log::{error, info, warn};
use std::sync::Arc;
use std::thread;

use whisper_integration::WhisperTranscriber;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();
    info!("Starting Stratus Voice Service...");

    // Load configuration
    let config = Config::load()?;
    info!("Configuration loaded.");

    // Initialize components
    let whisper = Arc::new(WhisperTranscriber::new(
        &config.whisper_model,
        &config.whisper_bin,
    ));
    info!("STT Backend: {}", whisper.backend_name());

    let audio = Arc::new(AudioPipeline::new());

    // D-Bus Setup
    let connection = Connection::new_session()?;
    // 4 = ReplaceExisting, 0 = no other flags
    connection.register_name("org.stratus.ATC.Voice", 4)?;

    let f = Factory::new_fn::<()>();

    // We need shared access to components in the DBus callbacks
    let audio_clone_start = audio.clone();
    let audio_clone_stop = audio.clone();
    let whisper_clone = whisper.clone();

    // Signal type placeholder - standard dbus crate usage involves defining interface
    // For brevity/prototype we use the tree builder

    let tree = f.tree(()).add(
        f.object_path("/org/stratus/ATC/Voice", ())
            .introspectable()
            .add(
                f.interface("org.stratus.ATC.Voice", ())
                    .add_s(f.signal("SpeechRecognized", ())) // Argument: text
                    .add_m(f.method(
                        "StartListening",
                        (),
                        move |_ctx: &MethodInfo<MTFn<()>, ()>| {
                            info!("Received StartListening signal");
                            match audio_clone_start.start_capture() {
                                Ok(_) => {
                                    audio_clone_start.start_recording();
                                    Ok(vec![])
                                }
                                Err(e) => {
                                    error!("Failed to start capture: {}", e);
                                    Err(MethodErr::failed(&e))
                                }
                            }
                        },
                    ))
                    .add_m(f.method(
                        "StopListening",
                        (),
                        move |ctx: &MethodInfo<MTFn<()>, ()>| {
                            info!("Received StopListening signal");
                            let audio_data = audio_clone_stop.stop_recording();

                            if audio_data.is_empty() {
                                warn!("Audio buffer empty!");
                                return Ok(vec![ctx.msg.method_return().append1(String::from(""))]);
                            }

                            let w = whisper_clone.clone();
                            let text = match w.transcribe(&audio_data, 16000) {
                                Ok(t) => t,
                                Err(e) => {
                                    error!("Transcription failed: {}", e);
                                    String::from("Error")
                                }
                            };

                            // Emit SpeechRecognized signal
                            let signal_msg = dbus::Message::new_signal(
                                "/org/stratus/ATC/Voice",
                                "org.stratus.ATC.Voice",
                                "SpeechRecognized",
                            )
                            .unwrap()
                            .append1(&text);

                            Ok(vec![ctx.msg.method_return().append1(text), signal_msg])
                        },
                    )),
            ),
    );

    tree.set_registered(&connection, true)?;

    info!("Service registered. Listening for calls...");

    // Spawn PTT file monitor in background thread
    // Watches stratus_ptt.json written by X-Plane plugin
    let ptt_file = Config::ptt_file();
    info!("PTT file path: {:?}", ptt_file);
    thread::spawn(move || match ptt_hook::PTTMonitor::new(&ptt_file) {
        Ok(mut monitor) => {
            if let Err(e) = monitor.listen() {
                error!("PTT Monitor crashed: {}", e);
            }
        }
        Err(e) => error!(
            "Failed to initialize PTT Monitor: {}. Is X-Plane running?",
            e
        ),
    });

    // Add Match for method calls
    connection.add_match("interface='org.stratus.ATC.Voice'")?;

    loop {
        if let Some(msg) = connection.incoming(1000).next() {
            tree.handle(&msg);
        }
    }
}
