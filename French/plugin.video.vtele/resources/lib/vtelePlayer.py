﻿import os
import sys
import xbmc
import xbmcgui

from scraper import getVideo
from traceback import print_exc
from xbmcaddon import Addon
from vteleapiservice import *

ADDON = Addon( "plugin.video.vtele" )

# set our infolabels
infoLabels = {
    "tvshowtitle": unicode( xbmc.getInfoLabel( "ListItem.TvShowTitle" ), "utf-8" ),
    "title":       unicode( xbmc.getInfoLabel( "ListItem.Title" ),       "utf-8" )
    #"genre":       unicode( xbmc.getInfoLabel( "ListItem.Genre" ),       "utf-8" ),
    #"plot":        unicode( xbmc.getInfoLabel( "ListItem.Plot" ),        "utf-8" ),
    #"Aired":       unicode( xbmc.getInfoLabel( "ListItem.Premiered" ),   "utf-8" ),
    #"mpaa":        unicode( xbmc.getInfoLabel( "ListItem.MPAA" ),        "utf-8" ),
    #"duration":    unicode( xbmc.getInfoLabel( "ListItem.DUration" ),    "utf-8" ),
    #"studio":      unicode( xbmc.getInfoLabel( "ListItem.Studio" ),      "utf-8" ),
    #"cast":        unicode( xbmc.getInfoLabel( "ListItem.Cast" ),        "utf-8" ),
    #"writer":      unicode( xbmc.getInfoLabel( "ListItem.Writer" ),      "utf-8" ),
    #"director":    unicode( xbmc.getInfoLabel( "ListItem.Director" ),    "utf-8" ),
    #"season":      int(     xbmc.getInfoLabel( "ListItem.Season" )    or "-1"    ),
    #"episode":     int(     xbmc.getInfoLabel( "ListItem.Episode" )   or "1"     ),
    #"year":        int(     xbmc.getInfoLabel( "ListItem.Year" )      or "0"     ),
    }
# set our thumbnail
g_thumbnail = unicode( xbmc.getInfoImage( "ListItem.Thumb" ), "utf-8" )
#set our str watched
g_strwatched = xbmc.getInfoLabel( "ListItem.Property(strwatched)" )


def setWatched( listitem ):
    try:
        sys.modules[ 'resources.lib.vtele' ].setWatched( g_strwatched, refresh=False )
        listitem.setInfo( "video", { "playcount": 1 } )
    except: print_exc()


class XBMCPlayer( xbmc.Player ):
    """ Subclass of XBMC Player class.
        Overrides onplayback events, for custom actions.
        but onplayback not work with rtmp ! :(
    """
    def _play( self, url, listitem ):
        xbmc.log( "vtelePlayer: " + url, xbmc.LOGNOTICE )
        self.listitem = listitem
        self.play( url, self.listitem )

    def onPlayBackStarted( self ):
        xbmc.log( "vtelePlayer::onPlayBackStarted", xbmc.LOGNOTICE )

    def onPlayBackEnded( self ):
        xbmc.log( "vtelePlayer::onPlayBackEnded", xbmc.LOGNOTICE )
        setWatched()

    def onPlayBackStopped( self ):
        try: xbmc.log( "Resume: %r" % self.getTime(), xbmc.LOGNOTICE )
        except: pass
        xbmc.log( "vtelePlayer::onPlayBackStopped", xbmc.LOGNOTICE )


class vtelePlayer( XBMCPlayer ):
    def __new__( cls, *args ):
        return XBMCPlayer.__new__( cls, *args )


def playVideo( PID, startoffset=None, strwatched=None, listitem=None ):
    global g_strwatched
    if not g_strwatched and strwatched is not None:
        g_strwatched = strwatched

    #obtenir tous les PID
    #exemple de PID (avant changement) uid: "48172"
    videos_vtele = get_html_source(API_SERVICE_URL + "videos/" + PID)
    videos_vtele = json.loads( videos_vtele ).get( "data" ).get( "playlist" )
    
    playlist = xbmc.PlayList( xbmc.PLAYLIST_VIDEO )
    playlist.clear()
    
    for v in videos_vtele:
        print v["idBC"]
    
        #Obtenir les URLS des PID
        #exemple de PID : idBC: "1834631615001"
            
        #Obtenir l'info sur le serveur de streaming
        #video_json = getVideo( PID )
        video_json = getVideo( v["idBC"] )
        
        video = video_json["videoFullLength"]["url"]
        quality = {'0': 480,'1': 640,'2': 720}
        quality = quality[ADDON.getSetting( "quality" )]
        
        #Ici on recherche le vidéo de meilleure qualité (720p)
        for v in video_json["renditions"]:
            if v["frameHeight"] == quality:
                    video = v["url"]
        
        #set listitem
        #if listitem is None:
        listitem = xbmcgui.ListItem( infoLabels[ "title" ], '', "DefaultVideo.png", g_thumbnail )
        listitem.setInfo( "Video", infoLabels )

        #listitem.setProperty( "PlayPath", playpath )
        listitem.setProperty( "PID", PID )

        if str( startoffset ).isdigit():
            listitem.setProperty( "startoffset", str( startoffset ) ) #in second

        # play media
        #player = vtelePlayer( xbmc.PLAYER_CORE_DVDPLAYER )
        #player._play( rtmp_url, listitem )
        setWatched( listitem )
        #player = xbmc.Player( xbmc.PLAYER_CORE_DVDPLAYER )
        #player.play( video, listitem )
        playlist.add(video, listitem)

    xbmc.Player().play( playlist)
    

if ( __name__ == "__main__" ):
    try:
        # get pid
        PID = sys.argv[ 1 ]
        playVideo( PID )
    except:
        print_exc()

