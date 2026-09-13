# Static Rule Testing Report: BindToAllInterfaces

## Summary

- Language: python
- Rule goal: This rule detects Python socket binding operations that expose services to all network interfaces, which is a security vulnerability. When a socket is bound to addresses like '0.0.0.0', '' (empty string), '::', or '::0', it accepts connections from any IPv4 or IPv6 address respectively, rather than being restricted to specific interfaces. This creates security risks because: (1) the service becomes accessible from potentially untrusted networks, (2) it may expose internal services that should be localhost-only, (3) it increases the attack surface by allowing external connections that weren't intended. This is classified under CWE-200 (Information Exposure) and represents a common misconfiguration in network service deployment where developers intend to bind to localhost but accidentally bind to all interfaces.
- Total generated mutants: 40
- Total verified mutants: 40
- Reportable mutants: 11
- False positives: 1
- False negatives: 10

## Original Rule Implementation

```
# File: dataset/codeql-rules/BindToAllInterfaces/BindToAllInterfaces.ql
/**
 * @name Binding a socket to all network interfaces
 * @description Binding a socket to all interfaces opens it up to traffic from any IPv4 address
 * and is therefore associated with security risks.
 * @kind problem
 * @tags security
 *       external/cwe/cwe-200
 * @problem.severity error
 * @security-severity 6.5
 * @sub-severity low
 * @precision high
 * @id py/bind-socket-all-network-interfaces
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.ApiGraphs

/** Gets a hostname that can be used to bind to all interfaces. */
private string vulnerableHostname() {
  result in [
      // IPv4
      "0.0.0.0", "",
      // IPv6
      "::", "::0"
    ]
}

/** Gets a reference to a hostname that can be used to bind to all interfaces. */
private DataFlow::TypeTrackingNode vulnerableHostnameRef(DataFlow::TypeTracker t, string hostname) {
  t.start() and
  exists(StringLiteral allInterfacesStringLiteral | hostname = vulnerableHostname() |
    allInterfacesStringLiteral.getText() = hostname and
    result.asExpr() = allInterfacesStringLiteral
  )
  or
  exists(DataFlow::TypeTracker t2 | result = vulnerableHostnameRef(t2, hostname).track(t2, t))
}

/** Gets a reference to a hostname that can be used to bind to all interfaces. */
DataFlow::Node vulnerableHostnameRef(string hostname) {
  vulnerableHostnameRef(DataFlow::TypeTracker::end(), hostname).flowsTo(result)
}

/** Gets a reference to a tuple for which the first element is a hostname that can be used to bind to all interfaces. */
private DataFlow::TypeTrackingNode vulnerableAddressTuple(DataFlow::TypeTracker t, string hostname) {
  t.start() and
  result.asExpr() = any(Tuple tup | tup.getElt(0) = vulnerableHostnameRef(hostname).asExpr())
  or
  exists(DataFlow::TypeTracker t2 | result = vulnerableAddressTuple(t2, hostname).track(t2, t))
}

/** Gets a reference to a tuple for which the first element is a hostname that can be used to bind to all interfaces. */
DataFlow::Node vulnerableAddressTuple(string hostname) {
  vulnerableAddressTuple(DataFlow::TypeTracker::end(), hostname).flowsTo(result)
}

/**
 * Gets an instance of `socket.socket` using _some_ address family.
 *
 * See https://docs.python.org/3/library/socket.html
 */
API::Node socketInstance() { result = API::moduleImport("socket").getMember("socket").getReturn() }

from DataFlow::CallCfgNode bindCall, DataFlow::Node addressArg, string hostname
where
  bindCall = socketInstance().getMember("bind").getACall() and
  addressArg = bindCall.getArg(0) and
  addressArg = vulnerableAddressTuple(hostname)
select bindCall.asExpr(), "'" + hostname + "' binds a socket to all interfaces."


```

## Original Seed Test Case

