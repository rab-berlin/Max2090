"""Test fuer maexchen-06.mic (feste Seiten; Bluff 3/4 nah, 1/4 Kopfwurf bis 21) im Emulator2090 (microtronic.py) gegen ein unabhaengiges Regelmodell.

Der simulierte Spieler sitzt an der Tastatur: bei jedem KIN liest er LEDs und Anzeige,
prueft sie gegen das Modell und waehlt eine Taste. Die Wartezeit vor jeder Taste setzt den
RND-Zaehler auf einen zufaelligen Wert (wie am Geraet, Zaehler laeuft waehrend KIN).
Jede RND-Ausfuehrung wird protokolliert; das Modell rechnet daraus Wuerfel, Zweifel und Luege
des Computers nach (eigene Formeln in Rang-Darstellung, nicht der 2090-Code).

Aufruf: python maexchen_test.py [Ordner mit microtronic.py]  (oder Umgebungsvariable EMULATOR2090)
"""
import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
EMU = os.environ.get("EMULATOR2090") or next(
    (a for a in sys.argv[1:] if os.path.isdir(a)), os.path.join(HERE, "..", "Emulator2090"))
sys.path.insert(0, EMU)
import microtronic as mt  # noqa: E402

VALS = [31, 32, 41, 42, 43, 51, 52, 53, 54, 61, 62, 63, 64, 65, 11, 22, 33, 44, 55, 66, 21]
R51, R65, R64 = VALS.index(51), VALS.index(65), VALS.index(64)
MAEX = 20


def rank_of(a, b):
    h, l = max(a, b), min(a, b)
    return VALS.index(10 * h + l)


def digits(r):
    return VALS[r] // 10, VALS[r] % 10


# ---- Modell -------------------------------------------------------------------------
def third(a, b):
    """Summe zweier Ziffern mit Uebertrag als +1 (also mod 15, 15 bleibt 15), dann Drittel 0-5/6-10/11-15."""
    x = a + b
    if x > 15:
        x -= 15
    return 0 if x <= 5 else (1 if x <= 10 else 2)


def model_dice(ctr):
    """Wuerfel aus dem Zaehlerstand (v06): 1 + 2 g(E+F) + (D mod 2), 1 + 2 g(D+F) + (E mod 2)."""
    d, e, f = ctr & 15, (ctr >> 4) & 15, ctr >> 8
    return 1 + 2 * third(e, f) + (d & 1), 1 + 2 * third(d, f) + (e & 1)


def model_el(level):
    return min(15, 2 * (9 - level))


def model_doubt(A, Q, u, v, el):
    """Zweifelt der Computer die Spieleransage A (Rang) an? Q = seine eigene vorige Ansage oder None.
    u = Zaehler vor der Taste, v = Zaehler nach der Taste: Y = F(u) + D(v), Z = E(u) + E(v)."""
    if A == MAEX:
        return True, False
    y = ((u >> 8) + (v & 15)) % 16
    z = (((u >> 4) & 15) + ((v >> 4) & 15)) % 16
    distracted = y < el
    if distracted:
        return z >= 8, True
    limit = R64 if (z & 3) == 0 else R65        # zweifeln, wenn A ueber 64 bzw. ueber 65
    if A > limit:
        return True, False
    if Q is not None and Q >= R51 and A == Q + 1:
        return True, False
    return False, False


def model_announce(R, P, ctr, distracted, heads=(), z=0):
    """Ansage des Computers bei eigenem Wurf R (Rang) und Ansage P (Rang oder None).
    ctr = Zaehlerstand V der Entscheidung: Ziffer F bestimmt die nahe Luegenweite.
    v06: ist z & 6 = 6 (Z = E(U) + E(V)), gilt der erste Kopfwurf aus heads, der P schlaegt."""
    if P is None or R > P:
        return R
    if z & 6 == 6:
        for H in heads:
            if H > P:
                return H
    k = (ctr >> 8) & 3
    n = k + 1 if distracted else max(k, 1)
    return min(P + n, MAEX)


