use anyhow::Result;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use stratus_core::atc::AtcEngine;
use stratus_core::telemetry::Telemetry;
use tracing::{error, info, warn};
use wiremock::matchers::{method, path as wiremock_path};
use wiremock::{Mock, MockServer, ResponseTemplate};

#[derive(Debug, Serialize, Deserialize)]
struct Scenario {
    meta: Meta,
    context: GlobalContext,
    steps: Vec<Step>,
}

#[derive(Debug, Serialize, Deserialize)]
struct Meta {
    id: String,
    description: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct GlobalContext {
    airport: String,
    aircraft: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct Step {
    id: u32,
    action: String,
    telemetry: StepTelemetry,
    input_voice: String,
    llm_mock_response: String,
    expectations: Vec<Expectation>,
}

#[derive(Debug, Serialize, Deserialize)]
struct StepTelemetry {
    on_ground: bool,
    ground_speed_kts: f32,
    alt_agl_ft: f32,
}

#[derive(Debug, Serialize, Deserialize)]
struct Expectation {
    #[serde(rename = "type")]
    kind: String,
    value: String,
    severity: String,
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    info!("Starting Stratus ATC Evaluation Suite");

    let mock_server = MockServer::start().await;
    info!("LLM Mock Server running at {}", mock_server.uri());

    let scenarios_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("scenarios");
    let mut passed = 0;
    let mut total = 0;

    // Run vfr_basic.yaml
    let basic_path = scenarios_dir.join("vfr_basic.yaml");
    if basic_path.exists() {
        total += 1;
        if run_scenario(&basic_path, &mock_server).await? {
            passed += 1;
        }
    }

    info!("Evaluation Summary: {}/{} scenarios passed", passed, total);

    if passed < total {
        std::process::exit(1);
    }

    Ok(())
}

async fn run_scenario(path_to_scenario: &PathBuf, server: &MockServer) -> Result<bool> {
    let content = fs::read_to_string(path_to_scenario)?;
    let scenario: Scenario = serde_yaml::from_str(&content)?;

    info!(
        "Running Scenario: {} - {}",
        scenario.meta.id, scenario.meta.description
    );

    let mut engine = AtcEngine::new(&scenario.context.aircraft, "C172")
        .with_model("eval-model")
        .with_url(server.uri());

    let mut scenario_ok = true;

    for step in scenario.steps {
        info!("Step {}: {}", step.id, step.action);

        // 0. Reset mocks for this step
        server.reset().await;

        // 1. Setup Mock for this step
        let response_json = serde_json::json!({
            "response": step.llm_mock_response,
            "done": true
        });

        Mock::given(method("POST"))
            .and(wiremock_path("/api/generate"))
            .respond_with(ResponseTemplate::new(200).set_body_json(response_json))
            .mount(server)
            .await;

        // 2. Prepare Telemetry
        let mut telemetry = Telemetry::default();
        telemetry.state.on_ground = step.telemetry.on_ground;
        telemetry.speed.ground_speed_mps = step.telemetry.ground_speed_kts / 1.94384;
        telemetry.position.altitude_agl_m = (step.telemetry.alt_agl_ft / 3.28084) as f64;

        // 3. Process Input (if any)
        if !step.input_voice.is_empty() {
            match engine
                .process_pilot_input(&step.input_voice, &telemetry)
                .await
            {
                Ok((response, _)) => {
                    let state_debug = format!("{:?}", engine.state());
                    info!("  Engine State: {}", state_debug);

                    for exp in step.expectations {
                        match exp.kind.as_str() {
                            "regex" => {
                                let re = Regex::new(&exp.value)?;
                                if !re.is_match(&response.to_uppercase()) {
                                    error!(
                                        "  FAIL: [{}] Regex '{}' not found in response: '{}'",
                                        exp.severity, exp.value, response
                                    );
                                    scenario_ok = false;
                                } else {
                                    info!("  PASS: Regex '{}' matched", exp.value);
                                }
                            }
                            "state" => {
                                if state_debug != exp.value {
                                    error!(
                                        "  FAIL: [{}] Expected state {:?}, got {:?}",
                                        exp.severity, exp.value, state_debug
                                    );
                                    scenario_ok = false;
                                } else {
                                    info!("  PASS: State is {:?}", state_debug);
                                }
                            }
                            _ => warn!("  Unknown expectation type: {}", exp.kind),
                        }
                    }
                }
                Err(e) => {
                    error!("  ERROR: LLM request failed: {:?}", e);
                    scenario_ok = false;
                }
            }
        } else {
            // No input, just update state and verify
            engine.update_state(&telemetry);
            let state_debug = format!("{:?}", engine.state());
            info!("  Engine State Updated: {}", state_debug);
            for exp in step.expectations {
                if exp.kind == "state" {
                    if state_debug != exp.value {
                        error!(
                            "  FAIL: [{}] Expected state {:?}, got {:?}",
                            exp.severity, exp.value, state_debug
                        );
                        scenario_ok = false;
                    } else {
                        info!("  PASS: State is {:?}", state_debug);
                    }
                }
            }
        }
    }

    Ok(scenario_ok)
}
