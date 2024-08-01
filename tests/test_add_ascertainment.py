#!/usr/bin/env python3
#coding=utf-8
import pytest
from pathlib import Path
from nexus import NexusReader, NexusWriter

from add_ascertainment.__main__ import get_words, get_characters, parse_word, is_sequential
from add_ascertainment.__main__ import add_ascertainment_words, add_ascertainment_overall
from add_ascertainment.__main__ import create_assumptions, add_assumptions


# fixtures
@pytest.fixture
def taxa():
    return ("ASLIAN_CheqWong", "ASLIAN_JahHut", "ASLIAN_Jahai", "ASLIAN_Kensiw")


@pytest.fixture
def nexus():
    return NexusReader(Path(__file__).parent / 'test_add_ascertainment.nex')


def test_parse_word():
    assert parse_word("One_1") == ("One", "1")
    assert parse_word("One_13") == ("One", "13")
    assert parse_word("One_u_21") == ("One", "u_21")
    assert parse_word("One_u21") == ("One", "u21")
    assert parse_word("One_Hundred_16") == ("One_Hundred", "16")
    assert parse_word("One_Hundred_u_16") == ("One_Hundred", "u_16")
    assert parse_word("One_Hundred_u16") == ("One_Hundred", "u16")
    assert parse_word("Eight_u_3569") == ("Eight", "u_3569")
    assert parse_word("Eight_u3569") == ("Eight", "u3569")
    assert parse_word("correct_true_u_5631") == ("correct_true", "u_5631")
    assert parse_word("correct_true_u5631") == ("correct_true", "u5631")
    assert parse_word("to_tie_up_fasten_u_5685") == ("to_tie_up_fasten", "u_5685")
    assert parse_word("to_tie_up_fasten_u5685") == ("to_tie_up_fasten", "u5685")

    with pytest.raises(ValueError):
        parse_word("Eight_569", "X")


def test_get_words_hand():
    labels = ['hand_1', 'hand_2', 'hand_3']
    words = get_words(labels)
    assert 'hand' in words
    assert words['hand'] == labels


def test_get_words_mixture():
    labels = []
    for word in range(0, 5):
        labels.extend(["word%d_%d" % (word, i) for i in range(0, 10)])
    words = get_words(labels)
    for word in range(0, 5):
        assert "word%d" % word in words
        assert words["word%d" % word] == [
            "word%d_%d" % (word, i) for i in range(0, 10)
        ]


def test_get_words_with_uniques():
    labels = ['hand_1', 'hand_2', 'hand_3', 'hand_u_1']
    words = get_words(labels)
    assert 'hand' in words
    assert words['hand'] == labels


# ascertainment overall
def test_add_ascertainment_overall(taxa, nexus):
    nex_asc = add_ascertainment_overall(nexus)
    for idx, label in nexus.data.charlabels.items():
        for taxon in taxa:
            assert nexus.data.matrix[taxon][idx] == nex_asc.data[label][taxon]
    # check asc char
    for taxon in taxa:
        assert nex_asc.data['_ascertainment'][taxon] == '0'
    
    assert len(nex_asc.data) == nexus.data.nchar + 1


# ascertainment by words
@pytest.fixture
def nexus_ascwords(nexus):
    return add_ascertainment_words(nexus)


def test_words_error_on_nocharacters():
    n = NexusReader.from_string("""
    #NEXUS
    
    Begin data;
    Dimensions ntax=1 nchar=1;
    Format datatype=standard symbols="01" gap=-;
    Matrix
    Harry              1
    ;
    """)
    with pytest.raises(ValueError):
        add_ascertainment_words(n)


def test_error_on_nexuswriter():
    with pytest.raises(TypeError):
        add_ascertainment_words(NexusWriter())
    

def test_error_on_charlabel_with_0(nexus):
    nexus.data.charlabels[6] = 'many_0'
    with pytest.raises(ValueError):
        add_ascertainment_words(nexus)


