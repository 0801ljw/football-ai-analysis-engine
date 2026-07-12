use std::{
    net::TcpListener,
    sync::{Arc, Mutex},
    thread,
    time::{Duration, Instant},
};

use tauri::{AppHandle, Manager, Runtime};
use tauri_plugin_shell::process::CommandChild;
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

fn choose_free_localhost_port() -> Result<u16, String> {
    let listener = TcpListener::bind("127.0.0.1:0").map_err(|error| error.to_string())?;
    let port = listener
        .local_addr()
        .map_err(|error| error.to_string())?
        .port();
    drop(listener);
    Ok(port)
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

fn wait_for_sidecar_ready(port: u16) -> Result<(), String> {
    let doctor_url = format!("http://127.0.0.1:{port}/api/system/doctor");
    let deadline = Instant::now() + READY_TIMEOUT;
    let mut last_error = String::from("not checked yet");

    while Instant::now() < deadline {
        match ureq::get(&doctor_url).timeout(READY_POLL_INTERVAL).call() {
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
        "sidecar did not become ready at {doctor_url} within {:?}: {last_error}. Port selection uses a beta bind/drop handoff; restart the app if the local port was taken during startup.",
        READY_TIMEOUT
    ))
}

fn app_data_dir<R: Runtime>(app: &AppHandle<R>) -> Result<String, String> {
    app.path()
        .app_data_dir()
        .map_err(|error| error.to_string())
        .map(|path| path.to_string_lossy().to_string())
}

fn start_sidecar<R: Runtime>(app: &AppHandle<R>) -> Result<(ChildGuard, u16), String> {
    let port = choose_free_localhost_port()?;
    let data_dir = app_data_dir(app)?;
    let port_string = port.to_string();

    let (_rx, child) = app
        .shell()
        .sidecar("pitchmind-sidecar")
        .map_err(|error| format!("failed to create Python sidecar command: {error}"))?
        .env("WC_DESKTOP_MODE", "1")
        .env("WC_APP_DATA_DIR", data_dir)
        .env("WC_HOST", "127.0.0.1")
        .env("PORT", port_string)
        .spawn()
        .map_err(|error| format!("failed to start Python sidecar: {error}"))?;

    Ok((ChildGuard::new(child), port))
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

fn navigate_main_window<R: Runtime>(app: &AppHandle<R>, result: Result<u16, String>) {
    if let Some(window) = app.get_webview_window(MAIN_WINDOW_LABEL) {
        let url = match result {
            Ok(port) => format!("http://127.0.0.1:{port}/"),
            Err(message) => build_error_page(&message),
        };
        let _ = window.eval(&format!("window.location.replace({:?});", url));
    }
}

fn spawn_sidecar_worker<R: Runtime>(app: AppHandle<R>) {
    thread::spawn(move || {
        let result = match start_sidecar(&app) {
            Ok((guard, port)) => {
                app.manage(guard);
                wait_for_sidecar_ready(port).map(|_| port)
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
