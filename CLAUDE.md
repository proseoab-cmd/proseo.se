# proseo.se – instruktioner för Claude Code

Repot innehåller webbplatsen för Proseo AB. Det är publikt, så allt som checkas in kan läsas av vem som helst.

## Hårda regler

1. Inga personnamn i någon fil, i något filnamn eller i ändringshistoriken. Avsändaren i Git ska vara neutral och använda GitHubs noreply-adress.
2. Bolagets mejladress får bara finnas som bild med konturer (`docs/assets/epost.svg`). Den får aldrig stå som text, länk, bildbeskrivning eller kommentar, och inte heller uppdelad eller kodad.
3. Sajten har inga skript och inga kakor, och den hämtar inget från andra värdar. Typsnitten ligger i repot.
4. Texten på sajten är godkänd ord för ord av ägaren. Ändra, lägg till eller ta bort text bara efter ägarens ja. Testet `test_godkand_text` håller den godkända lydelsen.
5. Arbeta på en egen gren och öppna en pull request. Skriv aldrig direkt till `main`, som publiceras.
6. Kör testerna före varje pull request: `py -I -m unittest discover -s tests -v`.
7. Underlag med personuppgifter, till exempel CV och research, hör inte hemma i repot.

## Utformning

Riktningen heter Register och är vald av ägaren.

- Rubriken sätts i Libre Caslon Display, all annan text i Libre Franklin.
- En röd linje (`#B5412F`) skiljer en marginal från sidan. På breda skärmar står ordmärket i marginalen.
- Tunna linjer delar sidan i rubrik, text och bolagsuppgifter. Texten och bolagsuppgifterna delar samma kolumnnät.
- Brytpunkterna är 700, 960 och 1100 px.
- Botten är ljus. Inga foton, inga övertoningar och inga rörelser.

## Arbetssätt

- Ett delmoment i taget. Avsluta med en kort rapport: gjort, testat, overifierat och beslut som krävs.
- Skriv steglistor med GHD (GitHub Desktop) och GHW (GitHub på webben).
- `git` finns inte i PATH på ägarens dator. Använd GitHub Desktops git. Python heter `py`.
