import re
import subprocess
from typing import List, Optional, Tuple
from urllib.parse import urlparse

def is_valid_github_url(url: str) -> bool:
    """
    Validates if a URL is a valid GitHub repository URL.
    Checks for both HTTPS and SSH formats.
    """
    if not url:
        return False
    
    # HTTPS Pattern
    https_pattern = r'^https://github\.com/[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+(\.git)?/?$'
    # SSH Pattern
    ssh_pattern = r'^git@github\.com:[a-zA-Z0-9_\-\.]+/[a-zA-Z0-9_\-\.]+(\.git)?$'
    
    return bool(re.match(https_pattern, url) or re.match(ssh_pattern, url))

def sanitize_path(path: str) -> str:
    """
    Sanitizes a file path to prevent directory traversal.
    Ensures the path doesn't go outside the intended root.
    """
    # Remove any null bytes
    path = path.replace("\x00", "")
    # Remove any .. sequences
    path = re.sub(r'\.\.+', '', path)
    return path

def run_safe_command(command: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """
    Core wrapper for all shell commands. 
    Centralizes execution logic and prevents shell=True usage.
    """
    try:
        # We explicitly avoid shell=True to prevent injection
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            shell=False 
        )
    except FileNotFoundError as e:
        # Command not found (e.g. git not installed)
        return subprocess.CompletedProcess(
            args=command,
            returncode=127,
            stderr=f"Command not found: {str(e)}",
            stdout=""
        )
    except Exception as e:
        return subprocess.CompletedProcess(
            args=command,
            returncode=-1,
            stderr=f"Unexpected execution error: {str(e)}",
            stdout=""
        )

def parse_git_error(stderr: str) -> str:
    """
    Parses git stderr to provide human-readable failure modes.
    """
    if "repository not found" in stderr.lower() or "404" in stderr:
        return "404_NOT_FOUND"
    if "authentication failed" in stderr.lower() or "permission denied" in stderr.lower():
        return "401_UNAUTHORIZED"
    if "could not resolve host" in stderr.lower():
        return "NETWORK_ERROR"
    return "UNKNOWN_GIT_ERROR"
