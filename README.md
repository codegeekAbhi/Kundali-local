# Kundli Local

A command-line Vedic birth chart calculator with optional interpretations. It calculates D1 and D9 placements, Moon nakshatra and pada, and Vimshottari periods through Pratyantardasha. The optional Lal Kitab view shows numbered D1 house occupancy for a traditional reading. Lal Kitab-specific dasha, varshphal and remedy calculations are outside the current feature set.

## Setup

Use Python 3.9 or newer with a compatible Swiss Ephemeris installation.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

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

## Privacy and calculation settings

Chart computation runs on your machine in every mode. Hosted mode sends derived chart placements, dasha dates and reading options to OpenAI. Derived charts can still be sensitive. The request omits your raw birth timestamp, coordinates and timezone. Ollama mode connects directly to the local loopback address. The tool does not save a profile. Your shell can record the command in its history.

Calculations use Swiss Ephemeris with the built-in Moshier ephemeris, Lahiri ayanamsha, whole-sign houses, mean nodes, and a 365.25-day Vimshottari year. Traditional interpretations cannot reliably predict future events.

## Upload to GitHub

Extract the ZIP and upload the contents of the `kundli-local` folder to a new repository. The archive contains source and setup files. It contains no personal birth details, API keys, or AstroTalk files.

Swiss Ephemeris is installed as a dependency and has [open-source and commercial licensing options](https://www.astro.com/swisseph/swephinfo_e.htm). Review its licensing before distributing a bundled binary or offering this tool as a public service. Choose a license for this repository before inviting reuse.
