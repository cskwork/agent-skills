#!/usr/bin/env python3
"""Hardened existing-profile connector for NAVER Cloud SSL VPN on macOS."""

from __future__ import annotations

import argparse
import base64
import binascii
import contextlib
import getpass
import http.client
import ipaddress
import json
import os
import plistlib
import re
import shlex
import signal
import socket
import ssl
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterator, Protocol


APP_PATH = Path("/Applications/NAVER Cloud SSL VPN.app")
APP_INFO = APP_PATH / "Contents/Info.plist"
OPENVPN = APP_PATH / "Contents/vpn/openvpn"
APP_BUNDLE_ID = "com.ncurity.ncurionsa"
APP_TEAM_ID = "RX8JGWX6RU"
PROFILES_DIR = Path.home() / "Library/Application Support/ncurion-sa-client/vpn/profiles"
DEFAULT_ENV_FILE = Path.home() / ".config/naver-cloud-vpn/.env"
RUNTIME_DIR = Path.home() / ".config/naver-cloud-vpn/runtime"
MANAGEMENT = ("127.0.0.1", 7501)

MAX_CONFIG_BYTES = 16_384
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_PROFILE_BYTES = 1024 * 1024
EXPECTED_ENV_KEYS = {
    "NAVER_VPN_PROFILE",
    "NAVER_VPN_USERNAME",
    "NAVER_VPN_PASSWORD",
}
ALLOWED_RESPONSE_FIELDS = {
    "success",
    "err_msg",
    "state",
    "profile_body",
    "profile_name",
}
ALLOWED_DIRECTIVES = {
    "allow-compression",
    "auth",
    "auth-nocache",
    "auth-user-pass",
    "client",
    "comp-lzo",
    "connect-retry-max",
    "connect-timeout",
    "data-ciphers",
    "data-ciphers-fallback",
    "dev",
    "keepalive",
    "keysize",
    "management",
    "mssfix",
    "mute-replay-warnings",
    "persist-local-ip",
    "persist-remote-ip",
    "port",
    "proto",
    "pull-filter",
    "push-peer-info",
    "remote",
    "remote-cert-tls",
    "reneg-sec",
    "tcp-queue-limit",
    "tls-cipher",
    "tls-client",
    "tls-exit",
    "tls-version-max",
    "tls-version-min",
    "tun-mtu",
    "tun-mtu-extra",
    "verb",
}
DANGEROUS_DIRECTIVES = {
    "client-connect",
    "client-disconnect",
    "down",
    "down-pre",
    "ipchange",
    "learn-address",
    "plugin",
    "route-up",
    "script-security",
    "tls-verify",
    "up",
}


class VpnError(RuntimeError):
    """Expected failure whose message contains no secret values."""


class ConfigError(VpnError):
    pass


class ProfileError(VpnError):
    pass


class ApiError(VpnError):
    pass


class ApiVersionError(ApiError):
    pass


class RuntimeSafetyError(VpnError):
    pass


class HttpStatusError(ApiError):
    def __init__(self, status: int):
        self.status = status
        super().__init__(f"VPN API returned HTTP {status}")


@dataclass(frozen=True)
class Credentials:
    profile: str
    username: str
    password: str


@dataclass(frozen=True)
class ProfileInfo:
    path: Path
    remote_host: str
    remote_port: int
    management: tuple[str, int]
    text: str
    directives: tuple[str, ...]


@dataclass(frozen=True)
class ClientMetadata:
    version: str
    os_name: str
    os_version: str
    mac: tuple[str, ...]


@dataclass(frozen=True)
class ApiRequest:
    host: str
    port: int
    path: str
    headers: dict[str, str]
    body: dict[str, object]


@dataclass(frozen=True)
class AuthResult:
    otp_required: bool
    profile_bytes: bytes | None = None
    profile_name: str | None = None
    api_version: int = 3


class Transport(Protocol):
    def post(self, request: ApiRequest) -> dict[str, object]: ...


