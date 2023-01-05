# -*- coding: utf-8 -*-
"""
    MindiGO Kodi addon
    Copyright (C) 2019-2021 Mr Dini
    Copyright (C) 2020 ratcashdev

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>
"""
import sys
from time import time

import xbmcaddon
import xbmcgui
from mindigo_client import MindigoClient,ContentVisibilityError
from mrdini.routines import routines
from xbmcplugin import endOfDirectory, setContent
import xbmcvfs
import epg_transform

if sys.version_info[0] == 3:
    from urllib.parse import parse_qsl, quote
else:
    # python2 compatibility
    from urlparse import parse_qsl

utils = routines.Utils(xbmcaddon.Addon())
client = MindigoClient()
__addon__ = xbmcaddon.Addon(id='plugin.video.mindigo')
__addondir__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))


def setupSession():
    if (
        client.session is None
        and utils.get_setting("session") is not None
        and int(time()) - int(utils.get_setting("last_ts") or 0) < int(1200)
    ):
        client.session = utils.get_setting("session")
        utils.set_setting("last_ts", str(int(time())))
        return

    utils.set_setting("session", login())
    utils.set_setting("last_ts", str(int(time())))


def login():
    if not all([utils.get_setting("username"), utils.get_setting("password")]):
        utils.create_notification("Kérlek add meg email címed és jelszavad!")
        utils.open_settings()
        exit(0)

    try:
        response = client.login(
            utils.get_setting("username"), utils.get_setting("password")
        )
        if response.status_code in [400, 404]:
            utils.create_ok_dialog(
                "Bejelentkezésed sikertelen volt. Biztosan jól adtad meg az email címed és jelszavad?"
            )
            utils.open_settings()
            exit(1)
        elif response.status_code != 200:
            utils.create_ok_dialog(
                "Ennek a hibának nem kellett volna előfordulnia. Kérlek jelezd a fejlesztőnek"
                ", hogy az addon hibára futott bejelentkezésnél. A szerver válasza: %i\nEsetleg próbáld újra később, lehet, hogy a szerver túlterhelt."
                % (response.status_code)
            )
            exit(1)
    except RuntimeError as e:
        raise routines.Error(e)
    utils.set_setting("session", client.session)
    return client.session


def main_window():
    routines.add_item(
        *sys.argv[:2],
        name="Élő Csatornakínálat",
        action="channels",
        is_directory=True,
        fanart=utils.fanart,
        icon="https://i.imgur.com/n0AbCQn.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="Bejelentkezési gyorsítótár törlése",
        description="A kiegészítő, a haladó beállításokban megadott időközönként bejelentkezik, majd lementi a kapott bejelentkezési adatokat."
        "Ha valami oknál fogva a kiegészítő nem működik, érdemes az opcióval próbálkozni.",
        action="clear_login",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/RoT6O6r.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="Beállítások",
        description="Addon beállításai",
        action="settings",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/MI42pRz.png"
    )
    routines.add_item(
        *sys.argv[:2],
        name="A kiegészítőről",
        description="Egyéb infók",
        action="about",
        is_directory=False,
        fanart=utils.fanart,
        icon="https://i.imgur.com/bKJK0nc.png"
    )

def create_epg_guide(channels, epg):
    epg_transform.write_str(__addondir__, 'mindigo_xmltv.xml', epg_transform.make_xml_guide(channels, epg))

def create_channel_list(channels):
    epg_transform.write_str(__addondir__, 'channels.m3u8', epg_transform.make_m3u(channels))    


def live_window():
    all_channels = client.get_visible_channels()
    channel_ids = [str(k) for k, v in all_channels.items()]
    channel_list = ",".join(channel_ids)
    epg = client.get_epg(channel_list)
    create_epg_guide(all_channels, epg)
    create_channel_list(all_channels)

    for program in epg:
        if program.get("state") != "LIVE":
            continue
        if utils.get_setting("display_epg") != "2":
            name = "%s[CR][COLOR gray]%s[/COLOR]" % (
                routines.py2_encode(all_channels[program["channelId"]]["displayName"]),
                routines.py2_encode(program["title"]),
            )
        else:
            name = routines.py2_encode(program["title"])

        if program.get("imageUrl"):
            fan_art = "%s%s" % (
                client.web_url,
                routines.py2_encode(program.get("imageUrl")),
            )
        else:
            fan_art = utils.fanart

        routines.add_item(
            *sys.argv[:2],
            name=name,
            description=(routines.py2_encode(program.get("description") or "")),
            action="translate_link",
            icon="%s%s" % (client.web_url, program["imageUrls"]["channel_logo"]),
            id=program["channelId"],
            fanart=fan_art,
            type="video",
            refresh=True,
            is_directory=False,
            is_livestream=True
        )
    setContent(int(sys.argv[1]), "tvshows")

def play_protected_dash(handle, video, _type, **kwargs):
    icon = kwargs.get("icon")
    user_agent = kwargs.get("user_agent", routines.random_uagent())

    listitem = xbmcgui.ListItem(label=video.name)
    listitem.setProperty('inputstream', 'inputstream.adaptive')
    listitem.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    listitem.setMimeType('application/dash+xml')
    listitem.setProperty('inputstream.adaptive.stream_headers', "User-Agent=%s" % user_agent)
   
    license_url = 'https://drm-prod.mindigo.hu/widevine/license?drmToken=%s' % quote(video.drm_token) 
    listitem.setProperty('inputstream.adaptive.license_type','com.widevine.alpha')
    listitem.setProperty('inputstream.adaptive.license_key', license_url + '|Content-Type=application/octet-stream|R{SSM}|')
    
    listitem.setContentLookup(False)
    listitem.setInfo(type=_type, infoLabels={"Title": video.name, "Plot": video.desc})
    xbmc.Player().play(video.url, listitem)

def translate_link(channel_id, vod_asset_id):
    video = {}
    try:
        if vod_asset_id:
            video = client.get_video_play_data(vod_asset_id)
        else:
            video = client.get_channel_play_data(channel_id)
    except ContentVisibilityError as err:
        utils.create_ok_dialog("A kívánt tartalom nem sugározható: %s" % err.message)
        return

    if not video.url:
        utils.create_ok_dialog("A kívánt tartalom nem sugározható.")
        exit()

    play_protected_dash(
        int(sys.argv[1]),
        video,
        "video",
        user_agent=utils.get_setting("user_agent")
    )


if __name__ == "__main__":
    params = dict(parse_qsl(sys.argv[2].replace("?", "")))
    action = params.get("action")
    setupSession()

    if action is None:
        if utils.get_setting("is_firstrun") == "true":
            utils.set_setting("is_firstrun", "false")
            from utils.informations import text

            utils.create_textbox(text % (utils.addon_name, utils.version))
            utils.create_ok_dialog("Kérlek jelentkezz be az addon használatához!")
            utils.open_settings()
        main_window()
        endOfDirectory(int(sys.argv[1]))
    if action == "channels":
        live_window()
        endOfDirectory(int(sys.argv[1]))
    if action == "clear_login":
        utils.set_setting("refresh_token", "")
        utils.set_setting("token_updated_at", "0")
        utils.create_notification("Gyorsítótár sikeresen törölve.")
    if action == "settings":
        utils.open_settings()
    if action == "about":
        from utils.informations import text

        utils.create_textbox(text % (utils.addon_name, utils.version))
    if action == "translate_link":
        translate_link(
            params.get("id"),
            params.get("extra")
        )
