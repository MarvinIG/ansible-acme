Du bist professioneller Entwickler und willst ein produktionsfertiges Ansible Modul entwickeln, welches einmalig das ACME.sh Script einrichtet mit Cronjob und allem. Die nötigen Informationen wie EMail Adresse, Domain Name, Web Server, KeyChain File, Full Chain File, reload command, CA Authority Server werden per Modulparameter eingeladen (vars).
Arbeite mit http Validation (nicht DNS).
Verwende den nginx/apache Modues
Das ganze soll sowohl für nginx als auch apache funktionieren.
Dieser Task soll idempotent sein, also nur einmal ausgeführt werden. Falls der Cronjob bereits läuft, wird es entsprechend nicht erneut initialisiert.
Sowohl das Betriebssystem (=Linux) als auch die Software Dependencies auf der Maschine (z.B. wget/curl) sollen vor Durchführung des Scripts geprüft werden 