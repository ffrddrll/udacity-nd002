# -*- coding: utf-8 -*-

import xml.etree.cElementTree as ET
import re
import json
from collections import defaultdict
from pprint import pprint

PROBLEMCHARS = r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]'
CITIES = ["臺北", "台北", "新北", "基隆", "桃園"]
DISTRICTS = ["中正", "大同", "中山", "松山", "大安", "萬華",
             "信義", "士林", "北投", "內湖", "南港", "文山",
             "板橋", "新莊", "中和", "永和", "土城", "樹林",
             "三峽", "鶯歌", "三重", "蘆洲", "五股", "泰山",
             "林口", "淡水", "金山", "八里", "萬里", "三芝",
             "汐止", "深坑", "石碇", "新店", "坪林", "七堵",
             "安樂", "龜山", "蘆竹"]
STREET_TYPE = ["大道", "路", "街", "段", "巷", "弄"]

CITY_PATTERN = r"({})市?".format('|'.join(CITIES))
DISTRICT_PATTERN = r"({})區?".format('|'.join(DISTRICTS))
STREET_PATTERN = r'({})$'.format('|'.join(STREET_TYPE))

# 1st group: city name, 2nd group: district name,
# 3rd group: village name, 4th group: neighborhoods name,
# 5th group: street name, 6th group: street type,
# 7th group: house number, 8th group: floor
ADDRESS_PATTERN = (r"(.+市)?(.+區)?(.+里)?(.+鄰)?"
                   r"(.+({}))(.+號)?(.+樓)?").format('|'.join(STREET_TYPE))


def parse_common_attr(element):
    result = {
        'type': element.tag,
        'id': element.get('id'),
        'edited': {}
    }
    for key in ['user', 'uid', 'timestamp', 'version', 'changeset']:
        result['edited'][key] = element.get(key)
    return result


def fix_city_name(tags):
    if 'addr:city' not in tags:
        return None
    city = tags['addr:city']
    match = re.search(CITY_PATTERN, city)
    if match:
        tags['addr:city'] = match[1] + "市"
    else:
        del tags['addr:city']
    return None


def fix_district_name(tags):
    if 'addr:district' not in tags:
        return None
    district = tags['addr:district']
    match = re.search(DISTRICT_PATTERN, district)
    if match:
        tags['addr:district'] = match[1] + "區"
    else:
        del tags['addr:district']
    return None


def fix_street_name(tags):
    if 'addr:street' not in tags:
        return None
    street = tags['addr:street']
    match = re.search(ADDRESS_PATTERN, street)
    if match and match[5]:
        tags['addr:street'] = match[5]
    else:
        del tags['addr:street']
    return None


def parse_tags(element):
    result = {}
    for tag in element.iter('tag'):
        key = tag.get('k')
        value = tag.get('v')
        if re.search(PROBLEMCHARS, key) is None:
            result[key] = value
    fix_city_name(result)
    # fix_district_name(result)
    fix_street_name(result)
    return result


def parse_node(node):
    result = parse_common_attr(node)
    lat = float(node.get('lat'))
    lon = float(node.get('lon'))
    result['coordinate'] = (lat, lon)
    result['tags'] = parse_tags(node)
    return result


def parse_way(way):
    result = parse_common_attr(way)
    result['node_refs'] = [node.get('ref') for node in way.iter('nd')]
    result['tags'] = parse_tags(way)
    return result


def parse_members(relation):
    result = []
    for member in relation.iter('member'):
        result.append(member.attrib)
    return result


def parse_relation(relation):
    result = parse_common_attr(relation)
    result['members'] = parse_members(relation)
    result['tags'] = parse_tags(relation)
    return result


def process_map_data(filename):
    data = []
    parsers = {
        'node': parse_node,
        'way': parse_way,
        'relation': parse_relation,
    }
    for event, element in ET.iterparse(filename):
        if element.tag in parsers:
            result = parsers[element.tag](element)
            data.append(result)
    json_filename = filename.split('.')[0] + '.json'
    with open(json_filename, 'w') as file_obj:
        json.dump(data, file_obj, separators=(',', ':'))
    print("Number of elements: {}".format(len(data)))
    return None


def print_unexpected_tags(unexpected_tags):
    for key in unexpected_tags:
        unique_values = unexpected_tags[key]
        if list(unique_values.keys()) == [None]:
            continue
        print("Unexpected \"{}\" tag:".format(key))
        pprint(dict(unique_values))
    return None


def audit_pattern(pattern, string):
    match = re.search(pattern, string)
    return None if match else string


def audit_tag(key, value):
    if key == 'addr:city':
        return audit_pattern(CITY_PATTERN[:-1], value)
    elif key == 'addr:district':
        return audit_pattern(DISTRICT_PATTERN[:-1], value)
    elif key == 'addr:street':
        return audit_pattern(STREET_PATTERN, value)
    else:
        return None


def audit_osm(filename):
    unexpected_tags = defaultdict(lambda: defaultdict(int))
    for event, element in ET.iterparse(filename):
        if element.tag not in ['node', 'way', 'relation']:
            continue
        for tag in element.iter('tag'):
            key = tag.get('k')
            result = audit_tag(key, tag.get('v'))
            unexpected_tags[key][result] += 1
    print("## Auditing {} ##".format(filename))
    print_unexpected_tags(unexpected_tags)
    return None


def audit_json(filename):
    unexpected_tags = defaultdict(lambda: defaultdict(int))
    data = None
    with open(filename, 'rb') as file_obj:
        data = json.load(file_obj)
    for element in data:
        for key in element['tags']:
            result = audit_tag(key, element['tags'][key])
            unexpected_tags[key][result] += 1
    print("## Auditing {} ##".format(filename))
    print_unexpected_tags(unexpected_tags)
    return None
