# Kundali Local — Offline Vedic Astrology, Numerology & AI Palmistry

A command-line Vedic birth chart calculator with optional interpretations. It calculates D1 and D9 placements, Moon nakshatra and pada, and Vimshottari periods through Pratyantardasha. The optional Lal Kitab view shows numbered D1 house occupancy for a traditional reading. Lal Kitab-specific dasha, varshphal and remedy calculations are outside the current feature set.

**Generate a kundli without an account or API key.** Kundali Local is a Python CLI for calculating a Vedic birth chart, exploring planetary timing, and reading palm lines from a photo with an optional vision model.

| What you can explore | What the tool calculates or shows |
| --- | --- |
| **Vedic astrology (Jyotish)** | D1 birth chart, D9 Navamsha, Moon nakshatra and pada, Vimshottari dasha timeline, and Jupiter, Saturn, Rahu, and Ketu transits. |
| **Lal Kitab** | Numbered house placements for a traditional reading. |
| **Date-based numerology** | Life Path, Birth Day, and Personal Year numbers. |
| **Palmistry** | Heart, head, life, and fate line readings using manual input or photo suggestions you confirm. |


## Setup

Use Python 3.9 or newer with a compatible Swiss Ephemeris installation.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Desktop GUI

After setup, launch the app from the repository root:

```sh
python gui.py
```

- **Vedic chart:** Enter birth date and local time, the IANA time zone, and coordinates. Choose a reading date and focus, then select **Calculate chart**. The default includes current transits and the next 31 days of dasha changes. This is a rolling timing report.
- **Numerology:** Enter a birth date and the calendar year you want to explore.
- **Palmistry:** Select line shapes manually, or choose an image with a vision model enabled. Review the suggestions before selecting **Read selected lines**.

The app opens in offline mode and needs no API key. OpenAI actions ask for confirmation before sending chart data, a photo, or line descriptions. The GUI has no profile storage and does not save the results. For local photo analysis, use a downloaded Ollama vision model with cloud features disabled.

The GUI uses Tkinter. If `python -m tkinter` fails, use a Python installation with Tk support (on many Linux distributions the package is called `python3-tk`).

## Choose a reading mode

All examples use sample inputs. Supply local birth time, an IANA time zone, and latitude and longitude in decimal degrees. East is positive. Use `--as-of YYYY-MM-DD` to look up timing on a particular date at midnight UTC.

**Offline, no key.** Generates a basic interpretation locally. Omit `--reading` for chart output alone.

```sh
python kundli.py 2000-01-01T12:00 Asia/Kolkata 28.6139 77.2090 --reading offline --lal-kitab
```

