mod paths;
mod ports;
mod process;

use std::sync::Mutex;

use tauri::Manager;

/// Holds the supervised PostgreSQL + API processes for the lifetime of the app.
struct BackendState(Mutex<Option<process::Backend>>);

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
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .manage(BackendState(Mutex::new(None)))
        .setup(|app| {
            if process::manager_enabled() {
                let resource_dir = app.path().resource_dir().ok();
                // Start off the UI thread so the window appears immediately;
                // failures are logged and surface as the offline banner.
                let handle = app.handle().clone();
                std::thread::spawn(move || {
                    match process::Backend::start(resource_dir.as_deref()) {
                        Ok(backend) => {
                            if let Some(state) = handle.try_state::<BackendState>() {
                                if let Ok(mut slot) = state.0.lock() {
                                    *slot = Some(backend);
                                }
                            }
                        }
                        Err(err) => process::record_failure(&err),
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
