from thefuzz import process, fuzz
from .app_logger import setup_logger
from PySide6.QtCore import QSettings


utils_logger = setup_logger(__name__)

class Translator:
    """Çoklu dil desteği sağlamak için çevirileri yöneten sınıf"""
    
    # Desteklenen diller
    LANGUAGES = {
        "en": "English",
        "tr": "Türkçe"
    }
    
    # Çeviriler sözlüğü
    TRANSLATIONS = {
        # Ana pencere başlığı
        "main_window_title": {
            "en": "TrackShift",
            "tr": "TrackShift"
        },
        # Menü
        "language_menu": {
            "en": "Language",
            "tr": "Dil"
        },
        # Ayarlar
        "spotify_settings": {
            "en": "Spotify Settings",
            "tr": "Spotify Ayarları"
        },
        "youtube_settings": {
            "en": "YouTube Settings",
            "tr": "YouTube Ayarları"
        },
        # Spotify ayarları penceresi
        "spotify_settings_title": {
            "en": "Spotify Settings",
            "tr": "Spotify Ayarları"
        },
        "user_id": {
            "en": "User ID",
            "tr": "Kullanıcı ID"
        },
        "redirect_uri": {
            "en": "Redirect URI",
            "tr": "Yönlendirme URI"
        },
        "save": {
            "en": "Save",
            "tr": "Kaydet"
        },
        "error": {
            "en": "Error",
            "tr": "Hata"
        },
        "fill_all_fields": {
            "en": "Please fill all fields",
            "tr": "Lütfen tüm alanları doldurun"
        },
        # YouTube ayarları penceresi
        "youtube_settings_title": {
            "en": "YouTube Settings",
            "tr": "YouTube Ayarları"
        },
        "private_playlists_only": {
            "en": "Required only for private playlists",
            "tr": "Sadece özel çalma listeleri için gereklidir"
        },
        "browser_cookies": {
            "en": "We will use browser cookies for authentication.\n\nFor Brave users: Press F12 to open the dev tools, go to the 'Application' tab, navigate to 'Cookies' > 'https://www.youtube.com' on the left and find the cookies.",
            "tr": "Kimlik doğrulaması için tarayıcı çerezlerini kullanacağız.\n\nBrave kullanıcıları için: F12 tuşuna basarak geliştirici araçlarını açın, 'Application' sekmesine geçin, sol tarafta 'Cookies' > 'https://www.youtube.com' yolunu izleyin ve çerezleri bulun."
        },
        "get_youtube_auth": {
            "en": "Get YouTube Authentication",
            "tr": "YouTube Kimlik Doğrulaması Al"
        },
        "youtube_auth_not_found": {
            "en": "YouTube authentication not found",
            "tr": "YouTube kimlik doğrulaması bulunamadı"
        },
        "youtube_auth_saved": {
            "en": "YouTube authentication saved to: ",
            "tr": "YouTube kimlik doğrulaması şuraya kaydedildi: "
        },
        "youtube_auth_success": {
            "en": "\n=== YouTube Authentication Successful ===\nYour cookies have been saved successfully. You can now access private playlists.\nExample: Your Liked videos playlist (https://www.youtube.com/playlist?list=LL)\n=========================================\n",
            "tr": "\n=== YouTube Kimlik Doğrulaması Başarılı ===\nÇerezleriniz başarıyla kaydedildi. Artık özel çalma listelerine erişebilirsiniz.\nÖrnek: Beğendiklerim listesi (https://www.youtube.com/playlist?list=LL)\n=========================================\n"
        },
        # YouTube çerezleri için yeni çeviriler
        "youtube_cookies_help": {
            "en": "To access private YouTube playlists, you need to provide your YouTube cookies. There are two ways to do this:",
            "tr": "Özel YouTube çalma listelerine erişmek için YouTube çerezlerinizi sağlamanız gerekiyor. Bunu yapmanın iki yolu var:"
        },
        "cookie_input_methods": {
            "en": "YouTube Cookie Methods",
            "tr": "YouTube Çerez Yöntemleri"
        },
        "manual_cookie_entry": {
            "en": "You can manually enter your YouTube cookies. To get these, go to YouTube Music, open developer tools (F12), go to Application tab > Cookies > https://music.youtube.com and find these cookies:",
            "tr": "YouTube çerezlerinizi manuel olarak girebilirsiniz. Bunları elde etmek için, YouTube Music'e gidin, geliştirici araçlarını açın (F12), Application sekmesine gidip Cookies > https://music.youtube.com yolunu izleyerek şu çerezleri bulun:"
        },
        "save_cookies": {
            "en": "Save Cookies",
            "tr": "Çerezleri Kaydet"
        },
        "alternative_methods": {
            "en": "Or you can use the automatic authentication method (recommended):",
            "tr": "Veya otomatik kimlik doğrulama yöntemini kullanabilirsiniz (önerilir):"
        },
        "cookies_empty": {
            "en": "Please fill all cookie fields",
            "tr": "Lütfen tüm çerez alanlarını doldurun"
        },
        "youtube_auth_failed": {
            "en": "YouTube authentication process failed",
            "tr": "YouTube kimlik doğrulama işlemi başarısız oldu"
        },
        # YouTube Grup Başlığı
        "youtube_group": {
            "en": "YouTube",
            "tr": "YouTube"
        },
        "playlist_url_or_id": {
            "en": "Playlist URL or ID",
            "tr": "Çalma Listesi URL veya ID"
        },
        "private_playlist": {
            "en": "Private Playlist",
            "tr": "Özel Çalma Listesi"
        },
        # Spotify Grup Başlığı
        "spotify_group": {
            "en": "Spotify (configure)",
            "tr": "Spotify (yapılandır)"
        },
        "use_playlist_name": {
            "en": "Use Playlist Name (New or Existing)",
            "tr": "Çalma Listesi Adı Kullan (Yeni veya Mevcut)"
        },
        "use_playlist_url": {
            "en": "Use Playlist URL or ID",
            "tr": "Çalma Listesi URL veya ID Kullan"
        },
        "playlist_name": {
            "en": "Playlist Name (Optional)",
            "tr": "Çalma Listesi Adı (İsteğe Bağlı)"
        },
        "create_new_playlist": {
            "en": "Create New Playlist",
            "tr": "Yeni Çalma Listesi Oluştur"
        },
        # Diğer Seçenekler
        "other_options": {
            "en": "Other Options",
            "tr": "Diğer Seçenekler"
        },
        "limit": {
            "en": "Limit",
            "tr": "Limit"
        },
        "dry_run": {
            "en": "Dry Run",
            "tr": "Kuru Çalıştırma"
        },
        # Komut Bölümü
        "command": {
            "en": "Command",
            "tr": "Komut"
        },
        "run_command": {
            "en": "Run Command",
            "tr": "Komutu Çalıştır"
        },
        "stop_command": {
            "en": "Stop Command",
            "tr": "Komutu Durdur"
        },
        "youtube_required": {
            "en": "YouTube playlist URL or ID is required",
            "tr": "YouTube çalma listesi URL veya ID gereklidir"
        },
        "info": {
            "en": "Information",
            "tr": "Bilgi"
        },
        "ytm2spt_completed": {
            "en": "TrackShift run completed",
            "tr": "TrackShift çalıştırması tamamlandı"
        },
        "error_running_command": {
            "en": "Error occurred while running command: ",
            "tr": "Komut çalıştırılırken hata oluştu: "
        },
        "error_running_ytm2spt": {
            "en": "Error: Failed to run TrackShift",
            "tr": "Hata: TrackShift çalıştırılamadı"
        },
        # Hoşgeldin mesajı
        "welcome": {
            "en": "Welcome to TrackShift!",
            "tr": "TrackShift'e Hoş Geldiniz!"
        }
    }
    
    @staticmethod
    def get_current_language():
        """Mevcut dil ayarını döndürür"""
        settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "TrackShift", "config")
        return settings.value("language", "tr")  # Varsayılan dil olarak Türkçe
    
    @staticmethod
    def set_language(lang_code):
        """Dil ayarını günceller"""
        if lang_code in Translator.LANGUAGES:
            settings = QSettings(QSettings.IniFormat, QSettings.UserScope, "TrackShift", "config")
            settings.setValue("language", lang_code)
            settings.sync()
    
    @staticmethod
    def translate(key):
        """Verilen anahtar için çeviriyi döndürür"""
        lang = Translator.get_current_language()
        
        # Anahtarın çevirisi yoksa
        if key not in Translator.TRANSLATIONS:
            return key
        
        # Dil çevirisi yoksa İngilizce'ye geri dön
        if lang not in Translator.TRANSLATIONS[key]:
            return Translator.TRANSLATIONS[key].get("en", key)
            
        return Translator.TRANSLATIONS[key][lang]


def artist_names_from_tracks(items: dict):
    artist_names = set()

    for idx, track in enumerate(items):
        artist_names.add(track['artists'][0]['name'])
    return artist_names


def fuzzy_match_artist(artist_names: set, track_input: str) -> bool: 
    match_grade = process.extract(track_input, artist_names, limit=3, scorer=fuzz.token_sort_ratio)
    try:
        if match_grade[0][1] > 70:
            print(f'Fuzy match found {match_grade}')
            return True
        else:
            print(f'Fuzy match not found {match_grade}')
            return False
    except IndexError:
        utils_logger.debug('Issue with ingest to fuzzmatch with data')
        utils_logger.debug(f'Track {track_input}')
        utils_logger.debug(f'{artist_names}')
        print("No data provided to matching process")
        return False
