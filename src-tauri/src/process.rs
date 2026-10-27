//! Backend supervisor: PostgreSQL -> API -> health gate.
//!
//! Only active in a managed (packaged) run. `FLOW_MANAGED=1` forces it on for
//! local testing; `FLOW_SKIP_MANAGER=1` disables it. Debug builds skip the
//! manager by default so `npm run tauri dev` keeps using `start-flow.bat`.

use std::fs::{self, OpenOptions};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use crate::paths::FlowPaths;
use crate::ports;

const HEALTH_TIMEOUT: Duration = Duration::from_secs(60);
const PG_START_TIMEOUT: Duration = Duration::from_secs(30);

pub fn manager_enabled() -> bool {
    if std::env::var_os("FLOW_SKIP_MANAGER").is_some() {
        return false;
    }
    if std::env::var_os("FLOW_MANAGED").is_some() {
        return true;
    }
    !cfg!(debug_assertions)
}

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

pub fn log_line(paths: &FlowPaths, message: &str) {
    let line = format!("{} {message}\n", now_secs());
    if let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(paths.startup_log())
    {
        let _ = file.write_all(line.as_bytes());
    }
    eprintln!("[flow] {message}");
}

/// Persist a startup failure so support can see why the app has no data.
pub fn record_failure(message: &str) {
    let paths = FlowPaths::resolve();
    let _ = paths.ensure();
    log_line(&paths, &format!("ERROR {message}"));
}

pub struct Backend {
    api: Option<Child>,
    postgres: Option<Child>,
    pg_bin: Option<PathBuf>,
    pgdata: PathBuf,
    pg_port: u16,
    api_port: u16,
    job: Option<Job>,
    paths: FlowPaths,
}

impl Backend {
    pub fn start() -> Result<Backend, String> {
        let paths = FlowPaths::resolve();
        paths
            .ensure()
            .map_err(|e| format!("cannot create {}: {e}", paths.root.display()))?;

        let (api_port, pg_port) =
            ports::pick_ports().ok_or_else(|| "no free port found near 8001/5433".to_string())?;
        log_line(
            &paths,
            &format!("starting: api_port={api_port} postgres_port={pg_port}"),
        );

        let job = Job::new();
        if job.is_none() {
            log_line(&paths, "warning: job object unavailable; children may outlive Flow");
        }

        let (database_url, pg_bin, postgres) =
            match std::env::var("DATABASE_URL") {
                Ok(url) if !url.trim().is_empty() => {
                    log_line(&paths, "using DATABASE_URL from the environment");
                    (url, None, None)
                }
                _ => {
                    let (url, bin, child) = start_postgres(&paths, pg_port)?;
                    (url, Some(bin), Some(child))
                }
            };

        let (program, args, cwd) = api_launch(api_port);
        log_line(
            &paths,
            &format!("api command: {} {}", program.display(), args.join(" ")),
        );

        let mut command = Command::new(&program);
        command
            .args(&args)
            .current_dir(&cwd)
            .env("FLOW_DATA_DIR", &paths.data)
            .env("DATABASE_URL", &database_url)
            .env("API_HOST", "127.0.0.1")
            .env("API_PORT", api_port.to_string())
            .env("ENVIRONMENT", "production")
            .env("FLOW_BOOTSTRAP", "1")
            .env(
                "CORS_ORIGINS",
                "[\"http://tauri.localhost\",\"http://localhost:1420\",\"http://127.0.0.1:1420\"]",
            );

        let api = spawn_logged(&mut command, &paths.logs.join("api.log"))
            .map_err(|e| format!("cannot start the API: {e}"))?;

        if let Some(job) = &job {
            if !job.assign(&api) {
                log_line(&paths, "warning: could not attach the API to the job object");
            }
            if let Some(child) = &postgres {
                if !job.assign(child) {
                    log_line(&paths, "warning: could not attach PostgreSQL to the job object");
                }
            }
        }

        wait_for_health(&paths, api_port)?;
        log_line(&paths, "ready");

        Ok(Backend {
            api: Some(api),
            postgres,
            pg_bin,
            pgdata: paths.pgdata.clone(),
            pg_port,
            api_port,
            job,
            paths,
        })
    }

    pub fn stop(&mut self) {
        if let Some(mut child) = self.api.take() {
            let _ = child.kill();
            let _ = child.wait();
            log_line(&self.paths, "api stopped");
        }

        if self.postgres.is_some() {
            if let Some(bin) = &self.pg_bin {
                let ok = run_status(
                    &bin.join("pg_ctl.exe"),
                    &[
                        "stop".into(),
                        "-D".into(),
                        self.pgdata.display().to_string(),
                        "-m".into(),
                        "fast".into(),
                        "-w".into(),
                    ],
                );
                log_line(&self.paths, &format!("postgres stop requested (ok={ok})"));
            }
            if let Some(mut child) = self.postgres.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }

        self.job.take();
        log_line(&self.paths, "shutdown complete");
    }

    #[allow(dead_code)]
    pub fn api_port(&self) -> u16 {
        self.api_port
    }