```python
import socket

# binds to all interfaces, insecure
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 31137))

# binds to all interfaces, insecure
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 4040))

# binds only to a dedicated interface, secure
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('84.68.10.12', 8080))

# binds to all interfaces, insecure
ALL_LOCALS = "0.0.0.0"
s.bind((ALL_LOCALS, 9090))

# binds to all interfaces, insecure
tup = (ALL_LOCALS, 8080)
s.bind(tup)


# IPv6
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.bind(("::", 8080)) # NOT OK

```

## All Verified Mutants

### 1. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
#!/usr/bin/python
import socket, threading, sys

PASS = ""

class Server:
    def method_CONNECT(self, hostPort):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(hostPort)

srv = Server()
host = '0.0.0.0'
if len(PASS) != 0:
    host = '127.0.0.1'

srv.method_CONNECT((host, 8080))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "SocketBindCall"
}
```

### 2. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# Alternative pattern: dynamic construction of bind address
# May bypass rules looking for literal '0.0.0.0' strings
host = "".join(["0.0.0", ".0"])
port = 31137
config = (host, port)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(config)
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "SocketBindCall"
}
```

### 3. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

PORT = 8080
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(('0.0.0.0', PORT))
    s.listen()
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "SocketBindCall"
}
```

### 4. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# Abstract Unix socket - binds to local namespace without filesystem path
# Potentially vulnerable to local access if not namespaced properly
# Uses dynamic string concatenation similar to network bind patterns
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
service_name = "\0" + "my_service"
s.bind(service_name)
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "SocketBindCall"
}
```

### 5. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# CAN socket binding with single-element tuple structure
s = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
s.bind(('can0',))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "SocketBindCall"
}
```

### 6. P2 · FP · SocketBindCall

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```python
import socket

# binds to all interfaces on ephemeral port, potentially secure mitigation
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 0))
s.listen(1)
port = s.getsockname()[1]
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "SocketBindCall"
}
```

### 7. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# binds to a Unix domain socket, secure (no network interface exposure)
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
server_address = '/tmp/secure_socket'
sock.bind(server_address)
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "SocketBindCall"
}
```

### 8. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

# binds to all interfaces with socket options that might be mistaken for mitigation
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
s.bind(('0.0.0.0', 8080))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "SocketBindCall"
}
```

### 9. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# Secure binding using localhost variable, should not trigger detection
LOCALHOST = "127.0.0.1"
addr_tuple = (LOCALHOST, 0)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(addr_tuple)
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "SocketBindCall"
}
```

