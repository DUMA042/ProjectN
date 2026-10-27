//! Port selection: start at the documented defaults and walk upward when a
//! port is already in use (another Flow build, another PostgreSQL, ...).

use std::net::TcpListener;

pub const DEFAULT_API_PORT: u16 = 8001;
pub const DEFAULT_PG_PORT: u16 = 5433;

const MAX_ATTEMPTS: u16 = 50;

pub fn is_port_free(port: u16) -> bool {
    TcpListener::bind(("127.0.0.1", port)).is_ok()
}

/// First free port at or after `start`, or `None` if the window is exhausted.
pub fn next_free_port(start: u16) -> Option<u16> {
    (0..MAX_ATTEMPTS)
        .filter_map(|offset| start.checked_add(offset))
        .find(|port| is_port_free(*port))
}

/// Pick the API and PostgreSQL ports. They are chosen independently so the
/// documented defaults are kept whenever possible.
pub fn pick_ports() -> Option<(u16, u16)> {
    let api = next_free_port(DEFAULT_API_PORT)?;
    let pg = next_free_port(DEFAULT_PG_PORT)?;
    Some((api, pg))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_bound_port_is_reported_as_busy() {
        let listener = TcpListener::bind(("127.0.0.1", 0)).expect("bind");
        let port = listener.local_addr().expect("addr").port();
        assert!(!is_port_free(port));
    }

    #[test]
    fn next_free_port_skips_a_busy_port() {
        let listener = TcpListener::bind(("127.0.0.1", 0)).expect("bind");
        let busy = listener.local_addr().expect("addr").port();
        let found = next_free_port(busy).expect("a port");
        assert!(found > busy);
    }

    #[test]
    fn defaults_are_the_documented_ports() {
        assert_eq!(DEFAULT_API_PORT, 8001);
        assert_eq!(DEFAULT_PG_PORT, 5433);
    }
}
