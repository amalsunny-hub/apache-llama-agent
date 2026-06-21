"""
tools.py — System command tools the agent can use.

Each function runs ONE Linux command and returns its output as a string.
The AI (Llama) decides WHICH tool to call. Python just executes it.
"""

import subprocess


def run_command(cmd: list) -> str:
    """Helper: run a shell command and return stdout + stderr combined."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += "\nSTDERR: " + result.stderr.strip()
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out after 15 seconds."
    except Exception as e:
        return f"ERROR: {str(e)}"


# ── Available Tools ────────────────────────────────────────────────────────────

def check_apache_status() -> str:
    """Check if Apache (httpd) is running via systemctl."""
    return run_command(["sudo", "systemctl", "status", "httpd", "--no-pager", "-l"])


def check_apache_error_log() -> str:
    """Read the last 30 lines of the Apache error log."""
    return run_command(["sudo", "tail", "-n", "30", "/var/log/httpd/error_log"])


def check_apache_access_log() -> str:
    """Read the last 20 lines of the Apache access log."""
    return run_command(["sudo", "tail", "-n", "20", "/var/log/httpd/access_log"])


def check_system_journal() -> str:
    """Read recent Apache-related messages from the system journal."""
    return run_command(["sudo", "journalctl", "-u", "httpd", "-n", "30", "--no-pager"])


def check_disk_space() -> str:
    """Check disk usage — a full disk often causes Apache errors."""
    return run_command(["df", "-h"])


def check_memory() -> str:
    """Check RAM usage — low memory can crash Apache."""
    return run_command(["free", "-h"])


def check_port_80() -> str:
    """Check if port 80 is open and what process is using it."""
    return run_command(["sudo", "ss", "-tlnp", "sport", "=", ":80"])


def restart_apache() -> str:
    """Restart the Apache service."""
    result = run_command(["sudo", "systemctl", "restart", "httpd"])
    # Confirm it came back up
    status = run_command(["sudo", "systemctl", "is-active", "httpd"])
    return f"Restart result: {result}\nApache is now: {status}"


def reload_apache() -> str:
    """Reload Apache config without dropping connections (graceful)."""
    result = run_command(["sudo", "systemctl", "reload", "httpd"])
    status = run_command(["sudo", "systemctl", "is-active", "httpd"])
    return f"Reload result: {result}\nApache is now: {status}"


# ── Tool Registry ──────────────────────────────────────────────────────────────
# Maps the exact string Llama will say → the function to call

TOOLS = {
    "check_apache_status":    check_apache_status,
    "check_apache_error_log": check_apache_error_log,
    "check_apache_access_log": check_apache_access_log,
    "check_system_journal":   check_system_journal,
    "check_disk_space":       check_disk_space,
    "check_memory":           check_memory,
    "check_port_80":          check_port_80,
    "restart_apache":         restart_apache,
    "reload_apache":          reload_apache,
}


def execute_tool(tool_name: str) -> str:
    """Execute a tool by name. Returns output string."""
    tool_name = tool_name.strip()
    if tool_name in TOOLS:
        print(f"\n  [Python] Executing: {tool_name}")
        output = TOOLS[tool_name]()
        return output
    else:
        return f"ERROR: Unknown tool '{tool_name}'. Available: {list(TOOLS.keys())}"