### 10. P2 · NONE · SocketBindCall

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# binds to localhost via variable, secure
localhost = "127.0.0.1"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((localhost, 8080))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "SocketBindCall"
}
```

### 11. P2 · NONE · VulnerableHostnameWithFlow

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

# IPv6 wildcard variant using ::0 instead of ::
# Tests detection of alternative IPv6 all-zeros representation with data flow
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
bind_address = '::0'
s.bind((bind_address, 8080))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 12. P2 · FN · VulnerableHostnameWithFlow

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket

# IPv6 binding to all interfaces using mapped IPv4 notation
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
s.bind(("::0.0.0.0", 8080))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 13. P0 · FN · VulnerableHostnameWithFlow

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The static analyzer failed to flag the insecure network binding. The server is configured to listen on '0.0.0.0', exposing the service to all network interfaces instead of restricting it to localhost or specific trusted interfaces. This increases the attack surface and risks unauthorized access if the host is connected to an untrusted network.
- Assessment reason: The static analyzer produced no findings, indicating it failed to detect the security issue identified by the LLM. The code explicitly binds the asyncio server to '0.0.0.0', which listens on all available network interfaces. This is a well-known security anti-pattern (Attack Surface Expansion) because it can inadvertently expose internal services to public networks. Security static analyzers typically include rules to flag binding to all interfaces as it is a common source of misconfiguration leading to data breaches. Since the analyzer missed this common and high-risk pattern, it represents a False Negative.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import asyncio

async def handle_client(reader, writer):
    pass

async def main():
    # binds to all interfaces via asyncio high-level API, insecure
    server = await asyncio.start_server(handle_client, '0.0.0.0', 8080)
    async with server:
        await server.serve_forever()

asyncio.run(main())
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 14. P0 · FN · VulnerableHostnameWithFlow

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The static analyzer produced a False Negative. It did not flag the security risk of binding to '0.0.0.0' (all interfaces) because the value originates from the default parameter of 'os.environ.get'. This pattern (configuration via env var with insecure default) is common in production code, and missing it allows a significant network exposure vulnerability to go undetected.
- Assessment reason: The static analyzer failed to detect a security misconfiguration where the socket binds to '0.0.0.0' by default. This is a False Negative. The issue arises because the dangerous value is passed as a default argument to 'os.environ.get' rather than directly to 'socket.bind', indicating a limitation in the analyzer's data flow tracking or constant propagation capabilities regarding function default arguments. The LLM correctly identified the risk of exposing the service to all network interfaces.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket
import os

# Vulnerable host configured via environment variable, inspired by insight's use of os.environ
# Tests if data flow tracking resolves environment variables to detect hardcoded defaults
host = os.environ.get("SERVICE_HOST", "0.0.0.0")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, 8080))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 15. P0 · FN · VulnerableHostnameWithFlow

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The static analyzer produced a False Negative by failing to flag the insecure binding to '0.0.0.0' when using the high-level HTTPServer class. This is a security misconfiguration that increases the attack surface by exposing the service to external networks, which the analyzer should have detected given the explicit insecurity noted in the code comments.
- Assessment reason: The static analyzer failed to detect a security misconfiguration where the server binds to '0.0.0.0', exposing it to all network interfaces. The code snippet explicitly labels this pattern as 'insecure' and notes it might be missed by rules tracking only raw sockets. The LLM judge correctly identified this risk, while the analyzer returned no results. This constitutes a False Negative for the static analyzer, demonstrating a gap in its ability to analyze high-level library abstractions for security properties. Network exposure is a fundamental security boundary, making this a critical issue type, and the use of http.server is a common Python pattern.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
from http.server import HTTPServer, BaseHTTPRequestHandler

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()

# binds to all interfaces via high-level server, insecure
# This pattern might be missed if the rule only tracks raw socket.bind()
server = HTTPServer(('0.0.0.0', 8080), DashboardHandler)
server.serve_forever()
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 16. P0 · FN · VulnerableHostnameWithFlow

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The static analyzer produced a False Negative. It did not flag the socket binding to '0.0.0.0'. The code effectively hardcodes an insecure network binding due to a broken configuration class (which ignores keys and returns defaults), increasing the attack surface by exposing the service to all interfaces.
- Assessment reason: The static analyzer failed to detect a security issue that the LLM correctly identified. The code binds a socket to '0.0.0.0', which exposes the service to all network interfaces, a common security anti-pattern. Furthermore, the LLM correctly noted that the configuration mechanism is broken (the Config class always returns the default), meaning the insecure binding is effectively hardcoded despite appearing configurable. A security-focused static analyzer should flag binding to all interfaces, especially when derived from a fallback default. The analyzer's failure to report this constitutes a False Negative.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket

class Config:
    def get(self, key, default):
        return default

class App:
    config = Config()

app = App()

# Binding using config retrieval with insecure default based on insight pattern
bind_ip = app.config.get("BIND_IP", "0.0.0.0")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((bind_ip, 5000))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 17. P2 · NONE · VulnerableHostnameWithFlow

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

ipv6 = True
family = socket.AF_INET6 if ipv6 else socket.AF_INET
bind_addr = '::' if ipv6 else '0.0.0.0'
srv = socket.socket(family, socket.SOCK_STREAM)
srv.bind((bind_addr, 8080))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 18. P2 · NONE · VulnerableHostnameWithFlow

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

# binds to all interfaces with ephemeral port, potentially secure mitigation pattern
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 0))
addr = s.getsockname()
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 19. P2 · NONE · VulnerableHostnameWithFlow

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

# Intentional binding to all interfaces with suppression comment
host = "0.0.0.0"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, 8080))  # nosec
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 20. P2 · NONE · VulnerableHostnameWithFlow

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

host = "127.0.0.1"
# 如需外部访问，请以管理员权限运行或使用 host="0.0.0.0"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((host, 8080))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableHostnameWithFlow"
}
```

