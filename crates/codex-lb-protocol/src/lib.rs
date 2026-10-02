//! Versioned local IPC contract between the Python control plane and Rust egress worker.
//!
//! This crate intentionally has no async runtime or networking dependencies. Wire
//! compatibility can therefore be tested independently from either implementation.
//!
//! Commands are newline-terminated JSON. A command that carries a request body or
//! a websocket message declares its size in `payload_bytes`, and exactly that many
//! raw bytes follow the newline. Bulk payloads are therefore never escaped into
//! JSON or base64 on the way to the worker.

use serde::{Deserialize, Serialize};

pub const PROTOCOL_VERSION: u16 = 1;
pub const CAPABILITIES: &[&str] = &[
    "failure_provenance_v1",
    "framed_payload_v1",
    "http",
    "http2_profile_v1",
    "http_compact_collect_v1",
    "http_compact_sse_v1",
    "http_sse_v1",
    "http_responses_events_v1",
    "http_responses_completion_v1",
    "websocket",
    "websocket_responses_events_v1",
    "websocket_responses_routing_v1",
    "websocket_send_ack",
];

#[derive(Deserialize, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum NativeCommand {
    ClientHello {
        min_protocol_version: u16,
        max_protocol_version: u16,
    },
    Request(NativeRequest),
    WebsocketConnect(NativeWebSocketRequest),
    WebsocketSendText {
        request_id: String,
        command_id: String,
        payload_bytes: usize,
    },
    WebsocketSendBinary {
        request_id: String,
        command_id: String,
        payload_bytes: usize,
    },
    WebsocketClose {
        request_id: String,
        command_id: String,
        code: u16,
        reason: String,
    },
    Cancel {
        request_id: String,
    },
}

impl NativeCommand {
    /// Number of raw payload bytes that follow this command's JSON line.
    pub fn payload_bytes(&self) -> usize {
        match self {
            Self::Request(request) => request.payload_bytes.unwrap_or(0),
            Self::WebsocketSendText { payload_bytes, .. }
            | Self::WebsocketSendBinary { payload_bytes, .. } => *payload_bytes,
            Self::ClientHello { .. }
            | Self::WebsocketConnect(_)
            | Self::WebsocketClose { .. }
            | Self::Cancel { .. } => 0,
        }
    }
}

#[derive(Deserialize, Serialize)]
pub struct NativeRequest {
    pub request_id: String,
    pub method: String,
    pub url: String,
    pub headers: Vec<(String, String)>,
    /// Size of the raw request body that follows the command; absent for a
    /// request without a body.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub payload_bytes: Option<usize>,
    pub timeout_ms: Option<u64>,
    pub connect_timeout_ms: Option<u64>,
    pub proxy_url: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub sse: Option<NativeSseOptions>,
}

#[derive(Clone, Copy, Deserialize, Serialize)]
pub struct NativeSseOptions {
    pub idle_timeout_ms: u64,
    pub max_event_bytes: usize,
    #[serde(default)]
    pub content_type_aware: bool,
    #[serde(default)]
    pub collect_compact: bool,
    #[serde(default)]
    pub interpret_responses: bool,
}

#[derive(Deserialize, Serialize)]
pub struct NativeWebSocketRequest {
    pub request_id: String,
    pub url: String,
    pub headers: Vec<(String, String)>,
    pub connect_timeout_ms: u64,
    pub max_message_bytes: usize,
    pub ping_interval_ms: Option<u64>,
    pub ping_timeout_ms: Option<u64>,
    pub proxy_url: Option<String>,
    #[serde(default, skip_serializing_if = "is_false")]
    pub interpret_responses: bool,
}

fn is_false(value: &bool) -> bool {
    !*value
}

#[derive(Deserialize, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum NativeEvent {
    ServerHello {
        protocol_version: u16,
        capabilities: Vec<String>,
    },
    Head {
        request_id: String,
        status: u16,
        http_version: String,
        headers: Vec<(String, String)>,
    },
    Chunk {
        request_id: String,
        data: String,
    },
    Sse {
        request_id: String,
        text: String,
        more: bool,
    },
    ResponsesEvent {
        request_id: String,
        text: String,
        more: bool,
        event_type: Option<String>,
        python_normalization: bool,
        #[serde(default, skip_serializing_if = "is_false")]
        stream_complete: bool,
    },
    SseEventTooLarge {
        request_id: String,
        size_bytes: usize,
        limit_bytes: usize,
    },
    Compact {
        request_id: String,
        text: String,
        more: bool,
    },
    End {
        request_id: String,
    },
    WebsocketOpen {
        request_id: String,
        status: u16,
        headers: Vec<(String, String)>,
    },
    WebsocketText {
        request_id: String,
        text: String,
    },
    WebsocketResponsesText {
        request_id: String,
        text: String,
        event_type: Option<String>,
        payload: Box<serde_json::value::RawValue>,
        payload_response_id: Option<String>,
        sequence_number: Option<Box<serde_json::value::RawValue>>,
    },
    WebsocketBinary {
        request_id: String,
        data: String,
    },
    WebsocketSent {
        request_id: String,
        command_id: String,
    },
    WebsocketClose {
        request_id: String,
        code: Option<u16>,
        reason: Option<String>,
    },
    WebsocketError {
        request_id: String,
        command_id: Option<String>,
        message: String,
        failure_phase: String,
        /// Payload-free name of the underlying error variant (for example
        /// `io_connection_reset`), recorded so a failure can be attributed.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        failure_detail: Option<String>,
        retryable_same_contract: bool,
        is_tls_verification_failure: bool,
        status: Option<u16>,
        headers: Vec<(String, String)>,
        body: Option<String>,
    },
    Cancelled {
        request_id: String,
    },
    Error {
        request_id: String,
        message: String,
        failure_phase: String,
        retryable_same_contract: bool,
        is_tls_verification_failure: bool,
    },
}

#[cfg(test)]
mod tests {
    use super::{CAPABILITIES, NativeCommand, NativeEvent, PROTOCOL_VERSION};

    #[test]
    fn hello_contract_is_stable() {
        let fixture: serde_json::Value =
            serde_json::from_str(include_str!("../tests/fixtures/handshake-v1.json"))
                .expect("parse shared handshake fixture");
        let command = NativeCommand::ClientHello {
            min_protocol_version: PROTOCOL_VERSION,
            max_protocol_version: PROTOCOL_VERSION,
        };
        assert_eq!(
            serde_json::to_value(command).expect("serialize client hello"),
            fixture["client_hello"],
        );

        let event = NativeEvent::ServerHello {
            protocol_version: PROTOCOL_VERSION,
            capabilities: CAPABILITIES
                .iter()
                .map(|value| (*value).to_owned())
                .collect(),
        };
        assert_eq!(
            serde_json::to_value(event).expect("serialize server hello"),
            fixture["server_hello"],
        );
    }
}
