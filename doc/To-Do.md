# To-Do

- [x] Use filenames to match tracks when rerendering (instead of title/artist).
- [-] Fix path extraction on macOS.
- [x] Retain metadata from existing Traktor collection.
- [x] Merge playlists with existing Traktor playlists.
- [ ] ~~Generate stable UUIDs for playlists.~~
- [x] Selectively overwrite metadata or only cues.
- [ ] Automatically backup a target file when overwriting it.
- [ ] Support different origin/destination paths.
- [ ] Fix key representation in files: Traktor doesn't understand "Gmin/Gmaj", but "Gm/G".
- [ ] ~~Merge playlists, update ones coming from RB (use UUID as identifier: hash the name)~~
- [x] Rounding errors when exporting cues? they seem off by a bit in Traktor.
- [x] Convert memcues to a different type of traktor cue.
- [x] Rounding errors in exported loop lengths.
- [x] Support for (flexible) beat grids.