### 21. P2 · NONE · VulnerableAddressTuple

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

class CmdOpts:
    listen = True
    port = 8080

cmd_opts = CmdOpts()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Vulnerable address hidden within conditional expression
s.bind(("0.0.0.0" if cmd_opts.listen else "127.0.0.1", cmd_opts.port))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 22. P2 · NONE · VulnerableAddressTuple

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket
from os import environ

HOST = environ.get('APP_HOST')
HOST = HOST if HOST else '0.0.0.0'
PORT = 8080

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((HOST, PORT))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 23. P0 · FN · VulnerableAddressTuple

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: False Negative: The static analyzer did not flag the socket binding to '0.0.0.0' via a default configuration value. This allows the service to listen on all available network interfaces, potentially exposing it to untrusted networks if not properly firewalled, which is a significant security risk.
- Assessment reason: The static analyzer failed to detect a security vulnerability where a socket is bound to '0.0.0.0' by default. This is a classic 'Insecure Default' pattern (CWE-1188) that exposes services to all network interfaces. The LLM judge correctly identified the risk, while the analyzer produced no findings. This constitutes a False Negative for the static analyzer. The pattern of using configuration dictionaries with network defaults is very common in Python applications, and the risk of unintended network exposure is critical as it directly expands the attack surface.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket

# Simulating application configuration dictionary
conf = {}

# Retrieving network settings with vulnerable defaults
# If 'listen_ip' is not specified in conf, it defaults to '0.0.0.0'
listen_ip = conf.get('listen_ip', '0.0.0.0')
listen_port = conf.get('listen_port', 8080)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Binding using variables derived from configuration defaults
s.bind((listen_ip, listen_port))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 24. P0 · FN · VulnerableAddressTuple

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: False Negative: The static analyzer failed to detect the insecure network binding configuration. The code binds the TCP server to all interfaces using an empty string (''), which exposes the service to external networks. This is a critical security misconfiguration often flagged by SAST tools, but the analyzer missed it.
- Assessment reason: The static analyzer output is empty, indicating it found no security issues. However, the LLM judge correctly identified that initializing socketserver.TCPServer with an empty string host ('') binds the server to all network interfaces (0.0.0.0/INADDR_ANY). The code snippet explicitly contains comments labeling this behavior as 'insecure' and 'NOT OK', establishing the ground truth that this pattern should be flagged as a vulnerability in this context. The analyzer's failure to detect this known insecure network configuration constitutes a False Negative. This is a valuable finding because binding to all interfaces is a common source of security misconfiguration (CWE-284) that expands the attack surface.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socketserver

PORT = 8080
Handler = socketserver.BaseRequestHandler

# binds to all interfaces via socketserver, insecure
with socketserver.TCPServer(("", PORT), Handler) as httpd: # NOT OK
    httpd.serve_forever()
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 25. P0 · FN · VulnerableAddressTuple

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: Static Analyzer False Negative: The tool failed to detect the security vulnerability associated with binding a server to '0.0.0.0' (all interfaces), which exposes the application to untrusted external networks.
- Assessment reason: The static analyzer returned an empty result set, indicating it detected no security issues. However, the code explicitly binds a TCP server to '0.0.0.0', which configures the socket to listen on all available network interfaces. This is a well-documented security anti-pattern (e.g., flagged by Bandit as B104) because it unnecessarily exposes the service to external networks, significantly increasing the attack surface. The LLM judge correctly identified this risk, while the analyzer failed to do so. This constitutes a False Negative for the static analyzer.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socketserver

class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        pass

# binds to all interfaces via high-level server constructor, insecure
server = socketserver.ThreadingTCPServer(('0.0.0.0', 8080), RequestHandler, False)
server.allow_reuse_address = True
server.server_bind()
server.server_activate()
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 26. P2 · NONE · VulnerableAddressTuple

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(('0.0.0.0', 31137))
except socket.error as ex:
    if ex.errno == 98:
        pass
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 27. P2 · NONE · VulnerableAddressTuple

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket
import os

UNIX_SOCKET = '/tmp/secure_service'
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
if os.path.exists(UNIX_SOCKET):
    os.unlink(UNIX_SOCKET)
