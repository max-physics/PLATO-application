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
- Optionaler ExoPie-Vergleich für felsige Innenstrukturen mit sichtbaren Modellannahmen
- Bahndistanz und Kreisbahn-Geschwindigkeit; bei verfügbarer Exzentrizität auch Periastron-/Apoastron-Abstand und -Geschwindigkeit

Die Innenstrukturresultate sind Demonstrator-Näherungen. Die felsige Zwei-Schichten-Kurve nach Zeng et al. (2016) wird hier nur im begrenzten Bereich von 1–8 Erdmassen und CMF 0–0,4 verwendet; sie ersetzt keine vollständige thermodynamische Innenstrukturanalyse.

## Erste Analysemodelle

- Mittlere Dichte: `ρ = ρ⊕ · M/M⊕ · (R/R⊕)⁻³`
- Oberflächengravitation: `g = g⊕ · M/M⊕ · (R/R⊕)⁻²`
- Messunsicherheiten werden mit 20.000 unabhängigen Monte-Carlo-Ziehungen aus asymmetrischen Fehlerverteilungen fortgepflanzt. Fehlt eine benötigte Eingangsunsicherheit, wird nur der Zentralwert berechnet.
- Das logarithmische Masse-Radius-Diagramm auf der Startseite zeigt Katalogplaneten. Ein Klick öffnet die Detailseite.
- Unter dem Diagramm zeigt der Bereich „Modelle“ abgeleitete Dichte und Oberflächengravitation sowie das felsige Zwei-Schichten-Modell. Ein CMF-Regler reicht von 0 bis 100 %; die Kurve erscheint ausschließlich im dokumentierten Modellbereich CMF 0–40 % und 1–8 Erdmassen.
- Die optionale Zwei-Schichten-Näherung invertiert die Beziehung von [Zeng et al. (2016)](https://doi.org/10.3847/0004-637X/819/2/127), nimmt einen Eisenkern und Silikatmantel an und gilt nur für 1–8 Erdmassen sowie CMF 0–0,4. Sie ist keine eindeutige Messung der tatsächlichen Zusammensetzung.
- **ExoPie ist eine optionale Abhängigkeit** (`python -m pip install -r requirements-exopie.txt`). Die App nutzt dessen `rocky`-Planetmodell mit Katalogmasse und -radius samt asymmetrischen Fehlern. Masse und Radius werden unabhängig gezogen, weil der Katalog keine Kovarianz bereitstellt; die Stichprobenzahl ist dadurch exakt wie angefordert. Die Priorbereiche sind `xSi = 0–0,2` (Siliziumanteil im Kern) und `xFe = 0–0,2` (Eisenanteil im Mantel); die Zahl der Ziehungen ist in der Oberfläche wählbar. Der Standard von 50 Ziehungen ist nur eine schnelle Vorschau und liefert keine stabilen wissenschaftlichen Perzentile; für eine belastbarere Auswertung muss die Zahl erhöht werden. Die angezeigten Intervalle sind das 16., 50. und 84. Perzentil der vom Modell akzeptierten Ziehungen.
- ExoPies `planet-star`-Ansatz wird vorerst **nicht** gerechnet: Dafür erforderliche stellare Fe/Mg/Si-Häufigkeiten liegen in unserem lokalen Katalog nicht vor. Werte oder Fehler werden nicht ergänzt oder geschätzt. Der ExoPie-Reiter bleibt für einen Planeten ohne vollständige Masse-/Radiusfehler deaktiviert.
- **Gültigkeit:** Dieses ExoPie-Ergebnis ist eine bedingte Inferenz, keine eindeutige Innenstrukturmessung. Es gilt nur für die gewählte felsige Modellklasse und die angezeigten Prioren. Wasserreiche Welten und H/He-Hüllen brauchen andere Modellklassen und Annahmen; sie sind in dieser ersten Anbindung nicht enthalten. Siehe [ExoPie User Guide](https://exopie.readthedocs.io/en/latest/user_guide.html), [ExoPie auf PyPI](https://pypi.org/project/exopie/) und Plotnykov & Valencia (2024), [MNRAS, doi:10.1093/mnras/stae993](https://doi.org/10.1093/mnras/stae993).
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

Beim ersten Start wird `data/plato_demo.db` angelegt und mit einem synthetischen Demonstrationsplaneten sowie 1.000 bestätigten Exoplaneten initialisiert. Die öffentlichen Datensätze liegen statisch in `data/public_confirmed_planets.csv`; die App fragt beim Start keine externen Datenquellen ab. Die Planeten stammen aus der Tabelle *Planetary Systems Composite Parameters* des [NASA Exoplanet Archive](https://exoplanetarchive.ipac.caltech.edu/), abgerufen am 14. November 2026. Der Snapshot enthält 1.000 eindeutige Planeten mit bekannten Masse- und Radiuswerten; dafür wurden `pl_controv_flag=0`, Masse und Radius ungleich `NULL` abgefragt. Seit dem ursprünglichen 50-Planeten-Bestand wurden 950 weitere Namen alphabetisch aus dem öffentlichen Katalog ergänzt. Übernommene Werte umfassen Umlaufperiode, Radius und Masse, Sternmasse, große Halbachse und Exzentrizität sowie jeweils verfügbare Unsicherheiten. Fehlende Parameter oder Fehlerwerte bleiben leer. Jeder Planet ist mit seinem Hoststern verknüpft. `is_synthetic=False`, `provenance`, `source_url` und `data_release` kennzeichnen und dokumentieren die öffentlichen Datensätze.

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
