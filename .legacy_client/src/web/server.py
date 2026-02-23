"""
ComLink Web Server

A local web server providing a browser-based interface for StratusATC.
This mirrors the official Stratus ComLink feature, allowing users to:
- View communication history on a tablet/phone/second monitor
- Tune frequencies by tapping them
- Send quick transmissions
- Monitor connection status

Uses Flask for simplicity and Flask-SocketIO for real-time updates.
"""

import os
import sys
import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, asdict

from flask import Flask, render_template_string, jsonify, request, send_from_directory
from flask_socketio import SocketIO, emit

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


# =============================================================================
# HTML Template - Modern, Touch-Friendly ComLink Interface
# =============================================================================

COMLINK_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="theme-color" content="#0a0a12">
    <title>StratusATC ComLink</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.min.js"></script>
    <style>
        :root {
            --bg-primary: #0a0a12;
            --bg-secondary: #12121c;
            --bg-tertiary: #1a1a28;
            --bg-card: rgba(26, 26, 40, 0.85);
            --accent-primary: #6366f1;
            --accent-secondary: #818cf8;
            --accent-green: #00d26a;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-blue: #60a5fa;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --border-light: rgba(255, 255, 255, 0.1);
            --glow: 0 0 20px rgba(99, 102, 241, 0.3);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        
        body {
            font-family: 'Inter', -apple-system, sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, #0d0d1a 100%);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 16px;
        }
        
        /* Header */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-light);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            font-size: 1.2rem;
        }
        
        .logo-icon {
            font-size: 1.5rem;
        }
        
        .status-badge {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
        }
        
        .status-badge.connected {
            background: rgba(0, 210, 106, 0.15);
            color: var(--accent-green);
        }
        
        .status-badge.disconnected {
            background: rgba(239, 68, 68, 0.15);
            color: var(--accent-red);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-dot.connected { background: var(--accent-green); }
        .status-dot.disconnected { background: var(--accent-red); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        /* Radio Panel */
        .radio-panel {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-top: 16px;
        }
        
        @media (max-width: 500px) {
            .radio-panel {
                grid-template-columns: 1fr;
            }
        }
        
        .radio-card {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 16px;
            border: 1px solid var(--border-light);
        }
        
        .radio-label {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--accent-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .freq-display {
            font-family: 'JetBrains Mono', monospace;
            font-size: 2rem;
            font-weight: 700;
            color: var(--accent-green);
            cursor: pointer;
            transition: all 0.2s;
            padding: 8px;
            margin: -8px;
            border-radius: 8px;
        }
        
        .freq-display:hover {
            background: rgba(0, 210, 106, 0.1);
        }
        
        .freq-display:active {
            transform: scale(0.98);
        }
        
        .standby-row {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 8px;
        }
        
        .standby-label {
            font-size: 0.7rem;
            color: var(--text-muted);
        }
        
        .standby-freq {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1rem;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .standby-freq:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }
        
        .swap-btn {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 1.2rem;
            cursor: pointer;
            transition: all 0.2s;
            margin-left: auto;
        }
        
        .swap-btn:hover {
            background: var(--accent-secondary);
            transform: rotate(180deg);
        }
        
        .swap-btn:active {
            transform: scale(0.9) rotate(180deg);
        }
        
        /* Transponder */
        .xpdr-card {
            grid-column: 1 / -1;
        }
        
        .xpdr-row {
            display: flex;
            align-items: center;
            gap: 16px;
        }
        
        .xpdr-code {
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--accent-orange);
        }
        
        .xpdr-mode {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.8rem;
            font-weight: 700;
            background: var(--accent-green);
            color: var(--bg-primary);
        }
        
        /* Communications History */
        .comms-section {
            margin-top: 20px;
        }
        
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        
        .section-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .comms-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .comm-entry {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 14px;
            border: 1px solid var(--border-light);
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .comm-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        
        .comm-icon {
            font-size: 1.1rem;
        }
        
        .comm-station {
            font-weight: 600;
            color: var(--accent-blue);
            flex: 1;
        }
        
        .comm-freq {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            color: var(--text-muted);
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.2s;
        }
        
        .comm-freq:hover {
            background: var(--accent-green);
            color: var(--bg-primary);
        }
        
        .comm-message {
            color: var(--text-secondary);
            font-size: 0.95rem;
            line-height: 1.5;
        }
        
        .comm-message.pilot {
            color: var(--accent-orange);
            font-style: italic;
        }
        
        .comm-play-btn {
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            background: var(--accent-primary);
            color: white;
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 8px;
        }
        
        .comm-play-btn:hover {
            background: var(--accent-secondary);
            transform: scale(1.02);
        }
        
        .comm-play-btn:active {
            transform: scale(0.98);
        }
        
        /* Transmission Panel */
        .transmit-section {
            margin-top: 20px;
            background: var(--bg-card);
            border-radius: 16px;
            padding: 16px;
            border: 1px solid var(--border-light);
        }
        
        .transmit-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
        }
        
        .channel-toggle {
            padding: 6px 14px;
            border: none;
            border-radius: 6px;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            margin-left: auto;
        }
        
        .channel-toggle.com1 {
            background: var(--accent-green);
            color: var(--bg-primary);
        }
        
        .channel-toggle.com2 {
            background: var(--accent-orange);
            color: var(--bg-primary);
        }
        
        .transmit-input-row {
            display: flex;
            gap: 10px;
        }
        
        .transmit-input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid var(--border-light);
            border-radius: 10px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 1rem;
            outline: none;
            transition: border-color 0.2s;
        }
        
        .transmit-input:focus {
            border-color: var(--accent-primary);
        }
        
        .transmit-input::placeholder {
            color: var(--text-muted);
        }
        
        .send-btn {
            padding: 12px 20px;
            border: none;
            border-radius: 10px;
            background: var(--accent-primary);
            color: white;
            font-weight: 600;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .send-btn:hover {
            background: var(--accent-secondary);
            box-shadow: var(--glow);
        }
        
        .send-btn:active {
            transform: scale(0.98);
        }
        
        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        /* Quick Phrases */
        .quick-phrases {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
        }
        
        .phrase-btn {
            padding: 8px 14px;
            border: 1px solid var(--border-light);
            border-radius: 20px;
            background: transparent;
            color: var(--text-secondary);
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .phrase-btn:hover {
            background: var(--bg-tertiary);
            border-color: var(--accent-secondary);
            color: var(--text-primary);
        }
        
        .phrase-btn:active {
            transform: scale(0.95);
        }
        
        /* Copilot Toggle */
        .copilot-toggle {
            padding: 6px 14px;
            border: 1px solid var(--border-light);
            border-radius: 6px;
            font-weight: 500;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
            background: var(--bg-tertiary);
            color: var(--text-secondary);
        }
        
        .copilot-toggle:hover {
            background: var(--bg-secondary);
            border-color: var(--accent-secondary);
        }
        
        .copilot-toggle.active {
            background: var(--accent-primary);
            color: white;
            border-color: var(--accent-primary);
            animation: copilotPulse 2s infinite;
        }
        
        @keyframes copilotPulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.4); }
            50% { box-shadow: 0 0 10px 4px rgba(139, 92, 246, 0.2); }
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--text-muted);
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 12px;
        }
        
        /* Toast Notifications */
        .toast {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            padding: 12px 24px;
            border-radius: 10px;
            border: 1px solid var(--border-light);
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            animation: toastIn 0.3s ease-out;
        }
        
        .toast.success {
            border-color: var(--accent-green);
        }
        
        .toast.error {
            border-color: var(--accent-red);
        }
        
        @keyframes toastIn {
            from {
                opacity: 0;
                transform: translateX(-50%) translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }
        }
        
        /* Loading Spinner */
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid var(--border-light);
            border-top-color: var(--accent-primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Brain Section */
        .brain-section {
            margin-top: 20px;
            background: var(--bg-card);
            border-radius: 16px;
            padding: 16px;
            border: 1px solid var(--border-light);
        }
        
        .brain-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 10px;
        }
        
        .brain-model-info {
            font-size: 0.85rem;
            color: var(--text-muted);
        }
        
        .fix-btn {
            padding: 6px 14px;
            border: none;
            border-radius: 6px;
            background: var(--accent-red);
            color: white;
            font-weight: 600;
            font-size: 0.85rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .fix-btn:hover {
            box-shadow: 0 0 15px rgba(255, 71, 71, 0.4);
        }
        
        .badge {
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .badge.online { background: rgba(0, 210, 106, 0.2); color: var(--accent-green); }
        .badge.offline { background: rgba(255, 71, 71, 0.2); color: var(--accent-red); }
        
        /* Footer */
        .footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 0.8rem;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <header class="header">
        <div class="logo">
            <span class="logo-icon">📻</span>
            <span>ComLink</span>
        </div>
        <div id="status-badge" class="status-badge disconnected">
            <span class="status-dot disconnected"></span>
            <span id="status-text">Connecting...</span>
        </div>
    </header>
    
    <div class="container">
        <!-- Radio Panel -->
        <div class="radio-panel">
            <div class="radio-card">
                <div class="radio-label">COM1</div>
                <div class="freq-display" id="com1-active" onclick="tuneFreq('COM1', this.textContent)">---</div>
                <div class="standby-row">
                    <span class="standby-label">STBY:</span>
                    <span class="standby-freq" id="com1-standby" onclick="tuneStandby('COM1', this.textContent)">---</span>
                    <button class="swap-btn" onclick="swapFreq('COM1')" title="Swap Active/Standby">⇄</button>
                </div>
            </div>
            
            <div class="radio-card">
                <div class="radio-label">COM2</div>
                <div class="freq-display" id="com2-active" onclick="tuneFreq('COM2', this.textContent)">---</div>
                <div class="standby-row">
                    <span class="standby-label">STBY:</span>
                    <span class="standby-freq" id="com2-standby" onclick="tuneStandby('COM2', this.textContent)">---</span>
                    <button class="swap-btn" onclick="swapFreq('COM2')" title="Swap Active/Standby">⇄</button>
                </div>
            </div>
            
        </div>
        
        <!-- Brain Management (Local AI) -->
        <section id="brain-section" class="brain-section" style="display: none;">
            <div class="section-header">
                <span class="section-title">🧠 Local AI Brain</span>
                <span id="brain-status-badge" class="badge">---</span>
            </div>
            <div class="brain-controls">
                <div id="brain-model-info" class="brain-model-info">Model: ---</div>
                <button id="brain-fix-btn" class="fix-btn" onclick="startBrain()" style="display: none;">Fix / Start</button>
            </div>
        </section>
        
        <!-- Communications History -->
        <section class="comms-section">
            <div class="section-header">
                <span class="section-title">📡 Communications</span>
            </div>
            <div id="comms-list" class="comms-list">
                <div class="empty-state">
                    <div class="empty-state-icon">📭</div>
                    <div>No communications yet</div>
                    <div style="font-size: 0.85rem; margin-top: 8px;">
                        Connect to SAPI and start flying
                    </div>
                </div>
            </div>
        </section>
        
        <!-- Transmission Panel -->
        <section class="transmit-section">
            <div class="transmit-header">
                <span>✈️ Transmit</span>
                <button id="copilot-toggle" class="copilot-toggle" onclick="toggleCopilot()" title="Enable AI Copilot to handle ATC communications">🤖 Copilot</button>
                <button id="channel-toggle" class="channel-toggle com1" onclick="toggleChannel()">COM1</button>
            </div>
            <div class="transmit-input-row">
                <input 
                    type="text" 
                    id="transmit-input" 
                    class="transmit-input" 
                    placeholder="Type your transmission..."
                    onkeypress="if(event.key === 'Enter') sendTransmission()"
                >
                <button class="send-btn" onclick="sendTransmission()" id="send-btn">Send</button>
            </div>
            <div class="quick-phrases">
                <button class="phrase-btn" onclick="sendPhrase('Ready to copy')">Ready to Copy</button>
                <button class="phrase-btn" onclick="sendPhrase('Wilco')">Wilco</button>
                <button class="phrase-btn" onclick="sendPhrase('Unable')">Unable</button>
                <button class="phrase-btn" onclick="sendPhrase('Say again')">Say Again</button>
                <button class="phrase-btn" onclick="sendPhrase('Standby')">Standby</button>
                <button class="phrase-btn" onclick="sendPhrase('Request taxi')">Request Taxi</button>
            </div>
        </section>
        
        <footer class="footer">
            StratusATC • Native Linux/Mac Client
        </footer>
    </div>
    
    <script>
        // State
        let currentChannel = 'COM1';
        let connected = false;
        let copilotEnabled = false;
        let socket = null;
        
        // Initialize WebSocket connection
        function initSocket() {
            socket = io({ transports: ['websocket', 'polling'] });
            
            socket.on('connect', () => {
                console.log('WebSocket connected');
                // Request initial state
                socket.emit('get_state');
            });
            
            socket.on('disconnect', () => {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false, 'Disconnected');
            });
            
            socket.on('state_update', (data) => {
                updateFromState(data);
            });
            
            socket.on('comms_update', (data) => {
                updateComms(data.comms);
            });
            
            socket.on('telemetry_update', (data) => {
                updateTelemetry(data);
            });
            
            socket.on('toast', (data) => {
                showToast(data.message, data.type || 'info');
            });
        }
        
        // Update UI from state
        function updateFromState(state) {
            updateConnectionStatus(state.sapi_connected, state.status_text);
            updateTelemetry(state.telemetry);
            updateComms(state.comms);
            if (state.copilot !== undefined) {
                updateCopilotStatus(state.copilot.enabled);
            }
            if (state.brain) {
                updateBrainStatus(state.brain);
            }
        }
        
        // Update Brain Status
        function updateBrainStatus(brain) {
            const section = document.getElementById('brain-section');
            const badge = document.getElementById('brain-status-badge');
            const info = document.getElementById('brain-model-info');
            const fixBtn = document.getElementById('brain-fix-btn');
            
            section.style.display = 'block';
            
            if (brain.is_running) {
                badge.textContent = 'ONLINE';
                badge.className = 'badge online';
                fixBtn.style.display = 'none';
            } else {
                badge.textContent = 'OFFLINE';
                badge.className = 'badge offline';
                fixBtn.style.display = 'block';
            }
            
            info.textContent = `Model: ${brain.current_model || '---'}`;
        }
        
        function startBrain() {
            socket.emit('start_brain');
            showToast('Requesting brain start...');
        }
        
        // Update connection status
        function updateConnectionStatus(isConnected, text) {
            connected = isConnected;
            const badge = document.getElementById('status-badge');
            const statusText = document.getElementById('status-text');
            const dot = badge.querySelector('.status-dot');
            
            badge.className = `status-badge ${isConnected ? 'connected' : 'disconnected'}`;
            dot.className = `status-dot ${isConnected ? 'connected' : 'disconnected'}`;
            statusText.textContent = text || (isConnected ? 'Connected' : 'Disconnected');
            
            // Enable/disable send button
            document.getElementById('send-btn').disabled = !isConnected;
            document.getElementById('transmit-input').disabled = !isConnected;
        }
        
        // Update telemetry (frequencies)
        function updateTelemetry(telemetry) {
            if (!telemetry) return;
            
            // COM1
            if (telemetry.com1) {
                document.getElementById('com1-active').textContent = telemetry.com1.active || '---';
                document.getElementById('com1-standby').textContent = telemetry.com1.standby || '---';
            }
            
            // COM2
            if (telemetry.com2) {
                document.getElementById('com2-active').textContent = telemetry.com2.active || '---';
                document.getElementById('com2-standby').textContent = telemetry.com2.standby || '---';
            }
            
            // Transponder
            if (telemetry.transponder) {
                document.getElementById('xpdr-code').textContent = telemetry.transponder.code || '1200';
                document.getElementById('xpdr-mode').textContent = telemetry.transponder.mode || 'STBY';
            }
        }
        
        // Update communications list
        function updateComms(comms) {
            const list = document.getElementById('comms-list');
            
            if (!comms || comms.length === 0) {
                list.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">📭</div>
                        <div>No communications yet</div>
                        <div style="font-size: 0.85rem; margin-top: 8px;">
                            Connect to SAPI and start flying
                        </div>
                    </div>
                `;
                return;
            }
            
            // Build HTML for comms (newest first)
            let html = '';
            comms.slice().reverse().forEach(comm => {
                const hasAudio = comm.atc_url ? `
                    <button class="comm-play-btn" onclick="playAudio('${comm.atc_url}')">▶ Play</button>
                ` : '';
                
                html += `
                    <div class="comm-entry">
                        <div class="comm-header">
                            <span class="comm-icon">🗼</span>
                            <span class="comm-station">${comm.station_name || 'ATC'}</span>
                            <span class="comm-freq" onclick="tuneFreq('COM1', '${comm.frequency}')">${comm.frequency || ''}</span>
                        </div>
                        ${comm.incoming_message ? `<div class="comm-message pilot">"${comm.incoming_message}"</div>` : ''}
                        <div class="comm-message">${comm.outgoing_message || ''}</div>
                        ${hasAudio}
                    </div>
                `;
            });
            
            list.innerHTML = html;
        }
        
        // Channel toggle
        function toggleChannel() {
            const btn = document.getElementById('channel-toggle');
            if (currentChannel === 'COM1') {
                currentChannel = 'COM2';
                btn.textContent = 'COM2';
                btn.className = 'channel-toggle com2';
            } else {
                currentChannel = 'COM1';
                btn.textContent = 'COM1';
                btn.className = 'channel-toggle com1';
            }
        }
        
        // Send transmission
        function sendTransmission() {
            const input = document.getElementById('transmit-input');
            const message = input.value.trim();
            if (!message || !connected) return;
            
            socket.emit('send_transmission', { message, channel: currentChannel });
            input.value = '';
            showToast(`Transmitting on ${currentChannel}...`);
        }
        
        // Send quick phrase
        function sendPhrase(phrase) {
            if (!connected) return;
            socket.emit('send_transmission', { message: phrase, channel: currentChannel });
            showToast(`Transmitting: "${phrase}"`);
        }
        
        // Tune frequency (active)
        function tuneFreq(channel, freq) {
            if (freq === '---' || !freq) return;
            socket.emit('tune_frequency', { channel, frequency: freq });
            showToast(`Tuning ${channel} to ${freq}`);
        }
        
        // Tune standby
        function tuneStandby(channel, freq) {
            if (freq === '---' || !freq) return;
            // For now, same as tuneFreq - we could add a standby-specific action
            socket.emit('tune_standby', { channel, frequency: freq });
            showToast(`Setting ${channel} standby to ${freq}`);
        }
        
        // Swap frequencies
        function swapFreq(channel) {
            socket.emit('swap_frequency', { channel });
            showToast(`Swapped ${channel} frequencies`);
        }
        
        // Play audio
        function playAudio(url) {
            socket.emit('play_audio', { url });
            showToast('Playing audio...');
        }
        
        // Toast notification
        function showToast(message, type = 'info') {
            // Remove existing toasts
            document.querySelectorAll('.toast').forEach(t => t.remove());
            
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => toast.remove(), 3000);
        }
        
        // Toggle copilot
        function toggleCopilot() {
            copilotEnabled = !copilotEnabled;
            socket.emit('toggle_copilot', { enabled: copilotEnabled });
            updateCopilotStatus(copilotEnabled);
            showToast(copilotEnabled ? '🤖 Copilot enabled' : 'Copilot disabled', 
                      copilotEnabled ? 'success' : 'info');
        }
        
        // Update copilot status
        function updateCopilotStatus(enabled) {
            copilotEnabled = enabled;
            const btn = document.getElementById('copilot-toggle');
            if (enabled) {
                btn.classList.add('active');
                btn.textContent = '🤖 Copilot ON';
            } else {
                btn.classList.remove('active');
                btn.textContent = '🤖 Copilot';
            }
        }
        
        // Initialize on load
        document.addEventListener('DOMContentLoaded', () => {
            initSocket();
            
            // Periodic state refresh as backup
            setInterval(() => {
                if (socket && socket.connected) {
                    socket.emit('get_state');
                }
            }, 5000);
        });
    </script>
</body>
</html>
"""


# =============================================================================
# ComLink Server Class
# =============================================================================

class ComLinkServer:
    """
    Local web server providing browser-based interface to StratusATC.
    
    Features:
    - Real-time updates via WebSocket
    - Frequency display and tuning
    - Communications history
    - Text transmission
    """
    
    def __init__(self, port: int = 8080, host: str = "0.0.0.0"):
        """
        Initialize the ComLink server.
        
        Args:
            port: Port to listen on (default: 8080)
            host: Host to bind to (default: 0.0.0.0 for network access)
        """
        self.port = port
        self.host = host
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        # Callbacks to main app
        self.on_send_transmission: Optional[Callable[[str, str], None]] = None
        self.on_tune_frequency: Optional[Callable[[str, str], None]] = None
        self.on_tune_standby: Optional[Callable[[str, str], None]] = None
        self.on_swap_frequency: Optional[Callable[[str], None]] = None
        self.on_play_audio: Optional[Callable[[str], None]] = None
        self.on_toggle_copilot: Optional[Callable[[bool], None]] = None
        self.on_brain_start: Optional[Callable[[], None]] = None
        self.on_brain_pull: Optional[Callable[[str], None]] = None
        
        # State cache
        self._state = {
            "sapi_connected": False,
            "status_text": "Disconnected",
            "telemetry": None,
            "comms": [],
            "brain": {
                "is_running": False,
                "current_model": "---",
                "available_models": []
            }
        }
        
        # Create Flask app
        self.app = Flask(__name__)
        self.app.config['SECRET_KEY'] = 'stratusatc-comlink'
        
        # Create SocketIO
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            async_mode='threading',
            logger=False,
            engineio_logger=False
        )
        
        self._setup_routes()
        self._setup_socket_handlers()
        
        logger.info(f"ComLink server initialized on port {port}")
    
    def _setup_routes(self):
        """Setup HTTP routes."""
        
        @self.app.route('/')
        @self.app.route('/comlink')
        def comlink():
            """Serve the ComLink interface."""
            return render_template_string(COMLINK_HTML)
        
        @self.app.route('/api/state')
        def get_state():
            """Get current state as JSON."""
            return jsonify(self._state)
        
        @self.app.route('/api/health')
        def health():
            """Health check endpoint."""
            return jsonify({"status": "ok", "service": "comlink"})
    
    def _setup_socket_handlers(self):
        """Setup WebSocket event handlers."""
        
        @self.socketio.on('connect')
        def handle_connect():
            logger.debug("WebSocket client connected")
            # Send current state to new client
            emit('state_update', self._state)
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.debug("WebSocket client disconnected")
        
        @self.socketio.on('get_state')
        def handle_get_state():
            emit('state_update', self._state)
        
        @self.socketio.on('send_transmission')
        def handle_send_transmission(data):
            message = data.get('message', '')
            channel = data.get('channel', 'COM1')
            logger.info(f"WebSocket: send_transmission [{channel}] {message[:50]}...")
            if self.on_send_transmission:
                self.on_send_transmission(message, channel)
            emit('toast', {'message': 'Transmission sent', 'type': 'success'})
        
        @self.socketio.on('tune_frequency')
        def handle_tune_frequency(data):
            channel = data.get('channel', 'COM1')
            frequency = data.get('frequency', '')
            logger.info(f"WebSocket: tune_frequency {channel} -> {frequency}")
            if self.on_tune_frequency:
                self.on_tune_frequency(channel, frequency)
        
        @self.socketio.on('tune_standby')
        def handle_tune_standby(data):
            channel = data.get('channel', 'COM1')
            frequency = data.get('frequency', '')
            logger.info(f"WebSocket: tune_standby {channel} -> {frequency}")
            if self.on_tune_standby:
                self.on_tune_standby(channel, frequency)
        
        @self.socketio.on('swap_frequency')
        def handle_swap_frequency(data):
            channel = data.get('channel', 'COM1')
            logger.info(f"WebSocket: swap_frequency {channel}")
            if self.on_swap_frequency:
                self.on_swap_frequency(channel)
        
        @self.socketio.on('play_audio')
        def handle_play_audio(data):
            url = data.get('url', '')
            logger.info(f"WebSocket: play_audio {url[:50]}...")
            if self.on_play_audio:
                self.on_play_audio(url)
        
        @self.socketio.on('toggle_copilot')
        def handle_toggle_copilot(data):
            enabled = data.get('enabled', False)
            logger.info(f"WebSocket: toggle_copilot -> {enabled}")
            if self.on_toggle_copilot:
                self.on_toggle_copilot(enabled)
            self._state["copilot"] = {"enabled": enabled}
            self._broadcast_state()

        @self.socketio.on('start_brain')
        def handle_start_brain():
            logger.info("WebSocket: start_brain requested")
            if self.on_brain_start:
                self.on_brain_start()

        @self.socketio.on('pull_model')
        def handle_pull_model(data):
            model = data.get('model', '')
            logger.info(f"WebSocket: pull_model requested: {model}")
            if self.on_brain_pull:
                self.on_brain_pull(model)
    
    # =========================================================================
    # State Update Methods (called by main app)
    # =========================================================================
    
    def update_connection_status(self, connected: bool, status_text: str = ""):
        """Update SAPI connection status."""
        self._state["sapi_connected"] = connected
        self._state["status_text"] = status_text or ("Connected" if connected else "Disconnected")
        self._broadcast_state()
    
    def update_telemetry(self, telemetry: Dict[str, Any]):
        """Update telemetry data (frequencies, transponder)."""
        self._state["telemetry"] = telemetry
        self.socketio.emit('telemetry_update', telemetry)
    
    def update_comms(self, comms: List[Dict[str, Any]]):
        """Update communications history."""
        self._state["comms"] = comms
        self.socketio.emit('comms_update', {"comms": comms})
    
    def update_brain_status(self, is_running: bool, current_model: str, available_models: List[str]):
        """Update brain status info."""
        self._state["brain"] = {
            "is_running": is_running,
            "current_model": current_model,
            "available_models": available_models
        }
        self._broadcast_state()
    
    def _broadcast_state(self):
        """Broadcast full state to all connected clients."""
        self.socketio.emit('state_update', self._state)
    
    def send_toast(self, message: str, toast_type: str = "info"):
        """Send a toast notification to all clients."""
        self.socketio.emit('toast', {'message': message, 'type': toast_type})
    
    # =========================================================================
    # Server Lifecycle
    # =========================================================================
    
    def start(self):
        """Start the web server in a background thread."""
        if self._running:
            logger.warning("ComLink server already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True)
        self._thread.start()
        logger.info(f"ComLink server started at http://{self.host}:{self.port}/comlink")
    
    def _run_server(self):
        """Run the Flask server (in background thread)."""
        try:
            self.socketio.run(
                self.app, 
                host=self.host, 
                port=self.port, 
                debug=False,
                use_reloader=False,
                allow_unsafe_werkzeug=True
            )
        except Exception as e:
            logger.error(f"ComLink server error: {e}")
            self._running = False
    
    def stop(self):
        """Stop the web server."""
        self._running = False
        # Note: Flask-SocketIO doesn't have a clean shutdown method when running in thread
        logger.info("ComLink server stopped")
    
    @property
    def url(self) -> str:
        """Get the ComLink URL."""
        return f"http://localhost:{self.port}/comlink"


# =============================================================================
# Standalone Helper
# =============================================================================

def start_comlink_server(port: int = 8080) -> ComLinkServer:
    """
    Quick helper to start a ComLink server.
    
    Returns the server instance for callback registration.
    """
    server = ComLinkServer(port=port)
    server.start()
    return server


if __name__ == "__main__":
    # Test the server standalone
    logging.basicConfig(level=logging.INFO)
    print("Starting ComLink server...")
    server = start_comlink_server()
    print(f"ComLink available at: {server.url}")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        server.stop()