def parse_env_text(text: str) -> Credentials:
    values: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, separator, raw_value = line.partition("=")
        if not separator or key not in EXPECTED_ENV_KEYS:
            raise ConfigError(f"invalid credential entry on line {line_number}")
        if key in values:
            raise ConfigError(f"duplicate credential key on line {line_number}")
        if raw_value[:1] in {"'", '"'}:
            quote = raw_value[0]
            if len(raw_value) < 2 or raw_value[-1] != quote:
                raise ConfigError(f"unclosed quoted value on line {line_number}")
            raw_value = raw_value[1:-1]
        if not raw_value:
            raise ConfigError(f"empty credential value on line {line_number}")
        values[key] = raw_value
    if set(values) != EXPECTED_ENV_KEYS:
        raise ConfigError("credential file must define the three required keys")
    return Credentials(
        profile=values["NAVER_VPN_PROFILE"],
        username=values["NAVER_VPN_USERNAME"],
        password=values["NAVER_VPN_PASSWORD"],
    )


def _open_owned_file(path: Path, *, private: bool, max_bytes: int) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path.expanduser(), flags)
    except OSError as error:
        raise ConfigError("file could not be opened safely") from error
    try:
        metadata = os.fstat(descriptor)
        mode = stat.S_IMODE(metadata.st_mode)
        if not stat.S_ISREG(metadata.st_mode):
            raise ConfigError("path must be a regular file")
        if metadata.st_uid != os.getuid():
            raise ConfigError("file must belong to the current user")
        if mode & 0o022 or private and mode & 0o077:
            raise ConfigError("file permissions are too broad")
        with os.fdopen(descriptor, "r", encoding="utf-8", errors="strict") as handle:
            descriptor = -1
            content = handle.read(max_bytes + 1)
    except UnicodeError as error:
        raise ConfigError("file must be UTF-8") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content.encode("utf-8")) > max_bytes:
        raise ConfigError("file is too large")
    return content


def load_credentials(path: Path) -> Credentials:
    return parse_env_text(
        _open_owned_file(path, private=True, max_bytes=MAX_CONFIG_BYTES)
    )


def _safe_basename(name: str) -> str:
    if (
        not name
        or name != Path(name).name
        or not name.endswith(".ovpn")
        or any(character in name for character in ("\x00", "/", "\\"))
    ):
        raise ProfileError("profile filename is unsafe")
    return name


def resolve_profile(profile_dir: Path, alias: str) -> Path:
    if not alias or alias in {".", ".."} or any(token in alias for token in ("/", "\\", "\x00")):
        raise ProfileError("profile alias is unsafe")
    root = profile_dir.expanduser().resolve()
    try:
        alias_text = _open_owned_file(
            root / "alias.json", private=False, max_bytes=MAX_CONFIG_BYTES
        )
        mapping = json.loads(alias_text)
    except (ConfigError, json.JSONDecodeError) as error:
        raise ProfileError("profile alias map is invalid") from error
    if not isinstance(mapping, dict):
        raise ProfileError("profile alias map is invalid")
    matches = [
        stem
        for stem, display in mapping.items()
        if isinstance(stem, str)
        and isinstance(display, str)
        and alias in {stem, display, f"{stem}.ovpn"}
    ]
    if len(matches) != 1:
        raise ProfileError("profile alias did not resolve exactly once")
    candidate = root / _safe_basename(f"{matches[0]}.ovpn")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as error:
        raise ProfileError("profile file does not exist") from error
    if resolved.parent != root or candidate.is_symlink():
        raise ProfileError("profile path escaped the approved directory")
    try:
        _open_owned_file(resolved, private=False, max_bytes=MAX_PROFILE_BYTES)
    except ConfigError as error:
        raise ProfileError("profile file is unsafe") from error
    return resolved


def _valid_remote_host(host: str) -> bool:
    if not host or len(host) > 253 or any(token in host for token in ("/", "\\", "://")):
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        labels = host.rstrip(".").split(".")
        return all(
            label
            and len(label) <= 63
            and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
            for label in labels
        )


