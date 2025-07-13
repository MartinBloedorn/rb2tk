# rb2tk

`rb2tk` is a simple script to convert a Rekordbox XML export to a Traktor NML library. 

Execute it with `python3 rb2tk.py` in the same folder as a `rb2tk.ini` file containing your settings:

```ini
[Library]
RekordboxXmlInput = /path/to/rekordbox.xml
TraktorNmlOutput = /path/to/traktor.nml
[Options]
FixCuePositions = yes
```

`rb2tk.py` uses only standard Python libraries. For more options, see `python3 rb2tk.py -h`. 

## Settings

Available `rb2tk.ini` options are:
- `[Library]`
  - `RekordboxXmlInput`: Local path to exported XML of Rekorbox collection.
  - `TraktorNmlOutput`: Target path of generated collection.
  - `MergeOutput` (`yes/no`, default: `no`): If the file at `TraktorNmlOutput` already exists, the script will attempt merging the new conversion with the target collection. 
- `[Options]`
  - `FixCuePositions` (`yes/no`, default: `yes`): Will attempt to fix cue shifts/offsets that happen due to how Traktor handles MP3 and M4A/AAC files. See the **Documentation** section below for more information.
  - `LoopQuantization` (`float`, default: `0.0`): Quantizes exported Cue-Loops to the selected beat fraction (i.e., `1.0` = quarter note, `0.5` = eigth note, etc.).
  - `SmoothenGridMarkers` (`yes/no`, default: `yes`): Prunes excessive redundant (i.e., <0.5% BPM change) grid markers that Rekordbox might have generated, which clutter the visualization in Traktor.
  - `BackupExistingCollection` (`yes/no`, default: `yes`): Creates a backup of the existing collection (i.e., the file targeted by `TraktorNmlOutput`). 
  - `ParentPlaylistFolder` (default: `rekordbox`): The parent folder under which all your Rekorbox playlists will be exported in the newly generated Traktor collection. This folder will be created at the root level of your collection; if it already exists, all its previous content will be **erased** and regenerated.

## Documentation

- [To-Do.md](doc/To-Do.md): Scratchpad for planned tasks and known bugs.
- [References.md](doc/References.md): Useful resources.
- [Traktor Cue Shift.md](doc/Traktor%20Cue%20Shift.md): Sources, information and notes on fixing the convoluted issue of shifted cues in Traktor.