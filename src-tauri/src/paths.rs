//! Filesystem layout for a managed (packaged) run.
//!
//! Everything the app writes lives under `%APPDATA%\Flow` so an uninstall can
//! remove the program without touching the user's data.

use std::fs;
use std::io;
use std::path::PathBuf;

pub struct FlowPaths {
    pub root: PathBuf,
    pub logs: PathBuf,
    pub data: PathBuf,
    pub pgdata: PathBuf,
}

impl FlowPaths {
    /// Resolve the layout from `%APPDATA%`, falling back to the working
    /// directory when the variable is unavailable (non-Windows builds/tests).
    pub fn resolve() -> FlowPaths {
        let root = std::env::var_os("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| PathBuf::from("."))
            .join("Flow");
        FlowPaths {
            logs: root.join("logs"),
            data: root.join("data"),
            pgdata: root.join("pgdata"),
            root,
        }
    }

    pub fn ensure(&self) -> io::Result<()> {
        fs::create_dir_all(&self.root)?;
        fs::create_dir_all(&self.logs)?;
        fs::create_dir_all(&self.data)?;
        Ok(())
    }

    pub fn startup_log(&self) -> PathBuf {
        self.logs.join("startup.log")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn layout_is_anchored_on_the_flow_folder() {
        let paths = FlowPaths::resolve();
        assert!(paths.root.ends_with("Flow"));
        assert_eq!(paths.logs, paths.root.join("logs"));
        assert_eq!(paths.data, paths.root.join("data"));
        assert_eq!(paths.pgdata, paths.root.join("pgdata"));
        assert!(paths.startup_log().ends_with("startup.log"));
    }
}
