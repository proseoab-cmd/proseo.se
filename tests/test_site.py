"""Kontroller för proseo.se.

Kör från repots rot:

    py -I -m unittest discover -s tests -v

Testerna vaktar reglerna i CLAUDE.md: godkänd text, inga skript, inga externa
resurser, inga personnamn och ingen mejladress som text.
"""

import glob
import hashlib
import os
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
DOCS = ROT / "docs"
HOPPA_OVER = {".git", "__pycache__", ".claude", "underlag"}
BINARA = {".woff2", ".png", ".ico"}

# Kontrollsummor (SHA-256 med prefixet nedan) av ord som inte får förekomma
# någonstans i repot. Orden själva står inte här.
PREFIX = "proseo.se|"
FORBJUDNA_ORD = {
    "55387f0171febf7f864f56e6674ce8324d8189ddf399ea06994d633ec7fe446f",
    "f243512dd9256230c18ad69e23e961bf218e69cbf8433e56d20f79f8e77a80f3",
    "122390214e78d098eacddfd1edcda3397cdbe5fea9ae72bd0ece8796fbe89611",
}
FORBJUDEN_ADRESS = "ad8b4a626b63e2776676774a156bfedee080efe6418bc613465fe910e686f36e"

ADRESSMONSTER = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
ORDMONSTER = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]+")
KODADE_TECKEN = ("&#64;", "&#x40;", "&commat;", "%40", "(at)", "[at]", "snabel-a", "mailto:")

VANTADE_FILER = {
    ".nojekyll",
    "404.html",
    "CNAME",
    "apple-touch-icon.png",
    "favicon.ico",
    "index.html",
    "robots.txt",
    "assets/epost.svg",
    "assets/ikon.svg",
    "assets/site.css",
    "assets/fonts/OFL-libre-caslon-display.txt",
    "assets/fonts/OFL-libre-franklin.txt",
    "assets/fonts/libre-caslon-display-latin-400-normal.woff2",
    "assets/fonts/libre-franklin-latin-400-normal.woff2",
    "assets/fonts/libre-franklin-latin-600-normal.woff2",
}

TYPSNITT = {
    "libre-caslon-display-latin-400-normal.woff2": "84267e937417f10dff37df818c5ef7f1e9f2e6a703e03c2dd286d3320af53269",
    "libre-franklin-latin-400-normal.woff2": "50a24a85106ad722ab9d1353977c1f7b3b3d18465a807c0d6f1551b57a705f41",
    "libre-franklin-latin-600-normal.woff2": "aaa877781157fd03a54d6b0f27283e5b153a6d1b44a20c2d80c695f5e07d242b",
}

CSP = "default-src 'none'; style-src 'self'; img-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'"
KANONISK = "https://www.proseo.se/"

SIDFOT = (
    "Proseo AB · sedan 2013",
    "Säte Kungälv",
    "Org.nr 556920-0305",
    "Momsreg.nr SE556920030501",
    "Ängsgatan 20 b",
    "442 33 Kungälv",
    "Sidan använder inga kakor. Den ligger hos GitHub, som loggar besökarens IP-adress av säkerhetsskäl.",
)

STARTSIDA = {
    "titel": "Proseo – lokal affärsbevakning i Kungälv",
    "beskrivning": (
        "Proseo bedriver lokal affärsbevakning i Kungälv med omnejd. "
        "Från december 2026 ges bevakningen ut som ett veckobrev till lokala företag."
    ),
    "bildtext": "E-postadress till Proseo, visad som bild",
    "text": (
        "Proseo",
        "Proseo bedriver lokal affärsbevakning i Kungälv med omnejd.",
        "Bevakningen gäller bygglov, detaljplaner, kommunala beslut, markaffärer och nya etableringar. "
        "Från december 2026 ges den ut som ett veckobrev till lokala företag.",
        "Utöver bevakningen tar Proseo för närvarande inga uppdrag.",
    )
    + SIDFOT,
}

FELSIDA = {
    "titel": "Sidan finns inte – Proseo",
    "text": ("Proseo", "Sidan finns inte.", "Tillbaka till startsidan.") + SIDFOT,
}

FORBJUDNA_TAGGAR = {
    "script", "style", "iframe", "object", "embed", "form", "input", "button",
    "textarea", "select", "video", "audio", "base", "frame", "frameset", "applet",
}
ADRESSATTRIBUT = {"src", "href", "srcset", "poster", "data", "action", "formaction", "background"}


def summa(text):
    return hashlib.sha256((PREFIX + text).encode("utf-8")).hexdigest()


def alla_filer(rot=ROT):
    for dirpath, dirnames, filenames in os.walk(rot):
        dirnames[:] = [d for d in dirnames if d not in HOPPA_OVER]
        for namn in filenames:
            yield Path(dirpath) / namn


def textfiler(rot=ROT):
    for fil in alla_filer(rot):
        if fil.suffix.lower() not in BINARA:
            yield fil, fil.read_text(encoding="utf-8")


def relativ(fil, rot=ROT):
    return fil.relative_to(rot).as_posix()


