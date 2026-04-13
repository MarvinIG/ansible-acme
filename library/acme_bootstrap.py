#!/usr/bin/python

from __future__ import annotations

from typing import Dict, List, Tuple

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = r"""
---
module: acme_bootstrap
short_description: Einmalige Einrichtung von ACME.sh mit HTTP-Validierung und Cronjob
version_added: "1.0.0"
description:
  - Installiert ACME.sh auf Linux Hosts und richtet Zertifikatsausstellung via HTTP-Validation ein.
  - Unterstützt sowohl NGINX als auch Apache mittels C(--nginx) bzw. C(--apache).
  - Führt die Initialisierung nur einmal aus und erkennt vorhandene ACME-Cronjobs idempotent.
options:
  email:
    description: E-Mail-Adresse für ACME Account.
    required: true
    type: str
  domain:
    description: Domain für das Zertifikat.
    required: true
    type: str
  webserver:
    description: Webserver Integration für HTTP-Validation.
    required: true
    type: str
    choices: [nginx, apache]
  keychain_file:
    description: Zielpfad für den privaten Schlüssel.
    required: true
    type: path
  fullchain_file:
    description: Zielpfad für die Fullchain.
    required: true
    type: path
  reload_command:
    description: Kommando zum Reload des Webservers nach Zertifikatsinstallation.
    required: true
    type: str
  ca_server:
    description: ACME CA Server (z. B. letsencrypt, zerossl).
    required: false
    type: str
    default: letsencrypt
  acme_home:
    description: Installationsverzeichnis für ACME.sh.
    required: false
    type: path
    default: /root/.acme.sh
  acme_install_url:
    description: Installer URL für ACME.sh.
    required: false
    type: str
    default: https://get.acme.sh
  required_commands:
    description: Zusätzliche Kommandos, die vor Ausführung vorhanden sein müssen.
    required: false
    type: list
    elements: str
    default: []
author:
  - Codex
"""

EXAMPLES = r"""
- name: ACME.sh initialisieren (NGINX)
  acme_bootstrap:
    email: admin@example.com
    domain: example.com
    webserver: nginx
    keychain_file: /etc/ssl/private/example.key
    fullchain_file: /etc/ssl/certs/example.fullchain.pem
    reload_command: systemctl reload nginx
    ca_server: letsencrypt

- name: ACME.sh initialisieren (Apache)
  acme_bootstrap:
    email: admin@example.com
    domain: example.org
    webserver: apache
    keychain_file: /etc/pki/tls/private/example.key
    fullchain_file: /etc/pki/tls/certs/example.fullchain.pem
    reload_command: systemctl reload httpd
    ca_server: letsencrypt
"""

RETURN = r"""
changed:
  description: Gibt an, ob Initialisierung ausgeführt wurde.
  type: bool
  returned: always
commands:
  description: Ausgeführte Kommandos.
  type: list
  elements: str
  returned: always
message:
  description: Ergebnistext.
  type: str
  returned: always
"""


def _command_exists(module: AnsibleModule, command: str) -> bool:
    rc, _, _ = module.run_command(["sh", "-c", f"command -v {command}"])
    return rc == 0


def _validate_environment(module: AnsibleModule, webserver: str, extra_commands: List[str]) -> None:
    if module.params.get("ansible_system") and module.params["ansible_system"].lower() != "linux":
        module.fail_json(msg="Dieses Modul unterstützt nur Linux.")

    if webserver not in ("nginx", "apache"):
        module.fail_json(msg="webserver muss 'nginx' oder 'apache' sein.")

    dependencies = ["crontab"]
    if _command_exists(module, "curl"):
        pass
    elif _command_exists(module, "wget"):
        pass
    else:
        module.fail_json(msg="Fehlende Dependency: weder curl noch wget verfügbar.")

    dependencies.extend(extra_commands)
    dependencies.append(webserver)

    missing = [dep for dep in dependencies if not _command_exists(module, dep)]
    if missing:
        module.fail_json(msg=f"Fehlende Dependencies: {', '.join(sorted(set(missing)))}")


def _cronjob_exists(module: AnsibleModule) -> bool:
    checks = [
        ["sh", "-c", "crontab -l 2>/dev/null | grep -E 'acme\\.sh.+--cron'"],
        ["sh", "-c", "test -f /etc/cron.d/acme.sh"],
    ]

    for command in checks:
        rc, _, _ = module.run_command(command)
        if rc == 0:
            return True
    return False


def _build_commands(params: Dict[str, str]) -> Tuple[List[str], List[List[str]]]:
    install_cmd = [
        "sh",
        "-c",
        (
            "curl -fsSL {url} | sh -s email={email}"
            " || wget -qO- {url} | sh -s email={email}"
        ).format(url=params["acme_install_url"], email=params["email"]),
    ]

    challenge_flag = "--nginx" if params["webserver"] == "nginx" else "--apache"
    acme_bin = f"{params['acme_home']}/acme.sh"

    issue_cmd = [
        acme_bin,
        "--issue",
        "-d",
        params["domain"],
        challenge_flag,
        "--server",
        params["ca_server"],
    ]

    install_cert_cmd = [
        acme_bin,
        "--install-cert",
        "-d",
        params["domain"],
        "--key-file",
        params["keychain_file"],
        "--fullchain-file",
        params["fullchain_file"],
        "--reloadcmd",
        params["reload_command"],
    ]

    return [" ".join(install_cmd), " ".join(issue_cmd), " ".join(install_cert_cmd)], [
        install_cmd,
        issue_cmd,
        install_cert_cmd,
    ]


def run_module() -> None:
    module_args = dict(
        email=dict(type="str", required=True),
        domain=dict(type="str", required=True),
        webserver=dict(type="str", required=True, choices=["nginx", "apache"]),
        keychain_file=dict(type="path", required=True),
        fullchain_file=dict(type="path", required=True),
        reload_command=dict(type="str", required=True),
        ca_server=dict(type="str", required=False, default="letsencrypt"),
        acme_home=dict(type="path", required=False, default="/root/.acme.sh"),
        acme_install_url=dict(type="str", required=False, default="https://get.acme.sh"),
        required_commands=dict(type="list", elements="str", required=False, default=[]),
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    _validate_environment(module, module.params["webserver"], module.params["required_commands"])

    if _cronjob_exists(module):
        module.exit_json(changed=False, commands=[], message="ACME.sh Cronjob bereits vorhanden. Keine Initialisierung nötig.")

    command_text, commands = _build_commands(module.params)

    if module.check_mode:
        module.exit_json(changed=True, commands=command_text, message="Check-Mode: ACME.sh würde initialisiert werden.")

    for command in commands:
        rc, stdout, stderr = module.run_command(command)
        if rc != 0:
            module.fail_json(
                msg=f"Kommando fehlgeschlagen: {' '.join(command)}",
                rc=rc,
                stdout=stdout,
                stderr=stderr,
                commands=command_text,
            )

    module.exit_json(changed=True, commands=command_text, message="ACME.sh erfolgreich initialisiert.")


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