def parse_profile_text(text: str, path: Path) -> ProfileInfo:
    if len(text.encode("utf-8")) > MAX_PROFILE_BYTES:
        raise ProfileError("profile is too large")
    _safe_basename(path.name)
    directives: list[str] = []
    remotes: list[list[str]] = []
    port: int | None = None
    management: tuple[str, int] | None = None
    has_auth = False
    management_count = 0
    auth_count = 0
    port_count = 0
    remote_cert_tls_count = 0
    block: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith(("#", ";")):
            continue
        if block:
            if stripped == f"</{block}>":
                block = None
            continue
        if stripped.startswith("<"):
            if stripped != "<ca>":
                raise ProfileError(f"unsupported inline block on line {line_number}")
            block = "ca"
            continue
        try:
            tokens = shlex.split(stripped, comments=False, posix=True)
        except ValueError as error:
            raise ProfileError(f"invalid profile syntax on line {line_number}") from error
        if not tokens:
            continue
        directive = tokens[0]
        if directive in DANGEROUS_DIRECTIVES or directive not in ALLOWED_DIRECTIVES:
            raise ProfileError(f"unsafe profile directive on line {line_number}")
        directives.append(directive)
        if directive == "remote":
            if len(tokens) not in {2, 3}:
                raise ProfileError("remote directive has invalid shape")
            if len(tokens) == 3 and not tokens[2].isdigit():
                raise ProfileError("remote directive port was invalid")
            remotes.append(tokens)
        elif directive == "port":
            if len(tokens) != 2 or not tokens[1].isdigit():
                raise ProfileError("port directive has invalid shape")
            port_count += 1
            port = int(tokens[1])
        elif directive == "management":
            if len(tokens) != 3 or not tokens[2].isdigit():
                raise ProfileError("management directive has invalid shape")
            management_count += 1
            management = (tokens[1], int(tokens[2]))
        elif directive == "auth-user-pass":
            if len(tokens) != 1:
                raise ProfileError("profile embeds an authentication path")
            auth_count += 1
            has_auth = True
        elif directive == "remote-cert-tls":
            if tokens != ["remote-cert-tls", "server"]:
                raise ProfileError("profile peer certificate role was invalid")
            remote_cert_tls_count += 1

    if block:
        raise ProfileError("profile inline block is unclosed")
    if len(remotes) != 1:
        raise ProfileError("profile must contain exactly one remote")
    remote = remotes[0]
    host = remote[1]
    remote_port = int(remote[2]) if len(remote) == 3 and remote[2].isdigit() else port
    if not _valid_remote_host(host) or remote_port is None or not 1 <= remote_port <= 65535:
        raise ProfileError("profile remote endpoint is invalid")
    if management != MANAGEMENT:
        raise ProfileError("profile management endpoint is not approved")
    if management_count != 1:
        raise ProfileError("profile must contain one management directive")
    if port_count > 1:
        raise ProfileError("profile contains duplicate port directives")
    if not has_auth or auth_count != 1:
        raise ProfileError("profile does not require an authentication file")
    if remote_cert_tls_count != 1:
        raise ProfileError("profile must require a server certificate")
    return ProfileInfo(
        path=path,
        remote_host=host,
        remote_port=remote_port,
        management=management,
        text=text,
        directives=tuple(directives),
    )


def load_profile(path: Path) -> ProfileInfo:
    try:
        text = _open_owned_file(path, private=False, max_bytes=MAX_PROFILE_BYTES)
    except ConfigError as error:
        raise ProfileError("profile file is unsafe") from error
    return parse_profile_text(text, path)


def redacted_profile_summary(profile: ProfileInfo) -> dict[str, object]:
    return {
        "profile": profile.path.name,
        "remote": "<redacted>",
        "remote_port": profile.remote_port,
        "management": [profile.management[0], profile.management[1]],
        "directive_count": len(profile.directives),
    }


def build_v3_request(
    profile: ProfileInfo,
    credentials: Credentials,
    metadata: ClientMetadata,
) -> ApiRequest:
    return ApiRequest(
        host=profile.remote_host,
        port=8443,
        path="/api/v3/authstate",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Api-Version": "1",
        },
        body={
            "user_id": credentials.username,
            "passwd": credentials.password,
            "type": "connect",
            "ovpn_file_name": profile.path.name,
            "client_version": metadata.version,
            "os_name": metadata.os_name,
            "os_version": metadata.os_version,
            "mac": list(metadata.mac),
        },
    )


def build_v2_request(profile: ProfileInfo, credentials: Credentials) -> ApiRequest:
    return ApiRequest(
        host=profile.remote_host,
        port=8443,
        path="/api/v2/authstate",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        body={"user_id": credentials.username, "passwd": credentials.password},
    )


