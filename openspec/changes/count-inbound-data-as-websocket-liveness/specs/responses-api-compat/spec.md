## ADDED Requirements

### Requirement: Downstream websocket keepalive counts inbound data as liveness
The client-facing websocket listener SHALL treat any data received from the client while a keepalive ping is outstanding as proof of liveness: the pong deadline is cancelled and the next ping is scheduled. A client that sends no data at all MUST still be closed with 1011 once the ping timeout elapses. Ping interval and timeout settings MUST keep their meaning.

#### Scenario: Slow upload of a large response.create
- **WHEN** a client takes longer than the ping interval plus ping timeout to upload one message and does not answer pings meanwhile
- **THEN** the server keeps the connection open and delivers the message to the application

#### Scenario: Silent client
- **WHEN** a client sends nothing after a keepalive ping
- **THEN** the server closes the connection with 1011 after the ping timeout
