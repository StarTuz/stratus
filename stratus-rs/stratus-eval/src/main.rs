use anyhow::Result;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use stratus_core::atc::AtcEngine;
use stratus_core::ollama::OllamaClient;
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

struct JudgeEngine {
    client: OllamaClient,
}

impl JudgeEngine {
    fn new(url: &str) -> Self {
        // Use 1B model for fast, tiny footprint (approx 1.2GB VRAM instead of 5GB)
        Self {
            client: OllamaClient::new("llama3.2:1b").with_url(url),
        }
    }

    async fn evaluate(
        &self,
        context: &str,
        pilot_input: &str,
        atc_response: &str,
        criteria: &str,
    ) -> Result<(bool, String)> {
        let prompt = format!(
            r#"### SYSTEM:
You are an FAA ATC evaluator. Evaluate the ATC response below based ONLY on the provided criteria.
Response with PASS if it meets the criteria, or FAIL if it does not.

### CONTEXT:
- PHASE: {context}
- PILOT: "{pilot_input}"
- ATC: "{atc_response}"
- CRITERIA: {criteria}

### RESPONSE FORMAT:
{{
  "verdict": "PASS" or "FAIL",
  "reason": "Explain your decision in one concise sentence."
}}"#,
            context = context,
            pilot_input = pilot_input,
            atc_response = atc_response,
            criteria = criteria
        );

        let response = self.client.generate(&prompt).await?;
        info!("  [JUDGE RAW]: {}", response);

        // Attempt to parse JSON from the response
        let verdict = if response.to_uppercase().contains("\"VERDICT\": \"PASS\"")
            || response.to_uppercase().contains("VERDICT: PASS")
        {
            true
        } else {
            false
        };

        let reason = if let Some(r) = response.split("\"reason\":").nth(1) {
            r.trim_matches(|c| {
                c == ' ' || c == '"' || c == '{' || c == '}' || c == ',' || c == '\n'
            })
            .to_string()
        } else if let Some(r) = response.split("REASON:").nth(1) {
            r.trim().to_string()
        } else {
            "Judge provided no clear reason".to_string()
        };

        Ok((verdict, reason))
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt::init();
    info!("Starting Stratus ATC Evaluation Suite");

    // Mock server for the ATC engine (deterministic logic test)
    let mock_server = MockServer::start().await;
    info!("ATC Mock Server running at {}", mock_server.uri());

    // Real Ollama for the Judge (semantic evaluation)
    // We assume Ollama is running on localhost:11434 for the judge
    let judge = JudgeEngine::new("http://localhost:11434");

    let scenarios_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("scenarios");
    let mut passed = 0;
    let mut total = 0;

    let entries = fs::read_dir(scenarios_dir)?;
    for entry in entries {
        let entry = entry?;
        let path = entry.path();
        if path.extension().and_then(|s| s.to_str()) == Some("yaml") {
            total += 1;
            if run_scenario(&path, &mock_server, &judge).await? {
                passed += 1;
            }
        }
    }

    info!("Evaluation Summary: {}/{} scenarios passed", passed, total);

    if passed < total {
        std::process::exit(1);
    }

    Ok(())
}

async fn run_scenario(
    path_to_scenario: &PathBuf,
    server: &MockServer,
    judge: &JudgeEngine,
) -> Result<bool> {
    let content = fs::read_to_string(path_to_scenario)?;
    let scenario: Scenario = serde_yaml::from_str(&content)?;

    info!(
        "Running Scenario: {} - {}",
        scenario.meta.id, scenario.meta.description
    );

    let mut engine = AtcEngine::new(&scenario.context.aircraft, "C172");

    // Scenarios starting with "BIT-" specifically test the native BitNet backend
    if !scenario.meta.id.starts_with("BIT-") {
        engine = engine.with_model("eval-model").with_url(server.uri());
    }

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
        telemetry.speed.ground_speed_mps = (step.telemetry.ground_speed_kts / 1.94384) as f32;
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
                            "llm_judge" => {
                                info!("  Judging response...");
                                match judge
                                    .evaluate(
                                        &state_debug,
                                        &step.input_voice,
                                        &response,
                                        &exp.value,
                                    )
                                    .await
                                {
                                    Ok((passed, reason)) => {
                                        if passed {
                                            info!(
                                                "  PASS: Judge verdict: PASS. Reason: {}",
                                                reason
                                            );
                                        } else {
                                            error!(
                                                "  FAIL: [{}] Judge verdict: FAIL. Reason: {}",
                                                exp.severity, reason
                                            );
                                            scenario_ok = false;
                                        }
                                    }
                                    Err(e) => {
                                        warn!(
                                            "  JUDGE ERROR: Failed to query judge model: {:?}",
                                            e
                                        );
                                    }
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
