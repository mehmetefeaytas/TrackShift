import platform
import spotipy
import requests
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException
import os
from .app_logger import setup_logger
from .utils import fuzzy_match_artist, artist_names_from_tracks
from typing import Union
from datetime import datetime


def generate_description() -> str:
    isodate = datetime.now().strftime("%d/%m/%Y") # Gün/Ay/Yıl formatı
    return f"{isodate} - https://github.com/mehmetefeaytas"


class Spotify:
    def __init__(self):
        self.user_id = os.environ["SPOTIFY_USER_ID"]
        self.spotify_logger = setup_logger(__name__)
        
        # Bilgileri log'a kaydet
        self.spotify_logger.info(f"Spotify bilgileri: User ID: {self.user_id}")
        self.spotify_logger.info(f"Client ID: {os.environ['SPOTIFY_CLIENT_ID']}")
        self.spotify_logger.info(f"Redirect URI: {os.environ['SPOTIFY_REDIRECT_URI']}")
        
        # Sorunları aşmak için özel OAuth yapılandırması
        try:
            # Spotipy'yi basit, yeniden kullanılabilir bir cache ile yapılandır
            auth_manager = SpotifyOAuth(
                client_id=os.environ['SPOTIFY_CLIENT_ID'],
                client_secret=os.environ['SPOTIFY_CLIENT_SECRET'],
                redirect_uri="http://127.0.0.1:8888/callback",  # HTTP protokolü kullan
                scope='playlist-read-collaborative playlist-modify-private playlist-modify-public playlist-read-private ugc-image-upload',
                open_browser=True,
                cache_path=os.path.join(os.path.expanduser("~"), ".spotify_token"),
                show_dialog=True  # Her zaman izin ekranını göster
            )
            
            # Önceki token'ı temizle ve yeni bir oturum başlat
            try:
                if os.path.exists(os.path.join(os.path.expanduser("~"), ".spotify_token")):
                    os.remove(os.path.join(os.path.expanduser("~"), ".spotify_token"))
                    self.spotify_logger.info("Önceki Spotify token temizlendi.")
            except:
                pass
            
            # Kullanıcı için net yönergeler ekle
            print("\n\n=== ÖNEMLİ YÖNERGE ===")
            print("Spotify yetkilendirme sayfası açılacak ve erişim izni vermeniz istenecek.")
            print("Erişim verdikten sonra, yönlendirildiğiniz URL'deki 'code=' parametresini kopyalamanız gerekebilir.")
            print("Eğer boş sayfa veya bağlantı hatası görürseniz, endişelenmeyin.")
            print("Adres çubuğundaki URL'yi kopyalayıp, aşağıya yapıştırın.")
            print("=============================\n")
                
            self.spotify = spotipy.Spotify(auth_manager=auth_manager)
            
            # Bağlantıyı test et
            me = self.spotify.me()
            self.spotify_logger.info(f"Spotify hesabınıza bağlandı: {me['id']}")
            
        except Exception as e:
            self.spotify_logger.error(f"Spotify bağlantısı hatası: {str(e)}")
            self.spotify_logger.error(f"Lütfen Spotify Developer Dashboard'dan Redirect URI'nizi 'http://127.0.0.1:8888/callback' olarak ayarladığınızdan emin olun.")
            raise Exception(f"Spotify bağlantısı kurulamadı. Hata: {str(e)}")

        self.playlist_id = ""
    
    def set_playlist_id(self, playlist_id: str):
        self.playlist_id = playlist_id
        self.spotify_logger.debug(f"Çalma Listesi ID'si ayarlandı: {self.playlist_id}")
    
    def get_user_playlists(self) -> 'list':
        playlists = self.spotify.user_playlists(self.user_id)["items"]
        self.spotify_logger.debug(f"Kullanıcının Çalma Listeleri alındı: {playlists}")
        return playlists

    def create_playlist(self, playlist_name: str, description: str = "") -> str:
        playlist = self.spotify.user_playlist_create(self.user_id, playlist_name, description)
        self.spotify_logger.debug(f"Çalma Listesi oluşturuldu: {playlist}")
        return playlist['id']
    
    def set_playlist_description(self, description: str = "", playlist_id: str = "") -> None:
        if not playlist_id:
            playlist_id = self.playlist_id
        if not description:
            description = generate_description()
        self.spotify.playlist_change_details(playlist_id, description=description)
        self.spotify_logger.debug(f"Çalma Listesi {playlist_id} açıklaması ayarlandı: {description}")
    
    def get_playlist_name(self, playlist_id: str = "") -> str:
        if not playlist_id:
            playlist_id = self.playlist_id
        try:
            playlist = self.spotify.playlist(playlist_id)
            playlist_name = playlist["name"]
            self.spotify_logger.debug(f"Çalma Listesi adı alındı: {playlist_name}")
            return playlist_name
        except SpotifyException as e:
            self.spotify_logger.error(f"Çalma listesi bulunamadı (ID: {playlist_id}): {str(e)}")
            if "404" in str(e):
                self.spotify_logger.error("Çalma listesi ID'si bulunamadı. Lütfen ID'nin doğru olduğundan emin olun.")
            raise
    
    def get_playlist_items(self, playlist_id: str = "", limit: int = 100) -> 'dict':
        if not playlist_id:
            playlist_id = self.playlist_id
        result = self.spotify.playlist_tracks(playlist_id, limit=limit)["items"]
        track_ids = [t["track"]["id"] for t in result]
        self.spotify_logger.debug(f"Çalma Listesi öğeleri alındı: {track_ids}")
        return track_ids
    
    def empty_playlist(self, playlist_id: str = "") -> None:
        if not playlist_id:
            playlist_id = self.playlist_id
        tracks = self.get_playlist_items(playlist_id)
        track_ids = [id for id in tracks]

        if not track_ids:
            self.spotify_logger.debug(f"Çalma Listesi {playlist_id} zaten boş")
            return

        self.spotify.playlist_remove_all_occurrences_of_items(playlist_id, track_ids)
        self.spotify_logger.debug(f"Çalma Listesi {playlist_id} boşaltıldı")

    def get_song_uri(self, artist: str, song_name: str) -> Union['str', None]:
        # Maksimum 3 deneme yap
        max_retries = 3
        retry_delay = 1  # saniye
        
        for attempt in range(max_retries):
            try:
                results = self.spotify.search(f'{song_name} {artist}', type='track', limit=10)
                
                tracks_found = results['tracks']['items']
                
                artist_names = artist_names_from_tracks(tracks_found)
                track_name = f'{artist}'
                fuzzy_match_artist(
                    artist_names=artist_names,
                    track_input=track_name)
                
                if not tracks_found:
                    track_uri = None
                else:
                    track_uri = tracks_found[0]['uri']
                self.spotify_logger.debug(f"Parça URI'si alındı: {track_uri}")
                return track_uri
                
            except requests.exceptions.ConnectionError as e:
                self.spotify_logger.warning(f"Bağlantı hatası ({attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self.spotify_logger.info(f"{retry_delay} saniye bekleyip tekrar deneniyor...")
                    import time
                    time.sleep(retry_delay)
                    # Her denemede bekleme süresini artır
                    retry_delay *= 2
                else:
                    self.spotify_logger.error(f"Maksimum deneme sayısına ulaşıldı. Şarkı aranamadı: {song_name} - {artist}")
                    return None
            
            except SpotifyException as e:
                self.spotify_logger.error(f"Şarkı aranırken Spotify hatası oluştu: {e}")
                return None
            
            except Exception as e:
                self.spotify_logger.error(f"Şarkı aranırken bilinmeyen bir hata oluştu: {e}")
                import traceback
                self.spotify_logger.error(traceback.format_exc())
                return None

    def add_song_to_playlist(self, song_uri: str, playlist_id: str = "") -> bool:
        if not playlist_id:
            playlist_id = self.playlist_id
            
        # Maksimum 3 deneme yap
        max_retries = 3
        retry_delay = 1  # saniye
        
        for attempt in range(max_retries):
            try:
                self.spotify.playlist_add_items(playlist_id, [song_uri])
                self.spotify_logger.debug(f"Şarkı {song_uri} çalma listesine {playlist_id} eklendi")
                return True
                
            except requests.exceptions.ConnectionError as e:
                self.spotify_logger.warning(f"Bağlantı hatası ({attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    self.spotify_logger.info(f"{retry_delay} saniye bekleyip tekrar deneniyor...")
                    import time
                    time.sleep(retry_delay)
                    # Her denemede bekleme süresini artır
                    retry_delay *= 2
                else:
                    self.spotify_logger.error(f"Maksimum deneme sayısına ulaşıldı. Şarkı eklenemedi: {song_uri}")
                    return False
                
            except SpotifyException as e:
                self.spotify_logger.error(f"Şarkı çalma listesine eklenirken Spotify hatası oluştu: {e}")
                return False
                
            except Exception as e:
                self.spotify_logger.error(f"Şarkı çalma listesine eklenirken bilinmeyen bir hata oluştu: {e}")
                import traceback
                self.spotify_logger.error(traceback.format_exc())
                return False
    
    def set_playlist_cover(self, encoded_img: str, playlist_id: str = "") -> bool:
        if not playlist_id:
            playlist_id = self.playlist_id
        try:
            self.spotify.playlist_upload_cover_image(playlist_id, encoded_img)
            self.spotify_logger.debug(f"Çalma Listesi kapağı ayarlandı: {encoded_img}")
            return True
        except SpotifyException as e:
            self.spotify_logger.error(f"Çalma listesi kapağı ayarlanırken hata oluştu: {e}")
            return False

    def _num_playlist_songs(self, playlist_id: str = "") -> Union['int', None]:
        if not playlist_id:
            playlist_id = self.playlist_id
        results = self.spotify.playlist_items(playlist_id, limit=1)
        return results.get("total")
