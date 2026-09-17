from __future__ import annotations

import base64
import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts/naver_vpn.py"
SPEC = importlib.util.spec_from_file_location("naver_vpn", SCRIPT)
assert SPEC and SPEC.loader
vpn = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = vpn
SPEC.loader.exec_module(vpn)


SAFE_PROFILE = """\
client
dev tun
proto tcp4-client
remote vpn.example.test
port 12361
auth-user-pass
auth-nocache
management 127.0.0.1 7501
remote-cert-tls server
pull-filter ignore redirect-gateway
<ca>
-----BEGIN CERTIFICATE-----
synthetic-test-certificate
-----END CERTIFICATE-----
</ca>
"""


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def post(self, request):
        self.calls.append(request)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class EnvTests(unittest.TestCase):
    def test_parser_preserves_password_symbols_and_requires_profile(self):
        credentials = vpn.parse_env_text(
            "NAVER_VPN_PROFILE=AIDT 개발\n"
            "NAVER_VPN_USERNAME=user.name\n"
            "NAVER_VPN_PASSWORD='a # b=c\\d'\n"
        )
        self.assertEqual(credentials.profile, "AIDT 개발")
        self.assertEqual(credentials.username, "user.name")
        self.assertEqual(credentials.password, "a # b=c\\d")

    def test_parser_rejects_unknown_otp_and_duplicate_keys(self):
        with self.assertRaises(vpn.ConfigError):
            vpn.parse_env_text(
                "NAVER_VPN_PROFILE=AIDT 개발\n"
                "NAVER_VPN_USERNAME=user\n"
                "NAVER_VPN_PASSWORD=secret\n"
                "NAVER_VPN_OTP=123456\n"
            )
        with self.assertRaises(vpn.ConfigError):
            vpn.parse_env_text(
                "NAVER_VPN_PROFILE=AIDT 개발\n"
                "NAVER_VPN_USERNAME=one\n"
                "NAVER_VPN_USERNAME=two\n"
                "NAVER_VPN_PASSWORD=secret\n"
            )

    def test_loader_requires_private_regular_non_symlink_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / ".env"
            env_file.write_text(
                "NAVER_VPN_PROFILE=AIDT 개발\n"
                "NAVER_VPN_USERNAME=user\n"
                "NAVER_VPN_PASSWORD=secret\n",
                encoding="utf-8",
            )
            env_file.chmod(0o644)
            with self.assertRaises(vpn.ConfigError):
                vpn.load_credentials(env_file)
            env_file.chmod(0o600)
            link = root / "linked.env"
            link.symlink_to(env_file)
            with self.assertRaises(vpn.ConfigError):
                vpn.load_credentials(link)


class ProfileTests(unittest.TestCase):
    def write_profiles(self, root: Path):
        alias_file = root / "alias.json"
        alias_file.write_text(
            json.dumps({"vpn2361": "AIDT 개발"}, ensure_ascii=False),
            encoding="utf-8",
        )
        profile = root / "vpn2361.ovpn"
        profile.write_text(SAFE_PROFILE, encoding="utf-8")
        alias_file.chmod(0o600)
        profile.chmod(0o600)
        return profile

    def test_resolves_exact_alias_inside_profile_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            expected = self.write_profiles(root)
            resolved = vpn.resolve_profile(root, "AIDT 개발")
            self.assertEqual(resolved, expected.resolve())
            with self.assertRaises(vpn.ProfileError):
                vpn.resolve_profile(root, "../vpn2361")

    def test_parses_safe_profile_and_redacts_host(self):
        profile = vpn.parse_profile_text(SAFE_PROFILE, Path("vpn2361.ovpn"))
        self.assertEqual(profile.remote_host, "vpn.example.test")
        self.assertEqual(profile.remote_port, 12361)
        self.assertEqual(profile.management, ("127.0.0.1", 7501))
        summary = vpn.redacted_profile_summary(profile)
        self.assertNotIn("vpn.example.test", json.dumps(summary))

    def test_rejects_dangerous_or_ambiguous_directives(self):
        for extra in (
            "script-security 2\nup /tmp/evil\n",
            "plugin /tmp/evil.so\n",
            "remote second.example.test\n",
            "management 0.0.0.0 7501\n",
            "management 127.0.0.1 7501\n",
            "remote third.example.test not-a-port\n",
            "remote-cert-tls client\n",
        ):
            with self.subTest(extra=extra):
                with self.assertRaises(vpn.ProfileError):
                    vpn.parse_profile_text(
                        SAFE_PROFILE + extra,
                        Path("vpn2361.ovpn"),
                    )


