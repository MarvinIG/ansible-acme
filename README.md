# ansible-acme

Produktionsnahes Ansible-Modul zur **einmaligen** Einrichtung von [acme.sh](https://github.com/acmesh-official/acme.sh) inklusive Cronjob, HTTP-Validation und Zertifikatsinstallation für **nginx** oder **apache**.

## Features

- Linux-only Guard (führt auf Nicht-Linux mit Fehler ab)
- Dependency-Checks vor Ausführung (`crontab`, `curl` oder `wget`, sowie `nginx`/`apache`)
- HTTP Challenge via `--nginx` oder `--apache` (kein DNS-Mode)
- Idempotent: wenn ACME-Cronjob schon existiert, wird nichts erneut initialisiert
- Installation + Zertifikatsausstellung + Zertifikatsdeployment (`--install-cert`) inkl. Reload-Command

## Modulpfad

`library/acme_bootstrap.py`

## Beispiel (nginx)

```yaml
- hosts: web
  become: true
  tasks:
    - name: ACME.sh einmalig einrichten
      acme_bootstrap:
        email: admin@example.com
        domain: example.com
        webserver: nginx
        keychain_file: /etc/ssl/private/example.key
        fullchain_file: /etc/ssl/certs/example.fullchain.pem
        reload_command: systemctl reload nginx
        ca_server: letsencrypt
```

## Beispiel (apache)

```yaml
- hosts: web
  become: true
  tasks:
    - name: ACME.sh einmalig einrichten
      acme_bootstrap:
        email: admin@example.org
        domain: example.org
        webserver: apache
        keychain_file: /etc/pki/tls/private/example.key
        fullchain_file: /etc/pki/tls/certs/example.fullchain.pem
        reload_command: systemctl reload httpd
        ca_server: letsencrypt
```

## Tests

Automatisierte Tests liegen unter `tests/test_acme_bootstrap.py` und prüfen:

- Command-Building (`nginx` Flag, Install-/Issue-/Install-Cert Sequenz)
- Cronjob-Erkennung (vorhanden / nicht vorhanden)
- Environment-Validation (wget ohne curl, fehlende Downloader)