# ---- Emulator mit RND-Protokoll -----------------------------------------------------
class CPU(mt.Microtronic):
    def __init__(self, prog):
        super().__init__(prog)
        self.rnd_log = []

    def special(self, b, nxt):
        if mt.SPECIAL[b] == "RND":
            self.rnd_log.append((self.pc, self.ctr))
        return super().special(b, nxt)


def labels(path):
    lab = {}
    for line in open(path, encoding="utf-8"):
        if ";" not in line:
            continue
        rest = line.split(";", 1)[1].split()
        if len(rest) >= 2 and rest[1].endswith(":"):
            lab[rest[1][:-1]] = int(rest[0], 16)
    return lab


class Fail(Exception):
    pass


class Game:
    """Ein Spieler sitzt am Emulator. strategy(kind, ...) waehlt die Zuege."""

    def __init__(self, mic, strategy, seed, level_seq, games, noise=True):
        self.prog, n = mt.load_program(mic)
        self.lab = labels(mic)
        self.cpu = CPU(self.prog)
        self.cpu.on_display = lambda c: None
        self.cpu.on_dot = lambda v: None
        self.cpu.key_source = self.key
        self.rng = random.Random(seed)
        self.strategy = strategy
        self.noise = noise                 # ungueltige Tasten einstreuen
        self.level_seq = list(level_seq)
        self.games_left = games
        self.tally = [0, 0]                # Spiele Spieler, Computer
        self.results = []                  # (level, Spieler gewinnt)
        self.dice = Counter()
        self.stats = Counter()
        self.queue = []
        self.liesP = []
        self.expect = ("level",)
        self.level = None

    # Hilfen
    def R(self, i):
        return self.cpu.R[i]

    def field(self, hi, lo):
        return self.R(hi), self.R(lo)

    def links(self):                 # Spielerseite
        return self.field(4, 3)

    def rechts(self):                # Computerseite
        return self.field(2, 1)

    def check(self, cond, text):
        if not cond:
            raise Fail(f"{text} | erwartet {self.expect} R={''.join(f'{x:X}' for x in self.cpu.R)} "
                       f"M={''.join(f'{x:X}' for x in self.cpu.M)} LED={self.cpu.dout:X}")

    def take_rnd(self, label):
        """RND-Eintraege seit dem letzten Tastendruck; liefert den Zaehlerstand an Adresse label."""
        adr = self.lab[label]
        while self.prog[adr] != 0xF05:       # erstes RND ab der Marke
            adr += 1
        vals = [c for pc, c in self.cpu.rnd_log if pc == adr]
        return vals

    def check_lives(self):
        self.check(self.R(5) == self.lives[0] and self.R(0) == self.lives[1], "Leben")

    def press(self, k):
        # U: RND in GETK direkt vor diesem KIN (Zufall des vorigen Tastendrucks)
        pre = [c for pc, c in self.cpu.rnd_log if pc == self.lab["GETK"] + 2]
        self.lastU = pre[-1] if pre else None
        # Wartezeit vor der Taste: Zaehler gleichverteilt (Geraet: Echtzeit waehrend KIN)
        self.cpu.ctr = self.rng.randrange(4096)
        self.cpu.rnd_log.clear()
        self.stats["tasten"] += 1
        return k

    # ---- KIN ----
    def key(self):
        if self.queue:
            k = self.queue.pop(0)
            return self.press(k)
        led = self.cpu.dout
        e = self.expect
        if e[0] == "level":
            self.check(led == 0xF, "LED F beim Levelbild")
            self.check(self.R(5) == self.tally[0] and self.R(0) == self.tally[1]
                       and all(self.R(i) == 0 for i in (1, 2, 3, 4, 6, 7)), "Spielstand im Levelbild")
            if self.games_left == 0:
                raise StopIteration
            if self.noise and self.rng.random() < 0.3:
                return self.press(self.rng.choice([0, 0xA, 0xB, 0xF]))   # wird ignoriert
            self.level = self.level_seq[(len(self.results)) % len(self.level_seq)]
            self.lives = [6, 6]
            self.P = None
            self.Q = None
            self.expect = ("pturn",)
            return self.press(self.level)
        if e[0] == "pturn":
            return self.pturn(led)
        if e[0] == "pin":            # nach einer ungueltigen Ansage
            self.check(led == 1, "LED 1 nach ungueltiger Ansage")
            self.check(self.links() == e[1], "links steht die abgelehnte Ansage geordnet")
            self.stats["abgelehnt"] += 1
            return self.player_announce(self.actual, typed=True)   # W zeigt nicht mehr den Wurf
        if e[0] == "after_pann":
            return self.after_player_announce(led)
        if e[0] == "result":
            return self.result(led)
        raise Fail("Zustand " + str(e))

    def pturn(self, led):
        self.check(led == 1, "LED 1 im Spielerzug")
        self.check_lives()
        if self.P is None:
            self.check(self.rechts() == (0, 0), "rechts 00 bei Rundenbeginn")
        else:
            self.check(self.rechts() == digits(self.P), "Ansage des Computers rechts")
        rnd = self.take_rnd("ROLL")
        self.check(len(rnd) == 1, "ein RND fuer den Spielerwurf")
        a, b = model_dice(rnd[0])
        self.dice[rank_of(a, b)] += 1
        h, l = max(a, b), min(a, b)
        self.check(self.links() == (h, l), f"Spielerwurf {h}{l} links")
        self.check(sorted((self.cpu.M[0xD], self.cpu.M[0xE])) == sorted((a, b)), "Wurf in MD/ME")
        self.actual = rank_of(a, b)
        return self.player_announce(self.actual, first=True)

    def player_announce(self, actual, first=False, typed=False):
        A = self.strategy.announce(actual, self.P, self.rng)
        keys = []
        if first and self.noise and self.rng.random() < 0.25:
            keys += [self.rng.choice([0, 7, 8, 9, 0xB, 0xC, 0xF])]           # ignoriert
        if first and self.noise and self.P is not None and self.P > 0 and self.rng.random() < 0.2:
            bad = self.rng.randrange(0, self.P + 1)                        # zu niedrig
            h, l = digits(bad)
            keys += [l, h, 0xA] if self.rng.random() < 0.5 else [h, l, 0xA]
            self.queue = keys[1:]
            self.expect = ("pin", (h, l))
            return self.press(keys[0])
        if A == actual and not typed and self.rng.random() < 0.7:
            keys.append(0xA)                                               # Wurf uebernehmen
        else:
            h, l = digits(A)
            if self.rng.random() < 0.5:
                h, l = l, h
            keys += [h, l, 0xA]
        self.annA = A
        self.expect = ("after_pann",)
        self.queue = keys[1:]
        return self.press(keys[0])

    def after_player_announce(self, led):
        A, P = self.annA, self.P
        Q = P                      # eigene vorige Ansage des Computers (oder None)
        dec = self.take_rnd("PV")
        if A == MAEX:
            self.check(not dec, "bei Maexchen kein RND")
            doubt, distracted = True, False
        else:
            self.check(len(dec) == 1, "ein RND fuer die Entscheidung")
            doubt, distracted = model_doubt(A, Q, self.lastU, dec[0], model_el(self.level))
        self.stats["entscheidungen"] += 1
        if doubt:
            self.stats["comp_zweifelt"] += 1
            self.check(led in (4, 8), "Computer zweifelt: Ergebnis-LED")
            self.check(self.links() == digits(self.actual), "aufgedeckter Spielerwurf links")
            self.check(self.rechts() == (0, 0), "rechts 00 beim Aufdecken des Spielers")
            liar = self.actual < A
            loser = 0 if liar else 1
            return self.finish(loser, 2 if A == MAEX else 1, led)
        # Computer glaubt, wuerfelt, sagt an
        self.check(led == 2, "Computer glaubt: LED 2")
        rolls = self.take_rnd("ROLL")
        self.check(len(rolls) == 3, "drei RND: zwei Kopfwuerfe, dann der Computerwurf")
        a, b = model_dice(rolls[2])
        self.dice[rank_of(a, b)] += 1
        Rc = rank_of(a, b)
        heads = [rank_of(*model_dice(c)) for c in rolls[:2]]
        self.check(sorted((self.cpu.M[0xD], self.cpu.M[0xE])) == sorted((a, b)), "Computerwurf in MD/ME")
        z = (((self.lastU >> 4) & 15) + ((dec[0] >> 4) & 15)) % 16
        C = model_announce(Rc, A, dec[0], distracted, heads, z)
        if C != Rc:
            self.stats["luege_kopf" if (z & 6 == 6 and C in heads) else "luege_nah"] += 1
            self.liesP.append((A, C, Rc))
        self.check(self.rechts() == digits(C), f"Ansage des Computers {VALS[C]} rechts")
        self.check(self.links() == digits(A), "Ansage des Spielers bleibt links")
        self.check_lives()
        self.stats["comp_luegt" if C != Rc else "comp_wahr"] += 1
        self.Q, self.P = A, C
        return self.player_reply(Rc, C)

    def player_reply(self, Rc, C):
        keys = []
        if self.noise and self.rng.random() < 0.2:
            keys.append(self.rng.choice([0, 1, 5, 9, 0xC, 0xF]))            # ignoriert
        doubt = self.strategy.doubt(C, self.Q, self.rng)
        if C == MAEX and not doubt:
            keys.append(0xA)
            self.stats["glaubt_maexchen"] += 1
            self.expect = ("result", ("concede",))
        elif doubt:
            keys.append(0xB)
            self.expect = ("result", ("pdoubt", Rc, C))
        else:
            keys.append(0xA)
            self.expect = ("pturn",)
        self.queue = keys[1:]
        return self.press(keys[0])

    def result(self, led):
        e = self.expect[1]
        if e[0] == "concede":
            self.check(self.rechts() == digits(MAEX), "rechts bleibt 21, kein Aufdecken beim Glauben")
            return self.finish(0, 1, led)
        _, Rc, C = e
        self.check(self.rechts() == digits(Rc), "aufgedeckter Computerwurf rechts")
        self.check(self.links() == (0, 0), "links 00 beim Aufdecken des Computers")
        liar = Rc < C
        return self.finish(1 if liar else 0, 2 if C == MAEX else 1, led)

    def finish(self, loser, amount, led):
        self.check(led == (4 if loser == 0 else 8), "LED zeigt den Verlierer")
        self.lives[loser] = max(0, self.lives[loser] - amount)
        self.check_lives()
        self.stats["runden"] += 1
        if amount == 2:
            self.stats["maexchen_doppelt"] += 1
        self.P = self.Q = None
        if self.lives[loser] == 0:
            winner = 1 - loser
            self.tally[winner] = (self.tally[winner] + 1) & 15
            self.results.append((self.level, winner == 0))
            self.games_left -= 1
            self.expect = ("level",)
        elif loser == 0:
            self.expect = ("pturn",)
        else:
            self.expect = ("cturn_open",)
            # Computer beginnt: naechster KIN ist seine Ansage (LED 2) ohne Entscheidung
        k = self.press(self.rng.randrange(16))
        return k

    def run(self, max_steps=50_000_000):
        cpu = self.cpu
        while cpu.steps < max_steps:
            try:
                if not cpu.step():
                    raise Fail("HALT/Fehler " + str(cpu.error))
            except StopIteration:
                return
            if self.expect[0] == "cturn_open" and cpu.prog[cpu.pc] == 0xFFD:   # KIN rD
                self.cturn_open()
        raise Fail("zu viele Schritte")

    def cturn_open(self):
        """Computer eroeffnet: der naechste KIN zeigt seine wahre Ansage."""
        self.expect = ("copen",)
        k = self.key_copen()
        self.queue.insert(0, k)

    def key_copen(self):
        led = self.cpu.dout
        self.check(led == 2, "Computer eroeffnet: LED 2")
        rolls = self.take_rnd("ROLL")
        self.check(len(rolls) == 3, "drei RND beim Eroeffnen")
        a, b = model_dice(rolls[2])
        self.dice[rank_of(a, b)] += 1
        Rc = rank_of(a, b)
        self.check(self.rechts() == digits(Rc), "Eroeffnung ist wahr, rechts")
        self.check(self.links() == (0, 0), "links 00 bei Eroeffnung des Computers")
        self.check_lives()
        self.P, self.Q = Rc, None
        self.stats["comp_eroeffnet"] += 1
        # Antwort des Spielers wie sonst; der Tastendruck selbst kommt aus der Queue
        doubt = self.strategy.doubt(Rc, None, self.rng)
        if Rc == MAEX and not doubt:
            self.expect = ("result", ("concede",))
            return 0xA
        if doubt:
            self.expect = ("result", ("pdoubt", Rc, Rc))
            return 0xB
        self.expect = ("pturn",)
        return 0xA


