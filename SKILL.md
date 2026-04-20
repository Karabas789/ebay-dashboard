[SKILL.md](https://github.com/user-attachments/files/26876917/SKILL.md)
---
name: ebay-dashboard-erstellung
description: >
  Verwende diesen Skill bei JEDER Anfrage rund um das eBay-Dashboard, SvelteKit-Migration,
  n8n-Workflows oder die fünf Kernfunktionen: automatische eBay-Nachrichten nach Kauf,
  Rechnungserstellung, KI-gestützte Angebotserstellung, Auto-Repricing und Buchhaltungsmodul.
  Trigger-Situationen: „Dashboard bauen", „Dashboard erweitern", „neuen Tab einbauen",
  „neuen Workflow bauen", „Rechnung erstellen", „Rechnungsvorlage",
  „eBay Nachricht automatisch senden", „Repricing einrichten", „Preisanpassung",
  „Angebot mit KI erstellen", „eBay Listing generieren", „Dashboard anpassen",
  „Dashboard_neu_v8", „SvelteKit portieren", „Svelte 5", „Seite portieren",
  „Bestellungen verarbeiten", „Lagerbestand synchronisieren",
  „n8n Webhook erstellen", „Nachrichtenvorlage bearbeiten", „Workflow debuggen",
  „eBay API Aufruf", „Tab hinzufügen", „Modal bauen", „CSS anpassen",
  „Deploy", „Docker build", „git push",
  „Buchhaltung", „Eingangsrechnung", „EÜR", „Einnahmenüberschussrechnung",
  „UStVA", „Umsatzsteuer-Voranmeldung", „OCR", „Rechnungserkennung",
  „Quittung hochladen", „Ausgaben erfassen", „Vorsteuer", „Zahllast",
  „E-Mail Import", „IMAP", „Posteingang", „email_inbox".
  Enthält vollständige Referenz zu Technologie-Stack, allen n8n-Workflows,
  Datenbankschema, Design-System v3, SvelteKit-Patterns und Deploy-Prozess.
connected: false
metadata:
  author: Vitali
  version: '7.0'
  based_on: Wissensbasis (Stand 2026-04-19)
---

# eBay-Dashboard: Vollständiger Entwicklungs-Skill

> **Änderungshistorie v7.0:** E-Mail-Rechnungsimport (Phase 2) komplett fertig.
> Neue Tabelle `email_inbox`, 3 neue Workflows (WF-BH-INBOX-HELPER, WF-BH-INBOX-ACTION, WF-BH-05),
> Frontend `/buchhaltung/eingang` mit Posteingang-Tab, S3-Integration für Anhänge.
> Object Storage + Server-Wartung aus v6 übernommen.

---

## 1. Projekt-Übersicht

### Firma & Kontext
- **Firma:** Import & Produkte Vertrieb Inh. Oxana Dubs
- **Nutzer:** Vitali
- **Zweck:** eBay-Shop-Verwaltung mit Dashboard für Nachrichten, Produkte, Bestellungen, Rechnungen und KI-Kundenservice

### Technologie-Stack

| Komponente | Details |
|---|---|
| **Frontend** | SvelteKit 2 (`ebay.ai-online.cloud`) |
| **Framework** | SvelteKit 2, Svelte 5, Vite 6, adapter-node 5, `type: module` |
| **Backend** | n8n Workflows (Webhooks + PostgreSQL + eBay Trading API) |
| **Datenbank** | PostgreSQL |
| **eBay API** | Trading API (XML/SOAP) |
| **KI** | Mistral API (Kundenservice), Claude/Octopus AI (Angebotserstellung) |
| **PDF-Service** | Gotenberg (`gotenberg.ai-online.cloud`) — HTML→PDF |
| **E-Mail-Service** | Node.js/Express/Nodemailer (`email.ai-online.cloud`) |
| **Proxy/Deploy** | Coolify + Traefik v3.6.5, Docker-Netzwerk: `coolify` |
| **VCS** | GitHub: `https://github.com/Karabas789/ebay-dashboard` |

### URLs & Zugangsdaten

| Parameter | Wert |
|---|---|
| n8n-Host | `https://n8n.ai-online.cloud` |
| API-Basis-URL | `https://n8n.ai-online.cloud/webhook` |
| Dashboard-URL | `https://ebay.ai-online.cloud` |
| Gotenberg-URL | `https://gotenberg.ai-online.cloud` |
| E-Mail-Service-URL | `https://email.ai-online.cloud` |
| PostgreSQL-Credential | `ebay_automation`, ID: `4yOALkbLmo3zuewo` |
| eBay App-Name | `VitaliDu-TestAPI-PRD-2b448418d-05f39944` |
| Server-Pfad | `/opt/ebay-dashboard` |
| n8n-Container | `n8n-x04008o88c4w0cg4gwkskkk8` |
| n8n Coolify-Compose | `/data/coolify/services/x04008o88c4w0cg4gwkskkk8/docker-compose.yml` |

### Service-Endpunkte

**E-Mail-Service** (`email.ai-online.cloud`):
| Methode | Pfad | Funktion |
|---|---|---|
| POST | `/send` | E-Mail senden |
| POST | `/test` | SMTP-Verbindung testen |
| GET | `/health` | Health Check |

**Gotenberg** (`gotenberg.ai-online.cloud`):
| Methode | Pfad | Funktion |
|---|---|---|
| POST | `/forms/chromium/convert/html` | HTML zu PDF konvertieren |

---

## 2. Regeln — IMMER LESEN BEVOR CODE GESCHRIEBEN WIRD

1. **Auth-Pattern respektieren** — Jeder n8n-Webhook erwartet `Authorization: Bearer <token>`.
2. **Dashboard-Konventionen einhalten** — CSS-Variablen nutzen (`var(--primary)`, `var(--surface)` etc.).
3. **SvelteKit-Patterns** — Svelte 5 Syntax (`$state`, `$derived`, `bind:value`).
4. **Fehlerbehandlung** — Jeder fetch/API-Call braucht try/catch.
5. **n8n-Workflows als JSON** — Kompletten n8n-Export-JSON zum direkten Import liefern.
6. **Kein Raten** — Wenn Infos fehlen, fragen.
7. **PostgreSQL-Credential** — ALLE Postgres-Nodes MÜSSEN `ebay_automation` (ID: `4yOALkbLmo3zuewo`) verwenden.
8. **n8n Active Version** — Nach Speichern Toggle aus/an schalten.
9. **Änderungen kompakt im Chat** — Direkt das Delta zeigen, kein Code doppelt.
10. **DB-Spaltennamen prüfen** — Vor jedem SQL die echten Spaltennamen aus Abschnitt 3 prüfen.
11. **Token-Helper im Frontend** — `getToken()` aus `$lib/api.js` verwenden, NICHT `localStorage.getItem('token')` direkt.
12. **Frontend nutzt apiCall()** — `apiCall('/endpoint', { body })` aus `$lib/api.js`, NICHT eigene fetch-Calls für n8n-Webhooks.

---

## 3. Datenbank-Schema

**Datenbank:** PostgreSQL | **Credential:** `ebay_automation` (ID: `4yOALkbLmo3zuewo`)

### Tabelle: `produkte`
| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `user_id` | Benutzer-Zuordnung |
| `ebay_artikel_id` | eBay-Artikel-ID |
| `name` | Produktname |
| `preis` | Preis |
| `lagerbestand` | Tatsächlicher Lagerbestand |
| `min_lagerbestand` | eBay-Anzeigemenge |
| `artikelnummer` | Interne Artikelnummer |
| `basisname` | Basisname des Produkts |
| `variante` | Variantenbezeichnung |
| `bild_url` | Produktbild-URL |
| `aktiv` | Aktiv-Flag |
| `aktualisiert_am` | Zeitstempel |

### Tabelle: `users`
| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `email` | E-Mail-Adresse |
| `ebay_user_id` | eBay Benutzer-ID |
| `access_token` | Auth-Token |
| `plan` | Abo-Plan |
| `trial_end` | Ende der Testphase |

### Rechnungssystem-Tabellen

#### `invoices`
| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `user_id` | Benutzer-Zuordnung |
| `order_id` | Bestell-ID |
| `rechnung_typ` | `rechnung` oder `storno` |
| `rechnung_nr` | Rechnungsnummer |
| `netto_betrag, steuersatz, steuer_betrag, brutto_betrag` | Beträge |
| `pdf_base64` | PDF als Base64 |
| `pdf_generiert_am` | Zeitstempel PDF-Generierung |
| `status` | `erstellt` / `gesendet` / `storniert` |

> ⚠️ `invoices`-Tabelle hat KEINE Spalte `created_at`. Für Datums-Queries `pdf_generiert_am` verwenden!

#### `user_firmendaten`
| Spalte | Beschreibung |
|---|---|
| `user_id` | UNIQUE |
| `firmenname` | Firmenname |
| `strasse, hausnummer, plz, ort` | Adresse (KEINE Spalte `adresse`!) |
| `ust_idnr` | Umsatzsteuer-IdNr. |
| `steuersatz` | Steuersatz |
| `bank_iban` | IBAN (NICHT `iban`!) |
| `fusszeile` | Rechnungsfußzeile |

#### `user_email_config`
| Spalte | Beschreibung |
|---|---|
| `user_id` | UNIQUE |
| `host` | SMTP-Host |
| `port` | SMTP-Port |
| `user` | SMTP-Benutzername |
| `pass` | SMTP-Passwort (Base64-kodiert) |
| `from` | Absender-E-Mail |

> ⚠️ Tabelle heißt `user_email_config`, NICHT `user_smtp_config`.

#### `user_rechnung_config`
| Spalte | Beschreibung |
|---|---|
| `user_id` | UNIQUE |
| `re_praefix, re_trennzeichen` | Rechnungs-Präfix/Trennzeichen |
| `re_naechste_nr, re_min_stellen, re_mit_jahr` | Nummerierung (NICHT `re_startnummer`!) |
| `sr_praefix, sr_trennzeichen, sr_naechste_nr, sr_min_stellen, sr_mit_jahr` | Storno-Nummerierung |
| `auto_rechnung_aktiv` | Boolean |
| `zahlungsziel_tage` | Default: 14 |

### Buchhaltungs-Tabellen

#### `incoming_invoices`
| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | SERIAL PK | |
| `user_id` | INT FK→users | |
| `lieferant` | VARCHAR(255) | |
| `rechnungsnummer` | VARCHAR(100) | |
| `rechnungsdatum` | DATE | |
| `faelligkeitsdatum` | DATE | |
| `netto_betrag, mwst_satz, mwst_betrag, brutto_betrag` | DECIMAL | |
| `kategorie` | VARCHAR(100) | |
| `notiz` | TEXT | |
| `datei_s3_key` | VARCHAR(500) | S3-Key der Datei |
| `datei_groesse` | BIGINT | Dateigröße in Bytes |
| `datei_typ` | VARCHAR(20) | pdf, jpg, png etc. |
| `quelle` | VARCHAR(20) | 'upload' oder 'email' |
| `status` | VARCHAR(20) | 'entwurf', 'gebucht', 'bezahlt' |
| `bezahlt_am` | DATE | |
| `created_at` | TIMESTAMP | |

#### `email_inbox` (NEU v7)
| Spalte | Typ | Beschreibung |
|---|---|---|
| `id` | SERIAL PK | |
| `user_id` | INT FK→users ON DELETE CASCADE | |
| `imap_uid` | INT | IMAP-Nachrichten-UID |
| `imap_folder` | VARCHAR(200) | Quell-Ordner (z.B. 'INBOX') |
| `from_email` | VARCHAR(255) | Absender-E-Mail |
| `from_name` | VARCHAR(255) | Absender-Name |
| `subject` | TEXT | Betreff |
| `email_date` | TIMESTAMP | Datum der E-Mail |
| `attachment_name` | VARCHAR(500) | Dateiname des Anhangs |
| `attachment_s3_key` | VARCHAR(500) | S3-Key des Anhangs |
| `attachment_size` | INT | Dateigröße in Bytes |
| `attachment_typ` | VARCHAR(20) | pdf, jpg, png etc. |
| `ki_analyse` | JSONB | KI-Analyse-Ergebnis |
| `ki_status` | VARCHAR(20) | 'analysiert' oder 'fehler' |
| `ki_error` | TEXT | Fehlermeldung (nullable) |
| `status` | VARCHAR(20) | 'neu', 'gespeichert', 'verworfen' |
| `received_at` | TIMESTAMP DEFAULT NOW() | |
| `processed_at` | TIMESTAMP | Zeitpunkt der Verarbeitung |
| `processed_invoice_id` | INT FK→incoming_invoices ON DELETE SET NULL | |

**UNIQUE Constraint:** `(user_id, imap_uid, imap_folder, attachment_name)`

> ⚠️ **WICHTIG:** Bei mehreren Anhängen pro E-Mail bekommt jeder Anhang einen eigenen `email_inbox`-Eintrag. Der UNIQUE-Constraint enthält daher `attachment_name`.

#### `user_imap_config`
| Spalte | Typ | Beschreibung |
|---|---|---|
| `user_id` | INT UNIQUE FK→users | |
| `email` | VARCHAR(255) | E-Mail-Adresse des Postfachs |
| `host` | VARCHAR(255) | IMAP-Host |
| `port` | INT | Default: 993 |
| `user_name` | VARCHAR(255) | IMAP-Benutzername |
| `pass` | TEXT | Base64-kodiert |
| `folder` | VARCHAR(100) | Default: 'INBOX' |
| `processed_folder` | VARCHAR(100) | Zielordner nach Verarbeitung |
| `filter_betreff` | VARCHAR(255) | Optionaler Betreff-Filter |
| `aktiv` | BOOLEAN | Import aktiv? |
| `last_check` | TIMESTAMP | Letzter Abruf |
| `last_error` | TEXT | Letzter Fehler |

---

## 4. Alle n8n-Workflows

### 4.1 eBay Verkauf-Notification & Mengen-Reset
- **Workflow-ID:** `ZUw48rywY6uHCIQi`
- **Endpoint:** POST `/ebay-sale-notification`
- **Status:** ✅ Aktiv

### 4.2 SKU-Registrierung & Produkte
| Endpoint | Funktion |
|---|---|
| POST `/variante-sku-update` | Einzelne SKU registrieren |
| POST `/varianten-sku-bulk` | SKUs in Bulk |
| POST `/produkte-laden` | Alle Produkte + Varianten laden |
| POST `/produkte-bestand-update` | Einzelartikel Update |
| POST `/variante-bestand-update` | Variante Update |
| POST `/ebay-produkte-importieren` | eBay-Import |
| POST `/varianten-importieren` | Varianten parsen |
| POST `/produkt-bild-update` | Bild-URL speichern |

### 4.3 Rechnungssystem-Workflows
| ID | Endpoint | Funktion |
|---|---|---|
| WF-RE-01 | POST `/rechnung-erstellen` | PDF erstellen + DB |
| WF-RE-02 | POST `/rechnung-senden` | E-Mail mit PDF |
| WF-RE-03 | POST `/rechnungen-laden` | Alle Rechnungen laden |
| WF-RE-04 | POST `/rechnung-settings` | Firmendaten + Config |
| WF-RE-05 | POST `/rechnung-stornieren` | Storno erstellen |
| WF-RE-06 | POST `/rechnung-pdf` | PDF aus DB abrufen |
| WF-RE-07 | POST `/rechnung-bearbeiten` | Rechnung bearbeiten |

### 4.4 Nachrichten-Workflows
| Endpoint | Funktion |
|---|---|
| GET `/nachrichten?user_id=` | Nachrichten laden |
| POST `/nachrichten-abrufen` | Von eBay abrufen |
| POST `/antwort-senden` | Antwort senden |
| POST `/ki-antwort` | KI-Antwort generieren |

### 4.5 Bestellungen-Workflows
| Endpoint | Funktion |
|---|---|
| POST `/orders-laden` | Bestellungen laden |
| POST `/order-tracking` | Tracking speichern |
| POST `/orders-archivieren` | Archivieren |

### 4.6 Buchhaltungs-Workflows

| ID | WF-ID | Endpoint | Status |
|---|---|---|---|
| WF-BH-01 | `SBWFYB7RrzXXHWqg` | POST `/eingangsrechnung-analysieren` | ✅ Aktiv |
| WF-BH-02 | — | POST `/eingangsrechnung-speichern` | ✅ Aktiv |
| WF-BH-03 | — | POST `/eingangsrechnungen-laden` | ✅ Aktiv |
| WF-BH-04 | — | POST `/eingangsrechnung-update` | ✅ Aktiv |
| WF-BH-05 | `bD2yxz9EAfQQvOIW` | Schedule 30min + POST `/imap-jetzt-abrufen` | ✅ Aktiv |
| WF-BH-06 | — | POST `/eur-generieren` | ✅ Aktiv |
| WF-BH-07 | — | POST `/ustva-daten` | ✅ Aktiv |
| WF-BH-IMAP-CONFIG | `CSvI3jMhsYW5DrQz` | POST `/imap-config` | ✅ Aktiv |
| WF-BH-INBOX-HELPER | `hle7ii3Izq9Bm1Dg` | POST `/email-inbox-insert` + `/email-inbox-laden` | ✅ Aktiv |
| WF-BH-INBOX-ACTION | `N3Z5V7xEHIZnYDg5` | POST `/email-inbox-action` | ✅ Aktiv |

### 4.7 S3-Workflows
| ID | WF-ID | Endpoint | Status |
|---|---|---|---|
| WF-S3-01 | `CWmSnc2zPpVG4zb9` | POST `/s3-upload` | ✅ Aktiv |
| WF-S3-02 | `6O03qpijtFO1SL9y` | POST `/s3-download` | ✅ Aktiv |

---

## 5. SvelteKit-Projektstruktur

```
/opt/ebay-dashboard/
├── Dockerfile
├── package.json
├── svelte.config.js
├── vite.config.js
└── src/
    ├── app.html
    ├── app.css
    ├── lib/
    │   ├── api.js            (getToken, getUser, setAuth, clearAuth, apiCall, login)
    │   ├── stores.js
    │   └── components/
    │       ├── Sidebar.svelte
    │       └── Toast.svelte
    └── routes/
        ├── +layout.svelte
        ├── +page.svelte                (Nachrichten ✅)
        ├── login/+page.svelte
        ├── produkte/+page.svelte       (✅)
        ├── bestellungen/+page.svelte   (✅)
        ├── rechnungen/
        │   ├── +page.svelte            (✅)
        │   └── import/+page.svelte     (✅)
        ├── buchhaltung/
        │   ├── +page.svelte            (✅ Übersicht)
        │   ├── eingang/+page.svelte    (✅ Upload + Posteingang-Tab)
        │   ├── eur/+page.svelte        (✅ EÜR)
        │   └── ustva/+page.svelte      (✅ UStVA)
        └── einstellungen/
            ├── +page.svelte            (✅ Kacheln)
            ├── email/+page.svelte      (✅ IMAP-Konfiguration)
            └── [andere]/+page.svelte   (⏳)
```

### Portierungsstatus
| # | Seite | Status |
|---|---|---|
| 1 | Nachrichten | ✅ |
| 2 | Produkte | ✅ |
| 3 | Bestellungen | ✅ |
| 4 | Rechnungen | ✅ |
| 5 | Rechnungen/Import | ✅ |
| 6 | Buchhaltung | ✅ |
| 7 | Buchhaltung/Eingang | ✅ (Upload + Posteingang) |
| 8 | Buchhaltung/EÜR | ✅ |
| 9 | Buchhaltung/UStVA | ✅ |
| 10 | Einstellungen/Email (IMAP) | ✅ |
| 11 | Einstellungen/Firma | ⏳ |
| 12 | Einstellungen/Nummern | ⏳ |
| 13 | Einstellungen/SMTP | ⏳ |

---

## 6. api.js — Wichtige Signaturen

```js
// Richtig:
apiCall('/produkte-laden', { user_id: 4, ebay_username: 'kd*shop' })
// Falsch:
apiCall('/produkte-laden', { method: 'POST', body: { user_id: 4 } })
```

**Token holen:** `getToken()` aus `$lib/api.js` — NICHT `localStorage.getItem('token')` direkt!

```js
// Für direkte fetch-Calls (z.B. S3-Download):
const token = getToken();
const res = await fetch('https://n8n.ai-online.cloud/webhook/s3-download', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
  body: JSON.stringify({ s3_key })
});
```

---

## 7. Svelte 5 Patterns & Bekannte Pitfalls

| # | Problem | Lösung |
|---|---|---|
| 1 | `{@const}` in `<div>` | Nur in `{#each}`, `{#if}`, `{:else}` erlaubt |
| 2 | `$state()` während Rendering mutieren | In `onMount` oder `loadDaten()` |
| 3 | `apiCall()` falsche Signatur | `(path, body)` — NICHT `(path, { method, body })` |
| 4 | Token-Mismatch | Dashboard-Token ≠ eBay-Token |
| 5 | `</style>` in JS-String | Als `'</' + 'style>'` escapen |
| 6 | Identifier already declared | Funktion doppelt deklariert — mit `grep -n` prüfen, mit Python-Script löschen |

---

## 8. Design-System v3

### CSS-Variablen
```css
/* Light Mode */
--primary: #3777CF;
--primary-dark: #2d6ab8;
--primary-light: rgba(55, 119, 207, 0.05);
--bg: #ffffff;
--surface: #ffffff;
--surface2: #fafafa;
--border: #f0f0f0;
--text: #333333;
--text2: #737373;
--text3: #a3a3a3;

/* Dark Mode */
--primary: #5b9ae4;
--bg: #0a0a0a;
--surface: #141414;
--surface2: #1c1c1c;
--border: #2a2a2e;
--text: #f1f1f1;
```

### Button-Stile
| Klasse | Style |
|---|---|
| `.btn-primary` | `background: var(--primary)`, `color: white` |
| `.btn-secondary` | Transparent, dezenter Border |
| `.btn-danger` | `#ef4444` Rot |

---

## 13. Deploy-Prozess

```bash
cd /opt/ebay-dashboard
git pull origin main
bash /opt/deploy-ebay.sh
```

**Git Push (EINZELN ausführen!):**
```bash
cd /opt/ebay-dashboard
git add -A
git commit -m "<message>"
git push origin main
# Username: Karabas789, Password: GitHub PAT
```

**Deploy-Script** (`/opt/deploy-ebay.sh`) macht: git pull → docker stop/rm → docker build → docker run

> ⚠️ **KRITISCH:** deploy-ebay.sh macht `git pull` — lokale Änderungen werden überschrieben! Immer erst `git commit + push`, dann deployen.

### Deploy-Gotchas
| # | Problem | Lösung |
|---|---|---|
| 1 | CSS nicht übernommen | `docker build --no-cache` |
| 2 | Alte Version im Browser | `Cmd+Shift+R` |
| 3 | Lokale Änderungen überschrieben | Erst `git commit + push` dann deployen |
| 4 | Build-Fehler "Identifier already declared" | Funktion doppelt — mit Python-Script löschen: `content.find()` zweite Instanz entfernen |

---

## 16. Buchhaltungsmodul — Übersicht

### Architektur
```
Frontend (SvelteKit)          Backend (n8n)               Services
─────────────────────        ─────────────────           ─────────────────
/buchhaltung                 WF-BH-06 (EÜR)             PostgreSQL
/buchhaltung/eingang    →    WF-BH-01 (Analyse)    →    OCR-Service (Docker)
  Tab: Rechnungen            WF-BH-02 (Speichern)       Mistral Small (EU)
  Tab: Posteingang      →    WF-BH-05 (IMAP-Import)     Contabo S3
/buchhaltung/eur             WF-BH-06 (EÜR)
/buchhaltung/ustva           WF-BH-07 (UStVA)
```

---

## 17. Buchhaltungs-Datenbankschema

→ Siehe Abschnitt 3 (Tabellen `incoming_invoices`, `email_inbox`, `user_imap_config`)

---

## 18. Buchhaltungs-Workflows (Details)

### WF-BH-01: Eingangsrechnung analysieren
- **ID:** `SBWFYB7RrzXXHWqg`
- **Endpoint:** POST `/eingangsrechnung-analysieren`
- PDF → Text extrahieren → Mistral Small → strukturierte Daten
- **Mistral-Credential:** `B4HMuVL79Y3mHCpK`

### WF-BH-02: Eingangsrechnung speichern
- **Endpoint:** POST `/eingangsrechnung-speichern`
- Lädt Datei zu S3 hoch (WF-S3-01), speichert `datei_s3_key` statt `datei_base64`

### WF-BH-03: Eingangsrechnungen laden
- **Endpoint:** POST `/eingangsrechnungen-laden`
- Response: `{ success, rechnungen[], zusammenfassung }`

### WF-BH-04: Eingangsrechnung Update
- **Endpoint:** POST `/eingangsrechnung-update`
- Actions: `update`, `status`, `delete`

### WF-BH-05: IMAP Rechnungsimport
- **ID:** `bD2yxz9EAfQQvOIW`
- **Trigger:** Schedule 30min + Webhook `imap-jetzt-abrufen`
- **Ablauf:** IMAP-Configs laden → E-Mails abrufen → PDF/Bild-Anhänge finden → WF-BH-01 (Analyse) → WF-S3-01 (Upload) → WF-BH-INBOX-HELPER (INSERT)
- **Bild-Filter:** Bilder unter 100KB werden ignoriert (Logos/Signaturen)
- **Multi-Anhang:** Pro Anhang ein separater `email_inbox`-Eintrag
- **Status:** ✅ Aktiv

**Manuelle Triggerung:**
```js
const res = await fetch('https://n8n.ai-online.cloud/webhook/imap-jetzt-abrufen', {
  method: 'POST',
  headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
  body: JSON.stringify({ user_id: user?.id })
});
```

### WF-BH-06: EÜR generieren
- **Endpoint:** POST `/eur-generieren`
- Einnahmen aus `invoices` (`pdf_generiert_am`!) + Ausgaben aus `incoming_invoices`

### WF-BH-07: UStVA-Daten
- **Endpoint:** POST `/ustva-daten`
- ELSTER-Kennzahlen: Kz 81, 86, 66

### WF-BH-IMAP-CONFIG
- **ID:** `CSvI3jMhsYW5DrQz`
- **Endpoint:** POST `/imap-config`
- Actions: `load`, `save`, `test`, `delete`
- Testet IMAP-Verbindung und legt `processed_folder` an

### WF-BH-INBOX-HELPER
- **ID:** `hle7ii3Izq9Bm1Dg`
- **Endpunkte:**
  - POST `/email-inbox-insert` — Neuen Eintrag einfügen
  - POST `/email-inbox-laden` — Einträge laden (mit `status_filter`)
- **INSERT-Besonderheit:** `ki_error` wird NICHT als Parameter übergeben (verursacht `$14 param bug`). Stattdessen direkt als `$14` ohne NULLIF.
- **ON CONFLICT:** `(user_id, imap_uid, imap_folder, attachment_name) DO NOTHING`

### WF-BH-INBOX-ACTION
- **ID:** `N3Z5V7xEHIZnYDg5`
- **Endpoint:** POST `/email-inbox-action`
- **Actions:**
  - `freigeben` — Status → 'gespeichert', IMAP-Move in processed_folder, `processed_invoice_id` setzen
  - `verwerfen` — Status → 'verworfen', IMAP-Move
  - `rueckgaengig` — Status → 'neu', `processed_at` und `processed_invoice_id` auf NULL
- **Body:** `{ user_id, inbox_id, action, processed_invoice_id? }`

---

## 19. OCR-Service

| Parameter | Wert |
|---|---|
| Container | `ocr-service` |
| Port intern | 3200 |
| URL | `http://ocr-service:3200` (nur im Docker-Netzwerk) |
| Endpunkte | GET `/health`, POST `/ocr`, POST `/ocr/preview` |

---

## 20. Buchhaltungs-Frontend (Details)

### `/buchhaltung/eingang` — Tabs

**Tab 1: Rechnungen**
- Drop-Zone für PDF/JPG/PNG/HEIC/WebP (max 20 MB)
- Upload → `/eingangsrechnung-analysieren` → editierbares Modal → `/eingangsrechnung-speichern`
- Tabelle mit Filter, Suche, Status-Änderung, Bearbeiten, Löschen
- Vorschau: Blob-URL → iframe für PDF, img für Bilder
- Download: separater Button, Blob-URL mit `a.download`

**Tab 2: Posteingang**
- Zeigt `email_inbox`-Einträge (automatisch importierte E-Mails)
- Filter: Neu / Gespeichert / Verworfen / Alle
- Button „Jetzt abrufen" → triggert WF-BH-05 manuell
- Karten zeigen: Betreff, Absender, Empfangsdatum, Anhangname, KI-Analyse-Preview
- Aktionen je Status:
  - `neu`: Vorschau, Download, Prüfen & Speichern, Verwerfen
  - `verworfen`: Rückgängig-Button
  - `gespeichert`: Zur Rechnung-Button

**PDF-Vorschau in Chrome:**
- Chrome muss auf „PDFs in Chrome öffnen" eingestellt sein (chrome://settings → PDF)
- Blob-URL + `<iframe>` im Modal funktioniert dann
- `URL.revokeObjectURL()` beim Schließen aufrufen

**Confirm-Modal:** Eigenes Modal statt `window.confirm()` — kein hässlicher Browser-Dialog

**Rückgängig-Modal:** Eigenes Modal mit Bestätigung vor `action: 'rueckgaengig'`

### Einstellungen `/einstellungen/email`
- IMAP-Konfiguration: Host, Port, User, Passwort, Ordner, Processed-Folder, Filter-Betreff
- Test-Button → `/imap-config` mit `action: 'test'`
- Zeigt verfügbare Ordner nach Test

---

## 23. Server-Infrastruktur

| Parameter | Wert |
|---|---|
| Provider | Contabo |
| Server | Cloud VPS 20 SSD |
| IP | `31.220.78.203` |
| RAM | 12 GB |
| Disk | 200 GB SSD |

### Object Storage (Contabo S3)
| Parameter | Wert |
|---|---|
| Endpoint | `https://eu2.contabostorage.com` |
| Bucket | `ebay-dashboard` (privat) |
| Region | `eu2` |
| Access Key | `70af5ef610934d696d1772a54ffe7348` |
| n8n Credential | `S3 account` (ID: `2DqpVbZtAAGPEQKi`) |

> ⚠️ **Force Path Style MUSS aktiviert sein** in der S3-Credential!

### S3-Key-Konvention
```
user_{user_id}/{YYYY-MM}/{timestamp}_{random8chars}.{ext}
```

### n8n-Pruning (PFLICHT)
```
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=336
EXECUTIONS_DATA_PRUNE_MAX_COUNT=5000
```

---

## 24. n8n-Wartung

**SQLite-Cleanup bei überfüllter DB:**
```bash
SQLITE_PATH="/var/lib/docker/volumes/x04008o88c4w0cg4gwkskkk8_n8n-data/_data/database.sqlite"
tmux new -s n8n-cleanup
docker stop n8n-x04008o88c4w0cg4gwkskkk8
sqlite3 "$SQLITE_PATH" "DELETE FROM execution_entity WHERE id NOT IN (SELECT id FROM execution_entity ORDER BY id DESC LIMIT 100);"
sqlite3 "$SQLITE_PATH" "VACUUM INTO '/tmp/database_new.sqlite';"
# Nach Integrity-Check: Dateien tauschen, n8n starten
```

---

## 25. S3-Integration

### WF-S3-01 Upload
- **ID:** `CWmSnc2zPpVG4zb9`
- **Endpoint:** POST `/s3-upload`
- **Body:** `{ user_id, datei_base64, datei_typ }`
- **Response:** `{ success, s3_key, groesse, datei_typ }`

**KRITISCHER BUG (bekannt):** Postgres-Node verwirft Binary-Daten. Lösung: Base64 als JSON zwischenspeichern, nach Auth in separatem Code-Node wieder als Binary umwandeln.

### WF-S3-02 Download
- **ID:** `6O03qpijtFO1SL9y`
- **Endpoint:** POST `/s3-download`
- **Body:** `{ s3_key }`
- **Auth:** Prüft ob `s3_key` in `incoming_invoices` ODER `email_inbox` des Users existiert
- **Response:** Binary-Stream mit korrektem Content-Type

---

## 26. Bekannte Gotchas (komplett)

| # | Problem | Lösung |
|---|---|---|
| 1 | `column f.adresse does not exist` | Einzelspalten: `strasse, hausnummer, plz, ort` |
| 2 | `column f.iban does not exist` | `bank_iban` verwenden |
| 3 | `column re_startnummer does not exist` | `re_naechste_nr`, `re_min_stellen`, `re_mit_jahr` |
| 4 | `relation "users" does not exist` | Alle Postgres-Nodes auf `ebay_automation` setzen |
| 5 | `column "created_at" does not exist` | `pdf_generiert_am` für `invoices`-Queries |
| 6 | Workflow gespeichert aber alter Code läuft | Toggle aus/an nach Speichern |
| 7 | n8n SQLite explodiert | Pruning aktivieren, manuell cleanup mit tmux |
| 8 | Postgres-Node verwirft Binary | Base64 als JSON zwischenspeichern |
| 9 | S3-Node "encryption error" | `serversideEncryptionCustomerKey` LEER lassen |
| 10 | Contabo S3 Fehler | Force Path Style ✅ in Credential |
| 11 | `$14 param bug` in INSERT email_inbox | `ki_error` nicht als separaten Parameter — direkt `$14` ohne NULLIF |
| 12 | Mehrere Anhänge: nur erster gespeichert | UNIQUE Constraint muss `attachment_name` enthalten |
| 13 | Bilder-Filter zu aggressiv/zu schwach | Bilder < 100KB ausfiltern (Logos/Signaturen) |
| 14 | PDF-Vorschau in Chrome wird heruntergeladen | Chrome: Einstellungen → PDF → „PDFs in Chrome öffnen" |
| 15 | `window.open(dataUrl)` lädt herunter | Blob-URL + iframe im Modal verwenden statt neuem Tab |
| 16 | deploy-ebay.sh überschreibt lokale Änderungen | Erst `git commit + push`, dann deployen |
| 17 | Identifier already declared | Doppelte Funktion — mit Python-Script `content.find()` zweite Instanz entfernen, dann git commit + push |
| 18 | `localStorage.getItem('token')` direkt | Immer `getToken()` aus `$lib/api.js` verwenden |
| 19 | Lange SSH-Operation bricht ab | IMMER `tmux new -s NAME` verwenden |

---

## 27. Wichtige Container-Namen

| Container | Zweck |
|---|---|
| `ebay-dashboard` | Hauptdashboard |
| `n8n-x04008o88c4w0cg4gwkskkk8` | n8n |
| `ocr-service` | Tesseract OCR |
| `ew0s0w40k08wss8c4c8gogw4` | Dashboard-PostgreSQL |
| `coolify-db` | Coolify-System-DB |
| `coolify-proxy` | Traefik |

---

## ÄNDERUNGSHISTORIE

| Version | Datum | Änderung |
|---|---|---|
| 4.0 | 2026-04-15 | eBay-Dashboard-Grundlagen |
| 5.0 | 2026-04-16 | Buchhaltungsmodul (WF-BH-01 bis WF-BH-07, OCR, Frontend) |
| 6.0 | 2026-04-17 | Object Storage (Contabo S3), Server-Wartung, n8n-Pruning |
| **7.0** | **2026-04-19** | **E-Mail-Import komplett: email_inbox-Tabelle, WF-BH-INBOX-HELPER/ACTION, WF-BH-05 aktiv, Frontend Posteingang-Tab, PDF-Vorschau-Fixes, Deploy-Gotchas** |

## Passwort-Reset (implementiert 2026-04-20)

### Frontend
- /passwort-vergessen/+page.svelte — E-Mail eingeben, sendet Reset-Link
- /reset-password/+page.svelte — Token aus URL, neues Passwort setzen
- /login/+page.svelte — "Passwort vergessen?" Link unter Passwort-Feld
- +layout.svelte — isLoginPage enthält jetzt auch /passwort-vergessen und /reset-password

### n8n Workflows
- WF: "Passwort Reset Anfordern" (ID: EXCJoKc2v9O6PA46)
  Endpoint: POST /passwort-reset-anfordern
  Ablauf: E-Mail prüfen → User suchen → Token (crypto 32 bytes hex) generieren →
          reset_token + reset_token_expires (1h) in users speichern → E-Mail senden
- WF: "Passwort Reset Bestätigen" (ID: SoX1TPJNOfUppjBJ)
  Endpoint: POST /passwort-reset-bestaetigen
  Ablauf: Token + Passwort prüfen → reset_token in DB validieren (expires > NOW()) →
          crypt($password, gen_salt('bf')) → reset_token + reset_token_expires = NULL

### DB
- Tabelle users: reset_token (VARCHAR), reset_token_expires (TIMESTAMP) — bereits vorhanden
- Passwörter: PostgreSQL crypt() + gen_salt('bf')

### SMTP
- Credential: "SMTP account 2" (ID: QQE2G03YAEMX9RRT)
- fromEmail muss mit dem SMTP-User übereinstimmen (service@ai-online.cloud)

# Skill-Ergänzung: Multi-Gerät-Auth + 2FA

---

## 1. Multi-Gerät-Auth via `user_sessions`

### Problem
`users.access_token` speichert nur einen Token — neuer Login überschreibt alten.

### Lösung: Tabelle `user_sessions`
```sql
CREATE TABLE user_sessions (
  id          SERIAL PRIMARY KEY,
  user_id     INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token       VARCHAR(255) NOT NULL UNIQUE,
  device_info TEXT,
  created_at  TIMESTAMP DEFAULT NOW(),
  last_used   TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_user_sessions_token   ON user_sessions(token);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
```

### Token-Migration (einmalig)
```sql
INSERT INTO user_sessions (user_id, token, device_info, created_at, last_used)
SELECT id, access_token, 'migrated', NOW(), NOW()
FROM users WHERE access_token IS NOT NULL
ON CONFLICT (token) DO NOTHING;
```

### Auth-Query in allen Workflows
```sql
-- Alt:
SELECT id FROM users WHERE access_token = $1 LIMIT 1

-- Neu:
SELECT user_id AS id FROM user_sessions WHERE token = $1 LIMIT 1
```

### Alle Query-Varianten die vorkamen
| Alt | Neu |
|-----|-----|
| `SELECT id FROM users WHERE access_token = '{{ $json.clean_token }}' LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE token = '{{ $json.clean_token }}' LIMIT 1` |
| `SELECT id AS user_id FROM users WHERE access_token = '{{ $json.clean_token }}' LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE token = '{{ $json.clean_token }}' LIMIT 1` |
| `SELECT id FROM users WHERE access_token = '{{ $json.token }}' LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE token = '{{ $json.token }}' LIMIT 1` |
| `SELECT id FROM users WHERE access_token = $1 LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE token = $1 LIMIT 1` |
| `SELECT id FROM users WHERE id = $1 AND access_token = $2 LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE user_id = $1 AND token = $2 LIMIT 1` |
| `id as user_id FROM users WHERE access_token = '{{ $json.token }}'` (Kleinbuchstabe!) | `user_id AS id FROM user_sessions WHERE token = '{{ $json.token }}'` |
| `SELECT id FROM users WHERE access_token = '{{ $json.headers.authorization.replace("Bearer ", "") }}' LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE token = '{{ $json.headers.authorization.replace("Bearer ", "") }}' LIMIT 1` |
| `SELECT id FROM users WHERE access_token = '{{ $input.first().json.headers.authorization.replace(/^bearer /i,"").trim() }}' LIMIT 1` | `SELECT user_id AS id FROM user_sessions WHERE token = '{{ $input.first().json.headers.authorization.replace(/^bearer /i,"").trim() }}' LIMIT 1` |
| `WHERE u.access_token = $1 ORDER BY t.updated_at DESC LIMIT 1` (JOIN-Variante) | `JOIN user_sessions _us ON _us.token = $1 AND _us.user_id = u.id WHERE 1=1 ORDER BY t.updated_at DESC LIMIT 1` |

> **Achtung bei `queryReplacement`:** Wenn Query von 2 auf 1 Parameter reduziert wird, auch `queryReplacement` anpassen:
> `={{ [$json.user_id, $json.token] }}` → `={{ [$json.token] }}`

---

## 2. n8n SQLite-Patch-Strategie

n8n speichert die aktive WF-Version in **`workflow_history`** (Spalte `nodes`, nach `versionId`), NICHT nur in `workflow_entity.nodes`. Ein Patch muss **beide** Tabellen treffen, danach `publish_workflow`.

### Patch-Skript Vorlage
```bash
cat > /tmp/patchX.js << 'EOF'
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');

const patches = [
  ["OLD_QUERY_1", "NEW_QUERY_1"],
  ["OLD_QUERY_2", "NEW_QUERY_2"],
];

function applyPatches(text) {
  let changed = false;
  for (const [old, neu] of patches) {
    if (text && text.includes(old)) { text = text.split(old).join(neu); changed = true; }
  }
  return { text, changed };
}

function patchTable(table, idCol, wfCol, cb) {
  const q = wfCol
    ? `SELECT ${idCol}, nodes FROM ${table} WHERE ${wfCol} IN (?,?,?) AND nodes LIKE '%SEARCH_TERM%'`
    : `SELECT ${idCol}, nodes FROM ${table} WHERE nodes LIKE '%SEARCH_TERM%'`;
  db.all(q, [], (err, rows) => {
    if (err) { console.error(err); cb(0); return; }
    console.log(`${table}: ${rows.length}`);
    const updates = [];
    for (const row of rows) {
      const { text, changed } = applyPatches(row.nodes);
      if (changed) updates.push([text, row[idCol]]);
    }
    if (!updates.length) { cb(0); return; }
    let done = 0;
    for (const [text, id] of updates) {
      db.run(`UPDATE ${table} SET nodes=? WHERE ${idCol}=?`, [text, id], () => {
        console.log('  ->', id);
        if (++done === updates.length) cb(done);
      });
    }
  });
}

patchTable('workflow_entity', 'id', null, (n1) => {
  patchTable('workflow_history', 'versionId', 'workflowId', (n2) => {
    console.log('Fertig:', n1 + n2);
    db.close();
  });
});
EOF

docker cp /tmp/patchX.js n8n-x04008o88c4w0cg4gwkskkk8:/tmp/patchX.js
docker exec n8n-x04008o88c4w0cg4gwkskkk8 node /tmp/patchX.js
# Danach: n8n:publish_workflow für alle betroffenen Workflows
```

### Prüf-Skript: Noch verbleibende alte Queries finden
```bash
docker exec n8n-x04008o88c4w0cg4gwkskkk8 node -e "
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');
db.all(\"SELECT id, name FROM workflow_entity WHERE nodes LIKE '%users WHERE access_token%' AND active = 1\", [], (e, r) => {
  console.log('Noch alt:', r.length, r.map(x=>x.name));
  db.close();
});
"
```

---

## 3. 2-Faktor-Authentifizierung (2FA)

### Neue DB-Tabellen
```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS two_fa_enabled BOOLEAN DEFAULT false;

CREATE TABLE IF NOT EXISTS two_fa_codes (
  id         SERIAL PRIMARY KEY,
  user_id    INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code       VARCHAR(6) NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used       BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trusted_devices (
  id           SERIAL PRIMARY KEY,
  user_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  device_token VARCHAR(64) NOT NULL UNIQUE,
  device_info  TEXT,
  expires_at   TIMESTAMP NOT NULL,
  created_at   TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_2fa_codes_user        ON two_fa_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_token ON trusted_devices(device_token);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_user  ON trusted_devices(user_id);
```

### n8n Workflows

| WF-ID | Name | Webhook | Funktion |
|---|---|---|---|
| `CyVkNHgAuyeq5221` | Dashboard API - Login | POST `/login` | Prüft 2FA: sendet Code per E-Mail oder gibt direkt Token zurück |
| `Qy8pDYhL8xNAIXK0` | 2FA Code verifizieren | POST `/2fa-verify` | Code prüfen, Session erstellen, optional Gerät merken (30 Tage) |
| `X6DLR71NdRxOZInN` | 2FA Einstellungen | POST `/2fa-settings` | Actions: `enable`, `disable`, `status` |

### Login-Flow

```
POST /login  { email, password, device_token? }
  ↓ Passwort korrekt + 2FA aktiv + Gerät unbekannt
  → { success: true, requires_2fa: true, user_id }

POST /2fa-verify  { user_id, code, remember_device: true/false }
  ↓ Code korrekt
  → { success: true, token, device_token?, user: {...} }
  device_token wird 30 Tage in localStorage gespeichert
```

```
POST /login  { email, password, device_token }
  ↓ Gerät bekannt (device_token in trusted_devices + nicht abgelaufen)
  → { success: true, token, user: {...} }  ← direkt, kein 2FA-Step
```

```
POST /login  { email, password }
  ↓ 2FA nicht aktiv
  → { success: true, token, user: {...} }  ← direkt
```

### 2FA-Settings Actions
```js
POST /2fa-settings  { action: 'status' }   // → { success, two_fa_enabled }
POST /2fa-settings  { action: 'enable' }   // setzt two_fa_enabled = true
POST /2fa-settings  { action: 'disable' }  // setzt two_fa_enabled = false + löscht trusted_devices
```

### Frontend-Änderungen

**`src/lib/api.js`** — neue/geänderte Funktionen:
```js
// login mit optionalem device_token
async function login(email, password, deviceToken = null)

// 2FA Code verifizieren
async function verify2FA(userId, code, rememberDevice = false)

// 2FA Status laden
async function get2FAStatus()

// 2FA ein/ausschalten
async function set2FA(enabled)

// clearAuth löscht jetzt auch dashboard_device_token
function clearAuth()
```

**localStorage Keys:**
| Key | Inhalt |
|-----|--------|
| `dashboard_token` | Session-Token |
| `dashboard_user` | User-Objekt (JSON) |
| `dashboard_device_token` | Vertrauenswürdiges Gerät (30 Tage) |

**`src/routes/login/+page.svelte`** — 2-Step Login:
- Step 1: E-Mail + Passwort → wenn `requires_2fa: true` → Step 2
- Step 2: 6-stelliger Code + Checkbox "Dieses Gerät 30 Tage merken"
- Bei bekanntem `device_token` im localStorage → wird automatisch mitgeschickt → kein 2FA-Step

**`src/routes/einstellungen/sicherheit/+page.svelte`** — Toggle:
- Lädt Status via `get2FAStatus()` beim Mount
- Schaltet via `set2FA(!enabled)` beim Klick

### Toggle-CSS — bekanntes Problem
`position: absolute` mit fixen Pixel-Werten für den Knob funktioniert nicht zuverlässig (weißer Kreis sichtbar). Korrekte Implementierung:

```css
/* Toggle-Container: flexbox statt position:relative */
.toggle {
  display: flex;
  align-items: center;
  padding: 0 3px;
  width: 56px;
  height: 30px;
  background: #d1d5db;
  border-radius: 15px;
  cursor: pointer;
  transition: background 0.25s;
  box-sizing: border-box;
}
.toggle.active { background: #3777CF; }

/* Knob: kein position:absolute */
.toggle-knob {
  width: 24px;
  height: 24px;
  background: white;
  border-radius: 50%;
  transition: transform 0.25s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.25);
  flex-shrink: 0;
}
.toggle.active .toggle-knob { transform: translateX(26px); }
```