testdata = [
    ('bodyhairfeathers_0', '0', []), # asc char
    ('bodyhairfeathers_1', '1', ["ASLIAN_CheqWong", "ASLIAN_JahHut", "ASLIAN_Jahai", "ASLIAN_Kensiw"]),
    ('bear_0', '0', []),  # ascertainment
    ('bear_1', '1', ["ASLIAN_Jahai", "ASLIAN_Kensiw"]),
    ('many_0', '0', []),  # ascertainment
    ('many_1', '1', ["ASLIAN_CheqWong"]),
    ('many_2', '1', ["ASLIAN_JahHut", "ASLIAN_Jahai"]),
    ('many_3', '1', ["ASLIAN_Jahai"]),
    ('many_4', '1', ["ASLIAN_Kensiw"]),
    ('many_74', '1', ["ASLIAN_Jahai"]),
]
@pytest.mark.parametrize("key,state,members", testdata)
def test_ascwords_values(key, state, members, nexus_ascwords, taxa):
    assert key in nexus_ascwords.data, "missing %s in .data" % key
    for taxon in taxa:
        if taxon in members:
            assert nexus_ascwords.data[key][taxon] == state


# test that we set to ? if no cognates for the given language & word
def test_ascwords_sets_all_missing(nexus):
    nexus.data.characters['skinbark_1']['ASLIAN_CheqWong'] = '?'
    nexus.data.characters['skinbark_2']['ASLIAN_CheqWong'] = '?'
            
    output = add_ascertainment_words(nexus)
    assert output.data['skinbark_0']["ASLIAN_CheqWong"] == '?'  # no form stored
    assert output.data['skinbark_0']["ASLIAN_Jahai"] == '0'
    assert output.data['skinbark_0']["ASLIAN_Jahai"] == '0'
    assert output.data['skinbark_0']["ASLIAN_Kensiw"] == '0'


# test that one missing character doesn't change the ascertainment
# state add a new char with all missing
def test_one_missing(nexus):
    nexus.data.characters['skinbark_1']['ASLIAN_CheqWong'] = '?'
    nexus.data.characters['skinbark_2']['ASLIAN_CheqWong'] = '1'

    output = add_ascertainment_words(nexus)
    assert output.data['skinbark_0']["ASLIAN_CheqWong"] == '0'
    assert output.data['skinbark_0']["ASLIAN_Jahai"] == '0'
    assert output.data['skinbark_0']["ASLIAN_Jahai"] == '0'
    assert output.data['skinbark_0']["ASLIAN_Kensiw"] == '0'



## Assumptions
def test_is_sequential():
    assert is_sequential([1,2,3,4,5])
    assert is_sequential([3,4,5,6,7])
    assert not is_sequential([1, 3])


def test_get_characters_simple(nexus):
    chars = get_characters(nexus)
    # NOTE characters are zero indexed
    assert chars['bear'] == [0]
    assert chars['bodyhairfeathers'] == [1]
    assert chars['many'] == [2, 3, 4, 5, 6]
    assert chars['skinbark'] == [7, 8]


def test_get_characters_delim(nexus):
    chars = get_characters(nexus, delimiter="a")
    # NOTE characters are zero indexed
    assert chars['be'] == [0]
    assert chars['bodyhairfe'] == [1]
    assert chars['m'] == [2, 3, 4, 5, 6]
    assert chars['skinb'] == [7, 8]


def test_get_characters_error(nexus):
    with pytest.raises(ValueError):
        get_characters(nexus, delimiter="X")


def test_create_assumptions(nexus):
    assumpts = create_assumptions(get_characters(nexus))
    assert assumpts[0].strip() == 'charset bear = 1;'
    assert assumpts[1].strip() == 'charset bodyhairfeathers = 2;'
    assert assumpts[2].strip() == 'charset many = 3-7;'
    assert assumpts[3].strip() == 'charset skinbark = 8-9;'
    assert len(assumpts) == 4


def test_add_assumpts(nexus):
    nex = NexusReader.from_string(add_assumptions(nexus).write())
    assert nex.blocks['assumptions'].block == [
        'begin assumptions;',
        'charset bear = 1;',
        'charset bodyhairfeathers = 2;',
        'charset many = 3-7;',
        'charset skinbark = 8-9;',
        'end;'
    ]


def test_add_assumpts_after_words(nexus):
    nexus = add_ascertainment_words(nexus)
    nex = NexusReader.from_string(add_assumptions(nexus).write())
    assert nex.blocks['assumptions'].block == [
        'begin assumptions;',
        'charset bear = 1-2;',
        'charset bodyhairfeathers = 3-4;',
        'charset many = 5-10;',
        'charset skinbark = 11-13;',
        'end;'
    ]