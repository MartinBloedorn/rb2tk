# -*- coding: utf-8 -*-

import os

import xml.etree.ElementTree as ET
from xml.dom import minidom

from enum import Enum
from collections import namedtuple

import codecs
import urllib.parse


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Cue
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class Cue:
    class Type(Enum):
        """
        Most cue types can be inferred:
          MemCue  -> num < 0
          Cue     -> num >=0
          + Loop  -> len > 0.0
        'Type' will be used to annotate extra info when needed:
        """
        Cue = 0
        Load = 1
        FadeIn = 2
        FadeOut = 3
        Grid = 4

    def __init__(self):
        self.name = ""
        self.start = 0.0
        self.len = 0.0
        self.num = -1
        self.type = Cue.Type.Cue

    def __str__(self):
        return "{} @{} [{}]".format(repr(self.type), self.start, self.num)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Track
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class Track:
    def __init__(self):
        self.id = ""
        self.name = ""
        self.artist = ""
        self.album = ""
        self.bpm = 120.0
        self.tonality = ""
        self.fileurl = ""
        self.cues = []

    def __str__(self):
        return "{}:\t{} ({}) [{}, {}, {} cues]" \
            .format(self.id, self.name, self.artist,
                    self.tonality, self.bpm, len(self.cues))


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Playlist
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class Playlist:
    class Type(Enum):
        Folder = 0
        List = 1

    def __init__(self):
        self.id = ""
        self.name = ""
        self.type = Playlist.Type.Folder
        self.children = []


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Library
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class Library:
    def __init__(self):
        self.track_dict = {}
        self.playl_tree = None


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# RekordboxReader
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class RekordboxReader:
    def __init__(self):
        pass

    def read(self, path_xml : str) -> Library:
        l = Library()
        l.track_dict = self.__parse_tracks(path_xml)
        return l

    def __parse_tracks(self, path_xml):
        tree = ET.parse(path_xml)
        root = tree.getroot()
        tracks = {}

        coll_elem = root.find('COLLECTION')
        for track_elem in coll_elem.iter('TRACK'):
            a = track_elem.attrib
            t = Track()
            t.id = a['TrackID']
            t.name = a['Name']
            t.artist = a['Artist']
            t.bpm = float(a['AverageBpm'])
            t.tonality = a['Tonality']
            t.fileurl = a['Location']
            t.album = a['Album']

            for mark_elem in track_elem.iter('POSITION_MARK'):
                t.cues.append(self.__make_cue(mark_elem.attrib))

            t.cues.sort(key=lambda c: c.start)
            tracks[t.id] = t

        return tracks

    def __make_cue(self, cue_dict) -> Cue:
        c = Cue()
        c.start = float(cue_dict['Start'])
        c.len = float(cue_dict['End']) - c.start if 'End' in cue_dict else 0.0
        c.num = int(cue_dict['Num'])
        c.name = cue_dict['Name']
        c.type = Cue.Type.Cue
        return c


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# TraktorWriter
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class TraktorWriter:
    def __init__(self):
        pass

    def write(self, lib : Library, path_xml : str):
        root = self.__init_dom()
        root = self.__render_tracks(root, lib.track_dict.values())
        self.__write_to_output(path_xml, root)
        pass

    def __init_dom(self):
        root = ET.Element("NML", {"VERSION": "19"})
        for e in ["MUSICNODES", "COLLECTION", "PLAYLISTS", "SETS"]:
            ET.SubElement(root, e)
        return root

    def __generate_location(self, fileurl : str) -> dict:
        """
        Generates attribute dictionary for a LOCATION element from a file URL.
        {"DIR": ..., "FILE", ..., "VOLUME": ...}
        """
        url = urllib.parse.urlparse(fileurl)
        path = os.path.normpath(url.path)
        path = urllib.parse.unquote_plus(path)
        tokens = path.split(os.sep)

        locdict = {}
        locdict["VOLUME"] = tokens.pop(1)
        locdict["FILE"] = tokens.pop(-1)
        locdict["DIR"] = "/:".join(tokens)
        return locdict

    def __generate_cue(self, cue : Cue) -> dict:
        """
        Generates attribute dictionary for a CUE_V2 element from a file URL.
        {"NAME": ..., "TYPE", ..., "START": ...}
        """
        is_loop = cue.len > 0.0
        is_hot = cue.num > -1

        cuedict = {}
        cuedict["NAME"] = cue.name if cue.name != "" else \
                            "Loop" if is_loop else \
                            "Cue"  if is_hot else "Mem"
        cuedict["LEN"] = str(cue.len*1000.0)
        cuedict["TYPE"] = "5" if is_loop else "0"
        cuedict["START"] = str(cue.start*1000.0)
        cuedict["HOTCUE"] = str(cue.num)
        cuedict["DISPL_ORDER"] = "0"
        cuedict["REPEATS"] = "-1"
        return cuedict

    def __generate_info(self, track : Track) -> dict:
        infodict = {}
        infodict["BITRATE"] = "320"
        return infodict

    def __render_tracks(self, root, tracks):
        coll_elem = root.find('COLLECTION')
        coll_elem.attrib["ENTRIES"] = str(len(tracks))

        for t in tracks:
            t_e = ET.SubElement(coll_elem, "ENTRY")
            t_e.attrib['TITLE'] = t.name
            t_e.attrib['ARTIST'] = t.artist

            ET.SubElement(t_e, "LOCATION", self.__generate_location(t.fileurl))
            ET.SubElement(t_e, "ALBUM", {"TITLE": t.album})
            ET.SubElement(t_e, "INFO", self.__generate_info(t))
            ET.SubElement(t_e, "MODIFICATION_INFO", {"AUTHOR_TYPE": "user"})
            ET.SubElement(t_e, "TEMPO", {"BPM_QUALITY": "100",
                                         "BPM": str(t.bpm)})
            for c in t.cues:
                ET.SubElement(t_e, "CUE_V2", self.__generate_cue(c))

        return root

    def __write_to_output(self, xml_path, root):
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with codecs.open(xml_path, "w", "utf-8") as f:
            f.write(xmlstr)


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# main
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
if __name__ == "__main__":
    xml_in = 'rb.xml'
    xml_out = 'tk.nml'

    rr = RekordboxReader()
    tw = TraktorWriter()

    lib = rr.read(xml_in)
    for track in lib.track_dict.values():
        print(track)
        print(track.fileurl)
        # for c in track.cues:
        #     print(c)

    tw.write(lib, xml_out)


