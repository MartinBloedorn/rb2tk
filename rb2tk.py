#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import uuid
import math
import argparse
import logging
import configparser
import subprocess

import xml.etree.ElementTree as ET
from xml.dom import minidom

from enum import Enum

import codecs
import urllib.parse
import urllib.request


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Cue & GridMarker
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
        Grid = 4
        Loop = 5

    def __init__(self):
        self.name = ""
        self.start = 0.0
        self.len = 0.0
        self.num = -1
        self.type = Cue.Type.Cue

    def __str__(self):
        return "{} @{} [{}]".format(repr(self.type), self.start, self.num)


class GridMarker:
    def __init__(self):
        self.start = 0.0
        self.bpm = 0.0
        self.timesig = [4, 4]
        self.beat = 0
        """ 0 = marker is on downbeat """


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Track
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class Track:
    def __init__(self):
        cues: list[Cue]
        grids: list[GridMarker]

        self.id = ""
        self.name = ""
        self.artist = ""
        self.album = ""
        self.genre = ""
        self.comments = ""
        self.bpm = 120.0
        self.duration = 0
        self.tonality = ""
        self.fileurl = ""
        self.label = ""
        self.cues = []
        self.grids = []
        self.indate = ""
        self.rating = 0

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


class Utils:
    @staticmethod
    def url2path(url : str) -> str:
        ourl = urllib.parse.urlparse(url)
        path = os.path.normpath(ourl.path)
        path = urllib.request.url2pathname(path)
        return path


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# RekordboxReader
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
class RekordboxReader:
    def __init__(self, config):
        self.config = config
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
            t.duration = float(a['TotalTime'])
            t.genre = a['Genre']
            t.comments = a['Comments']
            t.tonality = a['Tonality']
            t.fileurl = a['Location']
            t.album = a['Album']
            t.indate = a['DateAdded']
            t.rating = a['Rating']
            t.label = a['Label']

            for mark_elem in track_elem.iter('POSITION_MARK'):
                t.cues.append(self.__make_cue(mark_elem.attrib))

            for tempo_elem in track_elem.iter('TEMPO'):
                t.grids.append(self.__make_grid_marker(tempo_elem.attrib))

            t.cues.sort(key=lambda c: c.start)
            tracks[t.id] = t

        logging.debug("{} tracks found.".format(len(tracks)))
        return tracks

    def __make_cue(self, cue_dict) -> Cue:
        c = Cue()
        c.start = float(cue_dict['Start'])
        c.len = (float(cue_dict['End']) - c.start) if 'End' in cue_dict else 0.0
        c.num = int(cue_dict['Num'])
        c.name = cue_dict['Name']
        c.type = Cue.Type.Cue
        return c

    def __make_grid_marker(self, marker_dict) -> Cue:
        g = GridMarker()
        g.start   = float(marker_dict['Inizio'])
        g.bpm     = float(marker_dict['Bpm'])
        g.beat    = int(marker_dict['Battito']) - 1
        g.timesig = [int(x) for x in marker_dict['Metro'].split("/")]
        return g

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
    def __init__(self, config):
        self.config = config
        self.volume = ""
        self.__sep = "/:"
        pass

    def write(self, lib : Library, path_xml : str):
        root = self.__init_dom(path_xml)
        root = self.__render_tracks(root, lib)
        root = self.__render_playlists(root, lib)
        self.__write_to_output(path_xml, root)

    def __init_dom(self, path_xml : str):
        root = None
        
        if self.config.getboolean("Library", "MergeOutput", fallback=True) \
            and os.path.exists(path_xml):
            logging.debug("Reading preexisting output file: {}".format(path_xml))
            try:
                tree = ET.parse(path_xml)
                root = tree.getroot()
            except:
                logging.warning("Existing output file isn't valid XML': {}".format(path_xml))

        if root is None:
            root = ET.Element("NML", {"VERSION": "19"})
            for e in ["MUSICNODES", "COLLECTION", "PLAYLISTS", "SETS"]:
                ET.SubElement(root, e)
                
        return root
    
    def __get_path_volume(self, path : str) -> str:
        """
        For macOS only. Extracts the name of the current '/' Volume.
        
        #TODO: This still ignores the input path, and will default to the 'Macintosh HD'. Fix it.
        """
        if sys.platform == "darwin" and self.volume == "":
            self.volume = str(subprocess.run(["diskutil info -plist / | plutil -extract VolumeName raw - -o -"], 
                                               shell=True, capture_output=True).stdout.decode('ascii').strip())
        return self.volume

    def __generate_location(self, fileurl : str) -> dict:
        """
        Generates attribute dictionary for a LOCATION element from a file URL.
        {"DIR": ..., "FILE", ..., "VOLUME": ...}
        """
        path = Utils.url2path(fileurl)
        tokens = path.split(os.sep)
        locdict = {}

        if sys.platform == "darwin":            
            locdict["VOLUME"] = self.__get_path_volume(path)
        else:
            locdict["VOLUME"] = tokens.pop(1) if len(tokens) > 1 else "" 

        locdict["VOLUMEID"] = ""
        locdict["FILE"] = tokens.pop(-1) if len(tokens) > 0 else ""
        locdict["DIR"] = self.__sep.join(tokens) + self.__sep
        return locdict

    def __generate_cue(self, cue : Cue) -> dict:
        """
        Generates attribute dictionary for a CUE_V2 element from a file URL.
        {"NAME": ..., "TYPE", ..., "START": ...}
        """
        is_loop = cue.len > 0.0
        is_hot = cue.num > -1
        name = "Mem"

        if cue.name != "":
            name = cue.name
        elif is_loop:
            name = "Loop"
        elif is_hot:
            name = "Cue"

        cuedict = {}
        cuedict["NAME"] = name
        cuedict["DISPL_ORDER"] = "0"
        cuedict["TYPE"] = str(Cue.Type.Loop.value if is_loop else cue.type.value)
        cuedict["START"] = str(cue.start*1000.0)
        cuedict["LEN"] = str(cue.len*1000.0)
        cuedict["REPEATS"] = "-1"
        cuedict["HOTCUE"] = str(cue.num)
        return cuedict
    
    def __generate_grid_marker(self, marker : GridMarker) -> dict:
        num = marker.timesig[0]
        den = marker.timesig[1]
        # If the marker doesn't start on the downbeat, offset its start to the next downbeat:
        dt = 60.0/(marker.bpm * float(den/4))
        beatoffset = (num - marker.beat) % num 

        c = Cue()
        c.type = Cue.Type.Grid
        c.name = "Beat Marker"
        c.start = marker.start + (dt * beatoffset)
        cuedict = self.__generate_cue(c)
        return cuedict
    
    @staticmethod
    def __get_child(parent, tag : str, attrib : dict = {}):
        """
        Retrieves or creates a child af a given tag under a certain parent. 
        """
        node = parent.find(tag)
        return node if node is not None else ET.SubElement(parent, tag, attrib)
    
    def __generate_info(self, track : Track) -> dict:
        infodict = {}
        infodict["BITRATE"] = "320" # TODO
        infodict["KEY"] = track.tonality 
        infodict["IMPORT_DATE"] = track.indate.replace('-', '/') # 2024-10-31 -> 2024/10/31
        infodict["RANKING"] = track.rating
        infodict["COMMENT"] = track.comments
        infodict["LABEL"] = track.label
        infodict["GENRE"] = track.genre
        return infodict

    def __render_tracks(self, root, lib : Library):
        track_dict = dict(lib.track_dict) # copy
        coll_elem = root.find('COLLECTION')
        
        def __render_track(t_e, t, lock=True):
            t_e.attrib['TITLE'] = t.name
            t_e.attrib['ARTIST'] = t.artist
            t_e.attrib['LOCK'] = "1" if lock else "0"

            # self.__get_child(t_e, "LOCATION", self.__generate_location(t.fileurl))
            # TODO: update BPM if overwriting track.
            self.__get_child(t_e, "ALBUM", {"TITLE": t.album})
            self.__get_child(t_e, "INFO", self.__generate_info(t))
            self.__get_child(t_e, "MODIFICATION_INFO", {"AUTHOR_TYPE": "user"})
            self.__get_child(t_e, "TEMPO", {"BPM_QUALITY": "100", "BPM": str(t.bpm)})

            # Always overwrite location to ensure we're synced: 
            self.__get_child(t_e, "LOCATION").attrib = self.__generate_location(t.fileurl)

            for e in t_e.findall("CUE_V2"):
                t_e.remove(e)
            for c in t.cues:
                ET.SubElement(t_e, "CUE_V2", self.__generate_cue(c))
            for g in t.grids:
                e = ET.SubElement(t_e, "CUE_V2", self.__generate_grid_marker(g))
                ET.SubElement(e, "GRID", {"BPM": str(g.bpm)})
            return t_e  
        
        for t_e in coll_elem.findall('ENTRY'):
            lock = t_e.attrib.get('LOCK')
            location = t_e.find('LOCATION')
            filename = location.attrib.get('FILE') if location is not None else ""

            for k in list(track_dict.keys()):
                t = track_dict[k]
                basename = os.path.basename(urllib.request.url2pathname(t.fileurl))
                if basename == filename:
                    if lock != "1":
                        __render_track(t_e, t, False)
                    del track_dict[k]
            
        for uuid, t in track_dict.items():
            t_e = ET.SubElement(coll_elem, "ENTRY")
            __render_track(t_e, t, False)
            logging.info(f"Added '{t.name}' by '{t.artist}' to collection.")
            
        coll_elem.attrib["ENTRIES"] = str(len(coll_elem))
        return root

    def __generate_playl_track(self, track_id : str, track_dict : dict) -> dict:
        """
        Generates attribute dictionary for a PRIMARYKEY ENTRY of a PLAYLIST NODE.
        """
        if track_id in track_dict:
            track = track_dict[track_id]
            locdict = self.__generate_location(track.fileurl)
            attrib = {}
            attrib["KEY"] = locdict["VOLUME"] + locdict["DIR"] + locdict["FILE"]
            attrib["TYPE"] = "TRACK"
            return attrib
        else:
            return None

    def __generate_node_recursive(self, parent, playl : Playlist, track_dict : dict):
        """
        @param parent       Parent DOM node.
        @param playl        Current Playlist node.
        @param track_dict   Track dictionary to render track info.
        @return Modified parent DOM
        """        
        node = parent if playl.name == "ROOT" else ET.SubElement(parent, "NODE", {"NAME": playl.name})

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
                playl_track = self.__generate_playl_track(c, track_dict)
                if playl_track is not None:
                    entry = ET.SubElement(playlist, "ENTRY")
                    ET.SubElement(entry, "PRIMARYKEY", self.__generate_playl_track(c, track_dict))
                else: 
                    logging.info(f"Skipping missing track ID {c} in playlist '{playl.name}'")

        return node

    def __render_playlists(self, root, lib : Library):
        # All rekordbox playlists will be exported under this folder; manual changes to it will be overwritten.
        rb_playlist_name = "rekordbox"

        if lib.playl_tree is not None:
            playlists_e = root.find('PLAYLISTS')
            playlroot_e = self.__get_child(playlists_e, "NODE", {"NAME": "$ROOT", "TYPE": "FOLDER"})
            psubnodes_e = self.__get_child(playlroot_e, "SUBNODES", {"COUNT": "1"})
            
            for node in psubnodes_e.findall("NODE"):
                if node.attrib["TYPE"] == "FOLDER" and node.attrib["NAME"] == rb_playlist_name:
                    psubnodes_e.remove(node)
                    break

            exportroot_e = ET.SubElement(psubnodes_e, "NODE", {"NAME": rb_playlist_name, "TYPE": "FOLDER"})
        
            self.__generate_node_recursive(exportroot_e, lib.playl_tree, lib.track_dict)
        return root
    
    # Method happily lifted from https://stackoverflow.com/a/4590052
    def __xml_indent(self, elem, level=0):
        i = "\n" + level*"  "
        j = "\n" + (level-1)*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for subelem in elem:
                self.__xml_indent(subelem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = j
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = j
        return elem   

    def __write_to_output(self, xml_path, root):
        self.__xml_indent(root)
        tree = ET.ElementTree(root)
        if tree.write(xml_path, encoding='utf-8', xml_declaration=True) is None:
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
        lib.track_dict = self.__prune_missing_tracks(lib.track_dict)

        if self.config.getboolean("Options", "SmoothenGridMarkers", fallback=True):
            lib.track_dict = self.__prune_redundant_grid_markers(lib.track_dict)

        if self.config.getboolean("Options", "FixCuePositions", fallback=True):
            lib.track_dict = self.__tk_fix_cue_positions(lib.track_dict)

        quantization = self.config.getfloat("Options", "LoopQuantization", fallback=0.0)
        if quantization >= 1.0/8.0: # minimum: 32nd note quantization
            lib.track_dict = self.__tk_quantize_loops(lib.track_dict, quantization)

        if self.config.getboolean("Options", "S8_AutoAssignCueToPads", fallback=False):
            lib.track_dict = self.__tk_s8_assign_cues_to_pads(lib.track_dict)
        
        return lib
    
    def __prune_missing_tracks(self, tracks : dict) -> Library: 
        """
        Remove tracks with missing files from exported library.
        """
        pruned_ids = []

        for tid in tracks:
            t = tracks[tid]
            path = Utils.url2path(t.fileurl)
            if not os.path.isfile(path):
                logging.info(f"Pruning missing track: {t.name} @ {t.fileurl}")
                pruned_ids.append(tid)

        for tid in pruned_ids:            
            del tracks[tid]
        
        return tracks
    
    def __prune_redundant_grid_markers(self, tracks : dict) -> Library:
        """
        Remove adjacent grid markers with less than 0.5% BPM change.
        """
        for tid in tracks:
            grids = []
            lastg = GridMarker()
            for g in tracks[tid].grids:
                if round(g.bpm) > 0.1 and abs(g.bpm - lastg.bpm)/g.bpm > 0.005:
                    grids.append(g)
                    lastg = g

            tracks[tid].grids = grids
        
        return tracks

    def __get_mp3_offset(self, mp3_file_path):
        offset_44k1 = 0.026 # Offsets in ms for each sample rate, as per RB release notes.
        offset_48k0 = 0.024

        def to_int7(buf):
            return (buf[0] << 21) | (buf[1] << 14) | (buf[2] << 7) | buf[3]
        
        try:
            with open(mp3_file_path, 'rb') as f:
                f.seek(0)
                header = f.read(10)
                if header[:3] != b'ID3':
                    return 0.0
                
                size = to_int7(header[6:])
                f.seek(size, 1)
                buffer = f.read(192)

                sample_rate_index = (buffer[2] >> 2) & 3
                tag = buffer[36:40]
                enc = buffer[156:160]

                if (tag == b'Xing' or tag == b'Info') and (enc == b'Lavc' or enc == b'Lavf'):
                    return offset_48k0 if sample_rate_index == 1 else offset_44k1
                return 0.0
            
        except Exception as e:
            logging.error(f"Error reading MP3 metadata of {mp3_file_path}: {e}")
            return 0.0
    
    def __tk_fix_cue_positions(self, tracks : dict) -> Library: 
        """
        Check doc/Traktor Cue Shift.md for more information on this function.
        """       
        for tid in tracks:
            t = tracks[tid]
            dcue = 0.0
            _, extension = os.path.splitext(t.fileurl)

            if extension == ".m4a":
                dcue = -0.048
            elif extension == ".mp3":
                path = Utils.url2path(t.fileurl)
                dcue = self.__get_mp3_offset(path)
            else:
                continue
                
            if abs(dcue) > 0.0:
                logging.debug("Offsetting cues in '{}' by {} seconds.".format(t.name, dcue))
                for i in range(0, len(t.cues)):
                    t.cues[i].start = t.cues[i].start + dcue
                for j in range(0, len(t.grids)):
                    t.grids[j].start = t.grids[j].start + dcue
                tracks[tid] = t

        return tracks
    
    def __tk_quantize_loops(self, tracks : dict, quantization) -> Library:
        """
        Quantizes loops. 
        @param tracks       Track collection.
        @param quantization Beat amount (or fraction) to quantize to, e.g, 1.0=quarter note, 0.5=eight note.
        """
        def get_bpm_for_cue(cue: Cue, track: Track) -> float:
            for g in reversed(track.grids):
                if cue.start > g.start or math.isclose(cue.start, g.start, rel_tol=1e-3):
                    return g.bpm
            # default to track's overall bpm if a cue was somehow before the first marker:
            return t.bpm

        for tid in tracks:
            t = tracks[tid]    
            for i in range(0, len(t.cues)):
                c = t.cues[i]
                b = get_bpm_for_cue(c, t)
                if b > 0.1:
                    k = float(quantization)*60.0/b
                    n = float(round(c.len/k))
                    t.cues[i].len = n*k

        return tracks

    def __tk_s8_assign_cues_to_pads(self, tracks : dict) -> dict:
        """
        Attribute pads to (a subset) of cues, so that they're visible on the S5/S8.
        Behavior is hard-coded to the author's (me) convenience :)
        """
        for tid in tracks:
            t = tracks[tid]
            pad = 7
            for i in reversed(range(0, len(t.cues))):
                if t.cues[i].num < 0:
                    t.cues[i].num = pad if pad >= 5 else -1
                    # memcues on the last half are FadeOuts; Load otherwise (FadeIns cause Traktor to autoplay)
                    t.cues[i].type = Cue.Type.FadeOut if (t.cues[i].start / t.duration) > 0.5 else Cue.Type.Load
                    pad = pad - 1
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
    rr = RekordboxReader(config)
    tw = TraktorWriter(config)
    oo = OptionalOperations(config)

    lib = rr.read(config["Library"]["RekordboxXmlInput"])
    lib = oo.apply(lib)
    tw.write(lib, config["Library"]["TraktorNmlOutput"])

