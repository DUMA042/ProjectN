mod paths;
mod ports;
mod process;

use std::sync::Mutex;

use serde::Serialize;
use tauri::Manager;

/// Holds the supervised PostgreSQL + API processes for the lifetime of the app.
struct BackendState(Mutex<Option<process::Backend>>);

/// What the frontend needs to know about the managed backend.
#[derive(Clone, Serialize)]
#[serde(tag = "state", rename_all = "lowercase")]
enum BackendPhase {
    /// The manager is not used (debug/dev builds).
    Disabled,
    Starting,
    Ready { api_port: u16, pg_port: u16 },
    Failed { message: String },
}

struct ManagerStatus(Mutex<BackendPhase>);

fn publish_status(app: &tauri::AppHandle, phase: BackendPhase) {
    if let Some(state) = app.try_state::<ManagerStatus>() {
        if let Ok(mut slot) = state.0.lock() {
            *slot = phase;
        }
    }
}

#[tauri::command]
fn backend_status(state: tauri::State<'_, ManagerStatus>) -> BackendPhase {
    match state.0.lock() {
        Ok(slot) => slot.clone(),
        Err(_) => BackendPhase::Failed {
            message: "The service status is unavailable.".to_string(),
        },
    }
}

/// Write download bytes to a path chosen by the user in the save dialog.
#[tauri::command]
fn save_download(path: String, data_base64: String) -> Result<(), String> {
    use base64::Engine as _;

    if path.trim().is_empty() {
        return Err("No destination path was chosen.".to_string());
    }
    let bytes = base64::engine::general_purpose::STANDARD
        .decode(data_base64.as_bytes())
        .map_err(|e| format!("Could not decode the file data: {e}"))?;
    std::fs::write(&path, &bytes).map_err(|e| format!("Could not save the file: {e}"))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let mut builder = tauri::Builder::default();

    // A second launch focuses the existing window instead of starting a rival
    // stack against the same data directory.
    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }));
    }

    let app = builder
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendState(Mutex::new(None)))
        .manage(ManagerStatus(Mutex::new(BackendPhase::Disabled)))
        .invoke_handler(tauri::generate_handler![backend_status, save_download])
        .setup(|app| {
            if process::manager_enabled() {
                publish_status(app.handle(), BackendPhase::Starting);

                let resource_dir = app.path().resource_dir().ok();
                // Start off the UI thread so the window appears immediately;
                // failures are published and surface on the startup screen.
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    match process::Backend::start(resource_dir.as_deref()) {
                        Ok(backend) => {
                            let phase = BackendPhase::Ready {
                                api_port: backend.api_port(),
                                pg_port: backend.pg_port(),
                            };
                            if let Some(state) = handle.try_state::<BackendState>() {
                                if let Ok(mut slot) = state.0.lock() {
                                    *slot = Some(backend);
                                }
                            }
                            publish_status(&handle, phase);
                        }
                        Err(err) => {
                            process::record_failure(&err);
                            publish_status(
                                &handle,
                                BackendPhase::Failed { message: err },
                            );
                        }
                    }
                });
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Flow");

    app.run(|app_handle, event| {
        if matches!(event, tauri::RunEvent::Exit) {
            if let Some(state) = app_handle.try_state::<BackendState>() {
                if let Ok(mut slot) = state.0.lock() {
                    if let Some(mut backend) = slot.take() {
                        backend.stop();
                    }
                }
            }
        }
    });
}

/// Headless self-check: start the managed PostgreSQL + API stack, print the
/// chosen ports, then stop everything. Exits 0 on success, 1 on failure.
pub fn backend_check() -> i32 {
    match process::Backend::start(None) {
        Ok(mut backend) => {
            eprintln!(
                "[flow] backend ready: api_port={} postgres_port={}",
                backend.api_port(),
                backend.pg_port()
            );
            backend.stop();
            eprintln!("[flow] backend check passed");
            0
        }
        Err(err) => {
            process::record_failure(&err);
            eprintln!("[flow] backend check failed: {err}");
            1
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ready_status_reports_both_ports() {
        let value = serde_json::to_value(BackendPhase::Ready {
            api_port: 8001,
            pg_port: 5433,
        })
        .expect("serialize");
        assert_eq!(value["state"], "ready");
        assert_eq!(value["api_port"], 8001);
        assert_eq!(value["pg_port"], 5433);
    }

    #[test]
    fn failed_status_carries_the_message() {
        let value = serde_json::to_value(BackendPhase::Failed {
            message: "boom".to_string(),
        })
        .expect("serialize");
        assert_eq!(value["state"], "failed");
        assert_eq!(value["message"], "boom");
    }
}