def validate_auth_response(
    response: dict[str, object], *, expected_name: str
) -> AuthResult:
    if not isinstance(response, dict) or set(response) - ALLOWED_RESPONSE_FIELDS:
        raise ApiError("VPN API response shape was not approved")
    if type(response.get("success")) is not bool:
        raise ApiError("VPN API success field was invalid")
    if response["success"] is not True:
        message = response.get("err_msg")
        if isinstance(message, str) and "api version" in message.lower():
            raise ApiVersionError("VPN API version is unsupported")
        raise ApiError("VPN credentials or device were rejected")
    state = response.get("state")
    if state is not None and not isinstance(state, (bool, str)):
        raise ApiError("VPN API state field was invalid")
    if isinstance(state, str) and len(state) > 4096:
        raise ApiError("VPN API state field was too large")
    profile_body = response.get("profile_body")
    profile_name = response.get("profile_name")
    if (profile_body is None) != (profile_name is None):
        raise ApiError("VPN API profile refresh was incomplete")
    decoded: bytes | None = None
    if profile_body is not None:
        if not isinstance(profile_body, str) or not isinstance(profile_name, str):
            raise ApiError("VPN API profile refresh had invalid types")
        if profile_name != expected_name:
            raise ApiError("VPN API profile filename did not match")
        _safe_basename(profile_name)
        if len(profile_body) > MAX_PROFILE_BYTES * 2:
            raise ApiError("VPN API profile body was too large")
        try:
            decoded = base64.b64decode(profile_body, validate=True)
        except (binascii.Error, ValueError) as error:
            raise ApiError("VPN API profile body was not valid base64") from error
        if len(decoded) > MAX_PROFILE_BYTES:
            raise ApiError("VPN API profile body was too large")
        try:
            parse_profile_text(decoded.decode("utf-8"), Path(expected_name))
        except (UnicodeError, ProfileError) as error:
            raise ApiError("VPN API profile body was unsafe") from error
    return AuthResult(
        otp_required=bool(state),
        profile_bytes=decoded,
        profile_name=profile_name if isinstance(profile_name, str) else None,
    )


def authenticate(
    transport: Transport,
    profile: ProfileInfo,
    credentials: Credentials,
    metadata: ClientMetadata,
) -> AuthResult:
    try:
        response = transport.post(build_v3_request(profile, credentials, metadata))
        return validate_auth_response(response, expected_name=profile.path.name)
    except HttpStatusError as error:
        if error.status != 404:
            raise
    except ApiVersionError:
        pass
    response = transport.post(build_v2_request(profile, credentials))
    return replace(
        validate_auth_response(response, expected_name=profile.path.name),
        api_version=2,
    )


class HttpsTransport:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    def post(self, request: ApiRequest) -> dict[str, object]:
        body = json.dumps(request.body, separators=(",", ":")).encode("utf-8")
        connection = http.client.HTTPSConnection(
            request.host,
            request.port,
            timeout=self.timeout,
            context=ssl.create_default_context(),
        )
        try:
            connection.request("POST", request.path, body=body, headers=request.headers)
            response = connection.getresponse()
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        except (OSError, ssl.SSLError, http.client.HTTPException) as error:
            raise ApiError("verified VPN API request failed") from error
        finally:
            connection.close()
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ApiError("VPN API response was too large")
        if not 200 <= response.status < 300:
            raise HttpStatusError(response.status)
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise ApiError("VPN API returned malformed JSON") from error
        if not isinstance(parsed, dict):
            raise ApiError("VPN API returned a non-object response")
        return parsed


@contextlib.contextmanager
def staged_profile(root: Path, name: str, content: bytes) -> Iterator[Path]:
    _safe_basename(name)
    if len(content) > MAX_PROFILE_BYTES:
        raise ProfileError("staged profile is too large")
    try:
        parse_profile_text(content.decode("utf-8"), Path(name))
    except UnicodeError as error:
        raise ProfileError("staged profile is not UTF-8") from error
    ensure_private_runtime(root)
    descriptor, raw_path = tempfile.mkstemp(prefix="profile-", suffix=".ovpn", dir=root)
    path = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as handle:
            descriptor = -1
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        yield path
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


