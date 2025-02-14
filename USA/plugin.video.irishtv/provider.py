# -*- coding: utf-8 -*-
import os
import sys
import re
import random
import socks
import proxyconfig
import unicodedata

from cookielib import Cookie

from loggingexception import LoggingException
from urlparse import urlunparse
import HTMLParser

from rtmp import RTMP

import xbmc
import xbmcgui
import xbmcplugin

from subprocess import Popen, PIPE, STDOUT
import mycgi
import utils

from irishtvplayer import BasePlayer, IrishTVPlayer, PlayerLockException
#import player

countryInfoUrl = u"http://api.hostip.info/country.php"

PLAYFROMSTART = u"playfromstart"
RESUME = u"resume"
DELETERESUME = u"deleteresume"
FORCERESUMEUNLOCK = u"force_resume_unlock"

class Provider(object):

    def __init__(self):
        self.proxy = None
        self.useBitRateSetting = False
        if hasattr(sys.modules["__main__"], "log"):
            self.log = sys.modules["__main__"].log
        else:
            from utils import log
            self.log = log

            self.log("")
        
        #self.player = xbmc.Player

    def SetPlayer(self, player):
        self.player = player

    #def GetPlayer(self):
    #    return BasePlayer() 
    
    def GetPlayer(self, pid, live):
        return BasePlayer() 
    
    def CreateForwardedForIP(self, currentForwardedForIP):
        currentSegments = currentForwardedForIP.split('.')
        
        ipSegment1 = int(float(self.addon.getSetting(u'forward_segment1')))
        ipSegment2 = int(float(self.addon.getSetting(u'forward_segment2')))

        if len(currentSegments) == 4 and int(currentSegments[0]) == ipSegment1 and int(currentSegments[1]) == ipSegment2:
            # Settings haven't changed, return the current ip
            return currentForwardedForIP
        
        forwardedForIP = '%d.%d.%d.%d' % (ipSegment1, ipSegment2, random.randint(0, 255), random.randint(0, 254)) 
 
        return forwardedForIP 

    """
    If there is exactly one parameter then we are showing a provider's root menu
    otherwise we need to look at the other parameters to see what we need to do
    """
    def ExecuteCommand(self, mycgi):
        self.log(u"mycgi.ParamCount(): " + unicode(mycgi.ParamCount()), xbmc.LOGDEBUG)
        self.resumeEnabled = self.addon.getSetting(u'resume_enabled') == u'true'

        (forwardedIP, episodeId, playFromStart, resume, deleteResume, forceResumeUnlock) = mycgi.Params( u'forwardedip', u'episodeId', PLAYFROMSTART, RESUME, DELETERESUME, FORCERESUMEUNLOCK)
        
        IrishTVPlayer.RESUME_FILE = os.path.join( sys.modules["__main__"].ADDON_DATA_FOLDER, self.GetProviderId() + u'player_resume.txt')
        IrishTVPlayer.RESUME_LOCK_FILE = os.path.join(sys.modules["__main__"].ADDON_DATA_FOLDER, self.GetProviderId() + u'player_resume_lock.txt')
        
        if deleteResume:
            IrishTVPlayer.delete_resume_point(deleteResume)
            xbmc.executebuiltin('Container.Refresh')
            return True

        if forceResumeUnlock:
            IrishTVPlayer.force_release_lock()
            return True
            
        if self.httpManager.GetIsForwardedForIP():
             forwardedIP = self.CreateForwardedForIP(forwardedIP)
             
        if forwardedIP <> u'':
            self.httpManager.SetForwardedForIP( forwardedIP )
 
        if self.resumeEnabled:
            if episodeId <> u'' and playFromStart == u'' and resume == u'':
                # Only use default if playFromStart or resume are not explicitly set
                if int(self.addon.getSetting(u'playaction')) == 0:
                    mycgi._GetParamDict()[RESUME] = '1'
 
        if mycgi.ParamCount() > 1:
            return self.ParseCommand(mycgi)
        else:
            return self.ShowRootMenu()
    
    def ShowLocationInfo(self):
        try:
            html = None
            html = self.httpManager.GetWebPageDirect(countryInfoUrl)
    
            self.log(u"Country code: " + html)
        except (Exception) as exception:
            self.log(u"Exception getting country code: " + repr(exception))
            
            
    def initialise(self, httpManager, baseurl, pluginHandle):
        self.baseurl = baseurl
        self.pluginHandle = pluginHandle
        self.addon = sys.modules[u"__main__"].addon
        self.language = sys.modules[u"__main__"].language
        self.log("INIT self.pluginHandle: " + str(self.pluginHandle), xbmc.LOGDEBUG)
        
        self.METHOD_IP_FORWARD = self.language(30370) 
        self.METHOD_PROXY = self.language(30040)
        self.METHOD_PROXY_STREAMS = self.language(30041)
        
        
        self.InitialiseHTTP(httpManager)
        
        return True
        
    def GetProxyConfig(self):

        proxy_server = None
        proxy_type_id = 0
        proxy_port = 8080
        proxy_user = None
        proxy_pass = None
        try:
            proxy_server = self.addon.getSetting(u'proxy_server').decode(u'utf8')
            proxy_type_id = int(self.addon.getSetting(u'proxy_type'))
            proxy_port = int(self.addon.getSetting(u'proxy_port'))
            proxy_user = self.addon.getSetting(u'proxy_user').decode(u'utf8')
            proxy_pass = self.addon.getSetting(u'proxy_pass').decode(u'utf8')
        except ( Exception ) as exception:
            raise exception
    
        if   proxy_type_id == 0: proxy_type = socks.PROXY_TYPE_HTTP_NO_TUNNEL
        elif proxy_type_id == 1: proxy_type = socks.PROXY_TYPE_HTTP
        elif proxy_type_id == 2: proxy_type = socks.PROXY_TYPE_SOCKS4
        elif proxy_type_id == 3: proxy_type = socks.PROXY_TYPE_SOCKS5
    
        proxy_dns = True
    
        if proxy_user == u'':
            proxy_user = None
    
        if proxy_pass == u'':
            proxy_pass = None

        proxyConfig = proxyconfig.ProxyConfig( proxy_type, proxy_server, proxy_port, proxy_dns, proxy_user, proxy_pass)
        
        return proxyConfig
    
        
    def InitialiseHTTP(self, httpManager):
        self.httpManager = httpManager
        self.httpManager.SetDefaultHeaders( self.GetHeaders() )

        proxy_method = self.addon.getSetting(self.GetProviderId() + u'_proxy_method') 
        self.log(u"proxy_method: %s" % proxy_method)
        
        if proxy_method == self.METHOD_PROXY or proxy_method == self.METHOD_PROXY_STREAMS:
            proxyConfig = self.GetProxyConfig()
            self.httpManager.SetProxyConfig( proxyConfig )
        elif proxy_method == self.METHOD_IP_FORWARD:
            self.httpManager.EnableForwardedForIP()

    def GetBitRateSetting(self):
        if self.useBitRateSetting is False:
            return None
        
        bitRates = {
            u"":None,                            #Setting not set, so use default value
            self.language(30070):None,           #Default
            self.language(30071):-1,             #Lowest Available
            self.language(30073):200 * 1024,     #Max 200kps
            self.language(30074):350 * 1024,     #Max 350kps
            self.language(30075):500 * 1024,     #Max 500kps
            self.language(30076):750 * 1024,     #Max 750kps
            self.language(30077):1000 * 1024,    #Max 1000kps
            self.language(30078):1500 * 1024,    #Max 1500kps
            self.language(30079):2000 * 1024,    #Max 2000kps
            self.language(30072):20000 * 1024    #Highest Available
            }

        bitrate_string = unicode(self.addon.getSetting(u'bitrate'))
        
        return bitRates[bitrate_string]


    def GetURLStart(self):
        urlStart = self.baseurl + u'?provider=' + self.GetProviderId() 
        forwardedIP = self.httpManager.GetForwardedForIP()
        if forwardedIP is not None:
            urlStart = urlStart + u'&forwardedip=' + forwardedIP
             
        return urlStart
    
    def GetHeaders(self):
        # Windows 8, Internet Explorer 10
        headers = {
                   'User-Agent' : "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)",
                   'DNT' : '1'
                   }
        return headers

    def GetProviderId(self):
        pass
    
    def ShowRootMenu(self):
        pass
    
    
    def ParseCommand(self, mycgi):
        """
        (pid, deleteresume, force_resume_unlock, playfromstart, playresume) = mycgi.Params( u'pid', u'deleteresume', u'force_resume_unlock', u'playfromstart', u'playresume' )

        if pid:
            pass
#            showDialog = __addon__.getSetting('displaydialog') == 'true'
#            watch(feed, pid, showDialog, __addon__.getSetting('playaction') == "0")
        elif deleteresume:
            IrishTVPlayer.delete_resume_point(deleteresume)
            xbmc.executebuiltin(u'Container.Refresh')
        elif playfromstart:
            pass
#            showDialog = __addon__.getSetting('displaydialog') == 'true'
#            watch(p, playfromstart, showDialog)
        elif playresume:
            pass
#            showDialog = __addon__.getSetting('displaydialog') == 'true'
#            watch(feed, playresume, showDialog, True)
        elif force_resume_unlock:
            player.Player.force_release_lock()
        """
        pass

    def GetRootContextMenuItems(self):
        return None

    def GetAction(self, title):
        actionSetting = self.addon.getSetting( u'select_action' ).decode(u'utf8')
        self.log (u"action: " + actionSetting, xbmc.LOGDEBUG)
    
        # Ask
        if ( actionSetting == self.language(30120) ):
            dialog = xbmcgui.Dialog()
            # Do you want to play or download?    
    
            action = dialog.yesno(title, self.language(30530), u'', u'', self.language(30140),  self.language(30130)) # 1=Play; 0=Download
        # Download
        elif ( actionSetting == self.language(30140) ):
            action = 0
        else:
            action = 1
    
        return action
    
    #==============================================================================
    def AddSocksToRTMP(self, rtmpVar):
        stream_method = self.addon.getSetting(self.GetProviderId() + u'_proxy_method').decode(u'utf8')
        if stream_method == self.METHOD_PROXY_STREAMS:
            proxyConfig = self.GetProxyConfig()
            rtmpVar.setProxyString(proxyConfig.toString())
        
    def PlayOrDownloadEpisode(self, infoLabels, thumbnail, rtmpVar = None, defaultFilename = u'', url = None, subtitles = None, resumeKey = None, resumeFlag = False):
        try:
            action = self.GetAction(infoLabels[u'Title'])
    
            if self.dialog.iscanceled():
                return False
            
            if ( action == 1 ):
                # Play
                # "Preparing to play video"
                self.dialog.update(50, self.language(30085))
                self.Play(infoLabels, thumbnail, rtmpVar, url, subtitles, resumeKey, resumeFlag)
        
            elif ( action == 0 ):
                    # Download
                    # "Preparing to download video"
                self.dialog.update(50, self.language(30086))
                self.Download(rtmpVar, defaultFilename, subtitles)
    
            return True
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            # Error playing or downloading episode %s
            exception.process(self.language(30051) % u'', u'', self.logLevel(xbmc.LOGERROR))
            return False
    
    # If the programme is in multiple parts, then second, etc. parts to the playList
    def AddSegments(self, playList):
        return

    def CreateListItem(self, infoLabels, thumbnail):
        if infoLabels is None:
            self.log (u'Play titleId: Unknown Title')
            listItem = xbmcgui.ListItem(u'Unknown Title')
        else:
            self.log (u'Play titleId: ' + infoLabels[u'Title'])
            listItem = xbmcgui.ListItem(infoLabels[u'Title'])
            listItem.setInfo(u'video', infoLabels)

        if thumbnail is not None:
            listItem.setThumbnailImage(thumbnail)
        
        return listItem

    def Play(self, infoLabels, thumbnail, rtmpVar = None, url = None, subtitles = None, resumeKey = None, resumeFlag = False):
        if url is None:
            url = rtmpVar.getPlayUrl()
            
        if thumbnail is not None:
            listItem = xbmcgui.ListItem(label=infoLabels[u'Title'], iconImage=thumbnail, thumbnailImage=thumbnail, path=url)
            infoLabels[u'thumbnail'] = thumbnail
        else:
            listItem = xbmcgui.ListItem(label=infoLabels[u'Title'], path=url)
        
        infoLabels[u'video_url'] = url
        listItem.setInfo(type=u'Video', infoLabels=infoLabels)

        if self.dialog.iscanceled():
            return False

        try:
            player = self.GetPlayer(pid=resumeKey, live=False)
        except PlayerLockException:
            exception_dialog = xbmcgui.Dialog()
            exception_dialog.ok("Stream Already Playing", "Unable to open stream", " - To continue, stop all other streams (try pressing 'x')[CR] - If you are sure there are no other streams [CR]playing, remove the resume lock (check addon settings -> advanced)")
            return
    
            
        player.resume_and_play( url, listItem, is_tv=True, playresume=resumeFlag )

        """        
        playList=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
        playList.clear()
        
        playList.add(url, listItem)
        player = self.GetPlayer()
        player.play(playList)
        """
        
        self.dialog.close()
        #xbmcplugin.setResolvedUrl(handle=self.pluginHandle, succeeded=True, listitem=listItem)
        if subtitles is not None:
            try:
                self.log (u"Subtitle processing", xbmc.LOGDEBUG)
                subtitleFile = subtitles.GetSubtitleFile()
                player.setSubtitles(subtitleFile)
            except (Exception) as exception:
                if not isinstance(exception, LoggingException):
                    exception = LoggingException.fromException(exception)
            
                # Error getting subtitles
                exception.addLogMessage(self.language(30970))
                exception.process('', '', severity = xbmc.LOGWARNING)


        self.log (u"AddSegments(playList)", xbmc.LOGDEBUG)
        self.AddSegments(player.get_playlist())
        self.log (u"Post AddSegments(playList)", xbmc.LOGDEBUG)
    
        if os.environ.get( "OS" ) != "xbox":
            while player.isPlaying() and not xbmc.abortRequested:
                xbmc.sleep(500)
    
            self.log("Exiting playback loop... (isPlaying %s, abortRequested %s)" % (player.isPlaying(), xbmc.abortRequested), level=xbmc.LOGDEBUG)
            player.set_cancelled()
    
        """
        # Keep script alive so that player can process the onPlayBackStart event
        if player.isPlaying():
            self.log (u"player.isPlaying()", xbmc.LOGDEBUG)
            xbmc.sleep(5000)
        """
        
    def Download(self, rtmpVar, defaultFilename, subtitles = None):
        (rtmpdumpPath, downloadFolder, filename) = self.GetDownloadSettings(defaultFilename)
    
        savePath = os.path.join( downloadFolder, filename )
        rtmpVar.setDownloadDetails(rtmpdumpPath, savePath)
        parameters = rtmpVar.getParameters()

        if subtitles is not None:
            self.log (u"Getting subtitles")

        if subtitles is not None:
            try:
                # Replace '.flv' or other 3 character extension with '.smi'
                subtitleFile = subtitles.GetSubtitleFile(savePath[0:-4] + u'.smi')
            except (Exception) as exception:
                if not isinstance(exception, LoggingException):
                    exception = LoggingException.fromException(exception)
            
                # Error getting subtitles
                exception.addLogMessage(self.language(30970))
                exception.process('', '', severity = xbmc.LOGWARNING)

        if self.dialog.iscanceled():
            return False

        self.dialog.close()

        # Starting downloads 
        self.log (u"Starting download: " + rtmpdumpPath + u" " + parameters)
    
        xbmc.executebuiltin((u'XBMC.Notification(%s, %s)' % ( self.language(30610), filename)).encode(u'utf8'))
    
        self.log(u'"%s" %s' % (rtmpdumpPath, parameters))
        if sys.modules[u"__main__"].get_system_platform() == u'windows':
            p = Popen( parameters, executable=rtmpdumpPath, shell=True, stdout=PIPE, stderr=PIPE )
        else:
            cmdline = u'"%s" %s' % (rtmpdumpPath, parameters)
            p = Popen( cmdline, shell=True, stdout=PIPE, stderr=PIPE )
    
        self.log (u"rtmpdump has started executing", xbmc.LOGDEBUG)
        (stdout, stderr) = p.communicate()
        self.log (u"rtmpdump has stopped executing", xbmc.LOGDEBUG)
    
        stderr = utils.normalize(stderr) 

        if u'Download complete' in stderr:
            # Download Finished!
            self.log (u'stdout: ' + str(stdout), xbmc.LOGDEBUG)
            self.log (u'stderr: ' + str(stderr), xbmc.LOGDEBUG)
            self.log (u"Download Finished!")
            xbmc.executebuiltin((u'XBMC.Notification(%s,%s,2000)' % ( self.language(30620), filename)).encode(u'utf8'))
        else:
            # Download Failed!
            self.log (u'stdout: ' + str(stdout), xbmc.LOGERROR)
            self.log (u'stderr: ' + str(stderr), xbmc.LOGERROR)
            self.log (u"Download Failed!")
            xbmc.executebuiltin((u'XBMC.Notification(%s,%s,2000)' % ( u"Download Failed! See log for details", filename)).encode(u'utf8'))

    #==============================================================================
    
    def GetDownloadSettings(self, defaultFilename):
    
        # Ensure rtmpdump has been located
        rtmpdumpPath = self.addon.getSetting(u'rtmpdump_path').decode(u'utf8')
        if ( rtmpdumpPath is u'' ):
            dialog = xbmcgui.Dialog()
            # Download Error - You have not located your rtmpdump executable...
            dialog.ok(self.language(30560),self.language(30570),u'',u'')
            self.addon.openSettings(sys.argv[ 0 ])
            
            rtmpdumpPath = self.addon.getSetting(u'rtmpdump_path').decode('utf8')

        if ( rtmpdumpPath is u'' ):
            return
        
        # Ensure default download folder is defined
        downloadFolder = self.addon.getSetting(u'download_folder').decode('utf8')
        if downloadFolder is '':
            d = xbmcgui.Dialog()
            # Download Error - You have not set the default download folder.\n Please update the self.addon settings and try again.','','')
            d.ok(self.language(30560),self.language(30580),u'',u'')
            self.addon.openSettings(sys.argv[ 0 ])
            
            downloadFolder = self.addon.getSetting(u'download_folder').decode('utf8')

        if downloadFolder is u'':
            return
        
        if ( self.addon.getSetting(u'ask_filename') == u'true' ):
            # Save programme as...
            kb = xbmc.Keyboard( defaultFilename, self.language(30590))
            kb.doModal()
            if (kb.isConfirmed()):
                filename = kb.getText().decode(u'utf8')
            else:
                return
        else:
            filename = defaultFilename
        
        if ( filename.endswith(u'.flv') == False ): 
            filename = filename + u'.flv'
        
        if ( self.addon.getSetting(u'ask_folder') == u'true' ):
            dialog = xbmcgui.Dialog()
            # Save to folder...
            downloadFolder = dialog.browse(  3, self.language(30600), u'files', u'', False, False, downloadFolder ).decode('utf8')

        if ( downloadFolder == u'' ):
            return
        
        return (rtmpdumpPath, downloadFolder, filename)

    def logLevel(self, requestLevel):
        if self.lastPageFromCache():
            return xbmc.LOGDEBUG
        
        return requestLevel
    
    def lastPageFromCache(self):
        if self.httpManager.getGotFromCache() and self.httpManager.getGotFromCache():
            return True
        
        return False
    
    #==============================================================================
    # thumbnail must be unicode, not str
    def GetThumbnailPath(self, thumbnail):
        thumbnail = unicodedata.normalize(u'NFKD', thumbnail).encode(u'ASCII', u'ignore')
        thumbnail = utils.replace_non_alphanum(thumbnail)
        self.log(u"thumbnail: " + thumbnail, xbmc.LOGDEBUG)
        path = os.path.join(sys.modules[u"__main__"].MEDIA_PATH, self.GetProviderId() + u'_' + thumbnail + u'.jpg')
        
        if not os.path.exists(path):
            path = os.path.join(sys.modules[u"__main__"].MEDIA_PATH, self.GetProviderId() + u'.jpg') 

        if self.log is not None:
            self.log(u"GetThumbnailPath: " + path, xbmc.LOGDEBUG)
        return path
    #
    def fullDecode(self, text):
        htmlparser = HTMLParser.HTMLParser()
        text = text.replace(u'&#39;', u"'" )
        text = htmlparser.unescape(text)

        mychr = chr
        myatoi = int
        list = text.split(u'%')
        res = [list[0]]
        myappend = res.append
        del list[0]
        for item in list:
            if item[1:2]:
                try:
                    myappend(unicode(chr(int(item[:2], 16)), u'latin1') + item[2:])
                except:
                    myappend(u'%' + item)
            else:
                myappend(u'%' + item)
        return u"".join(res)
                 
