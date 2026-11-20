# Firefly Observatory — Python Edition

A standard-library-only Python adaptation of the optimized Go Firefly Observatory. GPLv3 project conventions. Single-file Linux terminal simulation.

## Requirements

Python 3.9+ on Linux, a UTF-8 terminal with ANSI truecolor support for the best display. No pip dependencies.

## Quick start

```bash
python3 firefly-observatory.py -mode flock -palette aurora
python3 firefly-observatory.py -mode orbit -palette moon -agents 120 -fps 12 -eco
python3 firefly-observatory.py -mode rain -palette ocean -ascii
python3 firefly-observatory.py -mode breathe -telemetry
```

Use Ctrl+C to stop. The program restores terminal cursor visibility on normal termination.

## Commands

`run` animates indefinitely by default; `render` defaults to one frame; `inspect` suppresses animation; `modes`, `palettes`, and `version` print information.

## Parameters

Go-style single-dash flags and Python-style double-dash flags are both accepted: `-agents 120` and `--agents 120`.

| Option | Default | Purpose |
|---|---:|---|
| `-agents` | 420 | Agent population |
| `-fps` | 24 | Simulation and display frequency |
| `-width`, `-height` | terminal | Canvas dimensions |
| `-seed` | random | Random seed |
| `-palette` | aurora | Color palette |
| `-mode` | flock | Simulation behavior |
| `-coupling` | 1.4 | Phase synchronization strength |
| `-radius` | 6.5 | Toroidal neighborhood radius |
| `-speed` | 1 | Simulation timestep multiplier |
| `-noise` | 0.22 | Gaussian movement noise |
| `-trails` | 0.83 | Previous-frame luminance retention |
| `-wind` | 0.08 | Horizontal force |
| `-gravity` | 0.04 | Center attraction |
| `-bloom` | 0.85 | Glow radius multiplier |
| `-density` | 1 | Glow intensity multiplier |
| `-telemetry` | off | Sample Linux CPU, memory, and disk activity |
| `-eco` | off | Limit to 12 FPS and 240 initial agents |
| `-frames` | 0 | Stop after this many total frames |
| `-duration` | 0 | Wall-clock time limit in seconds |
| `-ascii` | off | Monochrome ASCII brightness renderer |
| `-headless` | off | Run without terminal animation |
| `-quiet` | off | Suppress animation and print final metrics |
| `-record` | none | Append JSONL metrics |
| `-snapshot` | none | Save JSON world state |
| `-restore` | none | Resume from JSON world state |
| `-output` | none | Export PPM image, text image, or JSON metrics |

## Export examples

```bash
python3 firefly-observatory.py -agents 120 -fps 12 -frames 120 -headless -record timeline.jsonl -snapshot state.json
python3 firefly-observatory.py -agents 120 -fps 12 -frames 240 -headless -restore state.json -snapshot state2.json
python3 firefly-observatory.py render -width 80 -height 24 -output firefly.ppm
```

## Model fidelity

The Python adaptation follows the Go implementation's agent state, spatial hash neighborhood search, toroidal distance, Kuramoto-like phase coupling, mode-specific forces, velocity damping, periodic wrapping, pulse energy, Gaussian light deposition, and field decay. The Python implementation uses the Mersenne Twister RNG and therefore does not produce bit-identical results to Go for the same seed. Restoring a snapshot preserves agents and time but not the original RNG stream or rendered light buffer. Python output and performance will differ from Go.

The Python edition currently supports JSONL recording, PPM/text/JSON output, and snapshot restore. The optimized Go edition additionally exposes profiling and other export behavior not replicated here. The Python edition accepts a `-border` option for CLI familiarity, but does not draw a border. It does not implement a complete Go binary-compatible snapshot format. Use Python-created snapshots for Python restore.

## Performance

Python has higher per-agent and per-pixel overhead than Go. Begin with:

```bash
python3 firefly-observatory.py -agents 100 -fps 12 -width 70 -height 22 -eco
```

The loop uses monotonic deadlines and sleeps between frames rather than spinning. Rendering is omitted in headless mode unless an output file is requested. At high populations, neighborhood iteration and glow deposition are CPU-intensive. The `-eco` switch limits population and FPS but does not guarantee a particular temperature or CPU load.

## Validation

```bash
python3 -m py_compile firefly-observatory.py
python3 firefly-observatory.py -agents 20 -width 30 -height 10 -frames 3 -headless -snapshot test.json
python3 firefly-observatory.py -agents 20 -width 30 -height 10 -frames 4 -headless -restore test.json
```

## License

GNU General Public License version 3.0. Include the GPLv3 license text when publishing the repository.
