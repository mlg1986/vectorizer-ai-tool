# Vectorizer AI Tool

Ein Python-Tool für die Vektorisierung von Bildern mit der Vectorizer.ai API. Das Tool bietet automatisches Upscaling, intelligente Palette-Optimierung und detaillierte Kontrolle über die Vektorisierungsparameter.

## Features

- 🖼️ **Automatisches Upscaling**: Skaliert Bilder lokal hoch, bevor sie an die API gesendet werden, für mehr Details bei großen Ausgabegrößen
- 🎨 **Palette-Optimierung**: Reorganisiert Farbpaletten, sodass Skin Tones zuletzt verwendet werden
- 📏 **Seitenverhältnis-Erhaltung**: Verhindert Verzerrung beim Upscaling
- ⚙️ **Vielseitige Parameter**: Kontrolle über Detailgrad, Mindestfläche, maximale Farben und mehr
- 💾 **Einstellungen speichern**: Alle Parameter werden in `config.ini` gespeichert
- 📁 **Ordnerbasierte Verarbeitung**: Unterstützt Batch-Verarbeitung über Ordnernummern

## Installation

### Voraussetzungen

- Python 3.7 oder höher
- pip (Python Package Manager)

### Abhängigkeiten installieren

```bash
pip install requests pillow cairosvg
```

**Hinweis**: `cairosvg` ist optional und wird nur für die SVG-Vorschau benötigt.

## Verwendung

### Starten des Tools

```bash
python vectorizer_ai.py
```

### Erste Schritte

1. **API-Schlüssel einrichten**:
   - Öffne die Einstellungen (Button "Einstellungen")
   - Gib deinen Vectorizer.ai API Key und Secret ein
   - Speichere die Einstellungen

2. **Bild auswählen**:
   - Klicke auf "Durchsuchen" und wähle ein Bild aus
   - Oder gib eine Ordnernummer ein, wenn du Bilder aus einem Ordner laden möchtest

3. **Parameter anpassen**:
   - **Breite/Höhe (cm)**: Gewünschte Ausgabegröße
   - **Mindestfläche (px)**: Minimale Fläche für Details (0.125 - 100)
   - **Maximale Farben**: Anzahl der verwendeten Farben
   - **Skin Tones**: Anzahl der Skin Tone Farben am Anfang der Palette (werden ans Ende verschoben)

4. **Vektorisieren**:
   - Klicke auf "Vektorisieren"
   - Das Tool skaliert das Bild automatisch hoch (wenn nötig) und sendet es an die API

## Wichtige Parameter

### Mindestfläche (min_area_px)

- **Bereich**: 0.125 - 100 Pixel
- **Wirkung**: Kleinere Werte = mehr Details, größere Werte = weniger Details
- **Hinweis**: Bei großen Bildern (durch Upscaling) wirkt derselbe Wert feiner, da er relativ zur Bildgröße kleiner wird

### Skin Tones

- **Standard**: 549 (für die mitgelieferte `malango_colors.gpl` Palette)
- **Funktion**: Die ersten N Farben der Palette werden ans Ende verschoben
- **Grund**: Die API verwendet die Palette "von hinten", daher werden Skin Tones zuletzt verwendet

### Upscaling

Das Tool erkennt automatisch, wenn die gewünschte Ausgabegröße größer ist als das Originalbild und skaliert es lokal hoch:
- **Seitenverhältnis wird beibehalten** (keine Verzerrung)
- **Maximale Dimension**: 8000px (um Timeouts zu vermeiden)
- **Resampling**: LANCZOS (hochwertige Interpolation)

## Projektstruktur

```
.
├── vectorizer_ai.py          # Hauptanwendung
├── config.ini                # Einstellungen (wird automatisch erstellt)
├── malango_colors.gpl        # Farbpalette
├── .gitignore                # Git Ignore-Datei
└── README.md                 # Diese Datei
```

## Konfiguration

Die Einstellungen werden in `config.ini` gespeichert:

```ini
[API]
api_key = dein_api_key
api_secret = dein_api_secret

[Settings]
input_base_folder = C:/Pfad/zum/Input
output_folder = C:/Pfad/zum/Output
gpl_file_path = Pfad/zur/palette.gpl
mode = preview
output.file_format = png
processing.shapes.min_area_px = 50
processing.max_colors = 36
skin_tone_count = 549
```

## Technische Details

### Upscaling-Logik

1. Berechnet Zielgröße in Pixeln basierend auf cm und DPI
2. Prüft, ob Zielgröße > Originalgröße (Faktor > 1.1)
3. Skaliert Bild lokal hoch mit LANCZOS-Resampling
4. Speichert temporär als PNG
5. Sendet hochskaliertes Bild an API
6. Löscht temporäre Datei nach Upload

### Palette-Reorganisation

1. Liest GPL-Datei ein
2. Extrahiert Hex-Farbwerte
3. Trennt erste N Farben (Skin Tones) vom Rest
4. Erstellt neue Reihenfolge: Rest + Skin Tones
5. Sendet reorganisierte Palette an API

## Fehlerbehebung

### "API parameter error: processing.shapes.min_area_px: Must be less or equal to 100"

- Der `min_area_px` Wert überschreitet das API-Limit
- Lösung: Reduziere den Wert auf maximal 100

### "Bild ist verzerrt"

- Das Upscaling sollte das Seitenverhältnis beibehalten
- Falls es trotzdem verzerrt ist, prüfe die Eingabewerte (Breite/Höhe in cm)

### "Zu große Flächen, Details gehen verloren"

- Reduziere `min_area_px` (z.B. von 50 auf 25)
- Erhöhe die Ausgabegröße (mehr cm) - das Tool skaliert automatisch hoch
- Prüfe, ob Upscaling aktiv ist (siehe Logs)

## Lizenz

Dieses Projekt ist für den internen Gebrauch bestimmt.

## Autor

Entwickelt für Hammer und Brücher GmbH