# ---- Spielerstrategien (Rangmodell) -------------------------------------------------
class Human:
    def __init__(self, T, spread, jmax, U, lie_prob=0.0):
        self.T, self.spread, self.jmax, self.U, self.lie_prob = T, spread, jmax, U, lie_prob

    def doubt(self, A, P, rng):
        if A == MAEX:
            return rng.random() < 0.9     # meist zweifeln, manchmal glauben (1 Leben)
        return A >= self.T + rng.randint(-self.spread, self.spread)

    def announce(self, R, P, rng):
        lo = -1 if P is None else P
        if R > lo and R >= self.U and rng.random() >= self.lie_prob:
            return R
        base = max(lo + 1, self.U) if R < self.U else lo + 1
        return min(base + rng.randint(0, self.jmax - 1), MAEX)


def pruefen(mic, games=60, seed=1):
    """Ablauf mit eingestreuten Fehleingaben, alle Level, gegen das Modell."""
    g = Game(mic, Human(12, 2, 3, 3, lie_prob=0.15), seed, level_seq=[1, 5, 9, 3, 7, 2, 8, 4, 6],
             games=games, noise=True)
    g.run()
    return g


def staerke(mic, level, games, seed, human):
    g = Game(mic, human, seed, level_seq=[level], games=games, noise=False)
    g.run()
    return sum(1 for lv, pw in g.results if not pw) / len(g.results), g