@contextlib.contextmanager
def auth_file(root: Path, username: str, secret: str) -> Iterator[Path]:
    if not username or not secret or "\n" in username or "\n" in secret or "\r" in username or "\r" in secret:
        raise ConfigError("authentication values had an invalid shape")
    ensure_private_runtime(root)
    descriptor, raw_path = tempfile.mkstemp(prefix="auth-", suffix=".txt", dir=root)
    path = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            descriptor = -1
            handle.write(f"{username}\n{secret}")
            handle.flush()
            os.fsync(handle.fileno())
        yield path
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def build_openvpn_command(
    openvpn: Path, profile: Path, authentication_file: Path
) -> list[str]:
    return [
        "/usr/bin/sudo",
        "-n",
        "--",
        str(openvpn),
        "--config",
        str(profile),
        "--auth-user-pass",
        str(authentication_file),
    ]


def ensure_private_runtime(root: Path) -> None:
    if root.is_symlink():
        raise RuntimeSafetyError("runtime directory must not be a symlink")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = root.lstat()
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise RuntimeSafetyError("runtime directory must be private and user-owned")


def cleanup_runtime(root: Path) -> None:
    ensure_private_runtime(root)
    for pattern in ("auth-*.txt", "profile-*.ovpn"):
        for path in root.glob(pattern):
            metadata = path.lstat()
            if path.is_symlink() or not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid():
                raise RuntimeSafetyError("stale runtime file was unsafe")
            path.unlink()


def management_port_open() -> bool:
    try:
        with socket.create_connection(MANAGEMENT, timeout=0.25):
            return True
    except OSError:
        return False


