# Rechner

Ein schlanker Desktop-Taschenrechner (Tkinter) als Alternative zum Windows-Standardrechner. Unterstützt Grundrechenarten, Klammern, Vorzeichenwechsel, Backspace, Tastatursteuerung sowie eine klickbare Verlaufsliste. Ergebnisse werden mit Leerzeichen als Tausender-Trenner formatiert. Das Fenster ist frei skalierbar, die UI füllt den verfügbaren Platz und nutzt einen modernen Dark-Look mit Akzentfarbe (inkl. dunkler Titelbar/Scrollbar, wenn vom System erlaubt). Lange Ausdrücke werden im Display automatisch über mehrere Zeilen umbrochen, und unter dem Display wird live das Ergebnis des aktuellen Ausdrucks gezeigt.

## Voraussetzungen
- Python 3.10+ (Standardbibliothek, keine Zusatzpakete nötig)

## Starten
```powershell
python app.py
```

## Bedienung
- Maus: Buttons anklicken
- Tastatur: Ziffern, `+ - * / ( ) .`, Enter (=), Backspace (Löschen eines Zeichens), Escape/Delete (Reset)
- `C` leert das Eingabefeld, `±` wechselt das Vorzeichen, `←` löscht das letzte Zeichen.
- Historie: Doppelklick auf einen Eintrag lädt den Ausdruck wieder ins Eingabefeld, um ihn anzupassen.

## Hinweise
- Ausdrücke werden sicher via Python-AST ausgewertet, d.h. kein Ausführen von Code, nur Zahlen und Operatoren.
- Division durch 0 wird abgefangen und als Fehler gemeldet.
