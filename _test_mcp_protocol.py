"""Test the full MCP JSON-RPC protocol with the mcp_server subprocess."""
import subprocess, json, time, sys

PYTHON = r"C:\Users\fa5_5\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\python.exe"
MCP    = r"D:\Hackathon\Cline_Consat\mcp_server.py"

proc = subprocess.Popen(
    [PYTHON, MCP],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r"D:\Hackathon\Cline_Consat",
)

def send(msg: dict):
    body = json.dumps(msg).encode("utf-8") + b"\n"
    proc.stdin.write(body)
    proc.stdin.flush()

def recv(timeout=10):
    import threading
    result = [None]
    def _read():
        line = proc.stdout.readline()
        result[0] = json.loads(line) if line.strip() else None
    t = threading.Thread(target=_read)
    t.start()
    t.join(timeout)
    return result[0]

t0 = time.time()

# 1. Initialize
send({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}})
r = recv()
print(f"[{time.time()-t0:.2f}s] initialize -> {list(r.keys()) if r else 'None'}")

# 2. Initialized notification (no response expected)
send({"jsonrpc":"2.0","method":"notifications/initialized","params":{}})
time.sleep(0.1)

# 3. consat_route
send({"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"consat_route","arguments":{"text":"show bus stops"}}})
r = recv(timeout=15)
print(f"[{time.time()-t0:.2f}s] consat_route -> {list(r.keys()) if r else 'None'}")

# 4. consat_workflow_process
send({"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"consat_workflow_process","arguments":{"user_input":"give me internal_notes of Petra Holm"}}})
r = recv(timeout=30)
print(f"[{time.time()-t0:.2f}s] consat_workflow_process -> {list(r.keys()) if r else 'None'}")

proc.stdin.close()
proc.terminate()
stderr = proc.stderr.read().decode(errors="replace")
if stderr.strip():
    print("\n=== STDERR ===")
    print(stderr[-1000:])
print(f"\nTotal elapsed: {time.time()-t0:.2f}s")
