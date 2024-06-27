# References

## Rekordbox XML

Documentation on the Rekordbox XML format can be found [here](https://cdn.rekordbox.com/files/20200410160904/xml_format_list.pdf).

## Traktor NML

There doesn't seem to be official documentation on the format. It is XML-based, however, and mostly straightforward.

### Cue Points

Traktor's different cue point types are [documented here](https://www.native-instruments.com/ni-tech-manuals/traktor-pro-manual/en/advanced-usage-tutorials#cue-point-types). A sample NML file excerpt with each type is listed below:

```xml
<CUE_V2 NAME="Cue" DISPL_ORDER="0" TYPE="0" START="310.000000" LEN="0.000000" REPEATS="-1" HOTCUE="0"></CUE_V2>
<CUE_V2 NAME="AutoGrid" DISPL_ORDER="0" TYPE="4" START="332.858643" LEN="0.000000" REPEATS="-1" HOTCUE="-1"></CUE_V2>
<CUE_V2 NAME="Fade-In" DISPL_ORDER="0" TYPE="1" START="4172.861689" LEN="0.000000" REPEATS="-1" HOTCUE="1"></CUE_V2>
<CUE_V2 NAME="Fade-Out" DISPL_ORDER="0" TYPE="2" START="8012.864736" LEN="0.000000" REPEATS="-1" HOTCUE="2"></CUE_V2>
<CUE_V2 NAME="Load" DISPL_ORDER="0" TYPE="3" START="11852.867783" LEN="0.000000" REPEATS="-1" HOTCUE="3"></CUE_V2>
<CUE_V2 NAME="Loop" DISPL_ORDER="0" TYPE="5" START="15692.870830" LEN="3840.003047" REPEATS="-1" 