# proseo.se

Källkoden till [www.proseo.se](https://www.proseo.se), webbplatsen för Proseo AB.

Sajten är en statisk sida. Den har inga skript och inga kakor, och den hämtar inget från andra värdar.

## Mappar

| Mapp | Innehåll |
| --- | --- |
| `docs/` | Det som publiceras: startsidan, felsidan och filerna de behöver |
| `tests/` | Kontroller som ska gå igenom före varje ändring |

## Kontrollera

```
py -I -m unittest discover -s tests -v
```

Testerna kontrollerar bland annat att sidans text är den godkända, att inga skript eller externa resurser finns, att ingen mejladress står som text och att alla länkade filer finns.

## Publicering

Sajten publiceras med GitHub Pages ur mappen `docs/` på grenen `main`. Ändringar görs på en egen gren och slås ihop med en pull request.

## Typsnitt

Libre Caslon Display och Libre Franklin, båda med licensen SIL Open Font License 1.1. Filerna och licenstexterna ligger i `docs/assets/fonts/`. De är hämtade oförändrade ur paketen `@fontsource/libre-caslon-display` och `@fontsource/libre-franklin`, version 5.3.0.

## Rättigheter

Text, bilder och utformning tillhör Proseo AB. Typsnitten har egna licenser enligt ovan.
