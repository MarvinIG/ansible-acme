from library.acme_bootstrap import _build_commands, _cronjob_exists, _validate_environment


class DummyModule:
    def __init__(self, command_results=None, params=None):
        self.command_results = command_results or {}
        self.params = params or {}
        self.failed = None

    def run_command(self, cmd):
        key = tuple(cmd)
        return self.command_results.get(key, (1, "", "not found"))

    def fail_json(self, **kwargs):
        self.failed = kwargs
        raise RuntimeError(kwargs.get("msg", "failed"))


def test_build_commands_nginx():
    text, cmds = _build_commands(
        {
            "acme_install_url": "https://get.acme.sh",
            "email": "admin@example.com",
            "acme_home": "/root/.acme.sh",
            "domain": "example.com",
            "webserver": "nginx",
            "ca_server": "letsencrypt",
            "keychain_file": "/tmp/key.pem",
            "fullchain_file": "/tmp/full.pem",
            "reload_command": "systemctl reload nginx",
        }
    )

    assert len(cmds) == 3
    assert "--nginx" in text[1]
    assert cmds[2][0] == "/root/.acme.sh/acme.sh"


def test_cronjob_exists_detects_user_cron():
    module = DummyModule(
        command_results={
            tuple(["sh", "-c", "crontab -l 2>/dev/null | grep -E 'acme\\.sh.+--cron'"]): (0, "ok", "")
        }
    )
    assert _cronjob_exists(module) is True


def test_cronjob_exists_detects_absence():
    module = DummyModule(command_results={})
    assert _cronjob_exists(module) is False


def test_validate_environment_accepts_wget_without_curl():
    results = {
        tuple(["sh", "-c", "command -v curl"]): (1, "", ""),
        tuple(["sh", "-c", "command -v wget"]): (0, "/usr/bin/wget", ""),
        tuple(["sh", "-c", "command -v crontab"]): (0, "/usr/bin/crontab", ""),
        tuple(["sh", "-c", "command -v nginx"]): (0, "/usr/sbin/nginx", ""),
    }
    module = DummyModule(command_results=results, params={"ansible_system": "Linux"})

    _validate_environment(module, "nginx", [])


def test_validate_environment_fails_without_download_tool():
    results = {
        tuple(["sh", "-c", "command -v curl"]): (1, "", ""),
        tuple(["sh", "-c", "command -v wget"]): (1, "", ""),
    }
    module = DummyModule(command_results=results, params={"ansible_system": "Linux"})

    try:
        _validate_environment(module, "apache", [])
        assert False, "expected failure"
    except RuntimeError as err:
        assert "weder curl noch wget" in str(err)