#==============================================================================
    def DoSearch(self):
        self.log(u"", xbmc.LOGDEBUG)
        # Search
        kb = xbmc.Keyboard( u"", self.language(30500) )
        kb.doModal()
        if ( kb.isConfirmed() == False ): return
        query = kb.getText()

        return self.DoSearchQuery( query = query )

    # Download the given url and return the first string that matches the pattern
    def GetStringFromURL(self, url, pattern, maxAge = 20000):
        self.log(u"url '%s', pattern '%s'" % (url, pattern), xbmc.LOGDEBUG)
    
        try:
            data = None
            data = self.httpManager.GetWebPage(url, maxAge)
    
            self.log(u"len(data): " + str(len(data)), xbmc.LOGDEBUG)
    
            return re.search(pattern, data).groups()
        
        except (Exception) as exception:
            if not isinstance(exception, LoggingException):
                exception = LoggingException.fromException(exception)
    
            if data is not None:
                msg = u"url: %s\n\n%s\n\n" % (url, data)
                exception.addLogMessage(msg)
                
            # Error getting web page %s
            exception.addLogMessage(self.language(30050) + u": " + url)
            raise exception
    
    def PlayVideoWithDialog(self, method, parameters):
        try:
            self.dialog = xbmcgui.DialogProgress()
            self.dialog.create(self.GetProviderId(), self.language(30080))
            
            return method(*parameters)
        finally:
            self.dialog.close()

    def MakeCookie(self, name, value, domain, expires = None):
        return Cookie(
                      version=0, 
                      name=name, 
                      value=value,
                      port=None, 
                      port_specified=False,
                      domain=domain, 
                      domain_specified=(domain is not None), 
                      domain_initial_dot=domain.startswith(u'.'),
                      path=u"/", 
                      path_specified=True,
                      secure=False,
                      expires=expires,
                      discard=False,
                      comment=None,
                      comment_url=None,
                      rest={}
                      )
 
    def ResumeListItem(self, url, title, newListItem, resumeKey):
        menuList = []
        resume, dates_added = IrishTVPlayer.load_resume_file()
        if resumeKey in resume.keys():
            resumeTime = self.ToHMS(resume[resumeKey])
            newTitle = u"%s [I](resumeable %s)[/I] " % (title, resumeTime)
            newListItem.setInfo(u'video', {u'Title': "%s" % newTitle, u'LastPlayed': dates_added[resumeKey]})
            newListItem.setLabel(newTitle)
            cmdDelete = u"XBMC.RunPlugin(%s&%s=%s)" % (self.GetURLStart(), DELETERESUME, resumeKey)
            
            # Play from start
            cmdFromStart = u"XBMC.RunPlugin(%s&%s=1)" % (url, PLAYFROMSTART) 
            cmdResume = u"XBMC.RunPlugin(%s&%s=1)" % (url, RESUME)
            menuList.append((u'Resume from %s' % resumeTime, cmdResume))
            menuList.append((u'Play from start', cmdFromStart))
            menuList.append((u'Remove resume point', cmdDelete))

        cmdForceUnlock = u"XBMC.RunPlugin(%s&%s=1)" % (self.GetURLStart(), FORCERESUMEUNLOCK)
        menuList.append((u'Force unlock resume file', cmdForceUnlock))
        newListItem.addContextMenuItems(menuList)
        #newListItem.addContextMenuItems([(u'Force unlock resume file', cmdForceUnlock)])
        return newListItem
    
    def ToHMS(self, time):
        hours = int(time / 3600)
        mins = int(time / 60) % 60
        secs = int(time) % 60
        return unicode(str.format("{0:02}:{1:02}:{2:02}", hours, mins, secs))


        
class Subtitle(object):
    
    def GetSubtitleFile(self, filename = None):
        return sys.modules[u"__main__"].NO_SUBTITLE_FILE
