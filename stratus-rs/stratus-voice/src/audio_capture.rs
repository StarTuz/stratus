use anyhow::{Context, Result};
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use log::{info, warn};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use webrtc_vad::{Vad, VadMode};

pub struct AudioPipeline {
    _vad: Arc<Mutex<Vad>>,
    is_recording: Arc<AtomicBool>,
    buffer: Arc<Mutex<Vec<i16>>>,
}

impl AudioPipeline {
    pub fn new() -> Self {
        let vad =
            Vad::new_with_rate_and_mode(webrtc_vad::SampleRate::Rate16kHz, VadMode::Aggressive);
        Self {
            _vad: Arc::new(Mutex::new(vad)),
            is_recording: Arc::new(AtomicBool::new(false)),
            buffer: Arc::new(Mutex::new(Vec::new())),
        }
    }

    pub fn start_capture(&self) -> Result<()> {
        let host = cpal::default_host();
        let device = host
            .default_input_device()
            .context("No input device available")?;

        info!(
            "Using input device: {}",
            device.name().unwrap_or("default".to_string())
        );

        let config = cpal::StreamConfig {
            channels: 1,
            sample_rate: cpal::SampleRate(16000),
            buffer_size: cpal::BufferSize::Default,
        };

        let is_recording = self.is_recording.clone();
        let buffer = self.buffer.clone();

        // VAD must be used on 10ms, 20ms, or 30ms frames.
        // 16kHz * 0.03s = 480 samples.

        let stream = device.build_input_stream(
            &config,
            move |data: &[i16], _: &_| {
                if is_recording.load(Ordering::Relaxed) {
                    let mut buf_lock = buffer.lock().unwrap();
                    buf_lock.extend_from_slice(data);
                }
            },
            move |err| {
                warn!("Audio stream error: {}", err);
            },
            None,
        )?;

        stream.play()?;

        // Keep stream alive references?
        // In a real implementation we would return the Stream object or handle lifecycle differently.
        // For this synthesized example we assume this struct manages the thread or stream object.
        // leaking stream for now as a quick prototype or storing it in the struct
        std::mem::forget(stream);

        Ok(())
    }

    pub fn start_recording(&self) {
        self.buffer.lock().unwrap().clear();
        self.is_recording.store(true, Ordering::SeqCst);
        info!("Started recording audio...");
    }

    pub fn stop_recording(&self) -> Vec<i16> {
        self.is_recording.store(false, Ordering::SeqCst);
        info!("Stopped recording.");
        let buf = self.buffer.lock().unwrap();
        buf.clone() // Return copy of data
    }
}