s.bind(UNIX_SOCKET)
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 28. P2 · FN · VulnerableAddressTuple

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import libzt

# binds to all interfaces on ZeroTier virtual network, secure context
serv = libzt.socket(libzt.ZTS_AF_INET, libzt.ZTS_SOCK_STREAM, 0)
serv.setsockopt(libzt.ZTS_SOL_SOCKET, libzt.ZTS_SO_REUSEADDR, 1)
serv.bind(("0.0.0.0", 8080))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 29. P0 · FN · VulnerableAddressTuple

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The static analyzer missed a security vulnerability where the socket binds to all network interfaces ('0.0.0.0'). This occurs because the config.get method uses a hardcoded insecure fallback value when the configuration option is missing. The analyzer likely failed to perform sufficient dataflow analysis to trace the fallback string to the socket bind call.
- Assessment reason: The static analyzer produced a False Negative. It failed to detect that the socket binds to '0.0.0.0' (all interfaces) due to a hardcoded insecure fallback value in the configuration retrieval. This is a security misconfiguration (CWE-284) that exposes the service to external networks. The LLM correctly identified that the missing configuration option forces the use of the insecure fallback. This pattern is common in Python applications using configparser for flexibility, and it is critical because it significantly increases the attack surface by allowing remote connections to services intended for local use.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket
import configparser

config = configparser.ConfigParser()
config.add_section('Server')

# Config retrieval pattern often used for remediation, but fallback is insecure
ipv4_bind = config.get('Server', 'IPv4_Bind', fallback='0.0.0.0')
port = 31137

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Binding uses variable derived from config lookup instead of literal string
s.bind((ipv4_bind, port))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 30. P2 · NONE · VulnerableAddressTuple

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

local_port = 8080
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', local_port))
s.listen(5)
print(f"VPN client listening on localhost:{local_port}")
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "VulnerableAddressTuple"
}
```

### 31. P2 · NONE · BindWithVulnerableAddress

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
port = 8080
try:
    s.bind(('0.0.0.0', port))
except socket.error as ex:
    if ex.errno == 98:
        pass
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 32. P2 · NONE · BindWithVulnerableAddress

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("", 0))
addr = s.getsockname()
local_port = addr[1]
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 33. P2 · NONE · BindWithVulnerableAddress

- Should report: False
- Risk type: false_negative
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket
import os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(("0.0.0.0", int(os.environ.get("PORT", 8080))))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 34. P0 · FN · BindWithVulnerableAddress

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The static analyzer produced a False Negative. It did not flag the use of unvalidated external input (sys.argv) in a sensitive network configuration sink (socket.bind). This omission allows the application to be configured to listen on all interfaces, potentially leading to unauthorized access.
- Assessment reason: The static analyzer failed to detect a security vulnerability where command-line arguments (sys.argv) are passed directly to socket.bind() without validation. This is a False Negative. The code snippet explicitly includes a comment indicating that static analysis might miss this pattern if it only looks for literals, suggesting this is a known limitation or test case. The LLM judge correctly identified that this allows the service to be bound to all network interfaces (e.g., '0.0.0.0'), which is a significant security risk (CWE-1327). This pattern is common in Python scripts configuring servers via CLI, and the impact is critical as it can expose internal services to the public internet.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket
import sys

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    # Address derived from command line arguments
    # Static analysis might miss this if looking only for literals
    s.bind((sys.argv[1], int(sys.argv[2])))
except Exception:
    sys.exit()
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 35. P0 · FN · BindWithVulnerableAddress

- Should report: True
- Risk type: false_negative
- Snippet source: 
- Bug description: The static analyzer failed to flag the insecure binding to '0.0.0.0' because the address value is indirect (assigned to an instance attribute). This is a False Negative caused by insufficient data flow tracking, allowing a common network exposure vulnerability to go undetected.
- Assessment reason: The static analyzer returned no results, indicating it failed to detect the security issue identified by the LLM. The code binds a socket to '0.0.0.0', which exposes the service to all network interfaces, a recognized security risk (often flagged by tools like Bandit or CodeQL security queries). The analyzer likely missed this because the IP address is stored in an instance attribute ('self.UDP_IP') rather than being a direct string literal in the 'bind' call. This indicates a limitation in the analyzer's data flow analysis. This is a valid False Negative because using variables or configuration attributes for network settings is a standard, common programming pattern, and missing such cases significantly reduces the tool's effectiveness in real-world scenarios.
- LLM judge says issue: True
- Tool says issue: False

#### Reproduction Code

```python
import socket