class ApiTests(unittest.TestCase):
    def metadata(self):
        return vpn.ClientMetadata(
            version="1.1.3",
            os_name="darwin",
            os_version="15.6.1-24G90",
            mac=("AA-BB-CC-DD-EE-FF",),
        )

    def credentials(self):
        return vpn.Credentials("AIDT 개발", "user-canary", "password-canary")

    def profile(self):
        return vpn.parse_profile_text(SAFE_PROFILE, Path("vpn2361.ovpn"))

    def test_builds_exact_v3_request_without_secrets_in_headers(self):
        request = vpn.build_v3_request(
            self.profile(), self.credentials(), self.metadata()
        )
        self.assertEqual(request.path, "/api/v3/authstate")
        self.assertEqual(request.headers["Api-Version"], "1")
        self.assertEqual(request.body["type"], "connect")
        self.assertEqual(request.body["ovpn_file_name"], "vpn2361.ovpn")
        self.assertEqual(request.body["user_id"], "user-canary")
        self.assertEqual(request.body["passwd"], "password-canary")
        self.assertNotIn("password-canary", json.dumps(request.headers))

    def test_falls_back_to_v2_only_for_http_404(self):
        transport = FakeTransport(
            [vpn.HttpStatusError(404), {"success": True, "state": ""}]
        )
        result = vpn.authenticate(
            transport, self.profile(), self.credentials(), self.metadata()
        )
        self.assertFalse(result.otp_required)
        self.assertEqual([call.path for call in transport.calls], [
            "/api/v3/authstate",
            "/api/v2/authstate",
        ])
        with self.assertRaises(vpn.HttpStatusError):
            vpn.authenticate(
                FakeTransport([vpn.HttpStatusError(500)]),
                self.profile(),
                self.credentials(),
                self.metadata(),
            )

        version_transport = FakeTransport(
            [
                {"success": False, "state": "", "err_msg": "api version mismatch"},
                {"success": True, "state": ""},
            ]
        )
        version_result = vpn.authenticate(
            version_transport, self.profile(), self.credentials(), self.metadata()
        )
        self.assertEqual(version_result.api_version, 2)

    def test_otp_and_optional_profile_refresh_are_validated(self):
        body = SAFE_PROFILE.encode("utf-8")
        response = {
            "success": True,
            "state": "otp-state",
            "profile_name": "vpn2361.ovpn",
            "profile_body": base64.b64encode(body).decode("ascii"),
        }
        result = vpn.validate_auth_response(response, expected_name="vpn2361.ovpn")
        self.assertTrue(result.otp_required)
        self.assertEqual(result.profile_bytes, body)
        with self.assertRaises(vpn.ApiError):
            vpn.validate_auth_response(
                {**response, "profile_name": "../../evil.ovpn"},
                expected_name="vpn2361.ovpn",
            )

    def test_rejects_unexpected_response_fields_and_never_formats_secrets(self):
        with self.assertRaises(vpn.ApiError) as caught:
            vpn.validate_auth_response(
                {"success": True, "state": "", "unexpected": "password-canary"},
                expected_name="vpn2361.ovpn",
            )
        self.assertNotIn("password-canary", str(caught.exception))


