# PLATO Scientific Data Analysis Lab

Eigenständiger wissenschaftlicher Softwaredemonstrator für die Exploration astronomischer Daten und die Vorbereitung von Analysen zu Exoplaneten. Der Bestand enthält öffentliche Katalogwerte und klar gekennzeichnete synthetische Demo-Daten. Die Anwendung ist nicht mit internen PLATO-Datenbanken verbunden.

> **Wichtiger Hinweis:** Das relationale Datenbankschema ist ein projektspezifischer Demonstrator. Es bildet kein originales oder offizielles PLATO-Datenbankschema ab.

## Funktionen im Grundgerüst

- Streamlit-Startseite mit Planetensuche und logarithmischem Masse-Radius-Diagramm; ein Punktklick öffnet die Planetendetails
- Unverändertes PLATO-Missionsemble mit Quellen- und Lizenzangabe (ESA, CC BY-SA 3.0 IGO); der Demonstrator ist nicht offiziell mit ESA verbunden
- Lokal eingebundenes, KI-generiertes Hintergrundmotiv: oben Sternenfeld, beim Scrollen nach unten eine aufgeschnittene Erde mit sichtbaren Schichten
- SQLite-Speicherung über SQLAlchemy ORM
- 1.000 bestätigte Exoplaneten aus einem statischen, öffentlich zugänglichen NASA Exoplanet Archive-Snapshot
- Getrennte Tabellen für Beobachtungen, Datenprodukte sowie Modellläufe und Modellresultate
- Beispielbestand wird beim ersten Start angelegt und ist in den Datensätzen als synthetisch markiert
- Erste Datenbanktests mit einer isolierten temporären SQLite-Datenbank
- Abgeleitete Dichte und Oberflächengravitation mit optionaler Unsicherheitsfortpflanzung
- Masse-Radius-Diagramm und eingeschränkte felsige Zwei-Schichten-Näherung
- Bahndistanz und Kreisbahn-Geschwindigkeit; bei verfügbarer Exzentrizität auch Periastron-/Apoastron-Abstand und -Geschwindigkeit

Die Innenstrukturresultate sind Demonstrator-Näherungen. Die felsige Zwei-Schichten-Kurve nach Zeng et al. (2016) wird hier nur im begrenzten Bereich von 1–8 Erdmassen und CMF 0–0,4 verwendet; sie ersetzt keine vollständige thermodynamische Innenstrukturanalyse.

## Erste Analysemodelle