class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Vulnerable address stored in instance attribute
        self.UDP_IP = "0.0.0.0"
        self.UDP_PORT = 31137
    
    def start(self):
        # Binding using instance attributes potentially bypassing simple literal checks
        self.sock.bind((self.UDP_IP, self.UDP_PORT))
```

#### Oracle

```json
{
  "has_issue": true,
  "reason": "This mutation aims to remain vulnerable and expose a potential false negative.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 36. P2 · NONE · BindWithVulnerableAddress

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: False

#### Reproduction Code

```python
import socket

# Secure mitigation: binds to localhost only, should not be flagged
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('127.0.0.1', 31137))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 37. P2 · NONE · BindWithVulnerableAddress

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

def listen_scan():
    lis = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lis.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lis.bind(('0.0.0.0', 911))
    lis.listen(1024)
    while 1:
        s, _ = lis.accept()
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 38. P2 · FP · BindWithVulnerableAddress

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```python
import socket

# Server initialization with reuse options followed by bind to all interfaces
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
if hasattr(socket, "SO_REUSEPORT"):
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
s.bind(('0.0.0.0', 31137))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 39. P1 · FP · BindWithVulnerableAddress

- Should report: True
- Risk type: false_positive
- Snippet source: 
- Bug description: The static analyzer flagged the presence of '0.0.0.0' in the bind logic as a security issue. However, due to the hardcoded truthy value of 'src_addr', the conditional logic ensures '0.0.0.0' is never assigned to 'bind_addr'. The analyzer incorrectly treated the potential data flow as an actual execution path, resulting in a False Positive.
- Assessment reason: The static analyzer produced a False Positive. The code snippet hardcodes 'src_addr' to a truthy value ('127.0.0.1'), making the insecure fallback ('0.0.0.0') statically unreachable. The LLM judge correctly identified that the socket binds only to localhost in this specific context. The analyzer failed to perform sufficient constant propagation or dead code elimination to recognize the insecure branch is never taken. While the pattern (insecure fallback) is common and the vulnerability class (binding to all interfaces) is critical, this specific instance is safe, making the finding a non-critical False Positive.
- LLM judge says issue: False
- Tool says issue: True

#### Reproduction Code

```python
import socket

# Secure configuration provided via src_addr, fallback is insecure
src_addr = '127.0.0.1'
bind_addr = src_addr if src_addr else '0.0.0.0'

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((bind_addr, 8080))
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

### 40. P2 · NONE · BindWithVulnerableAddress

- Should report: False
- Risk type: false_positive
- Snippet source: 
- Bug description: 
- Assessment reason: 
- LLM judge says issue: True
- Tool says issue: True

#### Reproduction Code

```python
import socket

# Secure fallback pattern - binds to specific multicast group first,
# falls back to all interfaces only if that fails
sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
try:
    sock.bind(('ff02::c', 3702, 0, 0))  # Specific multicast group - OK
except OSError:
    sock.bind(('::', 3702, 0, 0))  # Fallback to all interfaces - should not flag
```

#### Oracle

```json
{
  "has_issue": false,
  "reason": "This mutation aims to be a secure variant and expose a potential false positive.",
  "expected_focus": "BindWithVulnerableAddress"
}
```

## Grouped Reportable Mutants (by Root Cause)

### Group 1: Missing high-level API coverage - rule only tracks socket.bind() but misses alternative binding methods
**Type**: RULE_SPECIFIC
**Count**: 4

**Explanation**: Mutants 0, 2, 5, and 6 all use high-level server construction APIs (asyncio.start_server, HTTPServer, socketserver.TCPServer, socketserver.ThreadingTCPServer) that internally bind sockets but are not covered by the current rule which only tracks socket.socket().bind() calls. These require rule expansion to recognize additional binding sinks beyond the raw socket API.

- 1. P0 · VulnerableHostnameWithFlow · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer failed to flag the insecure network binding. The server is configured to listen on '0.0.0.0', exposing the service to all network interfaces instead of restricting it to localhost or specific trusted interfaces. This ...
- 2. P0 · VulnerableHostnameWithFlow · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer produced a False Negative by failing to flag the insecure binding to '0.0.0.0' when using the high-level HTTPServer class. This is a security misconfiguration that increases the attack surface by exposing the service ...
- 3. P0 · VulnerableAddressTuple · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=False Negative: The static analyzer failed to detect the insecure network binding configuration. The code binds the TCP server to all interfaces using an empty string (''), which exposes the service to external networks. This is a critic...
- 4. P0 · VulnerableAddressTuple · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=Static Analyzer False Negative: The tool failed to detect the security vulnerability associated with binding a server to '0.0.0.0' (all interfaces), which exposes the application to untrusted external networks.

### Group 2: Insufficient data flow tracking through variables, method calls, and object attributes
**Type**: TECHNIQUE
**Count**: 6

**Explanation**: Mutants 1, 3, 4, 7, 8, and 9 all involve the vulnerable address value being stored in variables or retrieved through method calls before reaching the bind sink. The current rule's data flow tracking (vulnerableHostnameRef, vulnerableAddressTuple) does not sufficiently follow values through: environment variables with defaults (1), custom config classes (3), dictionary.get() (4), configparser (7), command-line arguments (8), or instance attributes (9). All require enhanced constant propagation and flow tracking through intermediate assignments and method returns.

- 1. P0 · VulnerableHostnameWithFlow · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer produced a False Negative. It did not flag the security risk of binding to '0.0.0.0' (all interfaces) because the value originates from the default parameter of 'os.environ.get'. This pattern (configuration via env va...
- 2. P0 · VulnerableHostnameWithFlow · false_positive · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer produced a False Negative. It did not flag the socket binding to '0.0.0.0'. The code effectively hardcodes an insecure network binding due to a broken configuration class (which ignores keys and returns defaults), inc...
- 3. P0 · VulnerableAddressTuple · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=False Negative: The static analyzer did not flag the socket binding to '0.0.0.0' via a default configuration value. This allows the service to listen on all available network interfaces, potentially exposing it to untrusted networks if n...
- 4. P0 · VulnerableAddressTuple · false_positive · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer missed a security vulnerability where the socket binds to all network interfaces ('0.0.0.0'). This occurs because the config.get method uses a hardcoded insecure fallback value when the configuration option is missing...
- 5. P0 · BindWithVulnerableAddress · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer produced a False Negative. It did not flag the use of unvalidated external input (sys.argv) in a sensitive network configuration sink (socket.bind). This omission allows the application to be configured to listen on a...
- 6. P0 · BindWithVulnerableAddress · false_negative · FN
  should_report=True llm_issue=True tool_issue=False
  bug=The static analyzer failed to flag the insecure binding to '0.0.0.0' because the address value is indirect (assigned to an instance attribute). This is a False Negative caused by insufficient data flow tracking, allowing a common network...

### Group 3: Lack of path-sensitive analysis for conditional logic
**Type**: TECHNIQUE
**Count**: 1

**Explanation**: Mutant 10 is a False Positive where '0.0.0.0' appears in the code but is never actually executed due to conditional logic (src_addr is hardcoded to '127.0.0.1', making the else branch unreachable). The analyzer treats all potential data flows as actual execution paths without considering branch conditions. This requires path-sensitive analysis to determine which values can actually reach the sink at runtime.

- 1. P1 · BindWithVulnerableAddress · false_positive · FP
  should_report=True llm_issue=False tool_issue=True
  bug=The static analyzer flagged the presence of '0.0.0.0' in the bind logic as a security issue. However, due to the hardcoded truthy value of 'src_addr', the conditional logic ensures '0.0.0.0' is never assigned to 'bind_addr'. The analyzer...
