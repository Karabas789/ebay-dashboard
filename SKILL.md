[SKILL.md](https://github.com/user-attachments/files/26660629/SKILL.md)
---
name: ebay-dashboard-erstellung
description: >
  Verwende diesen Skill bei JEDER Anfrage rund um das eBay-Dashboard, SvelteKit-Migration,
  n8n-Workflows oder die vier Kernfunktionen: automatische eBay-Nachrichten nach Kauf,
  Rechnungserstellung, KI-gestützte Angebotserstellung und Auto-Repricing.
  Trigger-Situationen: „Dashboard bauen", „Dashboard erweitern", „neuen Tab einbauen",
  „neuen Workflow bauen", „Rechnung erstellen", „Rechnungsvorlage",
  „eBay Nachricht automatisch senden", „Repricing einrichten", „Preisanpassung",
  „Angebot mit KI erstellen", „eBay Listing generieren", „Dashboard anpassen",
  „Dashboard_neu_v8", „SvelteKit portieren", „Svelte 5", „Seite portieren",
  „Bestellungen verarbeiten", „Lagerbestand synchronisieren",
  „n8n Webhook erstellen", „Nachrichtenvorlage bearbeiten", „Workflow debuggen",
  „eBay API Aufruf", „Tab hinzufügen", „Modal bauen", „CSS anpassen",
  „Deploy", „Docker build", „git push". Enthält vollständige Referenz zu
  Technologie-Stack, allen n8n-Workflows, Datenbankschema, Design-System v3,
  SvelteKit-Patterns und Deploy-Prozess.
connected: false
metadata:
  author: Vitali
  version: '3.1'
  based_on: Wissensbasis (Stand 2026-04-12)
---

# eBay-Dashboard: Vollständiger Entwicklungs-Skill

---

## 1. Projekt-Übersicht

### Firma & Kontext
- **Firma:** Import & Produkte Vertrieb Inh. Oxana Dubs
- **Nutzer:** Vitali
- **Zweck:** eBay-Shop-Verwaltung mit Dashboard für Nachrichten, Produkte, Bestellungen, Rechnungen und KI-Kundenservice

### Technologie-Stack

| Komponente | Details |
|---|---|
| **Frontend** | SvelteKit 2 (`ebay.ai-online.cloud`) — Migration von `Dashboard_neu_v8.html` (Vanilla JS, ~3300 Zeilen) |
| **Framework** | SvelteKit 2, Svelte 5, Vite 6, adapter-node 5, `type: module` |
| **Backend** | n8n Workflows (Webhooks + PostgreSQL + eBay Trading API) |
| **Datenbank** | PostgreSQL |
| **eBay API** | Trading API (XML/SOAP) |
| **KI** | Mistral API (Kundenservice), Claude/Octopus AI (Angebotserstellung) |
| **PDF-Service** | Gotenberg (`gotenberg.ai-online.cloud`) — HTML→PDF, PDF/A-3b nativ |
| **E-Rechnung** | ZUGFeRD 2.4 (EN16931) via Python `factur-x` 3.16 im n8n-Container |
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
| POST | `/send` | E-Mail senden (`smtp`, `to`, `subject`, `body_html`, `attachment` mit `content_base64`) |
| POST | `/test` | SMTP-Verbindung testen |
| GET | `/health` | Health Check |

**Gotenberg** (`gotenberg.ai-online.cloud`):
| Methode | Pfad | Funktion |
|---|---|---|
| POST | `/forms/chromium/convert/html` | HTML zu PDF konvertieren |

---

## 2. Regeln — IMMER LESEN BEVOR CODE GESCHRIEBEN WIRD

1. **Auth-Pattern respektieren** — Jeder n8n-Webhook erwartet `Authorization: Bearer <token>`. Kein Webhook-Aufruf ohne Token.
2. **Dashboard-Konventionen einhalten** — CSS-Variablen nutzen (`var(--primary)`, `var(--surface)` etc.), Design-System v3 befolgen.
3. **SvelteKit-Patterns** — Svelte 5 Syntax (`$state`, `$derived`, `bind:value`), bekannte Pitfalls beachten (Abschnitt 7).
4. **Fehlerbehandlung** — Jeder fetch/API-Call braucht try/catch mit sinnvoller Fehlermeldung im UI.
5. **Vollständige Dateien liefern** — Wenn du eine Svelte-Seite änderst, liefere die komplette aktualisierte Datei als Download.
6. **n8n-Workflows als JSON** — Wenn ein neuer Workflow nötig ist, erstelle vollständigen n8n-Export-JSON zum direkten Import.
7. **Kein Raten** — Wenn Infos fehlen (z.B. aktuelle Dashboard-Version, Workflow-Details), fragen.
8. **eBay Sandbox zuerst** — Immer in der eBay Sandbox testen bevor Live-Daten angefasst werden.
9. **Rate Limits** — eBay Trading API: max. 5000 Calls/Tag. Immer Pausen einbauen.
10. **Fehler-Pfad in n8n** — Jeder Workflow braucht einen Error-Branch mit Logging und optionalem Retry.

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
| `min_lagerbestand` | eBay-Anzeigemenge (Maximum, das auf eBay angezeigt wird) |
| `artikelnummer` | Interne Artikelnummer |
| `basisname` | Basisname des Produkts |
| `variante` | Variantenbezeichnung |
| `bild_url` | Produktbild-URL (Hauptbild) |
| `aktiv` | Aktiv-Flag |
| `aktualisiert_am` | Zeitstempel der letzten Änderung |

### Tabelle: `produkte_varianten`

| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `produkt_id` | Fremdschlüssel → produkte.id |
| `user_id` | Benutzer-Zuordnung |
| `verpackungseinheit` | Verpackungseinheit |
| `produktart` | Produktart |
| `specific_name` | eBay Variation Specific Name |
| `preis` | Preis der Variante |
| `lagerbestand` | Lagerbestand der Variante |
| `min_lagerbestand` | eBay-Anzeigemenge der Variante |
| `bild_url` | Variantenbild-URL |
| `ebay_sku` | eBay SKU |
| `aktiv` | Aktiv-Flag |
| `aktualisiert_am` | Zeitstempel der letzten Änderung |

**UNIQUE CONSTRAINT:** `(produkt_id, COALESCE(verpackungseinheit,''), COALESCE(produktart,''))`

### Tabelle: `users`

| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `email` | E-Mail-Adresse |
| `ebay_user_id` | eBay Benutzer-ID |
| `access_token` | Auth-Token |
| `plan` | Abo-Plan |
| `trial_end` | Ende der Testphase |

### Tabelle: `ebay_tokens`

| Spalte | Beschreibung |
|---|---|
| `ebay_username` | eBay Benutzername |
| `access_token` | eBay Access Token |
| `updated_at` | Zeitstempel der letzten Aktualisierung |

### eBay-Menge-Logik (übergreifend)

```js
Math.min(lagerbestand, min_lagerbestand)
```
→ Die eBay-Anzeigemenge wird nur gesetzt, wenn ausreichend Lagerbestand vorhanden.

### Rechnungssystem-Tabellen

#### `invoices`
| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `user_id` | Benutzer-Zuordnung |
| `order_id` | eBay-Bestellnummer |
| `rechnung_typ` | `rechnung` oder `storno` |
| `storno_von` | FK → invoices.id (bei Storno) |
| `rechnung_nr` | Eindeutige Rechnungsnummer (UNIQUE) |
| `kaeufer_name/strasse/plz/ort/land/email` | Käuferdaten |
| `artikel_name` | Erste Position (Rückwärtskompatibilität) |
| `artikel_menge, einzelpreis, rabatt_pct` | Erste Position Beträge |
| `netto_betrag, steuersatz, steuer_betrag, brutto_betrag` | Gesamtbeträge |
| `kleinunternehmer` | Boolean |
| `pdf_base64` | PDF als Base64-String |
| `pdf_generiert_am` | Zeitstempel der PDF-Generierung |
| `status` | Rechnungsstatus (erstellt / gesendet / storniert) |
| `positionen_migriert` | Boolean — Multi-Positionen in `invoice_items` |

#### `invoice_items`
| Spalte | Beschreibung |
|---|---|
| `id` | Primärschlüssel |
| `invoice_id` | FK → invoices.id |
| `pos_nr` | Positionsnummer |
| `bezeichnung` | Artikelbezeichnung |
| `artikel_nr` | Interne Artikelnummer |
| `ebay_artikel_id` | eBay-Artikel-ID |
| `menge` | Menge |
| `einzelpreis` | Einzelpreis (Brutto) |
| `mwst_satz` | MwSt-Satz (z.B. 19) |
| `rabatt_pct` | Rabatt in Prozent |
| `netto_betrag` | Netto pro Position |
| `steuer_betrag` | Steuer pro Position |
| `brutto_betrag` | Brutto pro Position |

#### `user_firmendaten`
| Spalte | Beschreibung |
|---|---|
| `user_id` | UNIQUE |
| `firmenname` | Firmenname |
| `adresse` | Firmenadresse |
| `ust_idnr` | Umsatzsteuer-IdNr. |
| `steuersatz` | Steuersatz |
| `iban` | IBAN |
| `logo` | Logo (URL oder Base64) |
| `fusszeile` | Rechnungsfußzeile |

#### `user_smtp_config`
| Spalte | Beschreibung |
|---|---|
| `user_id` | UNIQUE |
| `host` | SMTP-Host |
| `port` | SMTP-Port |
| `user` | SMTP-Benutzername |
| `pass` | SMTP-Passwort (Base64-kodiert) |
| `from` | Absender-E-Mail-Adresse |

#### `user_rechnung_config`
| Spalte | Beschreibung |
|---|---|
| `user_id` | UNIQUE |
| `re_praefix` | Rechnungs-Präfix |
| `re_trennzeichen` | Rechnungs-Trennzeichen |
| `re_startnummer` | Startnummer für Rechnungen |
| `re_stellen` | Anzahl Stellen der Rechnungsnummer |
| `sr_praefix` | Stornorechnungs-Präfix |
| `sr_trennzeichen` | Stornorechnungs-Trennzeichen |
| `sr_startnummer` | Startnummer für Stornos |
| `sr_stellen` | Anzahl Stellen der Stornonummer |
| `jahr` | Jahreszahl (für Nummernkreis) |
| `auto_einstellungen` | Automatisierungseinstellungen (JSON) |
| `email_vorlage` | E-Mail-Vorlage |
| `sprache` | Rechnungssprache |
| `waehrung` | Währung |

---

## 4. Alle n8n-Workflows

### 4.1 eBay Verkauf-Notification & Mengen-Reset

- **Workflow-ID:** `ZUw48rywY6uHCIQi`
- **Endpoint:** POST `/ebay-sale-notification`
- **Webhook-URL:** `https://n8n.ai-online.cloud/webhook/ebay-sale-notification`
- **Trigger:** eBay Platform Notification (`FixedPriceTransaction` + `ItemSold`)
- **Status:** ✅ Aktiv

**Ablauf:**
1. eBay sendet SOAP/XML → n8n parst automatisch zu JSON
2. Verkauf parsen: `body["soapenv:envelope"]["soapenv:body"]["getitemtransactionsresponse"]`
3. Produkt + Token aus DB laden (per `ebay_artikel_id`)
4. Menge berechnen: `Math.min(lagerbestand, min_lagerbestand)` + `qty_sold` weitergeben
5. Varianten? → TRUE: Variante Lager reduzieren → eBay `ReviseInventoryStatus`
6. Varianten? → FALSE: Produkt Lager reduzieren → eBay `ReviseItem`

**SOAP-Parsing (JavaScript):**
```javascript
const envelope = body["soapenv:envelope"] || body;
const soapBody = envelope["soapenv:body"] || envelope;
const notification = soapBody["getitemtransactionsresponse"] || soapBody;
const item = notification.item || {};
const transaction = notification.transactionarray?.transaction || {};
const variation = transaction.variation || {};
// item.itemid, variation.sku, transaction.quantitypurchased, transaction.buyer.userid
```

**Node-Kette:**
Webhook Verkauf → Verkauf parsen → Gültig? → Produkt + Token laden → Menge berechnen → Nicht übersprungen? → Varianten? → Variante/Produkt Lager reduzieren → eBay ReviseInventory/ReviseItem → Ergebnis prüfen → OK Antwort

---

### 4.2 SKU-Registrierung & Produkte

| Endpoint | Funktion |
|---|---|
| POST `/variante-sku-update` | Einzelne SKU in DB & eBay registrieren |
| POST `/varianten-sku-bulk` | SKUs in Bulk (nutzt `GetItem` von eBay, nur SKU patchen) |
| POST `/produkte-laden` | Alle Produkte + Varianten per LEFT JOIN laden |
| POST `/produkte-bestand-update` | Einzelartikel: Lager + Preis speichern + eBay-Menge updaten |
| POST `/variante-bestand-update` | Variante: Lager + Preis + eBay-Menge speichern + eBay updaten |
| POST `/ebay-produkte-importieren` | `GetMyeBaySelling` → Produkte in DB importieren |
| POST `/varianten-importieren` | `GetItem` pro Produkt → Varianten parsen + speichern |
| POST `/produkt-bild-update` | `bild_url` in der `produkte`-Tabelle speichern |

> **Hinweis Bulk-SKU:** Node „Alle Varianten laden" → Settings → **Execute Once = true** (verhindert n-fache Multiplikation bei mehreren Input-Items)

---

### 4.3 Rechnungssystem-Workflows

| ID | Endpoint | Funktion |
|---|---|---|
| WF-RE-01 | POST `/rechnung-erstellen` | Bestelldaten → Berechnung → HTML → Gotenberg PDF → DB speichern (inkl. invoice_items). Rundungsfix: Steuer = netto × mwst/100, brutto = netto + steuer |
| WF-RE-02 | POST `/rechnung-senden` | Rechnung aus DB laden → SMTP → E-Mail mit PDF senden |
| WF-RE-03 | POST `/rechnungen-laden` | Alle invoices eines Users zurückgeben |
| WF-RE-04 | POST `/rechnung-settings` | Firmendaten + Config + SMTP laden oder speichern (`action: load/save`) |
| WF-RE-05 | POST `/smtp-testen` | SMTP-Daten → `email.ai-online.cloud/test` → Ergebnis |
| WF-RE-06 | POST `/rechnung-pdf` | PDF Base64 aus `invoices`-Tabelle abrufen |

**Rechnungsnummern-Format:** `RE-{YYYY}-{laufende Nummer 5-stellig}`, z.B. `RE-2026-00001`

---

### 4.4 Nachrichten-Workflows

| Endpoint | Funktion |
|---|---|
| GET `/nachrichten?user_id=` | Nachrichten laden |
| POST `/nachrichten-abrufen` | Nachrichten von eBay abrufen |
| POST `/antwort-update` | Antwort aktualisieren |
| POST `/antwort-senden` | Antwort senden |
| POST `/ki-antwort` | KI-Antwort generieren (Mistral API) |
| POST `/ki-ueberarbeiten` | KI-Antwort überarbeiten |
| POST `/nachricht-verschieben` | Nachricht in anderen Ordner verschieben |
| POST `/nachricht-loeschen` | Nachricht löschen |

---

### 4.5 Bestellungen-Workflows

| Endpoint | Funktion |
|---|---|
| POST `/orders-laden` | Bestellungen laden |
| POST `/order-tracking` | Tracking-Informationen speichern |
| POST `/orders-archivieren` | Bestellungen archivieren |

---

### 4.6 E-Rechnung Workflow (ZUGFeRD / XRechnung)

- **Workflow-ID:** `8aNYc6uei9w9Y2Of`
- **Endpoint:** POST `/e-rechnung-erstellen`
- **Status:** ✅ Aktiv, validiert (EU-Rechnung v2.51 + Bund-Validator = 0 Fehler)

**Ablauf:**
1. Auth prüfen (Token → users)
2. Rechnung + Firmendaten + Positionen + Vorlage aus DB laden (JOIN invoices, invoice_items, user_firmendaten, user_rechnung_config, user_rechnung_vorlage)
3. Format-Routing: `xrechnung` | `zugferd_en16931` | `zugferd_extended`
4. XML generieren (XRechnung = UBL 2.1, ZUGFeRD = CII)
5. PDF über Gotenberg (mit `pdfa: PDF/A-3b` Parameter)
6. ZUGFeRD: XML in PDF einbetten via Python `factur-x` Library → echtes PDF/A-3
7. Response: `{ success, format, xml, pdf_base64, zugferd_embedded, filename }`

**Formate:**

| Format | XML-Standard | GuidelineID | PDF |
|---|---|---|---|
| `xrechnung` | UBL 2.1 | `urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0` | Kein PDF |
| `zugferd_en16931` | CII (CrossIndustryInvoice) | `urn:cen.eu:en16931:2017` | PDF/A-3b mit eingebettetem XML |
| `zugferd_extended` | CII (CrossIndustryInvoice) | `urn:cen.eu:en16931:2017` | PDF/A-3b mit eingebettetem XML |

**ZUGFeRD GuidelineID — WICHTIG:**
Die offizielle `FACTURX_EN16931_codedb.xml` (cl id="1") erlaubt **nur** `urn:cen.eu:en16931:2017` — kein Suffix wie `#compliant#urn:factur-x.eu:1p0:en16931`. Die factur-x Python Library 3.16 akzeptiert das mit `check_xsd=False`.

**ZUGFeRD-Embedding (Python factur-x):**
```python
from facturx import generate_from_file
result_pdf = generate_from_file(
    pdf_file,
    xml_data,
    flavor='factur-x',
    level='en16931',      # oder 'extended'
    check_xsd=False,      # Pflicht wegen GuidelineID ohne Suffix
    output_pdf_file=out
)
```

**Gotenberg PDF/A-3b:**
Im fields-Array des Gotenberg-Uploads:
```javascript
{ name: 'pdfa', value: 'PDF/A-3b' }
```
Dieser Parameter muss im **Gotenberg Upload**-Block stehen, NICHT doppelt deklariert.

**Rundungsfix (WF-RE-01 „Nummer + Berechnung"):**
```javascript
// KORREKT: Steuer aus Netto berechnen, Brutto = Netto + Steuer
const netto = parseFloat((bruttoGesamt / (1 + mwstSatz / 100)).toFixed(2));
const steuer = parseFloat((netto * mwstSatz / 100).toFixed(2));
const brutto = parseFloat((netto + steuer).toFixed(2));
// FALSCH (Rundungsfehler): steuer = bruttoGesamt - netto
```

**n8n-Container Docker-Setup (factur-x permanent):**
Dockerfile unter `/data/coolify/services/x04008o88c4w0cg4gwkskkk8/Dockerfile`:
```dockerfile
FROM python:3.12-alpine AS python-build
RUN apk add --no-cache gcc musl-dev libxml2-dev libxslt-dev && \
    pip install --no-cache-dir factur-x

FROM docker.n8n.io/n8nio/n8n:2.14.2
USER root
COPY --from=python-build /usr/local/bin/python3 /usr/local/bin/python3
COPY --from=python-build /usr/local/bin/python3.12 /usr/local/bin/python3.12
COPY --from=python-build /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=python-build /usr/local/lib/libpython3.12.so* /usr/local/lib/
COPY --from=python-build /usr/lib/libxml2* /usr/lib/
COPY --from=python-build /usr/lib/libxslt* /usr/lib/
COPY --from=python-build /usr/lib/libexslt* /usr/lib/
COPY --from=python-build /usr/lib/libffi* /usr/lib/
COPY --from=python-build /usr/lib/libz* /usr/lib/
COPY --from=python-build /usr/lib/liblzma* /usr/lib/
COPY --from=python-build /usr/lib/libgcrypt* /usr/lib/
COPY --from=python-build /usr/lib/libgpg-error* /usr/lib/
ENV LD_LIBRARY_PATH=/usr/local/lib
RUN ln -sf /usr/local/bin/python3 /usr/bin/python3
USER node
```
docker-compose.yml: `image:` → `build: context: . dockerfile: Dockerfile` + Netzwerke `coolify: external: true`

**Validierungsstatus (Stand 2026-04-12):**

| Prüfung | Ergebnis |
|---|---|
| ZUGFeRD 2.4 (EN16931) erkannt | ✅ |
| factur-x.xml eingebettet | ✅ |
| PDF/A-3B (veraPDF) | ✅ |
| XML konform (KoSIT Validator) | ✅ 0 Fehler |
| Schematron (FACTUR-X_EN16931) | ✅ 0 Fehler |
| EU-Rechnung v2.51 Gesamturteil | ✅ konform |
| Bund-Validator (erechnungsvalidator.service.bund.de) | ✅ 0 Fehler |

**Bekannte Hinweise (nur Informationen, keine Fehler):**
- PEPPOL-EN16931-R001: Business process — nur für XRechnung relevant
- PEPPOL-EN16931-R020/R010: Seller/Buyer electronic address — nur für PEPPOL
- BR-DE-21: Specification identifier soll XRechnung entsprechen — irrelevant für ZUGFeRD
- BR-DE-2: Seller Contact — nur für XRechnung

---

## 5. SvelteKit-Projektstruktur

```
/opt/ebay-dashboard/
├── Dockerfile
├── package.json
├── svelte.config.js          (adapter-node)
├── vite.config.js
└── src/
    ├── app.html              (Shell mit Inter Font + Favicon)
    ├── app.css               (Design System v3: CSS-Variablen, Dark Mode, Buttons, Cards, Tables)
    ├── lib/
    │   ├── api.js            (API-Basis-URL, getToken, getUser, setAuth, clearAuth, apiCall, login + sessionExpired Store)
    │   ├── stores.js         (currentUser, theme, sidebarCollapsed, toastMessage, showToast, sessionExpired)
    │   └── components/
    │       ├── Sidebar.svelte  (Navigation + Einstellungen + User + eBay OAuth + Session-Modal + Tooltips)
    │       └── Toast.svelte
    └── routes/
        ├── +layout.svelte              (Auth-Guard, Sidebar-Shell, volle Breite)
        ├── +page.svelte                (Nachrichten — Startseite ✅ PORTIERT, 611 Zeilen)
        ├── login/+page.svelte          (Login mit Schwarzblau-Gradient → #2D43A8)
        ├── produkte/+page.svelte       (✅ PORTIERT, ~1890 Zeilen)
        ├── bestellungen/+page.svelte   (⏳ Stub — Nächste Priorität)
        ├── rechnungen/+page.svelte     (⏳ Stub)
        └── einstellungen/
            ├── +page.svelte            (Kacheln-Übersicht ✅)
            ├── firma/+page.svelte      (⏳)
            ├── nummern/+page.svelte    (⏳)
            ├── smtp/+page.svelte       (⏳)
            ├── ki/+page.svelte         (⏳)
            ├── kauf-nachricht/+page.svelte (⏳)
            └── bilder/+page.svelte     (⏳)
```

### Portierungsstatus

| # | Seite | Status | Besonderheiten |
|---|---|---|---|
| 1 | Nachrichten | ✅ PORTIERT | Ordner-Sidebar, Thread-Ansicht, KI-Antwort, Überarbeiten-Chat |
| 2 | Produkte | ✅ PORTIERT | Grid-Cards, Varianten-Modal, Bestand-Update, Import, CSV-Export |
| 3 | Bestellungen | ✅ PORTIERT | Tabelle, Filter-Tabs (Alle/Bezahlt/Versendet/Archiv), Tracking-Modal, Order-Detail-Modal, Archivierung, Nachricht senden, Auto-Rechnung |
| 4 | Rechnungen | ⏳ | Tabelle, Filter, PDF-Download, E-Mail senden, Storno, Manuell erstellen, E-Rechnung (ZUGFeRD/XRechnung) |
| 5 | Einstellungen/Firma | ⏳ | Firmendaten-Formular → `/rechnung-settings` (action: save) |
| 6 | Einstellungen/Nummern | ⏳ | RE/SR Konfiguration mit Live-Vorschau |
| 7 | Einstellungen/SMTP | ⏳ | SMTP-Formular + Test-Button |
| 8 | Einstellungen/KI | ⏳ | System-Prompt, Modell-Auswahl, Auto-Send, Wissensdatenbank |
| 9 | Einstellungen/Kauf-Nachricht | ⏳ | Toggle, Betreff, Vorlage, Platzhalter |
| 10 | Einstellungen/Bilder | ⏳ | Produkt-Select, Bild-URL, Preview |

---

## 6. api.js — Wichtige Signaturen

```js
// Richtig:
apiCall('/produkte-laden', { user_id: 4, ebay_username: 'kd*shop' })

// FALSCH:
apiCall('/produkte-laden', { method: 'POST', body: { user_id: 4 } })
```

**Signatur:** `async function apiCall(path, body = {}, method = 'POST')`

Bei 401 oder Auth-Fehlern setzt api.js `sessionExpired = true` → Sidebar zeigt automatisch Session-Modal.

**Standard fetch-Pattern für n8n-Webhooks:**
```javascript
async function loadDaten() {
  const token = localStorage.getItem('token');
  try {
    const res = await fetch('https://n8n.ai-online.cloud/webhook/ENDPOINT', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        user_id: currentUser.id,
        ebay_username: currentUser.ebay_user_id
      })
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const data = await res.json();
    renderDaten(data);
  } catch (err) {
    document.getElementById('container').innerHTML =
      '<p style="color:var(--warning)">⚠️ Fehler beim Laden: ' + err.message + '</p>';
  }
}
```

---

## 7. Svelte 5 Patterns & Bekannte Pitfalls

### Best Practices

```svelte
<script>
  // State
  let produkte = $state([]);
  let loading = $state(false);
  let suchbegriff = $state('');

  // Derived
  let gefiltert = $derived(
    produkte.filter(p => p.name.toLowerCase().includes(suchbegriff.toLowerCase()))
  );

  // Derived with logic
  let stats = $derived.by(() => ({
    total: produkte.length,
    ausverkauft: produkte.filter(p => p.lagerbestand === 0).length
  }));
</script>

<!-- bind:value statt getElementById -->
<input bind:value={suchbegriff} />

<!-- {#each} mit key -->
{#each gefiltert as produkt (produkt.id)}
  <!-- {@const} NUR innerhalb von {#each}, {#if}, {:else} erlaubt! -->
  {@const bild = produkt.bild_url || ''}
  <div>{bild}</div>
{/each}
```

### ⚠️ KRITISCHE Pitfalls

| # | Problem | Lösung |
|---|---|---|
| 1 | `{@const}` in `<div>` | Nur in `{#each}`, `{#if}`, `{:else}`, `{#snippet}` erlaubt |
| 2 | `$state()` während Rendering mutieren | `initInlineEdit()` NICHT im Template aufrufen — in `onMount` oder `loadDaten()` |
| 3 | `apiCall()` falsche Signatur | `(path, body)` — NICHT `(path, { method, body })` |
| 4 | Token-Mismatch | Dashboard-Token (`users.access_token`) ≠ eBay-Token (`ebay_tokens.access_token`) |
| 5 | `</style>` in JS-String | Als `'</' + 'style>'` escapen — sonst bricht Svelte den Style-Block |
| 6 | `{@const _ = initSomething()}` | State-Mutation im Template → Crash |

---

## 8. Design-System v3 (Monochrom / Octopus-Style)

### Design-Philosophie
- **Monochrom** — keine bunten Akzentfarben, nur dezentes Blau für Buttons
- **Vorbild:** Octopus AI — clean, ruhig, elegant, viel Weißraum
- **Borders:** hauchzart, kaum sichtbar
- **Kein Schwarz** als Textfarbe — weiches Dunkelgrau (#333333)

### CSS-Variablen

```css
/* Light Mode (:root) */
--primary: #3777CF;        /* Buttons, Links, Akzente */
--primary-dark: #2d6ab8;   /* Button Hover */
--primary-light: rgba(55, 119, 207, 0.05);
--accent: #0F2E93;         /* Reserviert fürs Logo */
--bg: #ffffff;
--surface: #ffffff;
--surface2: #fafafa;
--border: #f0f0f0;         /* Hauchzarte Trennlinien */
--text: #333333;           /* Weiches Dunkelgrau */
--text2: #737373;
--text3: #a3a3a3;

/* Dark Mode ([data-theme="dark"]) */
--primary: #5b9ae4;
--primary-dark: #3777CF;
--primary-light: rgba(91, 154, 228, 0.1);
--bg: #0a0a0a;
--surface: #141414;
--surface2: #1c1c1c;
--border: #2a2a2e;
--text: #f1f1f1;
--text2: #a3a3a3;
--text3: #525252;
```

### Button-Stile

| Klasse | Style |
|---|---|
| `.btn-primary` | `background: var(--primary)` (#3777CF), `color: white` |
| `.btn-secondary` | Transparent, dezenter Border |
| `.btn-ghost` | Kein Background, nur Text |
| `.btn-danger` | #ef4444 Rot |
| KI generieren | Lila Gradient: `linear-gradient(135deg, #6c63ff, #a855f7)` |
| Überarbeiten | Lila Border: `1.5px solid #a855f7` |

### Sidebar-Design
- **Aktiver Punkt:** `background: var(--surface2)`, `color: var(--text)`, `font-weight: 700` — dezent, kein farbiger Kasten
- **Avatar „K":** `background: #3777CF`, `color: white`
- **Keine Sektions-Labels** — clean
- **4 Action-Buttons** im Footer: 🌙/☀️ Theme, 🔑 eBay OAuth, 🔄 Session erneuern, 🚪 Logout
- **CSS-Tooltips:** Rechts vom Icon, über `data-tooltip-action` Attribut

### Login-Screen
```css
background: linear-gradient(135deg, #0a0a1a 0%, #1a2560 50%, #2D43A8 100%)
/* Login-Card: weiß, border-radius: 20px */
```

### Design-Regeln für Code
1. Keine hardcoded Border-Farben — immer `var(--border)` verwenden (Dark Mode!)
2. Keine `<button>` ohne `border: none` — Browser Default-Borders vermeiden
3. `</style>` in JS-Strings escapen: `'</' + 'style>'`
4. `max-width` auf `.page-container` entfernt — volle Browserbreite

---

## 9. Nachrichten-Seite (SvelteKit-Detail)

### Layout
- **3-Panel:** Folder-Sidebar (180px) | Nachrichten-Liste (300px) | Detail (flex: 1)
- Höhe: `calc(100vh - 130px)` — kein Scrollen der Gesamtseite

### Ordner-System
```
📬 Posteingang  — alle außer archiv/gelöscht
👥 Mitglieder   — nur echte Käufer (nicht eBay-System)
🔔 eBay-System  — sender = 'ebay'
📩 Gesendet     — direction = 'outgoing'
📁 Archiv       — _folder = 'archiv'
🗑️ Gelöscht    — _folder = 'geloescht'
```

### Thread-Logik
- Pro Käufer nur die neueste Nachricht in der Liste (Gruppierung nach buyer + item_id)
- eBay-System: jede Nachricht einzeln (keine Gruppierung)
- Thread-Count Badge neben Absendernamen

### Nachrichten-Darstellung
- **Mitglieder:** Text-Extraktion aus HTML (UserInputtedText, „Neue Nachricht:" Pattern, Fallback Strip-Tags)
- **eBay-System:** HTML als iframe mit `use:setupIframe` Directive
- **`setupIframe()`:** Injiziert Dark/Light CSS, `sandbox="allow-same-origin"`, Auto-Height

---

## 10. Produkte-Seite (SvelteKit-Detail)

### Features
- Grid-Ansicht mit Produktkarten (Bild, Name, Preis, Lagerbestand, Status-Badge)
- Getrennte Sektionen: 📦 Einzelartikel / 📋 Varianten-Artikel
- Inline-Bearbeitung für Einzelartikel (Lager, eBay-Menge, Preis)
- Varianten-Modal: alle Varianten mit Bild, Status, Lager/eBay-Menge/Preis Inputs, „Alle speichern"
- eBay Import Modal (nur neu / Lager / Preis / Name / Bild aktualisieren)
- CSV Export Modal: „Alle Produkte" (sofort) / „Produkte auswählen" (mit Filter + Merge)
- SKU Generator (Code vorhanden, Button auskommentiert — kommt auf „Angebote erstellen"-Seite)
- Suche (Name, eBay-ID, Artikelnummer)
- Filter-Chips: Alle / Einzelartikel / Varianten / Niedrig / Ausverkauft

### Produktbild-Logik
```js
// Priorität bei Varianten-Artikeln:
// 1. Hauptprodukt-Bild (p.bild_url)
// 2. Erstes Varianten-Bild
const bild = p.bild_url || (varianten.find(v => v.bild_url)?.bild_url || '');
```

### API-Endpunkte (Produkte-Seite)
```js
apiCall('/produkte-laden', { user_id, ebay_username })
apiCall('/produkte-bestand-update', { id, lagerbestand, min_lagerbestand, preis })
apiCall('/variante-bestand-update', { id, lagerbestand, min_lagerbestand, preis })
apiCall('/ebay-produkte-importieren', { user_id, ebay_username, mode })
apiCall('/varianten-importieren', { user_id, ebay_username })
apiCall('/varianten-sku-bulk', { user_id })
```

---

## 10b. Bestellungen-Seite (SvelteKit-Detail)

### Features
- Tabelle mit Spalten: Checkbox, Datum, Bestellung (klickbar → Detail-Modal), Käufer, Artikel (mit Produktbild), Menge, Gesamt, Status-Badge, Tracking
- Filter-Tabs: Alle / 💛 Bezahlt / ✅ Versendet / 📁 Archiv (jeweils mit Count-Badge)
- Suche über: order_id, buyer_name, buyer_username, artikel_name
- Multi-Select mit Checkbox (inkl. "Alle auswählen")
- Produktbilder werden aus `allProdukte` über `ebay_artikel_id` zugeordnet (optionaler Aufruf von `/produkte-laden`)

### Modals
- **Tracking-Modal** – Versanddienstleister + Sendungsnummer → `/order-tracking` → eBay wird automatisch informiert
- **Nachricht-Modal** – Betreff + Text → `/antwort-senden` (nur bei Einzelauswahl)
- **Archiv-Confirm-Modal** – Bestätigung vor Archivieren / Wiederherstellen
- **Detail-Modal** – Grid mit 4 Karten: Artikel, Käufer (mit vollständiger Adresse), Zahlung, Versand

### Auto-Rechnung nach Tracking
Nach erfolgreichem Tracking wird `autoCreateRechnungAfterTracking()` aufgerufen:
1. Prüft ob `auto_rechnung` in `/rechnung-settings` aktiviert ist
2. Prüft ob Rechnung für diese order_id bereits existiert
3. Falls nicht → `/rechnung-erstellen` mit Käufer- und Bestelldaten
4. Falls `auto_email` aktiv und buyer_email vorhanden → `/rechnung-senden`

### Order-Datenstruktur (aus `/orders-laden`)
```js
{
  order_id, buyer_name, buyer_username, buyer_strasse, buyer_plz,
  buyer_ort, buyer_land, buyer_email, artikel_name, ebay_artikel_id,
  menge, gesamt, status,  // 'bezahlt' | 'versendet' | 'storniert' | 'archiviert'
  archiviert,             // boolean
  bestelldatum, erstellt_am,
  tracking_nummer, versanddienstleister
}
```

### Status-Badges
```js
badge-versendet  → grün (#f0fdf4 / #16a34a)
badge-storniert  → rot  (#fef2f2 / #dc2626)
badge-bezahlt    → gelb (#fffbeb / #d97706)
badge-archiviert → grau (var(--surface2) / var(--text2))
```

### Tracking-URL-Logik
```js
DHL / Deutsche Post → dhl.de/…?idc=
Hermes             → myhermes.de/…#
DPD                → tracking.dpd.de/…/
UPS                → ups.com/track?tracknum=
```

### API-Endpunkte (Bestellungen-Seite)
```js
apiCall('/orders-laden',       { user_id, ebay_username })
apiCall('/orders-archivieren', { order_id, user_id, action?: 'unarchive' })
apiCall('/order-tracking',     { order_id, tracking_nummer, versanddienstleister, user_id, ebay_username })
apiCall('/antwort-senden',     { recipient, subject, reply, user_id, ebay_username })
apiCall('/rechnung-settings',  { action: 'load', user_id })
apiCall('/rechnung-erstellen', { user_id, typ, order_id, kaeufer_*, artikel_name, menge, einzelpreis, ebay_artikel_id })
apiCall('/rechnung-senden',    { invoice_id, user_id, to_email })
```

---

## 11. Dashboard-HTML: Tab / Modal Patterns (Vanilla JS, Dashboard_neu_v8)

> Nur relevant wenn noch an der alten HTML-Datei gearbeitet wird.

### Neuen Tab einbauen

```html
<!-- In <nav class="tab-nav"> einfügen -->
<button class="tab-btn" onclick="showPage('rechnungen', this)">🧾 Rechnungen</button>

<!-- Seiten-Div -->
<div class="page" id="page-rechnungen">
  <div class="page-hdr">
    <div>
      <div class="page-hdr-title">🧾 Rechnungen</div>
      <div class="page-hdr-sub">Automatisch erstellte Rechnungen verwalten</div>
    </div>
    <button class="btn-refresh" onclick="loadRechnungen()">🔄 Aktualisieren</button>
  </div>
  <div id="rechnungen-liste" style="margin-top:20px;">
    <p style="color:var(--text2)">Lade Rechnungen...</p>
  </div>
</div>

<!-- In showPage() einhängen (ca. Zeile 954) -->
if (name === 'rechnungen') loadRechnungen();
```

### Modal-Dialog Pattern

```html
<div class="modal-overlay" id="modal-detail" style="display:none">
  <div class="modal-box">
    <div class="modal-title">📋 Details</div>
    <div id="detail-content"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:20px">
      <button class="btn-cancel" onclick="document.getElementById('modal-detail').style.display='none'">Schließen</button>
      <button class="btn-primary" style="width:auto;padding:10px 26px" onclick="aktion()">✅ Bestätigen</button>
    </div>
  </div>
</div>
```

### Tabelle rendern (Vanilla JS)

```javascript
function renderTabelle(data) {
  const container = document.getElementById('container');
  if (!data || data.length === 0) {
    container.innerHTML = '<p style="color:var(--text2)">Keine Einträge vorhanden.</p>';
    return;
  }
  let html = `<table style="width:100%;border-collapse:collapse">
    <thead><tr style="background:var(--surface2)">
      <th style="padding:10px;text-align:left;border-bottom:1px solid var(--border)">Spalte 1</th>
      <th style="padding:10px;text-align:right;border-bottom:1px solid var(--border)">Betrag</th>
    </tr></thead><tbody>`;
  data.forEach(r => {
    html += `<tr style="border-bottom:1px solid var(--border)">
      <td style="padding:10px">${r.feld}</td>
      <td style="padding:10px;text-align:right">${Number(r.betrag).toFixed(2)} €</td>
    </tr>`;
  });
  html += '</tbody></table>';
  container.innerHTML = html;
}
```

---

## 12. Vier Kernfunktionen — Architektur

### Prioritätsliste
| # | Funktion | Priorität |
|---|---|---|
| A | Automatische eBay-Nachricht nach Kauf | 🔴 Hoch |
| B | Automatische Rechnungserstellung | 🔴 Hoch |
| C | KI-gestützte eBay-Angebotserstellung | 🟡 Mittel |
| D | Auto-Repricing | 🟡 Mittel |

---

### Funktion A: Automatische eBay-Nachricht nach Kauf

**Architektur:**
1. **Trigger:** eBay-Notification bei neuer Bestellung (Erweiterung von `/ebay-sale-notification`)
2. **Logik:** Bestelldaten → Nachrichtenvorlage befüllen → über eBay Trading API senden
3. **Dashboard:** Tab „Nachrichtenverwaltung" — Vorlagen bearbeiten, Versandlog einsehen

**eBay Trading API (XML):**
```xml
<AddMemberMessageAAQToPartnerRequest xmlns="urn:ebay:apis:eBLBaseComponents">
  <RequesterCredentials>
    <eBayAuthToken>{{ access_token }}</eBayAuthToken>
  </RequesterCredentials>
  <ItemID>{{ ebay_artikel_id }}</ItemID>
  <MemberMessage>
    <Body>{{ nachricht_text }}</Body>
    <RecipientID>{{ buyer_username }}</RecipientID>
    <MessageType>ContactTransactionSeller</MessageType>
    <Subject>Danke für deinen Kauf</Subject>
  </MemberMessage>
</AddMemberMessageAAQToPartnerRequest>
```

**DB-Schema:**
```sql
CREATE TABLE message_templates (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  name VARCHAR(100),
  subject VARCHAR(200),
  body TEXT,
  language VARCHAR(5) DEFAULT 'de',
  active BOOLEAN DEFAULT true
);
```

**Einstellungsseite:** `/einstellungen/kauf-nachricht` — Toggle, Betreff, Vorlage, Platzhalter

---

### Funktion B: Automatische Rechnungserstellung

**Architektur:**
1. **Trigger:** Zahlungseingang bestätigt (aus Order-Workflow)
2. **Workflow:** Käuferdaten + Bestelldetails → Rechnungsnummer → Gotenberg PDF → E-Mail
3. **Endpunkte:** Alle WF-RE-01 bis WF-RE-06 (siehe Abschnitt 4.3)

**Rechnungsnummern-Format:** `{praefix}{trennzeichen}{YYYY}{trennzeichen}{laufende Nummer}`
Beispiel: `RE-2026-00001`

---

### Funktion C: KI-gestützte Angebotserstellung

**Architektur:**
1. **Trigger:** Manuell aus Dashboard-Formular
2. **Workflow:** Produktdaten → KI (Claude/Mistral) → Titel + Beschreibung → User-Review → eBay Listing

**Prompt-Template:**
```
Erstelle ein professionelles eBay-Angebot für folgenden Artikel:
- Produktname: {{product_name}}
- Kategorie: {{category}}
- Zustand: {{condition}}
- Besonderheiten: {{features}}

Liefere als JSON:
{
  "title": "Max 80 Zeichen, SEO-optimiert",
  "description": "300-600 Wörter, HTML-formatiert",
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "item_specifics": {"Marke": "...", "Material": "...", "Farbe": "..."}
}
```

**DB-Schema:**
```sql
CREATE TABLE listings (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  product_id INT,
  ai_draft JSONB,
  final_text TEXT,
  ebay_item_id VARCHAR(50),
  status VARCHAR(20) DEFAULT 'entwurf',
  created_at TIMESTAMP DEFAULT NOW(),
  published_at TIMESTAMP
);
```

---

### Funktion D: Auto-Repricing

**Architektur:**
1. **Trigger:** Zeitgesteuert (stündlich via n8n Schedule-Trigger)
2. **Workflow:** Eigene Preise laden → eBay Marktpreise (Browse API) → Regeln anwenden → Preis updaten

**eBay Browse API:**
```
GET https://api.ebay.com/buy/browse/v1/item_summary/search?q={{suchbegriff}}&filter=deliveryCountry:DE&sort=price&limit=10
```

**DB-Schema:**
```sql
CREATE TABLE repricing_rules (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  ebay_artikel_id VARCHAR(50),
  strategy VARCHAR(30),  -- 'undercut' | 'margin' | 'fixed'
  min_price DECIMAL(10,2),
  max_price DECIMAL(10,2),
  target_margin DECIMAL(5,2),
  undercut_amount DECIMAL(10,2),
  active BOOLEAN DEFAULT true
);

CREATE TABLE price_history (
  id SERIAL PRIMARY KEY,
  item_id VARCHAR(50),
  old_price DECIMAL(10,2),
  new_price DECIMAL(10,2),
  competitor_price DECIMAL(10,2),
  strategy VARCHAR(30),
  reason TEXT,
  changed_at TIMESTAMP DEFAULT NOW()
);
```

---

## 13. Deploy-Prozess

### Standard-Deploy (nach Code-Änderung)

```bash
# 1. Git pull (EINZELN ausführen!)
cd /opt/ebay-dashboard
git pull origin main

# 2. Docker Container stoppen
docker stop ebay-dashboard && docker rm ebay-dashboard

# 3. Neu bauen (--no-cache wenn CSS sich geändert hat!)
docker build --no-cache -t ebay-dashboard:latest /opt/ebay-dashboard

# 4. Starten
docker run -d --name ebay-dashboard --restart unless-stopped \
  --network coolify -e PORT=3000 \
  -l "traefik.enable=true" \
  -l "traefik.http.routers.ebay-dashboard.rule=Host(\`ebay.ai-online.cloud\`)" \
  -l "traefik.http.routers.ebay-dashboard.entrypoints=https" \
  -l "traefik.http.routers.ebay-dashboard.tls=true" \
  -l "traefik.http.routers.ebay-dashboard.tls.certresolver=letsencrypt" \
  -l "traefik.http.services.ebay-dashboard.loadbalancer.server.port=3000" \
  ebay-dashboard:latest

# 5. Prüfen
docker logs ebay-dashboard --tail 10
```

### Git Push

```bash
cd /opt/ebay-dashboard
git config --global credential.helper store
git add -A
git commit -m "<message>"
git push origin main
# Username: Karabas789
# Password: GitHub Personal Access Token
```

> ⚠️ **Git Push IMMER EINZELN ausführen** — nicht mit Docker-Befehlen mischen!
> Git fragt nach dem Username und schluckt den nächsten Befehl als Eingabe.

### Deploy-Gotchas

| # | Problem | Lösung |
|---|---|---|
| 1 | CSS-Änderungen werden nicht übernommen | `docker build --no-cache` |
| 2 | Browser zeigt alte Version | `Cmd+Shift+R` (Hard Reload) |
| 3 | `</style>` in JS | `'</' + 'style>'` escapen |
| 4 | Workspace-Download-URLs auf Server | Dateien über GitHub hochladen oder per Terminal-Heredoc/SCP |
| 5 | `{@const}` in HTML-Element | Nur in Block-Tags erlaubt |
| 6 | Coolify Auto-Deploy | Deaktiviert (Bug mit HTTPS git clone) — manuell deployen |

---

## 14. Bekannte eBay API-Fehler

### Fehler 21920061: „Produktart" als variationSpecifics ungültig

- **Ursache:** `Produktart` wird fälschlicherweise als `variationSpecifics` übergeben
- **Betroffene Artikel:** IDs 1250, 2019, 481, 990, 2279, 232, 1759, u.v.m.
- **Fix:**
```js
const allowedVariantSpecifics = ["Größe", "Farbe", "Material", "Stil"];
const cleaned = items[0].json.variationSpecifics.filter(
  spec => allowedVariantSpecifics.includes(spec.name)
);
return [{ json: { ...items[0].json, variationSpecifics: cleaned } }];
```

### Fehler 21920287: Fehlende SKU bei Variante mit eBay-Fulfillment

- **Ursache:** Variante hat keine SKU, eBay-Fulfillment erfordert SKU
- **Fix:**
```js
const variations = items[0].json.variations.map((variant, index) => ({
  ...variant,
  sku: variant.sku || `AUTO-SKU-${items[0].json.itemId}-${index + 1}`
}));
return [{ json: { ...items[0].json, variations } }];
```

### SKU-Matching Risiko (Bulk)

- SKUs werden per Index zugeordnet, nicht per Value-Match
- Bei abweichender Reihenfolge können SKUs falsch zugeordnet werden
- **Status:** Offen

### Kein user_id-Filter im SKU-Bulk-Workflow

- Node „Alle Varianten laden" filtert nicht nach `user_id`
- **Risiko:** Theoretisches Datenleck bei gleicher `ebay_artikel_id` bei Fremd-Nutzern
- **Status:** Offen — Fix bei erstem Fremd-Nutzer

---

## 15. Einstellungen-Seite

### Kacheln-Übersicht

```javascript
const tiles = [
  { icon: '🏢', title: 'Firmendaten',      href: '/einstellungen/firma' },
  { icon: '🔢', title: 'Nummerierung',     href: '/einstellungen/nummern' },
  { icon: '📧', title: 'E-Mail / SMTP',    href: '/einstellungen/smtp' },
  { icon: '🤖', title: 'KI-Konfiguration', href: '/einstellungen/ki' },
  { icon: '💬', title: 'Kauf-Nachricht',   href: '/einstellungen/kauf-nachricht' },
  { icon: '🖼️', title: 'Produktbilder',   href: '/einstellungen/bilder' },
];
```

Alle Unterseiten haben einen `← Zurück`-Button (`goto('/einstellungen')`).
