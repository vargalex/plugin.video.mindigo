import os
from datetime import datetime
from html import escape
# class EpgHelper:


# output
def make_xml_guide(channels : dict, mindigo_epg : list, base_url = "https://mindigtvgo.hu"):
    #Returns the XMLTV as a string.

    #Parameters:
    #    channels (dict):Mindigo Channels json/list as returned by '/sb/public/channel/all'.
    #    mindigo_epg (list):Mindigo EPG json as returned by '/sb/public/epg/channels'.

    #Returns:
    #    make_xml_guide(str):the XMLTV as a string

    xmltv = '''<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE tv SYSTEM "xmltv.dtd" >

<tv source-info-url="%s" source-info-name="MindiGO TV EPG">
''' % (base_url)

    for ch_id, ch in channels.items():
        ch_line = '<channel id="%s@mindigo"><display-name>%s</display-name><icon src="%s%s"></icon></channel>\n' % (ch_id, ch["displayName"], base_url, ch["logoUrl"])
        xmltv += ch_line

    for program in mindigo_epg:
        start = datetime.fromisoformat(program["startTime"].replace('Z',' +00:00')).strftime("%Y%m%d%H%M%S +0000")
        end = datetime.fromisoformat(program["endTime"].replace('Z',' +00:00')).strftime("%Y%m%d%H%M%S +0000")
        title = escape(program["title"])
        desc = escape(program["description"])
        if (desc == ''):
            desc = title
        # or "state" : "CATCHUP"
        catchup_info = 'catchup-id="%s"' % program["vodAssetId"] if channels[program["channelId"]]["tvServices"]["catchupTv"] else ''
        prg_line = '<programme start="%s" channel="%s@mindigo" %s stop="%s"><title>%s</title><desc>%s</desc><icon src="%s%s"/></programme>\n' % (start, program["channelId"], catchup_info, end, title, desc, base_url, program.get("imageUrl"))
        xmltv += prg_line

    xmltv += '</tv>'

    # TODO
    # program["imageUrl"]
    # program["vodAssetId"]
    # program["id"]
    # program["imageUrls"]["channel_logo"]

    return xmltv

def make_m3u(channels:dict, base_url = "https://mindigtvgo.hu"):
    m3u = '#EXTM3U\n'
    for ch_id, ch in channels.items():
        catchup_info = 'catchup="append" catchup-source="&extra={catchup-id}"' if ch["tvServices"]["catchupTv"] else ''
        channel_data = '#EXTINF:-1 %s tvg-id="%s@mindigo" tvg-name="%s" tvg-logo="%s%s" radio="false",%s\nplugin://plugin.video.mindigo/?action=translate_link&id=%s\n\n' % (catchup_info, ch["id"], ch["displayName"], base_url, ch["logoUrl"], ch["displayName"], ch["id"])
        m3u += channel_data
    return m3u


def write_str(dst_dir, file_name:str, xmltv:str):
    path = os.path.join(dst_dir, file_name)
    with open(path, 'w', encoding='utf8') as f:
        f.write(xmltv)
