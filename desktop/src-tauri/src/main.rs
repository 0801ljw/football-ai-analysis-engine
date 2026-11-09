use std::{
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};

use rand::RngCore;
use tauri::{AppHandle, Manager, Runtime, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const READY_TIMEOUT: Duration = Duration::from_secs(30);
const READY_POLL_INTERVAL: Duration = Duration::from_millis(250);
const MAIN_WINDOW_LABEL: &str = "main";

#[derive(serde::Deserialize)]
struct DoctorReport {
    #[serde(default)]
    ok: bool,
    status: Option<String>,
}

struct ChildGuard {
    child: Arc<Mutex<Option<CommandChild>>>,
}

impl ChildGuard {
    fn new(child: CommandChild) -> Self {
        Self {
            child: Arc::new(Mutex::new(Some(child))),
        }
    }

    fn kill(&self) {
        if let Ok(mut child) = self.child.lock() {
            if let Some(child) = child.take() {
                let _ = child.kill();
            }
        }
    }
}

impl Drop for ChildGuard {
    fn drop(&mut self) {
        self.kill();
    }
}

fn doctor_response_is_ready(response: ureq::Response) -> Result<bool, String> {
    let status = response.status();
    if status != 200 {
        return Err(format!("doctor returned HTTP {status}"));
    }

    let report: DoctorReport = serde_json::from_reader(response.into_reader())
        .map_err(|error| format!("doctor returned malformed JSON: {error}"))?;
    if report.ok || report.status.as_deref() == Some("ready") {
        Ok(true)
    } else {
        Err(format!(
            "doctor is not ready: ok={}, status={}",
            report.ok,
            report.status.as_deref().unwrap_or("missing")
        ))
    }
}

fn wait_for_sidecar_ready(port: u16, token: &str) -> Result<(), String> {
    let doctor_url = format!("http://127.0.0.1:{port}/api/system/doctor");
    let deadline = Instant::now() + READY_TIMEOUT;
    let mut last_error = String::from("not checked yet");

    while Instant::now() < deadline {
        match ureq::get(&doctor_url)
            .set("X-Desktop-Session", token)
            .timeout(READY_POLL_INTERVAL)
            .call()
        {
            Ok(response) => match doctor_response_is_ready(response) {
                Ok(true) => return Ok(()),
                Ok(false) => last_error = String::from("doctor is not ready"),
                Err(error) => last_error = error,
            },
            Err(ureq::Error::Status(status, _response)) => {
                last_error = format!("doctor returned HTTP {status}")
            }
            Err(error) => last_error = error.to_string(),
        }
        thread::sleep(READY_POLL_INTERVAL);
    }

    Err(format!(
        "sidecar did not become ready at {doctor_url} within {:?}: {last_error}. Restart the app and check local runtime diagnostics.",
        READY_TIMEOUT
    ))
}

fn app_data_dir<R: Runtime>(app: &AppHandle<R>) -> Result<String, String> {
    app.path()
        .app_data_dir()
        .map_err(|error| error.to_string())
        .map(|path| path.to_string_lossy().to_string())
}

fn start_sidecar<R: Runtime>(app: &AppHandle<R>) -> Result<(ChildGuard, u16, String), String> {
    let data_dir = app_data_dir(app)?;
    let mut random = [0u8; 32];
    rand::rngs::OsRng.fill_bytes(&mut random);
    let token: String = random.iter().map(|byte| format!("{byte:02x}")).collect();
    let (mut rx, mut child) = app
        .shell()
        .sidecar("pitchmind-sidecar")
        .map_err(|_| String::from("failed to create Python sidecar command"))?
        .env("WC_DESKTOP_MODE", "1")
        .env("WC_APP_DATA_DIR", data_dir)
        .env("WC_HOST", "127.0.0.1")
        .env("PORT", "0")
        .spawn()
        .map_err(|_| String::from("failed to start Python sidecar"))?;
    if child
        .write(format!("{{\"token\":\"{token}\"}}\n").as_bytes())
        .is_err()
    {
        let _ = child.kill();
        return Err(String::from("failed to initialize desktop session"));
    }
    let guard = ChildGuard::new(child);
    let deadline = Instant::now() + READY_TIMEOUT;
    while Instant::now() < deadline {
        match rx.try_recv() {
            Ok(CommandEvent::Stdout(line)) => {
                if let Ok(value) = serde_json::from_slice::<serde_json::Value>(&line) {
                    if let Some(port) = value.get("pitchmind_port").and_then(|p| p.as_u64()) {
                        if port > 0 && port <= u16::MAX as u64 {
                            // Keep draining the pipe so later diagnostics cannot block the child.
                            tauri::async_runtime::spawn(async move {
                                while rx.recv().await.is_some() {}
                            });
                            return Ok((guard, port as u16, token));
                        }
                    }
                }
            }
            Ok(CommandEvent::Terminated(_)) => {
                return Err(String::from("Python sidecar exited during startup"))
            }
            _ => thread::sleep(Duration::from_millis(20)),
        }
    }
    Err(String::from("Python sidecar bootstrap timed out"))
}

fn build_error_page(message: &str) -> String {
    let escaped = message
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;");
    format!(
        "data:text/html,<html><head><meta charset='utf-8'><title>Startup error</title></head>\
         <body><h1>Python sidecar failed to start</h1><p>{escaped}</p>\
         <p>Check the application logs in the app data directory and restart the application.</p></body></html>"
    )
}

fn navigate_main_window<R: Runtime>(app: &AppHandle<R>, result: Result<(u16, String), String>) {
    match result {
        Ok((port, token)) => {
            let origin = format!("http://127.0.0.1:{port}");
            let url = format!("{origin}/").parse().expect("valid loopback URL");
            let script = include_str!("session.js")
                .replace("__ORIGIN__", &serde_json::to_string(&origin).unwrap())
                .replace("__TOKEN__", &serde_json::to_string(&token).unwrap());
            let allowed_origin = origin.clone();
            let workbench = WebviewWindowBuilder::new(app, "workbench", WebviewUrl::External(url))
                .title("足球赛事 AI 推演引擎")
                .inner_size(1280.0, 860.0)
                .initialization_script(&script)
                .on_navigation(move |url| {
                    url.origin().ascii_serialization() == allowed_origin
                        && url.path() == "/"
                        && url.query().is_none()
                })
                .build();
            if workbench.is_ok() {
                if let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) {
                    let _ = window.destroy();
                }
            } else if let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) {
                let _ = window.eval(&format!(
                    "window.location.replace({:?});",
                    build_error_page("Unable to open desktop workbench")
                ));
            }
        }
        Err(message) => {
            if let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) {
                let _ = window.eval(&format!(
                    "window.location.replace({:?});",
                    build_error_page(&message)
                ));
            }
        }
    }
}

fn spawn_sidecar_worker<R: Runtime>(app: AppHandle<R>) {
    thread::spawn(move || {
        let result = match start_sidecar(&app) {
            Ok((guard, port, token)) => {
                app.manage(guard);
                wait_for_sidecar_ready(port, &token).map(|_| (port, token))
            }
            Err(error) => Err(error),
        };
        let app_for_ui = app.clone();
        let _ = app.run_on_main_thread(move || navigate_main_window(&app_for_ui, result));
    });
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let app_handle = app.handle().clone();
            spawn_sidecar_worker(app_handle);
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                if let Some(guard) = window.try_state::<ChildGuard>() {
                    guard.kill();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running desktop host");
}