def zeit(mic, games=300, seed=11):
    """Wahrheit und Luege: Befehlszahl und Flags von CTURN bis zum naechsten KIN.

    Gruppiert nach (Ansage P, Luegenweite QK, Entscheidungsweg); in jeder Gruppe muessen
    Wahrheit und Luege gleich viele Befehle brauchen. Ausserdem: an welchen Stellen
    zeigen die Flags (C, Z) systematisch, ob der Computer luegt?"""
    g = Game(mic, Human(12, 2, 3, 3, lie_prob=0.15), seed, level_seq=[1, 5, 9], games=games, noise=False)
    cpu, lab = g.cpu, g.lab
    runs = []                    # (gruppe, wahr, befehle, flagfolge, dunkelzeit)
    cur = {"on": False}
    orig_step = cpu.step

    def step():
        if cpu.pc == lab["CTURN"] and g.expect[0] == "after_pann":
            cur.update(on=True, n=0, flags=[], P=(cpu.R[2], cpu.R[1]))
        r = orig_step()
        if cur["on"]:
            cur["n"] += 1
            cur["flags"].append((cpu.C, cpu.Z))
            if cpu.pc == lab["LP"] and "qk" not in cur:
                cur["qk"] = 0                                # Luegenweite spielt keine Rolle mehr
            if cpu.pc == lab["TR"]:
                cur["wahr"] = True                           # v06: Zweig TR = eigener Wurf reicht
            cur.setdefault("wahr", False)
            if cpu.prog[cpu.pc] == 0xFFD:                    # KIN erreicht
                runs.append((cur["P"] + (cur["qk"],), cur["wahr"], cur["n"], cur["flags"]))
                cur.clear()
                cur["on"] = False
        return r
    cpu.step = step
    g.run()
    groups = {}
    for key, wahr, n, fl in runs:
        groups.setdefault(key, {True: set(), False: set()})[wahr].add(n)
    gemischt = [k for k, v in groups.items() if v[True] and v[False]]
    schlecht = [k for k in gemischt if groups[k][True] != groups[k][False]]
    einzel = [k for k, v in groups.items() if len(v[True] | v[False]) > 1]
    # Flags: Anteil C = 1 und Z = 1 je Befehlsnummer, getrennt nach Wahrheit/Luege
    verrat = []
    for key in gemischt:
        fl = [(w, f) for k, w, n, f in runs if k == key]
        n = len(fl[0][1])
        for pos in range(n):
            for b in (0, 1):
                tw = [f[pos][b] for w, f in fl if w]
                tl = [f[pos][b] for w, f in fl if not w]
                if len(tw) >= 3 and len(tl) >= 3 and abs(sum(tw) / len(tw) - sum(tl) / len(tl)) > 0.9:
                    verrat.append((key, pos, "CZ"[b]))
    return runs, groups, gemischt, schlecht, einzel, verrat


