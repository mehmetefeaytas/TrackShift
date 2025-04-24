from ytmusicapi import YTMusic
from dataclasses import dataclass
import re
import requests
from .app_logger import setup_logger

@dataclass
class Song:
    artist: str
    title: str


def clean_song_info(song: Song) -> Song:
    artist, title = song.artist, song.title
    title = re.sub(r'\(.*', '', title)          # Parantez ve sonrasını kaldır
    title = re.sub(r'ft.*', '', title)          # 'ft' ve sonrasını kaldır
    title = re.sub(r',.*', '', title)           # Virgül ve sonrasını kaldır
    artist = re.sub(r'\sx\s.*', '', artist)     # ' x ' ve sonrasını kaldır
    artist = re.sub(r'\(.*', '', artist)        # Parantez ve sonrasını kaldır
    artist = re.sub(r'ft.*', '', artist)        # 'ft' ve sonrasını kaldır
    artist = re.sub(r',.*', '', artist)         # Virgül ve sonrasını kaldır
    return Song(artist.strip(), title.strip())  # Baş ve sondaki boşlukları kaldır


class YoutubeMusic:
    def __init__(self, oauth_json: str = None):
        self.playlist_id = ""
        self.playlist = {}
        self.songs = []
        self.yt_logger = setup_logger(__name__)
        
        try:
            # YTMusic API'sini, kimlik doğrulaması olmadan başlatma (herhangi bir çalma listesi için)
            self.ytmusic = YTMusic()
            
            # Youtube URL'inden doğrudan ID'yi parse etmek için bir metod ekleyelim
            self.parse_url_to_id = lambda url: url.split("list=")[1].split("&")[0] if "list=" in url else url
            
            # Özel çalma listeleri için, YouTube ana sitesini kullanacağız, YouTube Music API'yi değil
            if oauth_json:
                self.yt_logger.info(f"Özel çalma listesi erişimi için YouTube API kullanılıyor.")
                self.use_direct_youtube = True
                
                # YouTube için çerezleri oluşturalım - GitHub için bu kısmı temizliyoruz
                self.cookies = {
                    # Kullanıcı kendi çerezlerini doldurmalı
                    "__Secure-3PSID": "YOUR_SID_HERE", 
                    "__Secure-3PAPISID": "YOUR_APISID_HERE"
                }
                
                self.headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/112.0",
                    "Accept-Language": "en-US,en;q=0.5",
                    "X-YouTube-Client-Name": "1",
                    "X-YouTube-Client-Version": "2.20230503.00.00"
                }
                
                self.yt_logger.info("YouTube oturum çerezleri ayarlandı")
            else:
                self.use_direct_youtube = False
                self.yt_logger.info("Sadece herkese açık çalma listeleri kullanılabilir")
                
        except Exception as e:
            self.yt_logger.error(f"YouTube başlatma hatası: {str(e)}")
            print("\n\n=== YOUTUBE HATASI ===")
            print("YouTube API'ye erişilirken bir hata oluştu.")
            print("Lütfen internet bağlantınızı kontrol edin ve tekrar deneyin.")
            print("==================\n")
            raise

    def set_playlist_id(self, playlist_id: str):
        self.playlist_id = self.parse_url_to_id(playlist_id)
        
        if self.use_direct_youtube and ("LL" in self.playlist_id or "LM" in self.playlist_id):
            # Beğendiklerim listesi için YouTube web API'sini kullanın
            self.playlist = self.__fetch_youtube_liked_playlist()
        else:
            # Diğer listeler için YTMusic API'sini kullanın
            self.playlist = self.__fetch_playlist()
            
        self.songs = []

    def __fetch_youtube_liked_playlist(self) -> dict:
        """
        YouTube beğendiklerim listesini doğrudan YouTube web sitesinden alır
        """
        self.yt_logger.info(f"Özel çalma listesi alınıyor (ID: {self.playlist_id})")
        
        try:
            # YouTube çalma listesi URL'si
            url = f"https://www.youtube.com/playlist?list={self.playlist_id}"
            
            # İsteği gönder
            response = requests.get(url, cookies=self.cookies, headers=self.headers)
            response.raise_for_status()
            
            # Daha fazla bilgi loglamak için HTML içeriğini kontrol edelim
            html_content = response.text
            content_length = len(html_content)
            self.yt_logger.info(f"YouTube sayfası alındı, içerik uzunluğu: {content_length} karakter")
            
            # Çalma listesi başlığını HTML'den çıkart
            title_match = re.search(r'<title>([^<]*)</title>', html_content)
            title = title_match.group(1).replace(" - YouTube", "") if title_match else "Beğenilen Videolar"
            self.yt_logger.info(f"Çalma listesi başlığı: {title}")
            
            # İçeriğin bir kısmını alalım ve debug için loglamasını yapalım
            sample = html_content[:500] + "..." + html_content[-500:]
            self.yt_logger.debug(f"HTML örneği: {sample}")
            
            # YÖNTEM 1: YouTube'un JSON verilerini çıkarmayı deneyelim
            tracks = self._extract_videos_json_method(html_content)
            
            # YÖNTEM 2: Eğer YÖNTEM 1 başarısız olduysa ve hiç parça bulunamadıysa, direkt HTML parsing deneyelim
            if not tracks:
                self.yt_logger.warning("YÖNTEM 1 başarısız oldu, YÖNTEM 2 deneniyor...")
                tracks = self._extract_videos_html_method(html_content)
            
            # YÖNTEM 3: Eğer YÖNTEM 2 de başarısız olduysa, çok daha basit bir regex yaklaşımı deneyelim
            if not tracks:
                self.yt_logger.warning("YÖNTEM 2 başarısız oldu, YÖNTEM 3 deneniyor...")
                tracks = self._extract_videos_basic_regex(html_content)
            
            # Yöntemlerin hepsi başarısız olduysa
            if not tracks:
                self.yt_logger.warning("Tüm şarkı çıkarma yöntemleri başarısız oldu.")
                # Bu durumda kullanıcıya uyarı gösterelim, test verileri kullanmayacağız
                print("\n\n=== YOUTUBE UYARISI ===")
                print("Beğendiklerim listesindeki şarkılar alınamadı!")
                print("Lütfen YouTube sayfasındaki şarkıları manuel olarak Spotify'a ekleyin.")
                print("Ya da normal bir YouTube çalma listesi kullanmayı deneyin.")
                print("==================\n")
                # Boş bir liste döndür - test verileri kullanmıyoruz artık
                tracks = []
            
            # Çalma listesi verileri
            playlist_data = {
                "title": title if title != "undefined" else "Beğendiğim Videolar",
                "tracks": tracks,
                "thumbnails": [{"url": "https://www.gstatic.com/youtube/img/web/monochrome/logos/youtube_mono_light.png"}]
            }
            
            self.yt_logger.info(f"Beğendiklerim listesi başarıyla alındı: {len(tracks)} şarkı")
            return playlist_data
        
        except Exception as e:
            self.yt_logger.error(f"Beğendiklerim listesi alınamadı: {str(e)}")
            # Daha fazla hata ayıklama için istisna türünü logla
            import traceback
            self.yt_logger.error(f"Hata detayları: {traceback.format_exc()}")
            # Boş bir liste döndür, test verileri yok
            return {
                "title": "Beğenilen Videolar",
                "tracks": [],
                "thumbnails": [{"url": "https://www.gstatic.com/youtube/img/web/monochrome/logos/youtube_mono_light.png"}]
            }
    
    def _extract_videos_json_method(self, html_content):
        """JSON verilerini çıkararak videoları almaya çalışır"""
        tracks = []
        try:
            # YouTube'un yeni formatı için JSON verilerini çıkartalım
            initial_data_match = re.search(r'var\s+ytInitialData\s*=\s*({.+?})(?:;|</script>)', html_content, re.DOTALL)
            
            if not initial_data_match:
                self.yt_logger.warning("YouTube sayfasında ytInitialData bulunamadı")
                return []
                
            # ytInitialData'dan verileri ayrıştır
            import json
            
            # Bulunan JSON verilerini ayrıştır
            initial_data_str = initial_data_match.group(1)
            # Hatalı kaçış karakterlerini düzelt
            initial_data_str = re.sub(r'\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), initial_data_str)
            
            initial_data = json.loads(initial_data_str)
            
            # Olası JSON yollarını deneyelim
            paths = [
                # Yol 1
                lambda d: d.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [{}])[0].get("tabRenderer", {}).get("content", {}).get("sectionListRenderer", {}).get("contents", [{}])[0].get("itemSectionRenderer", {}).get("contents", [{}])[0].get("playlistVideoListRenderer", {}).get("contents", []),
                
                # Yol 2
                lambda d: d.get("contents", {}).get("twoColumnBrowseResultsRenderer", {}).get("tabs", [{}])[0].get("tabRenderer", {}).get("content", {}).get("richGridRenderer", {}).get("contents", []),
                
                # Yol 3
                lambda d: d.get("contents", {}).get("twoColumnWatchNextResults", {}).get("playlist", {}).get("playlist", {}).get("contents", [])
            ]
            
            # Her yolu deneyelim
            contents = None
            for path_func in paths:
                contents = path_func(initial_data)
                if contents:
                    self.yt_logger.info(f"JSON veri yolu bulundu: {len(contents)} video öğesi")
                    break
            
            if not contents:
                self.yt_logger.warning("JSON içinde video içeriği bulunamadı")
                return []
            
            # Çalma listesi verilerini oluştur
            for item in contents:
                # Olası key'leri kontrol edelim
                if "playlistVideoRenderer" in item:
                    video_data = item["playlistVideoRenderer"]
                    # Video başlığını al
                    title = video_data.get("title", {}).get("runs", [{}])[0].get("text", "")
                    # Kanal adını al
                    channel = video_data.get("shortBylineText", {}).get("runs", [{}])[0].get("text", "")
                elif "videoRenderer" in item:
                    video_data = item["videoRenderer"]
                    # Video başlığını al
                    title = video_data.get("title", {}).get("runs", [{}])[0].get("text", "")
                    # Kanal adını al
                    channel = video_data.get("ownerText", {}).get("runs", [{}])[0].get("text", "")
                elif "gridVideoRenderer" in item:
                    video_data = item["gridVideoRenderer"]
                    # Video başlığını al
                    title = video_data.get("title", {}).get("runs", [{}])[0].get("text", "")
                    # Kanal adını al
                    channel = video_data.get("shortBylineText", {}).get("runs", [{}])[0].get("text", "")
                else:
                    continue
                
                if title and channel:
                    tracks.append({
                        "title": title,
                        "artists": [{"name": channel}]
                    })
            
            self.yt_logger.info(f"JSON yöntemiyle {len(tracks)} şarkı bulundu")
            return tracks
            
        except Exception as e:
            self.yt_logger.error(f"JSON çıkarma yöntemi başarısız oldu: {str(e)}")
            return []
    
    def _extract_videos_html_method(self, html_content):
        """HTML içeriğinden videoları doğrudan çıkarmaya çalışır"""
        tracks = []
        try:
            # Video başlıklarını ve kanal adlarını eşleştirelim
            # Yöntem 1: videoRenderer sınıfı üzerinden
            video_blocks = re.findall(r'videoRenderer"[^}]*?"videoId":"([^"]+)"[^}]*?"title"[^}]*?"text":"([^"]+)"[^}]*?"ownerText"[^}]*?"text":"([^"]+)"', html_content)
            
            self.yt_logger.info(f"HTML yöntem 1 ile {len(video_blocks)} video bulundu")
            
            for video_id, title, channel in video_blocks:
                tracks.append({
                    "title": title,
                    "artists": [{"name": channel}]
                })
            
            # Eğer bu yöntem yeterli video bulamadıysa başka bir yöntem deneyelim
            if len(tracks) < 5:
                # Yöntem 2: a etiketleri ve span etiketleri üzerinden
                video_titles = re.findall(r'<a[^>]*?id="video-title"[^>]*?title="([^"]+)"', html_content)
                video_channels = re.findall(r'<a[^>]*?class="yt-simple-endpoint style-scope yt-formatted-string"[^>]*?>([^<]+)</a>', html_content)
                
                self.yt_logger.info(f"HTML yöntem 2 ile {len(video_titles)} başlık, {len(video_channels)} kanal adı bulundu")
                
                # Başlık ve kanal sayısı eşit olmayabilir, o yüzden minimum sayıyı kullanalım
                for i in range(min(len(video_titles), len(video_channels))):
                    tracks.append({
                        "title": video_titles[i],
                        "artists": [{"name": video_channels[i]}]
                    })
            
            self.yt_logger.info(f"HTML yöntemiyle toplam {len(tracks)} şarkı bulundu")
            return tracks
            
        except Exception as e:
            self.yt_logger.error(f"HTML çıkarma yöntemi başarısız oldu: {str(e)}")
            return []
    
    def _extract_videos_basic_regex(self, html_content):
        """En basit regex yaklaşımı ile video içeriklerini çıkarmayı dener"""
        tracks = []
        try:
            # En basit haliyle video-kanal eşleştirmelerini bulmaya çalışalım
            # İlk olarak yalnızca metin içeriklerini alalım
            content = re.sub(r'<[^>]+>', ' ', html_content)
            
            # YouTube sayfasından potansiyel şarkı-sanatçı eşleştirmelerini çıkaralım
            # Basit kural: Bir satırda "by" kelimesi varsa, öncesi şarkı, sonrası sanatçı olabilir
            lines = content.split('\n')
            potential_songs = []
            
            for i, line in enumerate(lines):
                if " by " in line and len(line.strip()) > 10:
                    parts = line.split(" by ")
                    if len(parts) == 2:
                        title = parts[0].strip()
                        artist = parts[1].strip()
                        if title and artist and len(title) < 100 and len(artist) < 50:
                            potential_songs.append((title, artist))
            
            self.yt_logger.info(f"Basit regex ile {len(potential_songs)} potansiyel şarkı bulundu")
            
            for title, artist in potential_songs:
                tracks.append({
                    "title": title,
                    "artists": [{"name": artist}]
                })
            
            # Eğer hiç şarkı bulunamadıysa, video başlıklarını tek başına aramayı deneyelim
            if not tracks:
                video_titles = re.findall(r'"title":{"runs":\[{"text":"([^"]+)"}]}', html_content)
                self.yt_logger.info(f"Basit video başlığı araması ile {len(video_titles)} başlık bulundu")
                
                for title in video_titles:
                    if title != "Watch later" and title != "İzlenecekler" and len(title) < 100:
                        tracks.append({
                            "title": title,
                            "artists": [{"name": "Unknown Artist"}]
                        })
            
            return tracks
            
        except Exception as e:
            self.yt_logger.error(f"Basit regex yöntemi başarısız oldu: {str(e)}")
            return []
    
    def _get_test_tracks(self):
        """Test şarkıları fonksiyonunu boşalttık"""
        self.yt_logger.warning("Test şarkıları devre dışı bırakıldı")
        return []

    def __fetch_playlist(self) -> dict:
        """
        Normal YouTube Music çalma listesini YTMusic API aracılığıyla alır
        """
        try:
            result = self.ytmusic.get_playlist(self.playlist_id, limit=None)
            return result
        except Exception as e:
            self.yt_logger.error(f"YouTube çalma listesi alınamadı (ID: {self.playlist_id}): {str(e)}")
            if "not found" in str(e).lower() or "bulunamadı" in str(e).lower():
                raise ValueError(f"YouTube çalma listesi bulunamadı (ID: {self.playlist_id}). Lütfen URL veya ID'yi kontrol edin.")
            elif "private" in str(e).lower() or "özel" in str(e).lower():
                raise ValueError(f"Bu özel bir YouTube çalma listesi. Erişmek için 'Özel Çalma Listesi' seçeneğini işaretleyin.")
            raise
    
    def get_songs_from_playlist(self, limit: int = None):
        if limit:
            tracks = self.playlist["tracks"][:limit]
        else:
            tracks = self.playlist["tracks"]
        for track in tracks:
            yt_title = track["title"]
            yt_artist = track["artists"][0]["name"]
            song = clean_song_info(Song(yt_artist, yt_title))
            self.songs.append(song)
        return self.songs

    def get_playlist_title(self):       
        return self.playlist["title"]
    
    def get_playlist_thumbnail(self):
        for thumbnails in reversed(self.playlist["thumbnails"]):
            res = requests.head(thumbnails["url"])
            if int(res.headers['content-length']) < 200*1024:
                return thumbnails["url"]
        self.yt_logger("Çalma Listesi Kapağı olarak kullanılabilecek küçük resim bulunamadı")


if __name__ == "__main__":
    pass
