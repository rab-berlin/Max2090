# Max2090 – Mäxchen gegen den Computer

Würfel-Bluffspiel (Mäxchen, Meiern) für den **Busch Microtronic 2090**: ein Spieler gegen den Computer, nur mit der 6-stelligen Anzeige, den vier Ausgangs-LEDs und der Hex-Tastatur.

- 255 Programmschritte (00-FE), 1 frei

## Datei

`maexchen.mic` – das Programm zum Laden, eine Zeile pro Schritt.

## Start

RESET, RUN. Alle vier LEDs an den Ausgängen leuchten, die Anzeige zeigt den Spielstand (gewonnene Spiele: links du, rechts der Computer). Level 1–9 tippen. Du beginnst.

## Anzeige

```
L  S S  K K  C
```

- **L** deine Leben, **C** Leben des Computers (je 6)
- **S S** deine Seite: dein Wurf, deine Eingabe, deine Ansage, beim Aufdecken dein echter Wurf
- **K K** Seite des Computers: seine Ansage, beim Aufdecken sein echter Wurf; 00 = nichts

## LEDs und Tasten

Die vier LEDs an den Ausgängen 1–4 zeigen, was gerade los ist. Es leuchtet immer genau eine, nur bei der Levelwahl alle vier.

| LED an | Bedeutung | Tasten |
|---|---|---|
| Ausgang 1 | du bist dran: dein Wurf steht links | A sagt den Wurf an; vorher kannst du ihn mit 1–6 überschreiben (die Ziffern schieben sich von rechts ein) |
| Ausgang 2 | der Computer hat angesagt (rechts) | A glauben, dann würfelst du; B anzweifeln |
| Ausgang 3 | du verlierst die Runde | beliebige Taste |
| Ausgang 4 | der Computer verliert die Runde | beliebige Taste |
| alle vier | Spiel zu Ende, Level wählen | 1–9 |

Nach dem Aufdecken steht der echte Wurf auf der Seite dessen, der angesagt hat; die andere Seite zeigt 00. Hast du ein Mäxchen geglaubt, wird nicht aufgedeckt.

## Regeln

- Rangfolge: 31 32 41 42 43 51 … 65, dann Pasch 11 22 … 66, ganz oben Mäxchen 21.
- Jede Ansage muss die vorige übertreffen; eine zu niedrige Eingabe bleibt stehen.
- Wer zweifelt, deckt den Wurf des Ansagers auf: Wurf mindestens so hoch wie die Ansage = der Zweifler verliert, sonst der Ansager.
- Eine verlorene Mäxchen-Runde kostet 2 Leben. Glaubt man ein angesagtes Mäxchen (A), kostet das 1 Leben ohne Aufdecken.
- Der Verlierer beginnt die nächste Runde. Bei 0 Leben ist das Spiel aus.

## Der Computer

Level 1 ist zerstreut und macht viele Fehler, Level 9 spielt seine volle Stärke. Gegen einen durchschnittlichen Spieler gewinnt er auf Level 1 etwa ein Drittel der Spiele, auf Level 9 gut die Hälfte.

Er blufft, er zweifelt, und er hat ein Gedächtnis für die laufende Runde. Wann er was tut, verrät er nicht – auch nicht über die Rechenzeit: Wahrheit und Lüge dauern genau gleich lang (gut 3 Sekunden, die Anzeige ist dabei dunkel). Wer ihn durchschauen will, muss ihn beim Spielen beobachten.

## Ein bisschen Spieltheorie

Mäxchen ist ein Spiel mit unvollständiger Information wie Poker: Jeder kennt nur seinen eigenen Wurf. Mit solchen Spielen beginnt die mathematische Spieltheorie. John von Neumann bewies 1928 sein Minimax-Theorem und untersuchte in *Theory of Games and Economic Behavior* (1944, mit Oskar Morgenstern) ein vereinfachtes Poker. Ergebnis: Bluffen ist kein psychologischer Trick, sondern Teil der besten Strategie – und zwar mit einer ganz bestimmten Häufigkeit.

Der Grund ist einfach. Wer nie blufft, dem glaubt man jede hohe Ansage nicht, wenn sie unwahrscheinlich ist, und jede niedrige sowieso. Wer immer blufft, wird immer angezweifelt. Wer nach einer festen Regel blufft, wird berechenbar, sobald der Gegner die Regel kennt. Gut ist nur eine **gemischte Strategie**: Bluffen nach Zufall, so dosiert, dass der Gegner aus der Ansage möglichst wenig lernt. Im Idealfall ist es ihm gleich, ob er glaubt oder zweifelt – das ist das Gleichgewicht, das John Nash 1950 allgemein für Spiele mit mehreren Spielern beschrieben hat.

Beim Mäxchen kommt eine Besonderheit dazu: Wer ein angesagtes Mäxchen glaubt, verliert ein Leben, wer es zu Unrecht anzweifelt, verliert zwei. Ein Mäxchen anzusagen kann sich deshalb auch dann lohnen, wenn man keines hat. Der Gegner muss wählen zwischen einem sicheren Verlust und einem doppelten Risiko.

Und schließlich die *Tells*: Beim Poker verraten sich Spieler durch Gesten oder Zögern. Ein Computer verrät sich durch seine Rechenzeit, wenn eine Lüge länger dauert als die Wahrheit. Deshalb rechnet dieser Computer immer alles durch, auch das, was er gerade nicht braucht.

## Zufall

Würfe kommen aus dem RND-Zähler direkt nach einem Tastendruck (der Zähler läuft, solange KIN wartet). Die Entscheidungen des Computers nutzen zusätzlich den Zählerstand vor der Taste, damit sie nicht an seinem Wurf hängen. Würfel: über alle 4096 Zählerstände höchstens 4,6 Prozent neben dem Sollwert.
