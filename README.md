
[![Docker Pulls](https://img.shields.io/docker/pulls/janweigang/threadbound)](https://hub.docker.com/r/janweigang/threadbound)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/Jan-Weigang/threadbound/docker-publish.yml?branch=main)](https://github.com/Jan-Weigang/threadbound/actions)
![Docker Image Size](https://img.shields.io/docker/image-size/janweigang/threadbound/latest)
[![Release](https://img.shields.io/github/v/release/Jan-Weigang/threadbound)](https://github.com/Jan-Weigang/threadbound/releases)

![Python](https://img.shields.io/badge/python-3.11-blue)
![HTMX](https://img.shields.io/badge/HTMX-1.9-blue)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

<img src="readme_assets/threadbound_logo.png" width="400"/>

## Wer?

In diesem Repo wird das Buchungssystem des 3TH entwickelt. 

Der [TableTopTreff Hannover](https://tabletoptreff-hannover.de/) ist mit über 200 Mitgliedern einer der größten Vereine Deutschlands für Tabletop-, Brett- und Rollenspiele. 

## Was?

Threadbound ist ein Buchungssystem. Unsere ~1500 Termine pro Jahr waren in einem üblichen Kalender nicht mehr vernünftig zu tracken: Häufige Doppelbuchungen, unhandliche Notizen für die Buchung bestimmter Tische, 20+ verschiedene Kalender für die Spielsysteme... 

Threadbound ist unsere Lösung für digitale Reservierungen. 

Es ist an die Kommunikationsplattform des Vereins (Discord) angebunden und spiegelt unsere Vereinsstruktur aus einem Vorstand und größerem Beirat mit regelmäßigen Stammtischen, Spielterminen und Turnieren sowie öffentlichen und geschlossenen Veranstaltungen auf beliebig vielen Tischen in zwei Räumlichkeiten wieder.

Demo: [Kalender des TableTopTreffs Hannover e. V.](https://3th-test.tabletoptreff.de/calendar/)

### **Architekturüberblick**

- **Frontend:** Jinja, HTML, HTMX, JS
- **Backend:** Python (*Flask, SQLAlchemy, APScheduler*)
- **Auth:** über Discord (*OAuth2*)
- **Datenbank:** SQLite


## Funktionen

#### Angeschlossen an Discord:
- SSO-Login mit übernahme der Server-Nicknames
- Rollenprüfung
- Automatische Posts mit übersichtlichem Embed und Thread für Absprachen zum Event
- Einstellbare Vorlaufzeit, wann das Event auf Discord gepostet wird
- Erinnerungsmeldungen für Ersteller und Absagemeldungen and Personen, die zugesagt haben
#### Funktionen der App:
- moderne Kalenderansicht auf allen Geräten
- Erstellen von Events mit Reservierung von Tischen in mehreren Räumen
- Zusagen und Absagen per App und Discord-Buttons möglich
- Unabsichtliche Doppelbuchungen werden geprüft und verhindert
#### Funktionen des Servers:
- Ausgeklügeltes System für Vormerkungen (Events, die noch Zustimmungen bedürfen)
- Discord-Tickets zur Absprache des Buchenden mit relevanten Personen bei:
  - Absichtliche Event-Überlagerung z. B. bei Turnieren (*bestehendes Event muss zustimmen*)
  - Zu große Buchungen z. B. 4+ Tische (*Vorstand muss zustimmen*)
- Änderungen im Kalender werden erkannt, Vormerkungen und Tickets entsprechend aufgelöst.
#### Sonstiges:
- Per Rolle zuweisbare Rechte "Stammtische" (regelmäßige Events) einzutragen.
- ICS Export für Events oder ganze Kalender
- Analytics der eingetragenen Events
- Leichte Bedienung, große Zahl an Shortcuts, Infozeile, Poweruser-Features

## Beispielbilder

### Hauptansicht in der App
<img src="readme_assets/hauptansicht.png" width="600"/>

### Ansicht einer Reservierung in der App
<img src="readme_assets/reservation_popup.png" width="600"/>

### Buchungs-Formular in der App
<img src="readme_assets/form.png" width="600"/>

### Discord Event-Post mit Zusagen, Absagen und Thread
<img src="readme_assets/discord_event_post.png" width="600"/>

### Mobile Ansicht der App
<img src="readme_assets/mobile_ansicht.png" width="400"/>

# Selbst aufsetzen

## Voraussetzungen

Die App lässt sich per Docker starten. Es wird ein Reverse Proxy empfohlen, der die für den SSO notwendige SSL-Verschlüsselung bereitstellt. 

Das Docker Image ist auf [Docker Hub](https://hub.docker.com/r/janweigang/threadbound) hinterlegt und can per Docker Compose genutzt werden:


### compose.yaml
```docker compose
services:
  threadbound:
    image: janweigang/threadbound:latest
    restart: unless-stopped
    ports:
      - "[PORT]:5000"
    volumes:
      - ./db_data:/usr/src/app/instance
    env_file:
      - .env
volumes:
  db_data:
```

### .env
```Environment variables
# Server Setup (Domain and Cookie Signing Key)
SERVER_NAME=
SECRET_KEY=

# Discord SSO (get these mostly from Discord Developer Portal)
REDIRECT_URI=
CLIENT_ID=
CLIENT_SECRET=

# Discord-Bot Setup
DISCORD_TOKEN=
PERMISSION_INT=309237721152

GUILD_ID=
TICKET_CATEGORY_ID=
TICKET_LOG_ID=

# Single ID
BOT_ROLE_ID=

# Role Setup - Single ID or comma-separated list of IDs
MEMBER_ROLE_ID=
BEIRAT_ROLE_ID=
VORSTAND_ROLE_ID=
ADMIN_ROLE_ID=

```


# Lizenz

Dieses Projekt wurde unter **GPL v3** veröffentlicht.