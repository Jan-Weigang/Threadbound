# Das Buchungssystem des TableTopTreff Hannover e. V.

## Wer?

In diesem Repo wird das Buchungssystem des 3TH entwickelt. 

Der [TableTopTreff Hannover](https://tabletoptreff-hannover.de/) ist mit über 200 Mitgliedern einer der größten Vereine Deutschlands für Tabletop-, Brett- und Rollenspiele. Dies war in einem üblichen Kalender nicht mehr vernünftig zu tracken. Dafür wurde dieses Buchungssystem entwickelt, welches an die Kommunikationsplattform des Vereins (Discord) angebunden ist.

## Funktionen

- SSO-Login per Discord
- Rollenprüfung über Discord
- Erstellen von Events mit Reservierung einer beliebigen Anzahl Tische in mehreren Räumen
- Automatische Discord-Posts mit übersichtlichem Embed und Thread für Absprachen zum Event
- Zusagen und Absagen per App und Discord-Buttons möglich
- Erinnerungsmeldungen für Ersteller und Absagemeldungen and Personen, die zugesagt haben
- Prävention von Kollisionen - Möglichkeit Kollisionen automatisch anzufragen und per Ticket in Discord zu klären
- Einschränkung der Buchungsgröße - Automatisches Anfragen für Erlaubnis beim Vorstand per Ticket in Discord
- Per Rolle zuweisbare Rechte "Stammtische" (Regelmäßige Events) einzutragen.
- Einstellbare Vorlaufzeit, wann das Event auf Discord gepostet wird

- Leichte Bedienung, Shortcuts, Infozeile, Mobiles Design

![alt text](readme_assets/hauptansicht.png)

![alt text](readme_assets/reservation_popup.png)

![alt text](readme_assets/form.png)

![alt text](readme_assets/discord_event_post.png)

![alt text](readme_assets/mobile_ansicht.png)

## Anleitung

[![Watch the video](https://img.youtube.com/vi/-Dex5jn4HPg/hqdefault.jpg)](https://www.youtube.com/watch?v=-Dex5jn4HPg)


## Voraussetzungen

## Einstellungen

```Environment variables
# Server Setup
OAUTHLIB_INSECURE_TRANSPORT=1
SERVER_NAME=
SECRET_KEY=

# Discord SSO
REDIRECT_URI=https://SERVERNAME/login/discord/authorized
CLIENT_ID=
CLIENT_SECRET=

# Discord Setup
DISCORD_TOKEN=
PERMISSION_INT=309237721152
GUILD_ID=
MEMBER_ROLE_ID=
BEIRAT_ROLE_ID=
VORSTAND_ROLE_ID=
MOD_ROLE_ID=
ADMIN_ROLE_ID=
TICKET_CATEGORY_ID=
TICKET_LOG_ID=

BOT_ROLE_ID=

```


### 🛠️ `.env` Konfigurationsübersicht

Folgende Umgebungsvariablen müssen gesetzt werden, um die Anwendung korrekt zu betreiben:


| Variable | Beschreibung |
|----------|--------------|
| Server Setup |
| `OAUTHLIB_INSECURE_TRANSPORT=1` | Aktiviert OAuth über HTTP für lokale Entwicklung. |
| `SERVER_NAME=` | Vollständiger Hostname (z. B. `kalender.beispiel.de`). |
| `SECRET_KEY=` | Geheimer Schlüssel für Flask Sessions. Sollte ein langer, zufälliger Wert sein (z. B. mit `openssl rand -hex 32` erzeugt). |
| Discord - SSO |
| `REDIRECT_URI=` | Muss mit der Redirect-URI in deiner Discord Developer App übereinstimmen. Typisch: `https://<deinserver>/login/discord/authorized` |
| `CLIENT_ID=` | Client ID aus deiner Discord Developer App |
| `CLIENT_SECRET=` | Client Secret aus deiner Discord Developer App |
| Discord - Bot |
| `DISCORD_TOKEN=` | Bot-Token für deinen Discord-Bot (Discord Developer)  |
| `PERMISSION_INT=309237721152` | Berechtigungs-Integer für den Bot-Invite-Link (legt fest, was der Bot darf) |
| `GUILD_ID=` | Die Discord Server-ID.  |
| `MEMBER_ROLE_ID=` | Rollen-ID für die Mitgliederrolle (Berechtigt Events zu erstellen) |
| `BEIRAT_ROLE_ID=` | Rollen-ID für gehobene Rolle (Berechtigt Stammtische zu erstellen) |
| `VORSTAND_ROLE_ID=` | Rollen-ID für höchste Zugriffsrechte (Berechtigt, Events zu Löschen und zuzusagen) |
| `MOD_ROLE_ID=` | useless atm |
| `ADMIN_ROLE_ID=` | Rollen-ID für Admins (berechtigt, Admin-Views zu sehen und Datenbankänderungen zu tätigen) |
| `TICKET_CATEGORY_ID=` | Kategorie, in der der Bot berechtigt ist, Channel zu verwalten.
| `TICKET_LOG_ID=` | Channel in welchen die Logs der geschlossenen Tickets als .txt hinterlegt werden sollen |
| `BOT_ROLE_ID=`| Rollen-ID des Bots auf dem Discordserver. 

---


Der aktuelle Branch der Entwicklung ist "htmx"