    #[allow(dead_code)]
    pub fn pg_port(&self) -> u16 {
        self.pg_port
    }
}

impl Drop for Backend {
    fn drop(&mut self) {
        self.stop();
    }
}

// â”€â”€ PostgreSQL â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

fn pg_bin_dir() -> Option<PathBuf> {
    if let Some(dir) = std::env::var_os("FLOW_PG_BIN") {
        return Some(PathBuf::from(dir));
    }
    let mut candidates = Vec::new();
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            candidates.push(dir.join("resources").join("postgres").join("bin"));
            candidates.push(dir.join("postgres").join("bin"));
        }
    }
    for version in ["17", "18"] {
        candidates.push(PathBuf::from(format!(
            "C:\\Program Files\\PostgreSQL\\{version}\\bin"
        )));
    }
    candidates
        .into_iter()
        .find(|path| path.join("postgres.exe").exists())
}

fn start_postgres(paths: &FlowPaths, port: u16) -> Result<(String, PathBuf, Child), String> {
    let bin = pg_bin_dir().ok_or_else(|| {
        "PostgreSQL binaries not found (set FLOW_PG_BIN or install the bundled copy)".to_string()
    })?;

    let password = db_password(paths).map_err(|e| format!("cannot store the database password: {e}"))?;

    if !paths.pgdata.join("PG_VERSION").exists() {
        fs::create_dir_all(&paths.pgdata)
            .map_err(|e| format!("cannot create {}: {e}", paths.pgdata.display()))?;
        let pwfile = paths.root.join("pg_pw.tmp");
        fs::write(&pwfile, &password).map_err(|e| format!("cannot write {pwfile:?}: {e}"))?;
        let args = vec![
            "-D".to_string(),
            paths.pgdata.display().to_string(),
            "-U".to_string(),
            "postgres".to_string(),
            "--auth-local=trust".to_string(),
            "--auth-host=scram-sha-256".to_string(),
            "--pwfile".to_string(),
            pwfile.display().to_string(),
            "-E".to_string(),
            "UTF8".to_string(),
        ];
        let result = run_status(&bin.join("initdb.exe"), &args);
        let _ = fs::remove_file(&pwfile);
        if !result {
            return Err("initdb failed (see logs/startup.log)".to_string());
        }
        log_line(paths, "initialised a new PostgreSQL cluster");
    }

    let mut command = Command::new(bin.join("postgres.exe"));
    let pg_args = vec![
        "-D".to_string(),
        paths.pgdata.display().to_string(),
        "-p".to_string(),
        port.to_string(),
        "-h".to_string(),
        "127.0.0.1".to_string(),
    ];
    command
        .args(&pg_args)
        .env("PGPASSWORD", &password);
    let child = spawn_logged(&mut command, &paths.logs.join("postgres.log"))
        .map_err(|e| format!("cannot start PostgreSQL: {e}"))?;

    if !wait_for_port(port, PG_START_TIMEOUT) {
        return Err(format!(
            "PostgreSQL did not accept connections on 127.0.0.1:{port}"
        ));
    }

    // Create the application database on first run; an existing one is fine.
    let createdb = run_status_env(
        &bin.join("createdb.exe"),
        &[
            "-h".into(),
            "127.0.0.1".into(),
            "-p".into(),
            port.to_string(),
            "-U".into(),
            "postgres".into(),
            "flowdb".into(),
        ],
        &[("PGPASSWORD", password.as_str())],
    );
    if !createdb {
        log_line(paths, "createdb reported a problem (the database may already exist)");
    }

    let url = format!(
        "postgresql+psycopg2://postgres:{password}@127.0.0.1:{port}/flowdb"
    );
    Ok((url, bin, child))
}

fn db_password(paths: &FlowPaths) -> std::io::Result<String> {
    let file = paths.data.join("db_password");
    if let Ok(existing) = fs::read_to_string(&file) {
        let trimmed = existing.trim();
        if !trimmed.is_empty() {
            return Ok(trimmed.to_string());
        }
    }
    let password = generate_password();
    fs::write(&file, &password)?;
    Ok(password)
}

fn generate_password() -> String {
    use std::collections::hash_map::RandomState;
    use std::hash::{BuildHasher, Hasher};

    let mut out = String::with_capacity(32);
    for _ in 0..2 {
        let mut hasher = RandomState::new().build_hasher();
        hasher.write_u128(
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0),
        );
        out.push_str(&format!("{:016x}", hasher.finish()));
    }
    out
}

// â”€â”€ API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

/// Bundled sidecar first (D3), then the development Python entry point.
fn api_launch(port: u16) -> (PathBuf, Vec<String>, PathBuf) {
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            let candidates = [
                dir.join("resources").join("api").join("flow-api.exe"),
                dir.join("api").join("flow-api.exe"),
            ];
            for candidate in candidates {
                if candidate.exists() {
                    let cwd = candidate
                        .parent()
                        .map(Path::to_path_buf)
                        .unwrap_or_else(|| dir.to_path_buf());
                    return (candidate, Vec::new(), cwd);
                }
            }
        }
    }

    let project_root = Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| PathBuf::from("."));
    (
        PathBuf::from("python"),
        vec![
            "-m".into(),
            "uvicorn".into(),
            "api.main:app".into(),
            "--host".into(),
            "127.0.0.1".into(),
            "--port".into(),
            port.to_string(),
        ],
        project_root,
    )
}

