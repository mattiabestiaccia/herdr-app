---
type: prototype
title: Herdr trasparente per macOS
status: awaiting-desktop-test
updated: 2026-11-10
description: Build personale compilata e firmata; prova della composizione sul desktop e accettazione ancora aperte.
---

# Herdr trasparente

È disponibile una build dimostrativa Apple Silicon compilata offline con Rust
1.95.0 e Zig 0.16.0. La firma ad hoc del bundle supera `codesign --verify
--deep --strict`. La trasparenza e il blur non sono ancora stati osservati sul
desktop: l'avvio dalla sessione sandbox si ferma sui servizi grafici/core macOS.

## Aprire la demo

Dal Terminale del Mac, oppure con Finder sul bundle:

```sh
open "$HOME/personal/tools/Herdr Transparency.app"
```

Il collegamento punta al bundle in `dist/Herdr Transparency.app` di questo
worktree. Nome e bundle ID (`personal.herdr.transparency.prototype`) sono
separati da Herdr quotidiano. Il launcher richiede questo checkout e il Python
con cui è stato creato: conservare il worktree al suo posto.

La configurazione privata è in
`~/personal/tools/herdr-transparency-state/home`, con socket sotto il limite
macOS di 104 byte. Il core usa una sessione `test-glass-<hash>` e uno stato
separato in `/tmp/htr-<uid>-<hash>/state`. I riferimenti HC/Herdr ereditati vengono
rimossi dal launcher. L'esperimento usa il binario core già installato senza
installarlo o aggiornarlo; l'app ufficiale e la sua configurazione restano separate.

Il layout iniziale è **Herdr trasparente**, modalità nitida all'85%.
Aprire un terminale nella demo e tenere una finestra riconoscibile dietro.
Per confrontare le modalità, senza riavviare l'app:

```sh
python3 ~/personal/tools/herdr-transparency.py set transparent 0.85
python3 ~/personal/tools/herdr-transparency.py set blurred 0.85
python3 ~/personal/tools/herdr-transparency.py set transparent 0.65
python3 ~/personal/tools/herdr-transparency.py set blurred 0.65
python3 ~/personal/tools/herdr-transparency.py set transparent 1.00
python3 ~/personal/tools/herdr-transparency.py set opaque 1.00
```

I valori vengono scritti atomicamente nel JSON del solo layout personale.
Il watcher del layout deve applicarli dal vivo; verificarlo nell'app.
Provare testo, cursore, selezioni, scrolling, split, TUI, menu, dialoghi,
resize, fullscreen, temi chiari/scuri e cambio layout. Chiudere e riaprire la
demo per controllare la persistenza. Occorre osservare lo schermo macOS:
la cattura interna dell'app non prova la composizione con il desktop.

## Schermo intero

Lo schermo intero nativo di macOS sposta la finestra in uno Space dedicato,
dove dietro non c'è la scrivania. Con modalità `transparent` o `blurred`
la patch `HERDR:` di `toggleFullScreen:` in `vendor/gpui-pre-macos` usa invece
uno schermo intero sullo Space corrente: finestra senza bordi a tutto
schermo, barra dei menu e Dock nascosti. Vale per il pulsante verde,
`ctrl-cmd-f` e il comando `window.fullscreen`; per uscire si usa
`ctrl-cmd-f`, perché i pulsanti della finestra spariscono. In modalità
opaca resta lo schermo intero nativo.

Al posto della scrivania si può mostrare un'immagine, solo a schermo intero:

```sh
python3 ~/personal/tools/herdr-transparency.py image ~/Pictures/sfondo.jpg
python3 ~/personal/tools/herdr-transparency.py image desktop
```

