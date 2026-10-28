#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    if std::env::args().any(|arg| arg == "--backend-check") {
        std::process::exit(flow_desktop_lib::backend_check());
    }
    flow_desktop_lib::run()
}
