# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`abba-python` is a thin Python wrapper that drives the **Java** application ABBA
(Aligning Big Brains and Atlases) over a JVM bridge. Almost no image-processing
logic lives in this repo — the heavy lifting is in Java jars pulled from Maven
(`maven.scijava.org`) at runtime. The Python layer has essentially one job: boot a
PyImageJ/ImageJ instance with the right classpath and expose ABBA's SciJava commands
as ergonomic Python methods (`Abba` class in `abba.py`). Two modules:
- `abba.py` — JVM startup and the `Abba` session (atlas, model, a few helpers);
- `commands.py` — `AbbaCommands`, the generated command methods `Abba` inherits.

An MCP server for LLM agents used to live here; it was dropped in favour of a standalone
server on the Java side, so there is no agent API in this package any more.

Historically this package also bridged [BrainGlobe](https://brainglobe.info) atlases
into ABBA by implementing ABBA's Java atlas interfaces *in Python* (JPype proxies).
As of `atlas:0.4.0` / `ImageToAtlasRegister:0.20.0`, BrainGlobe and DeepSlice are
handled **natively on the Java side** (via Appose, which manages its own Python
subprocess env), so that bridge and the `brainglobe-atlasapi` dependency were removed.

## Environment setup

No JDK or Maven install is needed — a plain venv works (conda is fine too):

```
uv venv --python 3.12
uv pip install -e .[test,dev]
```

This relies on `pyimagej>=1.8.0` (→ `scyjava>=1.12.4`, `jgo>=2.1`): scyjava downloads
a Zulu JRE through cjdk (default `fetch="always"`, so any system/conda JDK is
ignored) and jgo resolves the Maven jars in pure Python. Verified by starting ABBA
headless with no `mvn`/`java` on `PATH` and an empty `~/.m2`. pyimagej 1.7.x
still works without Maven (scyjava fetches one) but fails with
`JVMNotFoundException` unless a JDK is installed, because it probes the Java
version before scyjava fetches Java. `requires-python>=3.10` because jgo ≥2.1.3
and scyjava 1.12.5 need it (3.9 is stuck on jgo 2.1.0).

Java 21 is required: the ABBA jars (0.23.x and later) are compiled for Java 21 (class file
version 65) and fail with `UnsupportedClassVersionError` on older JVMs. scyjava
fetches Java 11 by default, so `configure_java()` in `abba.py` sets the version
to `JAVA_VERSION` before every `imagej.init`.

On Windows (long paths disabled), a jgo cache under a deep directory
(`scyjava.config.set_cache_dir`) fails with `FileNotFoundError [WinError 3]`
while linking jars: the paths exceed 260 characters. The default `~/.jgo` is fine.

## Common commands

- Run tests: `pytest`
- Single test: `pytest tests/test_abba_python.py::test_something`
- Lint + autofix: `ruff check --fix .` and `ruff format .`
- Type check: `mypy` (strict, configured over `src/**` in `pyproject.toml`)
- Run all pre-commit hooks: `pre-commit run --all-files`
- Manual smoke tests (need a full conda env + display): the scripts in `examples/`
  (`demo_api.py`, `demo_gui.py`, `demo_bench.py`).

Note: the test suite (`tests/`) is a placeholder and does **not** exercise the JVM
or ABBA itself. CI verifies install/import across OS × Python only. Real validation
is manual via the `examples/` scripts. `filterwarnings = ["error"]` is set, so any
warning fails the test run.

## Architecture

### The JVM bridge (the central concept)

Everything routes through a PyImageJ `ij` instance. The Java classpath is hardcoded
in `get_java_dependencies()` in `src/abba_python/abba.py` as a list of Maven GAV
coordinates — **this is where Java-side versions are bumped** (e.g. when releasing
against a new `ch.epfl.biop:ImageToAtlasRegister`). Keep these versions mutually
compatible; a mismatch surfaces only at runtime as Java `NoSuchMethodError`/linkage
errors, not at install. If a bump raises the Java bytecode level, also bump
`JAVA_VERSION` next to it (otherwise: `UnsupportedClassVersionError` at startup).

Two entry points create the JVM (both call `configure_java()` first):
- `start_imagej()` — launches Fiji with the full ABBA GUI (sets the Windows atlas
  cache dir under `%ProgramData%/abba-atlas`). BrainGlobe atlas discovery for the GUI
  chooser is now done Java-side, so no Python-side atlas registration happens here.
- `Abba(...)` — the programmatic object; can take an existing `ij` to share one JVM
  across instances (atlas objects are cached in the class-level `Abba.opened_atlases`).

### `Abba` command methods are generated

`commands.py` is **generated, never edited by hand**: run
`python scripts/generate_commands.py` after bumping the jars. The script starts the
JVM with `get_java_dependencies()` and describes the SciJava commands of
`ch.epfl.biop.atlas.aligner.command` with scijava-introspect. Each ABBA command becomes a
method of `AbbaCommands` (inherited by `Abba`) that calls
`self._run_command(class_name, {'mp': self.mp, ...})`; `self.mp` is the
"multipositioner" model object every command operates on. Generation rules, all in the
script:
- parameters are keyword-only, required ones first; choices become `Literal[...]`;
- defaults are the field values of a new command instance, except a numeric 0 (a field
  without initializer reads 0 too, so the caller must give it);
- a primitive number without default (NaN in Java) is `None` = not passed, the command
  computes it (e.g. DeepSlice pixel size);
- a single `Boolean`/`String` output is returned as a Python value, otherwise the module;
- commands run through `ModuleService`: `CommandService.run` returns no future for
  `DynamicCommand`s.
Behaviour a rule cannot express belongs in the Java command, not in hand edits. A
missing required input would make ABBA pop up a Swing dialog asking the user for it.

Defaults and choices computed in a command's `initialize()` (ontology keys of
`naming_choice`, DeepSlice pixel size) are not in the generated code; the docstring of
such a method says so.

### Atlas loading (`Abba.__init__`)

`Abba.__init__` branches on `atlas_name`:
- The built-in Java atlases (Allen CCFv3p1, Waxholm SD rat, the `*_java` ASR variant)
  are instantiated through dedicated SciJava commands in `ch.epfl.biop.atlas.mouse.*`
  / `ch.epfl.biop.atlas.rat.*`. Legacy display names are remapped to current ones at
  the top of the branch.
- **Any other name** is treated as a BrainGlobe atlas and delegated to the Java
  `ch.epfl.biop.atlas.brainglobe.BrainGlobeAtlas(String)`, which downloads/parses the
  atlas through its own managed Python env (Appose). There is no longer any Python
  implementation of ABBA's `ch.epfl.biop.atlas.struct.*` interfaces in this repo —
  that whole bridge moved into the `atlas` jar.

### Threading

Swing/BigDataViewer UI work must run on the Java EDT — see `show_bdv_ui()`, which
wraps creation in a `Runnable` and `SwingUtilities.invokeLater`. The GUI does not work
on macOS due to JVM/AWT threading issues (documented in the README). Long-running ABBA
commands return Java `Future`s; `.get()` blocks, and `wait_for_end_of_tasks()` joins
queued tasks.

## Releasing

Version is set manually in `pyproject.toml` (`version = ...`); hatch-vcs auto-
versioning is intentionally disabled. Pushing a `v*` tag triggers the `deploy` job in
`.github/workflows/ci.yml`, which builds and publishes to PyPI via trusted publishing.
A release typically also bumps the Java GAVs in `get_java_dependencies()`.