La chiave radice è `fullscreen_image` (assoluta, `~/` o relativa alla home
dell'app). L'immagine copre l'area (`cover`) sotto la tinta del workspace;
il blur di macOS non la sfoca, perché sta dentro la finestra.

## Implementazione e limiti

Sul nodo radice del layout:

- `background_mode`: `opaque`, `transparent`, `blurred`; assente significa opaco.
- `workspace_opacity`: numero finito 0..1; assente significa 1.
- In modalità opaca l'opacità effettiva del workspace è 1.
- Solo macOS attiva la composizione nativa; sulle altre piattaforme resta opaca.

Il layout personale copia `main`, rimuovendo il canvas coprente e i fondi dei
frame dei terminali. Sidebar, tab, stato e pannello laterale restano coprenti.
Gli header dei pane, menu e dialoghi mantengono i rispettivi sfondi esistenti.

In modalità desktop la radice disegna una sola tinta e i due riempimenti del
fondo predefinito dei terminali vengono omessi. Testo, cursore, selezioni,
ricerca e sfondi espliciti delle celle seguono il percorso esistente.
`terminal_opacity` mantiene il comportamento precedente in modalità opaca;
in modalità desktop non moltiplica `workspace_opacity`.

La tinta comune usa `background` del tema. OSC 11 del terminale non cambia
questa tinta, mentre le celle con sfondo esplicito restano disegnate.
Il parsing rifiuta modalità sconosciute e opacità fuori intervallo; il watcher
upstream mantiene il layout valido già mostrato e segnala `layout.error`.
Questo recupero dal vivo e la persistenza vanno ancora provati nell'app.
Un JSON invalido all'avvio segue il fallback upstream.

Il pannello con slider e selettore è la seconda fase, subordinata alla prova
di Mattia. Le misure CPU/rendering rispetto alla baseline non sono state eseguite.
La build dimostrativa usa il profilo dev e dipendenze con opt-level 0, come
nei controlli CI: non è una build per misurare le prestazioni finali.

## Sorgenti e riproducibilità

Checkout completo: `~/personal/third-party/herdr-transparency-full`.
Worktree: `.worktrees/transparency`, branch `pilot/desktop-transparency`.
Base upstream verificata: `816d2057d83f0cbd3705926c0231fb12963ae0fb`.
Ghostty: `291fd050b9e9c293c8adb6a140742649b7e42d3a`.
La patch iniziale era stata sviluppata sulla copia documentale di quel commit;
qui `git apply --check` è passato sul clone completo prima dell'applicazione.
Nessuna PR upstream è stata aperta: questa è una variante personale.

In un normale Terminale con sorgenti e dipendenze già scaricati:

```sh
ZIG="$HOME/personal/tools/zig-aarch64-macos-0.16.0/zig" cargo +1.95.0 build --offline --locked
python3 personal/transparency/prototype.py bundle
```

Per la build eseguita nella sandbox, `target` e la cache di compilazione Zig
sono stati collocati in `/private/tmp/herdr-transparency-build-j9k57v_o`.
Un wrapper `ZIG` ha selezionato tramite `--build-file` lo stesso commit Ghostty
nel checkout completo, per riusare i pacchetti già estratti dall'utente.
La configurazione temporanea effettiva è conservata in `dist/evidence/zig-cached-source`.
Non sono state rimosse le restrizioni sui file protetti.

Comando della build riuscita nella sessione:

```sh
CARGO_TARGET_DIR=/private/tmp/herdr-transparency-build-j9k57v_o \
ZIG=/private/tmp/herdr-transparency-build-j9k57v_o/zig-cached-source \
cargo +1.95.0 build --offline --locked -j 4 --config 'profile.dev.package."*".opt-level=0'
```

## Evidenza del 10 novembre 2026

| Verifica | Esito |
| --- | --- |
| Build nativa macOS dell'app | passata |
| Bundle separato, firma ad hoc, verifica deep/strict | passati |
| Test unitari Rust dell'app | 276 passati, 41 falliti, 2 ignorati |
| Analisi dei 41 fallimenti | 38 PermissionDenied/Operation not permitted; 3 timeout dei watcher filesystem |
| Integrazione commands/notices/skill/colrv1 | 4 passati; colrv1 non contiene test su macOS |
| Launcher: socket corto, isolamento, persistenza preset e valori invalidi | 3 passati |
| Test Bun della ricetta upstream | 33 passati, 458 asserzioni |
| Test Bun della documentazione | 4 passati, 29 asserzioni |
| Documentazione generata ed esempi CLI contro il binario compilato | passati |
| Trasparenza/blur reali, UI, riavvio e prestazioni | ancora da verificare |

I log Rust sono in `dist/evidence/rust-tests.log` e
`dist/evidence/integration-tests.log`. I 41 fallimenti sono stati classificati
in base agli errori osservati nella sandbox; non è stato eseguito un confronto
con la stessa suite su baseline fuori sandbox. La suite non è dichiarata verde.
Non è stato eseguito il gate no-mistakes.

La prima esecuzione del launcher ha scoperto un socket troppo lungo; il test
è stato aggiunto e osservato fallire (128 byte), poi il percorso è stato accorciato
ed è passato. L'avvio grafico dalla sandbox è abortito con errori dei servizi
macOS e del core; il prossimo passo è l'apertura della demo dal desktop.

## Ripristino e prossima fase

Per tornare opaco usare `set opaque 1.00` oppure selezionare `main` nella demo.
Chiudere la demo e i suoi terminali al termine della prova. La configurazione
app persiste sotto `personal/tools`; i terminali della demo non promettono
recupero dopo un riavvio del Mac, perché il core isolato usa stato in `/tmp`.

Per aggiornare la variante usare un nuovo worktree e verificare la patch,
le API GPUI e i test sulla nuova base prima di ricreare il bundle.
La seconda fase e l'eventuale sostituzione di Herdr quotidiano restano aperte.