- Mittlere Dichte: `ρ = ρ⊕ · M/M⊕ · (R/R⊕)⁻³`
- Oberflächengravitation: `g = g⊕ · M/M⊕ · (R/R⊕)⁻²`
- Messunsicherheiten werden mit 20.000 unabhängigen Monte-Carlo-Ziehungen aus asymmetrischen Fehlerverteilungen fortgepflanzt. Fehlt eine benötigte Eingangsunsicherheit, wird nur der Zentralwert berechnet.
- Das logarithmische Masse-Radius-Diagramm auf der Startseite zeigt Katalogplaneten. Ein Klick öffnet die Detailseite.
- Unter dem Diagramm zeigt der Bereich „Modelle“ abgeleitete Dichte und Oberflächengravitation sowie das felsige Zwei-Schichten-Modell. Ein CMF-Regler reicht von 0 bis 100 %; die Kurve erscheint ausschließlich im dokumentierten Modellbereich CMF 0–40 % und 1–8 Erdmassen.
- **Ein einziges Innenstrukturmodell:** Die App invertiert die semi-empirische PREM-basierte Näherung aus [Zeng, Sasselov & Jacobsen (2016)](https://doi.org/10.3847/0004-637X/819/2/127): `R/R⊕ = (1.07 − 0.21·CMF) · (M/M⊕)^(1/3.7)`. CMF ist der Eisenkern-Massenanteil. Das Zwei-Schichten-Modell nimmt einen Eisenkern und Silikatmantel ohne Wasser- oder H/He-Hülle an. Der im Artikel genannte Gültigkeitsbereich von 1–8 Erdmassen und CMF 0–0,4 wird eingehalten; außerhalb dieses Bereichs wird die Kurve nicht extrapoliert.
- **Unsicherheiten und Grenzen:** Bei vollständigen Fehlerangaben werden 20.000 unabhängige Monte-Carlo-Ziehungen für Masse und Radius verwendet. Masse und Radius werden mangels Katalogkovarianz unabhängig behandelt; unzulässige Ziehungen außerhalb des Gültigkeitsbereichs werden verworfen. Angezeigte Intervalle berücksichtigen Messfehler, aber nicht den zusätzlichen Näherungsfehler der publizierten Fitformel (im Artikel etwa 0,01 Erdradien bzw. ungefähr 0,02 CMF). Die CMF ist eine modellabhängige Schätzung, keine eindeutige Messung der tatsächlichen Zusammensetzung.
- Die CMF-Regler-Skala reicht zur Exploration von 0 bis 100 %. Die Zeng-Modellkurve wird jedoch nur im veröffentlichten Bereich CMF 0–40 % und 1–8 Erdmassen gezeigt.
- **Bahnnäherung:** Die Detailseite zeigt die große Halbachse aus dem Katalog oder leitet sie, falls nötig, mit Umlaufperiode und Sternmasse aus Keplers drittem Gesetz ab. Die Kreisbahngeschwindigkeit wird aus Stern-/Planetenmasse und großer Halbachse berechnet. Wenn die Exzentrizität vorliegt, kommen Periastron-/Apoastron-Abstand und die zugehörigen Geschwindigkeiten nach der Vis-Viva-Gleichung hinzu. Das sind Zentralwert-Näherungen; Messunsicherheiten der Bahngrößen werden dabei noch nicht fortgepflanzt.
- Berechnete Werte lassen sich als Modelllauf samt Version und Unsicherheiten in `model_runs` und `model_results` speichern.

## Lokal starten

Voraussetzung: Python 3.10 oder neuer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Beim ersten Start wird `data/plato_demo.db` angelegt und mit einem synthetischen Demonstrationsplaneten sowie 1.000 bestätigten Exoplaneten initialisiert. Die öffentlichen Datensätze liegen statisch in `data/public_confirmed_planets.csv`; die App fragt beim Start keine externen Datenquellen ab. Die Planeten stammen aus der Tabelle *Planetary Systems Composite Parameters* des [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/), abgerufen am 14. November 2026. Der Snapshot enthält 1.000 eindeutige Planeten. Masse ist bei allen vorhanden, Radius bei 999; bei HD 7199 b fehlt der Katalogradius und er bleibt deshalb unbekannt. Übernommene Werte umfassen Umlaufperiode, Radius und Masse, Sternmasse, große Halbachse und Exzentrizität sowie jeweils verfügbare Unsicherheiten. Fehlende Parameter oder Fehlerwerte bleiben leer. Jeder Planet ist mit seinem Hoststern verknüpft. `is_synthetic=False`, `provenance`, `source_url` und `data_release` kennzeichnen und dokumentieren die öffentlichen Datensätze.

Zum Zurücksetzen kann die lokale Datei `data/plato_demo.db` gelöscht werden; beim nächsten Start wird sie aus den mitgelieferten statischen Beispieldateien neu erzeugt. Der öffentliche Snapshot ist in [data/public_confirmed_planets.csv](data/public_confirmed_planets.csv) abgelegt.

## Datenmodell

| Tabelle | Zweck |
|---|---|
| `stars` | Sternkatalogeinträge mit optionaler Temperatur, Radius und Masse samt verfügbaren Fehlern |
| `planets` | Planetenparameter einschließlich Umlaufperiode, großer Halbachse und Exzentrizität, dem jeweiligen Stern zugeordnet |
| `observations` | Beobachtungsmessungen mit Wert, Einheit und optionaler Unsicherheit |
| `data_products` | Referenzen/Metadaten zu Produkten mit Stufe `L2` oder `L3`, Version und Herkunft |
| `model_runs` | Metadaten und Status eines Modelllaufs, getrennt von Messungen |
| `model_results` | Parameterwerte und Unsicherheiten, die zu einem Modelllauf gehören |

Fremdschlüssel halten die Beziehungen konsistent. Messwerte werden als numerischer Wert plus Einheit gespeichert; Unsicherheiten sind separat und optional. `is_synthetic` kennzeichnet synthetische Datensätze explizit. `provenance` und `version` dokumentieren Herkunft und Version von Datenprodukten; diese Felder sind Demonstrator-Metadaten und stellen keine PLATO-Spezifikation dar.

Die Datenbank wird beim Import nicht automatisch erstellt. `database.init_db()` legt Tabellen an und seedet nur dann, wenn die Datenbank noch keine Sterne enthält. Für Tests kann eine eigene SQLite-URL übergeben werden.

## Tests

```bash
pytest
```

## Projektdokumentation

Eine leere [LaTeX-Vorlage](docs/projektdokumentation.tex) für die eigene
technische und wissenschaftliche Dokumentation liegt im Projekt. Mit einer installierten
LaTeX-Distribution lässt sie sich im Projektordner beispielsweise so bauen:

```bash
pdflatex -output-directory=/tmp docs/projektdokumentation.tex
```

Für Inhaltsverzeichnis und Querverweise den Befehl ein zweites Mal ausführen.

## Projektstruktur

```text
app.py                 Streamlit-Einstiegspunkt
pages/                 Platzhalter für spätere Streamlit-Module
database/              Datenbankverbindung, Initialisierung und Seed-Daten
models/                SQLAlchemy-Modelle
analysis/              Platzhalter für spätere Analysefunktionen
data/                  lokale SQLite-Datenbank (wird beim Start erzeugt)
tests/                 automatisierte Datenbanktests
requirements.txt       Python-Abhängigkeiten
```
