# Traktor Cue Shift

## Overview

Issue: converting cues from Rekordbox to Traktor "blindly" (i.e., one to one) causes them to be ever so slightly shifted. 

- [Report on the MIXXX webpage](https://github.com/mixxxdj/mixxx/wiki/Traktor-Cue-Storage-Format):
> This issue depends on the actual decoder definition of the 00:00:00 time point

- [Reported issue + solution](https://github.com/digital-dj-tools/dj-data-converter/issues/3) on `dj-data-converter`, including solution algorithm and [hexdumps of MP3 headers](https://github.com/pestrela/music/blob/master/traktor/26ms_offsets/examples_tagged/hexdump%20of%20all%20examples.txt). The whole comment section is gold.
## Conceptual issue

Issue seems to be related with the encoder delay. For context, from this [bug ticket](https://sourceforge.net/p/lame/bugs/453/):

> Also, there are two things called encoder delay and decoder delay. Encoder delay comes from the fact that the first output block of the decoder has some prepended silent audio^1, and the size depends on its own implementation and the block sizes used in the first block.  
The decoder delay is almost the same concept, which means that the output of the decoder also has some prepended amount of audio at the beginning that depends on how it is implemented too.  
A decoder is able to skip its own delay (if it is coded to do so), but initially it had no way to know the encoder delay. Usually it doesn't matter, but for gapless music (mixed or continuous music), it can be annoying.
....
Some time later, LAME extended the original Xing header (used in VBR files) to add more information like the encoder delay and last block padding^2, which allowed the format to become aware of the exact audio size. Frauhofer encoder also added their VBR header (VBRi) and their size information, so two standards were born.

^1: Is a way to initialise & flush the FFT-buffers of the compression algorithm. More info and examples [here](https://github.com/tambien/Piano/issues/30). LAME documentation [here](https://lame.sourceforge.io/tech-FAQ.txt), explaining it as clearly as it gets.

^2: Some examples [here](https://hydrogenaud.io/index.php/topic,49438.0.html).

This issue was also mentioned in the [release notes for Rekordbox](https://github.com/digital-dj-tools/dj-data-converter/issues/3#issuecomment-461979891):

> Disabling gapless playback for MP3 files encoded with the LAME encoder in Version 1.5.4 will shift existing beat grids, loops or cue points of mp3 files encoded with the LAME encoder that have been analysed and adjusted with an older version of rekordbox. The offset value depends on the sampling frequency of the file: 24ms (in the case of 48kHz), 26ms (in the case of 44.1 kHz).

## Solutions

### dj-data-converter

From the thread:

```
if mp3 does NOT have a Xing/INFO tag:
     correction = 0ms
 
 elif mp3 has Xing/INFO, but does NOT have a LAME tag:
     # typical case: has LAVC header instead
     correction = 26ms
 
 elif LAME tag has invalid CRC:
     # typical case: CRC = zero
     correction = 26ms
     
 elif LAME tag has valid CRC:
     correction = 0ms
```

In [`offset.cljc`](https://github.com/digital-dj-tools/dj-data-converter/blob/master/src/converter/offset.cljc):

```clojure
(defn- calculate
  [{:keys [xing-tag? lame-tag?] {:keys [::mp3lame/crc-valid?]} :lame}]
  (->>
   (cond
     (not xing-tag?) ["A" 0]
     (not lame-tag?) ["B" 0.026]
     (not crc-valid?) ["C" 0.026]
     :else ["D" 0])
   (interleave [:bucket :value])
   (apply hash-map)))
```

### RekordBuddy

Deprecated library conversion utility. 

- **MP3:** See [`positionOffsetToAddToRekordboxMarkersInSeconds()`](https://github.com/prk0ghy/RekordBuddy/blob/main/TrackFiles/Objects/Internal/MPEGTrackFileInternal.hpp#L96) in the MPEG handler; scans for the Xing/Info/LAME tags in the [MP3 header](http://gabriel.mp3-tech.org/mp3infotag.html). Attempts to extract the *encoder delay* and *padding*.
- **MP4**: Also requires an offset ([see](https://github.com/prk0ghy/RekordBuddy/blob/main/TrackFiles/Objects/Internal/MP4TrackFileInternal.hpp#L411))!
```cpp
 DecimalNumber offsetToAddToMarkerPositionsForRekordboxInSeconds() const override
    {
        // -- rekordbox and the CDJs have a bug in their ACC M4A code that causes about 50ms of silence to be
        // -- inserted a the beginning of a track. Because of this we need to offset the markers accordingly
        // -- so they still match other programs.
        return p_mp4OffsetToAddToMarkerPositionsForRekordboxInSeconds;
    }
```
