# Max2090 – Mäxchen gegen den Computer

Würfel-Bluffspiel (Mäxchen, Meiern) für den **Busch Microtronic 2090**: ein Spieler gegen den Computer, nur mit der 6-stelligen Anzeige, den vier Ausgangs-LEDs und der Hex-Tastatur. Keine Matrix, keine Kabel, kein Userscript.

Aktuelle Version: **06** (die Versionsnummer steht nur in `maexchen.xml`), 255 Schritte (00–FE), 1 frei. Im Emulator2090 gegen ein unabhängiges Regelmodell getestet, noch nicht am Gerät gespielt.

## Dateien

| Datei | Inhalt |
|---|---|
| `maexchen.mic` | Programm zum Laden (eine Zeile pro Schritt) |
| `maexchen.src` | Quelle mit Marken und Registerrollen, übersetzt mit `micasm.py` (esp2090-firmware/tools) |
| `maexchen.xml` | Regeln, Strategie, Register, Routinen mit Adressen, Zeitverhalten, Tests, offene Punkte |
| `maexchen_test.py` | Test im Emulator2090: `python maexchen_test.py <Ordner mit microtronic.py>` |

## Start

RESET, RUN. Die LEDs zeigen F, die Anzeige den Spielstand (gewonnene Spiele: links du, rechts der Computer). Level 1–9 tippen. Du beginnst.

## Anzeige

```
L  S S  K K  C
```

- **L** deine Leben, **C** Leben des Computers (je 6)
- **S S** deine Seite: dein Wurf, deine Eingabe, deine Ansage, beim Aufdecken dein echter Wurf
- **K K** Seite des Computers: seine Ansage, beim Aufdecken sein echter Wurf; 00 = nichts

## LEDs und Tasten

| LEDs | Bedeutung | Tasten |
|---|---|---|
| 1 | du bist dran | 1–6 überschreiben den Wurf (Ziffern schieben von rechts ein), A sagt an |
| 2 | der Computer hat angesagt | A glauben und selbst würfeln, B anzweifeln |
| 4 | du verlierst die Runde | beliebige Taste |
| 8 | der Computer verliert die Runde | beliebige Taste |
| F | Level wählen (nach Spielende) | 1–9 |

## Regeln

- Rangfolge: 31 32 41 42 43 51 … 65, dann Pasch 11 22 … 66, ganz oben Mäxchen 21.
- Jede Ansage muss die vorige übertreffen; eine zu niedrige Eingabe bleibt stehen.
- Wer zweifelt, deckt den Wurf des Ansagers auf: Wurf mindestens so hoch wie die Ansage = der Zweifler verliert, sonst der Ansager.
- Eine verlorene Mäxchen-Runde kostet 2 Leben. Glaubt man ein angesagtes Mäxchen (A), kostet das 1 Leben ohne Aufdecken.
- Der Verlierer beginnt die nächste Runde. Bei 0 Leben ist das Spiel aus.

## Der Computer

- Zweifelt Mäxchen immer an, sonst Ansagen über 64 bzw. 65 (gestreut) und Minimalerhöhungen über seine eigene Ansage ab 51.
- Ist er abgelenkt (Level 1 fast immer, Level 9 nie), entscheidet eine Münze.
- Sagt wahr an, wenn sein Wurf reicht. Sonst lügt er: meist 1–3 Stufen über deiner Ansage, in etwa jedem vierten Fall aus zwei Würfen im Kopf – der erste, der deine Ansage schlägt, wird angesagt, bis 21.
- Wahrheit und Lüge dauern exakt gleich lang (Computerzug 3,4–3,6 s, nur von deiner Ansage abhängig). An der Rechendauer lässt sich die Lüge nicht erkennen.

## Zufall

Würfe kommen aus dem RND-Zähler direkt nach einem Tastendruck (der Zähler läuft, solange KIN wartet). Die Entscheidungen des Computers mischen den Zählerstand vor und nach der Taste, damit sie nicht an seinem Wurf hängen. Würfel: über alle 4096 Zählerstände höchstens 4,6 Prozent neben dem Sollwert.

## Versionen

- **06** Bluff ohne feste Obergrenze (1/4 der Lügen aus zwei Kopfwürfen, bis 21); Würfel mit Dritteln statt mod 3.
- **05** Feste Seiten: links immer der Spieler, rechts immer der Computer.
- **04** verworfen (nie mit 21 lügen – eine 21-Lüge lohnt sich, weil Zweifeln an Mäxchen 2 Leben kostet).
- **03** Ohne Flag-Kosmetik, gleiche Dauer mit vorbelegtem Merkspeicher.
- **02** Wahrheit und Lüge gleich lang.
- **01** Erste Fassung, 9 Level.
