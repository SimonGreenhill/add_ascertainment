#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
import sys
import argparse
from collections import defaultdict

from nexus import NexusWriter, NexusReader
from nexus.handlers import GenericHandler

is_unique = re.compile(r"""^(.*)_(u_?\d+)$""")

def parse_word(label, delimiter="_"):
    """
    Returns a tuple of word, cognate_id.
    """
    if is_unique.match(label):
        return is_unique.findall(label)[0]
    elif delimiter in label:
        return tuple(label.rsplit(delimiter, 1))
    else:
        raise ValueError("No delimiter %s in %s" % (delimiter, label))


def get_words(labels, delimiter="_"):
    chars = defaultdict(list)
    for label in labels:
        word, cogid = parse_word(label, delimiter)
        chars[word].append(label)
    return chars


def get_characters(nex, delimiter="_"):
    chars = {}
    sites = {label: site_id for (site_id, label) in nex.data.charlabels.items()}
    for word, members in get_words(sites.keys(), delimiter).items():
        chars[word] = sorted([sites[m] for m in members])
    return chars



def add_ascertainment_overall(nex, asclabel='_ascertainment'):
    out = NexusWriter()
    # add asc
    for taxon in nex.data.matrix:
        out.add(taxon, asclabel, 0)
    # add data
    for char in nex.data.characters:
        for taxon in nex.data.characters[char]:
            out.add(taxon, char, nex.data.characters[char][taxon])
    return out


def add_ascertainment_words(nex):
    # matrix Lang1   0 0010  0 011000 … Lang2   0 0100  0 001100 … Lang3   0
    # 0010  ? ?????? … ; End;
    #
    # begin assumptions; charset word1 = 1-5; charset word2 = 6-12; ...  end;
    #
    #
    # Note the question mark in the ascertainment column for Lang3, since word2
    # is missing for Lang3.
    #
    # SDollo has its own ascertainment correcting bit, so for SDollo
    # (annoyingly) you do not have to, which means the nexus file does not need
    # the columns to ascertain on (you may only change the assumptions block to
    # reflect that).
    
    def is_missing(v):
        return v in ("?", "-")
    
    # fail if not given a NexusReader object
    if not isinstance(nex, NexusReader):
        raise TypeError("Expecting a NexusReader instance")
    
    labels = [nex.data.charlabels[i] for i in sorted(nex.data.charlabels)]
    
    # fail if no character labels:
    if len(labels) == 0:
        raise ValueError("No character labels! Unable to proceed")
    
    # 1. collect characters, ensure there's no _0's
    words = get_words(labels)
    if any([l for l in labels if l.endswith("_0")]):
        raise ValueError(
            "Label cannot end with _0 as the _0 states will be used for ascertainment"
        )
        
    # making a local copy of nex.data.characters works around SLOW hashing of nex.data.characters
    characters = nex.data.characters.copy()
    out = NexusWriter()
    for word in words:
        chars = sorted(words[word])
        
        # go through each language. Check if it's ALL missing (? or -).
        # If yes, the ascertainment state is ?.
        # if no, the ascertainment state is 0.
        asc_label = "%s_0" % word
        assert asc_label not in out.data
        
        for language in nex.data.taxa:
            values = [characters[char][language] for char in chars]
            for char, value in zip(chars, values):
                out.add(language, char, value)

            if all([is_missing(v) for v in values]):
                out.add(language, asc_label, "?")
            else:
                out.add(language, asc_label, "0")
    return out



def is_sequential(siteids):
    return sorted(siteids) == list(range(min(siteids), max(siteids)+1))


def create_assumptions(chars):
    buffer = []
    for char in sorted(chars):
        siteids = sorted(chars[char])
        # increment by one as these are siteids not character positions
        siteids = [s+1 for s in siteids]
        assert is_sequential(siteids), "Character %s is not sequential (%s)" % (char, sorted(siteids))
        if min(siteids) == max(siteids):
            out = "\tcharset %s = %d;" % (char, min(siteids))
        else:
            out = "\tcharset %s = %d-%d;" % (char, min(siteids), max(siteids))
        buffer.append(out)
    return buffer


def add_assumptions(nex):
    if not isinstance(nex, NexusReader):
        nex = nex._convert_to_reader()
    chars = get_characters(nex)
    nex.blocks['assumptions'] = GenericHandler(name='assumptions', data=create_assumptions(chars))
    return nex




def parse_args(args):
    """
    Parses command line arguments

    Returns a tuple of (mode, inputfile, outputfile)
    """
    return args


def main(args=None):  # pragma: no cover
    parser = argparse.ArgumentParser(description='Makes Nexus File')
    parser.add_argument("mode", help='set mode', choices=("words", "overall"))
    parser.add_argument("filename", help='filename')
    parser.add_argument(
        "-o", "--out", dest='outfile', action='store',
        help="write to outfile"
    )
    args = parser.parse_args()

    if args.mode == 'overall':
        n = add_ascertainment_overall(NexusReader(args.filename))
        n = n._convert_to_reader()  # make sure we have a NexusReader instance
    elif args.mode == 'words':
        n = add_ascertainment_words(NexusReader(args.filename))
        n = add_assumptions(n)
    else:
        raise ValueError("Unknown mode: %s" % args.mode)
    
    if args.outfile:
        n.write_to_file(filename=outfile)
    else:
        print(n.write())
        