**Local AI, no key.** Run [Ollama](https://docs.ollama.com/api/openai-compatibility) locally on its default port. Install a local model such as `qwen3:8b` with `ollama pull qwen3:8b`. If privacy is your priority, use downloaded models and disable Ollama cloud features.

```sh
python kundli.py 2000-01-01T12:00 Asia/Kolkata 28.6139 77.2090 --reading ollama --model qwen3:8b --topic career
```

**Hosted AI, API key.** Set `OPENAI_API_KEY` in your environment. Choose a [Chat Completions model](https://developers.openai.com/api/reference/resources/chat) available to your API account. Provider charges and data handling apply.

```sh
python kundli.py 2000-01-01T12:00 Asia/Kolkata 28.6139 77.2090 --reading openai --model MODEL_ID --topic career
```

AI explains the calculated chart. Optional focus areas are overview, career and relationships. If the provider is unavailable, the CLI prints the chart and an offline reading.

## Transits, upcoming dasha changes, and numerology

```sh
python kundli.py 2000-01-01T12:00 Asia/Kolkata 28.6139 77.2090 \
  --as-of 2026-11-26 --transits --timeline 180
python numerology.py 2000-01-01 --year 2026
```

- `--transits` shows Jupiter, Saturn, mean Rahu and mean Ketu relative to the natal ascendant and Moon. It searches the next 90 days for the first sign crossing per body using six-hour samples. Listed dates are approximate UTC dates.
- `--timeline DAYS` prints each upcoming change to the three-level Vimshottari sequence. The window excludes its ending instant. Times are UTC and depend on the recorded birth time and the configured dasha-year convention.
- `numerology.py` prints Life Path, Birth Day, and Personal Year. Life Path reduces birth year + month + day. Birth Day reduces the day of the month. Personal Year replaces the birth year with the requested calendar year. This implementation reduces to one digit, including 11, 22, and 33. It needs only Python and runs offline.
- With `--transits` or `--timeline` enabled, optional AI modes can interpret those results alongside the natal chart.

## Palmistry

Enter the features you observe on one hand. Run `python palmistry.py --help` for the location of each line and the supported shapes. Omit any feature you are unsure about.

```sh
python palmistry.py --hand right --heart curved --head straight --life wide-arc --fate faint
python palmistry.py --hand right --heart curved --reading ollama --model qwen3:8b
python palmistry.py --hand right --heart curved --reading openai --model MODEL_ID
```

The default reading runs offline with Python alone. Ollama can expand it using a downloaded local model without a key. OpenAI mode sends the chosen hand and line descriptions to OpenAI and requires `OPENAI_API_KEY`. The command needs no birth details. Palmistry is presented as folklore for reflection.

### Palm photos

Take a straight-on photo of one open palm with even lighting. Keep the wrist and fingers in frame so the model can orient itself. Use a JPEG or PNG up to 10 MB and select a vision-capable model. The terminal asks you to confirm, edit, or skip suggested labels before it generates the reading.

```sh
python palmistry.py --hand right --photo palm.jpg --reading ollama --model VISION_MODEL
python palmistry.py --hand right --photo palm.jpg --reading openai --model VISION_MODEL --allow-photo-upload
```

With a downloaded Ollama vision model and cloud features disabled, photo analysis can run locally without a key. OpenAI photo mode uploads the original image bytes, which may contain metadata. It requires explicit permission via `--allow-photo-upload`. The second request, for interpretation, includes only confirmed line descriptions and the selected hand. The tool does not save the image or reading. For fully offline use without a vision model, enter the line shapes manually.

The model may miss or misclassify creases. Confirm the labels against your photo. A confirmed crease is an observation. Its traditional interpretation cannot reliably predict future events.

## Tests

```sh
python -m unittest discover -v
```

## Privacy and calculation settings

Chart computation runs on your machine in every mode. Hosted mode sends derived chart placements, dasha dates, requested transit results, and reading options to OpenAI. Derived charts can still be sensitive. The request omits your raw birth timestamp, coordinates and timezone. Ollama mode connects directly to the local loopback address. The tool does not save a profile. Your shell can record the command in its history.

Calculations use Swiss Ephemeris with the built-in Moshier ephemeris, Lahiri ayanamsha, whole-sign houses, mean nodes, and a 365.25-day Vimshottari year. Traditional interpretations cannot reliably predict future events.

## Upload to GitHub

Extract the ZIP and upload the contents of the `kundli-local` folder to a new repository. The archive contains source and setup files. It contains no personal birth details, API keys, or AstroTalk files.

Swiss Ephemeris is installed as a dependency and has [open-source and commercial licensing options](https://www.astro.com/swisseph/swephinfo_e.htm). Review its licensing before distributing a bundled binary or offering this tool as a public service. Choose a license for this repository before inviting reuse.


[\#VedicAstrology](https://github.com/topics/vedic-astrology) · [\#Kundli](https://github.com/topics/kundli) · [\#astrotalk like](https://github.com/topics/astrotalklike)  · [\#Numerology](https://github.com/topics/numerology) · [\#Palmistry](https://github.com/topics/palmistry) · [\#Ollama](https://github.com/topics/ollama) · 
