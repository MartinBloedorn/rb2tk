#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import uuid
import argparse
import logging
import configparser

import xml.etree.ElementTree as ET
from xml.dom import minidom

from enum import Enum

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
        'Type' will be used to annotate extra info when needed.

        Values of Cue, FadeIn, FadeOut and Load identical in RB and TK.
        No Grid cue is available in RB.
        """
        Cue = 0
        FadeIn = 1
        FadeOut = 2
        Load = 3
        Grid = 5

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
        self.name = ""
        self.type = Playlist.Type.Folder
        self.children = []

    def __str__(self):
        return self.__str_recursive(0)

    def __str_recursive(self, level):
        s = ""
        if self.type == Playlist.Type.Folder:
            s = "{}[{}]".format(' '*2*level, self.name)
            for c in self.children:
                s = s + "\n" + c.__str_recursive(level + 1)
        elif self.type == Playlist.Type.List:
            s = "{}{} ({} tracks)".format(' '*2*level, self.name, len(self.children))
            # for c in self.children:
            #     s = s + "\n{}- {}".format(' '*2*level, c)
        return s


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
        if not os.path.exists(path_xml):
            logging.error("File doesn't exist: {}".format(path_xml))
        else:
            logging.debug("Reading: {}".format(path_xml))
            l.track_dict = self.__parse_tracks(path_xml)
            l.playl_tree = self.__parse_playlists(path_xml)
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

        logging.debug("{} tracks found.".format(len(tracks)))
        return tracks

    def __make_cue(self, cue_dict) -> Cue:
        c = Cue()
        c.start = float(cue_dict['Start'])
        c.len = float(cue_dict['End']) - c.start if 'End' in cue_dict else 0.0
        c.num = int(cue_dict['Num'])
        c.name = cue_dict['Name']
        c.type = Cue.Type.Cue
        return c

    def __parse_playlists(self, path_xml) -> Playlist:
        tree = ET.parse(path_xml)
        root = tree.getroot()
        playl_root = None

        playl_elem = root.find('PLAYLISTS')
        for child in playl_elem:
            playl_root = self.__make_node_recursive(child)

        return playl_root

    def __make_node_recursive(self, node_elem) -> Playlist:
        a = node_elem.attrib
        p = Playlist()
        p.name = a['Name']
        p.type = Playlist.Type.Folder if a['Type'] == "0" else Playlist.Type.List

        for t_e in node_elem: # iterate over children
            if p.type == Playlist.Type.List and t_e.tag == "TRACK":
                p.children.append(t_e.attrib['Key'])
            elif p.type == Playlist.Type.Folder and t_e.tag == "NODE":
                p.children.append(self.__make_node_recursive(t_e))

        return p


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# TraktorWriter
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class TraktorWriter:
    def __init__(self):
        self.__sep = "/:"
        pass

    def write(self, lib : Library, path_xml : str):
        root = self.__init_dom()
        root = self.__render_tracks(root, lib)
        root = self.__render_playlists(root, lib)
        self.__write_to_output(path_xml, root)

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
        locdict["DIR"] = self.__sep.join(tokens)
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
        cuedict["DISPL_ORDER"] = "0"
        cuedict["TYPE"] = str("5" if is_loop else cue.type.value)
        cuedict["START"] = str(cue.start*1000.0)
        cuedict["LEN"] = str(cue.len*1000.0)
        cuedict["REPEATS"] = "-1"
        cuedict["HOTCUE"] = str(cue.num)
        return cuedict

    def __generate_info(self, track : Track) -> dict:
        infodict = {}
        infodict["BITRATE"] = "320" # TODO
        infodict["KEY"] = track.tonality
        return infodict

    def __render_tracks(self, root, lib : Library):
        tracks = lib.track_dict.values()
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

    def __generate_playl_track(self, track_id : str, track_dict : dict) -> dict:
        """
        Generates attribute dictionary for a PRIMARYKEY ENTRY of a PLAYLIST NODE.
        """
        track = track_dict[track_id]
        locdict = self.__generate_location(track.fileurl)
        attrib = {}
        attrib["KEY"] = locdict["VOLUME"] + locdict["DIR"] + self.__sep + locdict["FILE"]
        attrib["TYPE"] = "TRACK"
        return attrib

    def __generate_node_recursive(self, parent, playl : Playlist, track_dict : dict):
        """
        @param parent       Parent DOM node.
        @param playl        Current Playlist node.
        @param track_dict   Track dictionary to render track info.
        @return Modified parent DOM
        """
        node = ET.SubElement(parent, "NODE")
        node.attrib["NAME"] = "$ROOT" if playl.name == "ROOT" else playl.name

        if playl.type == Playlist.Type.Folder:
            node.attrib["TYPE"] = "FOLDER"
            subnode = ET.SubElement(node, "SUBNODES", {"COUNT": str(len(playl.children))})
            for c in playl.children:
                self.__generate_node_recursive(subnode, c, track_dict)
        elif playl.type == Playlist.Type.List:
            node.attrib["TYPE"] = "PLAYLIST"
            playlist = ET.SubElement(node, "PLAYLIST",
                                     {"ENTRIES": str(len(playl.children)),
                                      "TYPE": "LIST",
                                      "UUID": "/db/Playlist/" + str(uuid.uuid4())})
            for c in playl.children:
                entry = ET.SubElement(playlist, "ENTRY")
                ET.SubElement(entry, "PRIMARYKEY", self.__generate_playl_track(c, track_dict))

        return node

    def __render_playlists(self, root, lib : Library):
        if lib.playl_tree is not None:
            playl_elem = root.find('PLAYLISTS')
            self.__generate_node_recursive(playl_elem, lib.playl_tree, lib.track_dict)
        return root

    def __write_to_output(self, xml_path, root):
        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
        with codecs.open(xml_path, "w", "utf-8") as f:
            if f.write(xmlstr) is None:
                logging.info("Wrote output to file: {}".format(xml_path))
            else:
                logging.error("Failed to write to location: {}".format(xml_path))


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

class OptionalOperations:
    def __init__(self, config):
        self.config = config
        pass

    def apply(self, lib : Library) -> Library:
        lib.track_dict = self.__tk_add_grid_marker(lib.track_dict)
        lib.track_dict = self.__tk_assign_all_cues(lib.track_dict)
        return lib

    def __tk_add_grid_marker(self, tracks : dict) -> dict:
        if self.config.getboolean("Options", "GridMakerFromCue", fallback=False):
            for tid in tracks:
                t = tracks[tid]
                if len(t.cues) > 0:
                    gridcue = Cue()
                    gridcue.start = t.cues[0].start
                    gridcue.type = Cue.Type.Grid
                    gridcue.name = "Grid"
                    t.cues.insert(0, gridcue)
                    tracks[tid] = t
        return tracks

    def __tk_assign_all_cues(self, tracks : dict) -> dict:
        num = self.config.getint("Options", "AssignMemCueToPad", fallback=-1)
        if num > -1:
            for tid in tracks:
                t = tracks[tid]
                for i in range(0, len(t.cues)):
                    if t.cues[i].num < 0 and t.cues[i].type != Cue.Type.Grid:
                        t.cues[i].num = num
        return tracks


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# main
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
if __name__ == "__main__":

    ''' Args '''
    parser = argparse.ArgumentParser(
                    prog='rb2tk.py',
                    description='Convert a rekordbox XML library into a '
                                'Traktor Pro 3 NML collection.',
                    epilog='For more info: github.com/martinbloedorn')

    parser.add_argument('RekordboxXmlInput', nargs='?', default=None,
                        help="Path to rekordbox XML library export.")
    parser.add_argument('TraktorNmlOutput', nargs='?', default=None,
                        help="Output path of generated Traktor NML collection.")
    parser.add_argument('-c', '--conf', action='store', default="rb2tk.ini")
    parser.add_argument('-v', '--verbose', action='count', default=0)

    args = parser.parse_args()

    ''' Logging '''
    logging.basicConfig(format='%(levelname)s @ %(funcName)s: %(message)s')
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]
    logging.getLogger().setLevel(levels[min(args.verbose, len(levels)-1)])

    ''' Config '''
    config = configparser.ConfigParser()
    config.read(args.conf)

    if args.RekordboxXmlInput is not None:
        config["Library"]["RekordboxXmlInput"] = args.RekordboxXmlInput
    elif not config.has_option("Library", "RekordboxXmlInput"):
        config["Library"]["RekordboxXmlInput"] = "rekordbox.xml"

    if args.TraktorNmlOutput is not None:
        config["Library"]["TraktorNmlOutput"] = args.TraktorNmlOutput
    elif not config.has_option("Library", "TraktorNmlOutput"):
        config["Library"]["TraktorNmlOutput"] = "collection.nml"

    ''' Main '''
    rr = RekordboxReader()
    tw = TraktorWriter()
    oo = OptionalOperations(config)

    lib = rr.read(config["Library"]["RekordboxXmlInput"])
    lib = oo.apply(lib)
    tw.write(lib, config["Library"]["TraktorNmlOutput"])