fn spawn_logged(command: &mut Command, log: &Path) -> std::io::Result<Child> {
    let out = OpenOptions::new().create(true).append(true).open(log)?;
    let err = out.try_clone()?;
    command
        .stdin(Stdio::null())
        .stdout(Stdio::from(out))
        .stderr(Stdio::from(err));
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    command.spawn()
}

fn wait_for_health(paths: &FlowPaths, port: u16) -> Result<(), String> {
    let started = Instant::now();
    while started.elapsed() < HEALTH_TIMEOUT {
        if http_health_ok(port) {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    log_line(paths, &format!("api health check timed out on port {port}"));
    Err(format!(
        "the API did not become healthy on 127.0.0.1:{port} within {}s",
        HEALTH_TIMEOUT.as_secs()
    ))
}

fn http_health_ok(port: u16) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(400)) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(1_500)));
    if stream
        .write_all(b"GET /api/health HTTP/1.0\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut buffer = [0u8; 64];
    match stream.read(&mut buffer) {
        Ok(read) => String::from_utf8_lossy(&buffer[..read]).contains("200"),
        Err(_) => false,
    }
}

fn wait_for_port(port: u16, timeout: Duration) -> bool {
    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let started = Instant::now();
    while started.elapsed() < timeout {
        if TcpStream::connect_timeout(&addr, Duration::from_millis(300)).is_ok() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(250));
    }
    false
}

// â”€â”€ Child processes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

fn run_status(program: &Path, args: &[String]) -> bool {
    run_status_env(program, args, &[])
}

fn run_status_env(program: &Path, args: &[String], envs: &[(&str, &str)]) -> bool {
    let mut command = Command::new(program);
    command.args(args);
    for (key, value) in envs {
        command.env(key, value);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }
    match command.output() {
        Ok(output) => {
            if !output.status.success() {
                let stderr = String::from_utf8_lossy(&output.stderr);
                eprintln!("[flow] {} failed: {stderr}", program.display());
            }
            output.status.success()
        }
        Err(err) => {
            eprintln!("[flow] cannot run {}: {err}", program.display());
            false
        }
    }
}

// â”€â”€ Job object: kill children if Flow exits unexpectedly â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

#[cfg(windows)]
mod job_impl {
    use std::os::windows::io::AsRawHandle;
    use std::process::Child;

    use windows_sys::Win32::Foundation::{CloseHandle, HANDLE};
    use windows_sys::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, SetInformationJobObject,
        JobObjectExtendedLimitInformation, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };

    pub struct Job(HANDLE);

    // The handle is only used from the managing thread and is closed on drop.
    unsafe impl Send for Job {}

    impl Job {
        pub fn new() -> Option<Job> {
            unsafe {
                let handle = CreateJobObjectW(std::ptr::null(), std::ptr::null());
                if handle.is_null() {
                    return None;
                }
                let mut info: JOBOBJECT_EXTENDED_LIMIT_INFORMATION = std::mem::zeroed();
                info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
                let ok = SetInformationJobObject(
                    handle,
                    JobObjectExtendedLimitInformation,
                    &info as *const _ as *const core::ffi::c_void,
                    std::mem::size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
                );
                if ok == 0 {
                    let _ = CloseHandle(handle);
                    return None;
                }
                Some(Job(handle))
            }
        }

        pub fn assign(&self, child: &Child) -> bool {
            unsafe { AssignProcessToJobObject(self.0, child.as_raw_handle() as HANDLE) != 0 }
        }
    }

    impl Drop for Job {
        fn drop(&mut self) {
            unsafe {
                let _ = CloseHandle(self.0);
            }
        }
    }
}

#[cfg(windows)]
use job_impl::Job;

#[cfg(not(windows))]
struct Job;

#[cfg(not(windows))]
impl Job {
    fn new() -> Option<Job> {
        None
    }
    fn assign(&self, _child: &Child) -> bool {
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generated_passwords_are_long_and_unique() {
        let first = generate_password();
        let second = generate_password();
        assert_eq!(first.len(), 32);
        assert_ne!(first, second);
    }

    #[test]
    fn debug_builds_skip_the_manager_unless_forced() {
        // Tests run without FLOW_MANAGED / FLOW_SKIP_MANAGER set.
        if std::env::var_os("FLOW_MANAGED").is_none()
            && std::env::var_os("FLOW_SKIP_MANAGER").is_none()
        {
            assert!(!manager_enabled());
        }
    }

    #[test]
    fn health_check_fails_on_a_closed_port() {
        let listener = std::net::TcpListener::bind(("127.0.0.1", 0)).expect("bind");
        let port = listener.local_addr().expect("addr").port();
        drop(listener);
        assert!(!http_health_ok(port));
    }
}