class Sida(HTMLParser):
    """Samlar taggar, attribut och synlig text ur en HTML-fil."""

    def __init__(self, fil):
        super().__init__(convert_charrefs=True)
        self.fil = fil
        self.taggar = []
        self.sprak = None
        self.titel = ""
        self.i_titel = False
        self.i_body = False
        self.bitar = []
        self.feed(fil.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attribut = dict(attrs)
        self.taggar.append((tag, attribut))
        if tag == "html":
            self.sprak = attribut.get("lang")
        elif tag == "title":
            self.i_titel = True
        elif tag == "body":
            self.i_body = True
        elif tag == "br":
            self.bitar.append(" ")

    def handle_endtag(self, tag):
        if tag == "title":
            self.i_titel = False
        elif tag == "body":
            self.i_body = False

    def handle_data(self, data):
        if self.i_titel:
            self.titel += data
        elif self.i_body:
            self.bitar.append(data)

    @property
    def text(self):
        return " ".join("".join(self.bitar).split())

    def meta(self, namn):
        for tag, attribut in self.taggar:
            if tag == "meta" and attribut.get("name") == namn:
                return attribut.get("content")
        return None

    def adresser(self):
        for tag, attribut in self.taggar:
            for namn, varde in attribut.items():
                if namn in ADRESSATTRIBUT and varde is not None:
                    yield tag, attribut, namn, varde


def sidor():
    return [Sida(fil) for fil in sorted(DOCS.glob("*.html"))]


def hitta_git():
    kandidater = [os.environ.get("PROSEO_GIT"), shutil.which("git")]
    lokal = os.environ.get("LOCALAPPDATA")
    if lokal:
        monster = os.path.join(lokal, "GitHubDesktop", "app-*", "resources", "app", "git", "cmd", "git.exe")
        kandidater.extend(sorted(glob.glob(monster), reverse=True))
    for kandidat in kandidater:
        if kandidat and os.path.exists(kandidat):
            return kandidat
    return None


class GodkandText(unittest.TestCase):
    def test_startsidans_text_ar_den_godkanda(self):
        sida = Sida(DOCS / "index.html")
        self.assertEqual(sida.text, " ".join(STARTSIDA["text"]))

    def test_startsidans_titel_och_beskrivning(self):
        sida = Sida(DOCS / "index.html")
        self.assertEqual(sida.titel, STARTSIDA["titel"])
        self.assertEqual(sida.meta("description"), STARTSIDA["beskrivning"])

    def test_felsidans_text_ar_den_godkanda(self):
        sida = Sida(DOCS / "404.html")
        self.assertEqual(sida.text, " ".join(FELSIDA["text"]))
        self.assertEqual(sida.titel, FELSIDA["titel"])
        self.assertEqual(sida.meta("robots"), "noindex")

    def test_sprak_ar_svenska(self):
        for sida in sidor():
            self.assertEqual(sida.sprak, "sv", relativ(sida.fil))

    def test_mejlbilden_har_godkand_bildtext(self):
        sida = Sida(DOCS / "index.html")
        bilder = [attribut for tag, attribut in sida.taggar if tag == "img"]
        self.assertEqual(len(bilder), 1)
        self.assertEqual(bilder[0].get("src"), "assets/epost.svg")
        self.assertEqual(bilder[0].get("alt"), STARTSIDA["bildtext"])


class IngaSkriptOchIngaExternaResurser(unittest.TestCase):
    def test_inga_forbjudna_taggar_eller_attribut(self):
        for sida in sidor():
            for tag, attribut in sida.taggar:
                self.assertNotIn(tag, FORBJUDNA_TAGGAR, relativ(sida.fil))
                for namn in attribut:
                    self.assertFalse(namn.startswith("on"), f"{relativ(sida.fil)}: {tag} {namn}")
                    self.assertNotEqual(namn, "style", f"{relativ(sida.fil)}: {tag}")

    def test_sakerhetspolicyn_finns(self):
        for sida in sidor():
            policyer = [
                attribut.get("content")
                for tag, attribut in sida.taggar
                if tag == "meta" and attribut.get("http-equiv") == "Content-Security-Policy"
            ]
            self.assertEqual(policyer, [CSP], relativ(sida.fil))
            self.assertEqual(sida.meta("referrer"), "no-referrer", relativ(sida.fil))

    def test_inga_adresser_till_andra_vardar(self):
        for sida in sidor():
            for tag, attribut, namn, varde in sida.adresser():
                extern = "://" in varde or varde.startswith("//") or varde.lower().startswith(("data:", "javascript:"))
                if extern:
                    tillaten = tag == "link" and attribut.get("rel") == "canonical" and varde == KANONISK
                    self.assertTrue(tillaten, f"{relativ(sida.fil)}: {tag} {namn}={varde}")

    def test_stilmallen_hamtar_inget_utifran(self):
        for fil in DOCS.rglob("*.css"):
            css = fil.read_text(encoding="utf-8")
            self.assertNotIn("@import", css, relativ(fil))
            for adress in re.findall(r"url\(\s*[\"']?([^\"')]+)", css):
                self.assertFalse("://" in adress or adress.startswith(("//", "data:")), f"{relativ(fil)}: {adress}")

    def test_lankade_filer_finns(self):
        for sida in sidor():
            for tag, attribut, namn, varde in sida.adresser():
                if "://" in varde:
                    continue
                stig = varde.split("#")[0].split("?")[0]
                if stig in ("", "/", "./"):
                    mal = DOCS / "index.html"
                elif stig.startswith("/"):
                    mal = DOCS / stig.lstrip("/")
                else:
                    mal = sida.fil.parent / stig
                self.assertTrue(mal.is_file(), f"{relativ(sida.fil)}: {varde} saknas")
        for fil in DOCS.rglob("*.css"):
            css = fil.read_text(encoding="utf-8")
            for adress in re.findall(r"url\(\s*[\"']?([^\"')]+)", css):
                self.assertTrue((fil.parent / adress).is_file(), f"{relativ(fil)}: {adress} saknas")

    def test_bara_vantade_filer_publiceras(self):
        funna = {relativ(fil, DOCS) for fil in alla_filer(DOCS)}
        self.assertEqual(funna, VANTADE_FILER)

    def test_domanfilen_pekar_ut_sajtens_adress(self):
        doman = (DOCS / "CNAME").read_text(encoding="utf-8").strip()
        self.assertEqual(doman, "www.proseo.se")
        self.assertEqual(KANONISK, f"https://{doman}/")

    def test_sajten_ar_liten(self):
        storlek = sum(fil.stat().st_size for fil in alla_filer(DOCS))
        self.assertLess(storlek, 150_000, f"docs/ är {storlek} byte")


class IngaNamnOchIngenAdress(unittest.TestCase):
    def test_inga_personnamn_i_filer_eller_filnamn(self):
        for fil, text in textfiler():
            for ord_ in set(ORDMONSTER.findall(text.lower())):
                self.assertNotIn(summa(ord_), FORBJUDNA_ORD, relativ(fil))
        for fil in alla_filer():
            for ord_ in set(ORDMONSTER.findall(relativ(fil).lower())):
                self.assertNotIn(summa(ord_), FORBJUDNA_ORD, relativ(fil))

    def test_bolagets_adress_star_inte_som_text(self):
        for fil, text in textfiler():
            for adress in ADRESSMONSTER.findall(text):
                self.assertNotEqual(summa(adress.lower()), FORBJUDEN_ADRESS, relativ(fil))

    def test_inga_mejladresser_pa_sajten(self):
        for fil, text in textfiler(DOCS):
            if fil.parent.name == "fonts":
                continue
            self.assertEqual(ADRESSMONSTER.findall(text), [], relativ(fil))
            for kod in KODADE_TECKEN:
                self.assertNotIn(kod, text.lower(), f"{relativ(fil)}: {kod}")

    def test_mejlbilden_ar_bara_konturer(self):
        svg = (DOCS / "assets" / "epost.svg").read_text(encoding="utf-8")
        self.assertIn("<path", svg)
        for forbjudet in ("<text", "<tspan", "<title", "<desc", "aria-label", "@", "<a", "href"):
            self.assertNotIn(forbjudet, svg)

    def test_andringshistoriken_ar_neutral(self):
        git = hitta_git()
        if git is None or not (ROT / ".git").exists():
            self.skipTest("git eller .git saknas")
        svar = subprocess.run(
            [git, "-C", str(ROT), "log", "--all", "--format=%an%x09%ae%x09%cn%x09%ce"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if svar.returncode != 0 or not svar.stdout.strip():
            self.skipTest("inga incheckningar ännu")
        for rad in set(svar.stdout.strip().splitlines()):
            forfattare, forfattarpost, incheckare, incheckarpost = rad.split("\t")
            for ord_ in set(ORDMONSTER.findall((forfattare + " " + incheckare).lower())):
                self.assertNotIn(summa(ord_), FORBJUDNA_ORD, "namn i historiken")
            for post in (forfattarpost, incheckarpost):
                neutral = post.endswith("@users.noreply.github.com") or post == "noreply@github.com"
                self.assertTrue(neutral, "en avsändare i historiken använder inte GitHubs noreply-adress")


class Typsnitt(unittest.TestCase):
    def test_typsnittsfilerna_ar_oforandrade(self):
        for namn, vantad in TYPSNITT.items():
            data = (DOCS / "assets" / "fonts" / namn).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), vantad, namn)

    def test_licenstexterna_foljer_med(self):
        for namn in ("OFL-libre-caslon-display.txt", "OFL-libre-franklin.txt"):
            text = (DOCS / "assets" / "fonts" / namn).read_text(encoding="utf-8")
            self.assertIn("SIL Open Font License", text, namn)

    def test_stilmallen_anvander_bara_egna_typsnittsfiler(self):
        css = (DOCS / "assets" / "site.css").read_text(encoding="utf-8")
        filer = set(re.findall(r"fonts/([a-z0-9-]+\.woff2)", css))
        self.assertEqual(filer, set(TYPSNITT))


if __name__ == "__main__":
    unittest.main()
