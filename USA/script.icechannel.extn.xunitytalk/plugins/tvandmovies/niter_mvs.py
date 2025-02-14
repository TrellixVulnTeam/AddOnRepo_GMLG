'''
    Ice Channel    
'''

from entertainment.plugnplay.interfaces import MovieSource
from entertainment.plugnplay import Plugin
from entertainment import common

class yify(MovieSource):
    implements = [MovieSource]
    
    name = "Niter.tv"
    display_name = "Niter Tv"
    base_url = 'http://niter.tv/'
    source_enabled_by_default = 'true'

    icon = common.notify_icon
    
    
    def GetFileHosts(self, url, list, lock, message_queue): 
        
        import re
        
        from entertainment.net import Net

        net = Net(cached=False)
        content = net.http_GET(url).content
        pic=re.compile('pic=(.+?)</div>').findall (content)[0]
        if '&' in pic:
            pic=pic.split('&')[0]
              
        self.AddFileHost(list, 'HD', url+'|'+pic)
            
                
    def GetFileHostsForContent(self, title, name, year, season, episode, type, list, lock, message_queue):

        from entertainment.net import Net
        import re
        net = Net(cached=False)        
        
        name = self.CleanTextForSearch(name) 

            
        search_term = self.base_url+'search?q='+name.lower().replace(' ','+')

        html=   net.http_GET(search_term,{'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36'}).content
        
        match=re.compile('<figcaption title="(.+?)">.+?href="(.+?)">',re.DOTALL).findall(html)
        
        for NAME , URL  in match:
            name='"%s"' % name.lower()
            NAME='"%s"' % NAME.lower()
            if name in NAME:

                self.GetFileHosts(URL, list, lock, message_queue)
        
        

    def Resolve(self, url):

        import re        
        from entertainment.net import Net
        net = Net(cached=False)
        
        PIC=url.split('|')[1]
        Referer=url.split('|')[0]
        data     = {'url': PIC}
  
        headers  = {'Host':'niter.tv',
                                            'Origin':'http://niter.tv',
                                            'Referer':Referer,'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36'}
        html = net.http_POST('http://niter.tv/player/pk/pk/plugins/player_p2.php', data, headers).content
    
  
        if 'captcha' in html:
            import xbmcgui
            match=re.compile('"captcha":(.+?),"k":"(.+?)"').findall (html)
            cap  =  match[0][0]
            k    =  match[0][1]
            _url_= html = net.http_GET('http://www.google.com/recaptcha/api/challenge?k='+k).content
            challenge=re.compile("challenge : '(.+?)'").findall (html)[0]
            captchaimg = 'https://www.google.com/recaptcha/api/image?c=' + challenge
            img = xbmcgui.ControlImage(550,15,300,57,captchaimg)
            wdlg = xbmcgui.WindowDialog()
            wdlg.addControl(img)
            wdlg.show()
            
            import xbmc
            kb = xbmc.Keyboard('', 'Please enter the text in the image', False)
            kb.doModal()
            capcode = kb.getText()
            if (kb.isConfirmed()):
                userInput = kb.getText()
                if userInput != '': capcode = kb.getText()
                elif userInput == '':
                    common.addon.log(self.name.upper() + ' - Image-Text not entered')
                    common.addon.show_small_popup('[B][COLOR white]' + self.name.upper() + '[/COLOR][/B]', '[COLOR red]Image-Text not entered.[/COLOR]')                
                    return None
            else: return None
            wdlg.close() 
            data     = {'url': PIC,'chall':challenge,'res':capcode,'type':cap}
      
            headers  = {'Host':'niter.tv',
                                                'Origin':'http://niter.tv',
                                                'Referer':Referer,'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36'}
            html = net.http_POST('http://niter.tv/player/pk/pk/plugins/player_p2.php', data, headers).content
        
            match=re.compile('"url":"(.+?)"').findall (html)
            
            for URL in match:
                if not '.png' in URL:
                    if not '.jpg' in URL:
                        return URL                       
            
        elif '"url"' in html:

        
            match=re.compile('"url":"(.+?)"').findall (html)
            
            for URL in match:
                if not '.png' in URL:
                    if not '.jpg' in URL:
                        return URL

        else:
            common.addon.show_small_popup('[B][COLOR white]' + self.name.upper() + '[/COLOR][/B]', '[COLOR red]File Removed From Server[/COLOR]')                    
