#![allow(dead_code)]
//! ComLink - Embedded Web Server
//!
//! Serves the ComLink web interface for tablet/VR access.

use axum::{routing::get, Router};
use std::net::SocketAddr;

/// Create the Axum router for ComLink
pub fn create_router() -> Router {
    Router::new()
        .route("/", get(index_handler))
        .route("/api/status", get(status_handler))
        .route("/api/telemetry", get(telemetry_handler))
}

async fn index_handler() -> &'static str {
    r#"<!DOCTYPE html>
<html>
<head>
    <title>Stratus ComLink</title>
    <style>
        body { 
            background: #1a1a2e; 
            color: #eee; 
            font-family: sans-serif;
            padding: 20px;
        }
        h1 { color: #4a9eff; }
    </style>
</head>
<body>
    <h1>Stratus ComLink</h1>
    <p>Web interface coming soon...</p>
</body>
</html>"#
}

async fn status_handler() -> &'static str {
    r#"{"status": "ok", "connected": true}"#
}

async fn telemetry_handler() -> &'static str {
    r#"{"altitude": 0, "heading": 0, "speed": 0}"#
}

/// Start the ComLink web server
pub async fn start_server(port: u16) -> anyhow::Result<()> {
    let app = create_router();
    let addr = SocketAddr::from(([127, 0, 0, 1], port));

    tracing::info!("ComLink server listening on http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