if __name__ == "__main__":
    mic = os.path.join(HERE, "maexchen-06.mic")
    g = pruefen(mic, games=90, seed=7)
    print("Ablauftest:", dict(g.stats), "Schritte", g.cpu.steps)
    print("Spielstand", g.tally)
    tot = sum(g.dice.values())
    ideal = [2 / 36] * 14 + [1 / 36] * 6 + [2 / 36]
    print("Wuerfe", tot, "max. Abweichung je Wert (Stichprobe):",
          max(abs(g.dice[r] / tot - ideal[r]) / ideal[r] for r in range(21)))
    print("Ablauftest bestanden")
    full = Counter(rank_of(*model_dice(c)) for c in range(4096))
    dev = max(abs(full[r] / 4096 - ideal[r]) / ideal[r] for r in range(21))
    print("Wuerfel ueber alle 4096 Zaehlerstaende: max. rel. Abweichung %.3f" % dev)
    assert dev < 0.06
    runs, groups, gemischt, schlecht, einzel, verrat = zeit(mic)
    print("Zeittest:", len(runs), "Computeransagen,", sum(1 for r in runs if not r[1]), "Luegen,",
          len(gemischt), "Gruppen (Ansage) mit Wahrheit und Luege")
    print("  Gruppen mit unterschiedlicher Befehlszahl Wahrheit/Luege:", len(schlecht))
    print("  Gruppen mit mehr als einer Befehlszahl:", len(einzel))
    pos = sorted(set((p, b) for k, p, b in verrat))
    print("  Flag-Stellen, die die Wahrheit verraten (Befehlsnummer, Flag):", pos)
    assert not schlecht and not einzel
    ns = sorted(set(n for k, w, n, f in runs))
    print("  Befehle von CTURN bis KIN: %d-%d (%.2f-%.2f s bei 9,3 ms)" % (ns[0], ns[-1], ns[0] * .0093, ns[-1] * .0093))
    print("Zeittest bestanden")
