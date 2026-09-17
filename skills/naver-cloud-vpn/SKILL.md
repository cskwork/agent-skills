---
name: naver-cloud-vpn
description: Use when a user asks to inspect, verify credentials for, connect, or troubleshoot the installed NAVER Cloud SSL VPN client on macOS without GUI automation.
---

# NAVER Cloud VPN

Use the bundled Python script. It mirrors the installed client's existing-profile flow without Computer Use, AppleScript, shell interpolation, disabled TLS, or persistent authentication files.

## Authorization

- `--check` is read-only. It does not read `.env` or authenticate.
- `--auth-check` sends the configured ID and password to the selected profile's verified NAVER VPN endpoint. Run it only when the user explicitly requests credential verification.
- Ask for confirmation immediately before `--connect`. It changes network access and invokes the bundled OpenVPN through cached `sudo` authorization.
- Never accept credentials in chat, command arguments, process environment variables, or logs.

## Local configuration

Store this file at `~/.config/naver-cloud-vpn/.env` with mode `0600`:

```dotenv
NAVER_VPN_PROFILE=AIDT 개발
NAVER_VPN_USERNAME=your-id
NAVER_VPN_PASSWORD=your-password
```

Use an exact alias from the installed client's `alias.json`. OTP is never stored. If the server requires OTP, `--connect` asks through `getpass` in the user's terminal and refuses non-interactive input.

## Commands

```bash
python3 ~/.codex/skills/naver-cloud-vpn/scripts/naver_vpn.py --check --profile "AIDT 개발"
python3 ~/.codex/skills/naver-cloud-vpn/scripts/naver_vpn.py --auth-check
sudo -v  # user runs this in a terminal immediately before an approved connection
python3 ~/.codex/skills/naver-cloud-vpn/scripts/naver_vpn.py --connect
```

The connection stays attached to the command. `Ctrl+C` stops it. The script refuses an occupied OpenVPN management port and removes temporary profile and authentication files on every handled exit.

Treat `AUTH_OK` as credential proof only. Treat `CONNECTED` as tunnel-process proof only. Route behavior remains unverified unless separately checked.