def sudo_ready() -> bool:
    result = subprocess.run(
        ["/usr/bin/sudo", "-n", "true"],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def preflight_connect(
    *,
    management_port_open: Callable[[], bool],
    sudo_ready: Callable[[], bool],
    credential_loader: Callable[[], Credentials],
) -> Credentials:
    if management_port_open():
        raise RuntimeSafetyError("OpenVPN management port is already occupied")
    if not sudo_ready():
        raise RuntimeSafetyError("cached sudo authorization is required")
    return credential_loader()


def run_check(
    *,
    profile_loader: Callable[[], object],
    tls_checker: Callable[[object], bool],
) -> str:
    profile = profile_loader()
    if not tls_checker(profile):
        raise RuntimeSafetyError("VPN API TLS verification failed")
    return "CHECK_OK"


def verify_installation() -> str:
    if not APP_INFO.is_file() or not OPENVPN.is_file():
        raise RuntimeSafetyError("NAVER Cloud SSL VPN is not installed")
    try:
        with APP_INFO.open("rb") as handle:
            info = plistlib.load(handle)
    except (OSError, plistlib.InvalidFileException) as error:
        raise RuntimeSafetyError("VPN app metadata could not be read") from error
    if info.get("CFBundleIdentifier") != APP_BUNDLE_ID:
        raise RuntimeSafetyError("VPN app bundle identifier did not match")
    verified = subprocess.run(
        ["/usr/bin/codesign", "--verify", "--deep", "--strict", str(APP_PATH)],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if verified.returncode != 0:
        raise RuntimeSafetyError("VPN app code signature verification failed")
    details = subprocess.run(
        ["/usr/bin/codesign", "-dv", "--verbose=4", str(APP_PATH)],
        check=False,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    teams = [
        line.partition("=")[2]
        for line in details.stderr.splitlines()
        if line.startswith("TeamIdentifier=")
    ]
    if details.returncode != 0 or teams != [APP_TEAM_ID]:
        raise RuntimeSafetyError("VPN app signer Team ID did not match")
    version = info.get("CFBundleShortVersionString")
    if not isinstance(version, str) or not version:
        raise RuntimeSafetyError("VPN app version was missing")
    return version


def check_tls(profile: ProfileInfo) -> bool:
    context = ssl.create_default_context()
    try:
        with socket.create_connection((profile.remote_host, 8443), timeout=5) as raw:
            with context.wrap_socket(raw, server_hostname=profile.remote_host):
                return True
    except (OSError, ssl.SSLError):
        return False


def collect_metadata(version: str) -> ClientMetadata:
    try:
        with Path("/System/Library/CoreServices/SystemVersion.plist").open("rb") as handle:
            system = plistlib.load(handle)
        os_version = f"{system['ProductVersion']}-{system['ProductBuildVersion']}"
    except (OSError, KeyError, plistlib.InvalidFileException) as error:
        raise RuntimeSafetyError("macOS version metadata could not be read") from error
    result = subprocess.run(
        ["/sbin/ifconfig", "-a"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    macs = tuple(
        dict.fromkeys(
            match.group(1).replace(":", "-").upper()
            for match in re.finditer(r"\bether\s+([0-9a-fA-F:]{17})", result.stdout)
            if match.group(1) != "00:00:00:00:00:00"
        )
    )
    if not macs:
        raise RuntimeSafetyError("no local MAC address was found")
    return ClientMetadata(version, "darwin", os_version, macs)


def _monitor_openvpn(command: list[str], authentication_file: Path) -> int:
    child: subprocess.Popen[str] | None = None
    blocked = {signal.SIGINT, signal.SIGTERM, signal.SIGHUP}
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
    mask_restored = False
    connected = False
    try:
        child = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            bufsize=1,
        )
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        mask_restored = True
        assert child.stdout is not None
        print("CONNECTING", flush=True)
        for line in child.stdout:
            if "Initialization Sequence Completed" in line and not connected:
                connected = True
                authentication_file.unlink(missing_ok=True)
                print("CONNECTED", flush=True)
            elif "auth-failure" in line or "AUTH_FAILED" in line:
                print("AUTH_FAILED", flush=True)
            elif "TLS Error" in line:
                print("TLS_FAILED", flush=True)
        return child.wait()
    finally:
        if not mask_restored:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
        authentication_file.unlink(missing_ok=True)


@contextlib.contextmanager
def termination_guard(signal_api=signal):
    watched = (signal_api.SIGTERM, signal_api.SIGHUP)
    previous = {signum: signal_api.getsignal(signum) for signum in watched}

    def stop(_signum, _frame):
        raise KeyboardInterrupt

    for signum in watched:
        signal_api.signal(signum, stop)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal_api.signal(signum, handler)


def connect(credentials: Credentials, profile: ProfileInfo, version: str) -> int:
    cleanup_runtime(RUNTIME_DIR)
    result = authenticate(
        HttpsTransport(), profile, credentials, collect_metadata(version)
    )
    secret = credentials.password
    if result.otp_required:
        if not sys.stdin.isatty():
            raise RuntimeSafetyError("OTP_REQUIRED: rerun connect in the user's terminal")
        secret = getpass.getpass("OTP: ")
        if not secret:
            raise ConfigError("OTP was empty")
    with termination_guard():
        with contextlib.ExitStack() as stack:
            profile_bytes = (
                result.profile_bytes
                if result.profile_bytes is not None
                else profile.text.encode("utf-8")
            )
            active_profile = stack.enter_context(
                staged_profile(
                    RUNTIME_DIR,
                    result.profile_name or profile.path.name,
                    profile_bytes,
                )
            )
            authentication_file = stack.enter_context(
                auth_file(RUNTIME_DIR, credentials.username, secret)
            )
            command = build_openvpn_command(OPENVPN, active_profile, authentication_file)
            return _monitor_openvpn(command, authentication_file)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true", help="validate one profile and TLS")
    modes.add_argument("--auth-check", action="store_true", help="verify configured credentials")
    modes.add_argument("--connect", action="store_true", help="authenticate and run OpenVPN")
    parser.add_argument("--profile", help="exact installed profile alias for --check")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        version = verify_installation()
        if arguments.check:
            if not arguments.profile:
                raise ConfigError("--check requires --profile")
            profile_path = resolve_profile(PROFILES_DIR, arguments.profile)
            profile = load_profile(profile_path)
            status = run_check(
                profile_loader=lambda: profile,
                tls_checker=lambda loaded: check_tls(loaded),
            )
            summary = redacted_profile_summary(profile)
            print(f"{status} {json.dumps(summary, ensure_ascii=False)}")
            return 0

        if arguments.auth_check:
            credentials = load_credentials(arguments.env_file)
        else:
            credentials = preflight_connect(
                management_port_open=management_port_open,
                sudo_ready=sudo_ready,
                credential_loader=lambda: load_credentials(arguments.env_file),
            )
        profile_path = resolve_profile(PROFILES_DIR, credentials.profile)
        profile = load_profile(profile_path)
        if not check_tls(profile):
            raise RuntimeSafetyError("VPN API TLS verification failed")
        if arguments.auth_check:
            result = authenticate(
                HttpsTransport(), profile, credentials, collect_metadata(version)
            )
            print("OTP_REQUIRED" if result.otp_required else "AUTH_OK")
            return 0
        return connect(credentials, profile, version)
    except VpnError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
