# rb2tk

`rb2tk` is a simple script to convert a Rekordbox XML export to a Traktor NML library. 

The most straightforward use case is downloading and running the `rb2tk.py` in the same folder as a `rb2tk.ini` file containing settings, e.g.:

```ini
[Library]
RekordboxXmlInput = /path/to/rekordbox.xml
TraktorNmlOutput = /path/to/traktor.nml
[Options]
FixCuePositions = yes
```

`rb2tk.py` uses only standard Python libraries.

## Settings

Available `rb2tk.ini` options are:
- `[Library]`
  - `RekordboxXmlInput`: Local path to exported XML of Rekorbox collection.
  - `TraktorNmlOutput`: Target path of generated collection.
  - `MergeOutput` (`yes/no`): Experimental/buggy. If the file at `TraktorNmlOutput` already exists, the script will attempt merging the new conversion with the target collection. 
- `[Options]`
  - `FixCuePositions` (`yes/no`): Will attempt to fix cue shifts/offsets that happen due to how Traktor handles MP3 and M4A/AAC files. See the **Documentation** section below for more information.
  - `GridMarkerFromCue` (`yes/no`): Will create a grid marker from the first Hot- or Memory Cue detected.
  - `LoopQuantization` (`float`): Quantizes exported Cue-Loops to the selected beat fraction (i.e., `1.0` = quarter note, `0.5` = eigth note, etc.).

## Documentation

- [To-Do.md](doc/To-Do.md): Scratchpad for planned tasks and known bugs.
- [References.md](doc/References.md): Useful resources.
- [Traktor Cue Shift.md](doc/Traktor%20Cue%20Shift.md): Sources, information and notes on fixing the convoluted issue of shifted cues in Traktor.