class RuntimeTests(unittest.TestCase):
    class FakeSignal:
        SIGTERM = 15
        SIGHUP = 1

        def __init__(self):
            self.handlers = {self.SIGTERM: "old-term", self.SIGHUP: "old-hup"}

        def getsignal(self, signum):
            return self.handlers[signum]

        def signal(self, signum, handler):
            old = self.handlers[signum]
            self.handlers[signum] = handler
            return old

    def test_staged_profile_is_private_validated_and_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with vpn.staged_profile(root, "vpn2361.ovpn", SAFE_PROFILE.encode()) as path:
                self.assertTrue(path.exists())
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertFalse(path.exists())

    def test_runtime_directory_rejects_symlink_and_broad_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            broad = root / "broad"
            broad.mkdir(mode=0o755)
            with self.assertRaises(vpn.RuntimeSafetyError):
                vpn.ensure_private_runtime(broad)
            private = root / "private"
            private.mkdir(mode=0o700)
            link = root / "link"
            link.symlink_to(private, target_is_directory=True)
            with self.assertRaises(vpn.RuntimeSafetyError):
                vpn.ensure_private_runtime(link)

    def test_cleanup_removes_only_owned_stale_runtime_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "runtime"
            root.mkdir(mode=0o700)
            stale_auth = root / "auth-stale.txt"
            stale_profile = root / "profile-stale.ovpn"
            stale_auth.write_text("synthetic")
            stale_profile.write_text("synthetic")
            vpn.cleanup_runtime(root)
            self.assertFalse(stale_auth.exists())
            self.assertFalse(stale_profile.exists())

    def test_termination_guard_handles_term_and_hup_then_restores(self):
        for signum in (self.FakeSignal.SIGTERM, self.FakeSignal.SIGHUP):
            with self.subTest(signum=signum):
                fake = self.FakeSignal()
                with self.assertRaises(KeyboardInterrupt):
                    with vpn.termination_guard(fake):
                        fake.handlers[signum](signum, None)
                self.assertEqual(fake.handlers[self.FakeSignal.SIGTERM], "old-term")
                self.assertEqual(fake.handlers[self.FakeSignal.SIGHUP], "old-hup")

    def test_monitor_blocks_signals_until_child_is_owned(self):
        class FakeChild:
            stdout = []

            def poll(self):
                return 0

            def wait(self, timeout=None):
                return 0

        with tempfile.TemporaryDirectory() as directory:
            auth = Path(directory) / "auth.txt"
            auth.write_text("synthetic")
            with mock.patch.object(vpn.subprocess, "Popen", return_value=FakeChild()), mock.patch.object(
                vpn.signal,
                "pthread_sigmask",
                side_effect=[{"old-mask"}, None],
            ) as mask:
                self.assertEqual(vpn._monitor_openvpn(["synthetic"], auth), 0)
            self.assertEqual(mask.call_args_list[0].args[0], vpn.signal.SIG_BLOCK)
            self.assertEqual(mask.call_args_list[1].args, (vpn.signal.SIG_SETMASK, {"old-mask"}))
            self.assertFalse(auth.exists())

    def test_auth_file_is_exclusive_private_and_removed_on_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            captured = None
            with self.assertRaisesRegex(RuntimeError, "stop"):
                with vpn.auth_file(root, "user-canary", "password-canary") as path:
                    captured = path
                    self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
                    self.assertEqual(path.read_text(), "user-canary\npassword-canary")
                    raise RuntimeError("stop")
            self.assertIsNotNone(captured)
            self.assertFalse(captured.exists())

    def test_openvpn_command_is_argv_only_and_contains_no_secret(self):
        command = vpn.build_openvpn_command(
            Path("/Applications/NAVER Cloud SSL VPN.app/Contents/vpn/openvpn"),
            Path("/tmp/profile.ovpn"),
            Path("/tmp/auth.txt"),
        )
        self.assertEqual(command[:4], [
            "/usr/bin/sudo",
            "-n",
            "--",
            "/Applications/NAVER Cloud SSL VPN.app/Contents/vpn/openvpn",
        ])
        self.assertNotIn("user-canary", command)
        self.assertNotIn("password-canary", command)
        self.assertNotIn("sh", command)
        self.assertNotIn("osascript", command)

    def test_occupied_management_port_fails_before_credentials_load(self):
        events = []

        def forbidden_loader():
            events.append("credentials")
            raise AssertionError("credential file was read")

        with self.assertRaises(vpn.RuntimeSafetyError):
            vpn.preflight_connect(
                management_port_open=lambda: True,
                sudo_ready=lambda: events.append("sudo") or True,
                credential_loader=forbidden_loader,
            )
        self.assertEqual(events, [])

    def test_check_mode_never_reads_credentials_or_runs_auth_or_sudo(self):
        events = []
        status = vpn.run_check(
            profile_loader=lambda: events.append("profile") or object(),
            tls_checker=lambda profile: events.append("tls") or True,
        )
        self.assertEqual(status, "CHECK_OK")
        self.assertEqual(events, ["profile", "tls"])


if __name__ == "__main__":
    unittest.main()
