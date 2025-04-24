from .spotify import Spotify
from .youtube import YoutubeMusic
from urllib import request
import base64
import requests
import time
import traceback
from .app_logger import setup_logger

# Global değişkenleri tanımlayalım
yt = None
sp = None
ytm2spt_logger = None


def url_to_id(url: str, site: str) -> str:
    if site == "yt":
        for char in ["list=", "list\\="]:
            if char in url:
                return url.split(char)[1].split("&")[0]
        else:
            raise ValueError("Geçerli bir YouTube Çalma Listesi URL'si değil")
    
    elif site == "sp":
        if "playlist/" in url:
            return url.split("playlist/")[1].split("?")[0]
        elif "spotify:playlist:" in url:
            return url.removeprefix("spotify:playlist:")
        else:
            raise ValueError("Geçerli bir Spotify Çalma Listesi URL'si değil")


def get_youtube_playlist_id(youtube_arg: str) -> str:
    for site in ["youtube.com", "youtu.be"]:
        if site in youtube_arg:
            return url_to_id(youtube_arg, "yt")
    return youtube_arg


def get_spotify_playlist_id(spotify_arg: str, spotify_playlist_name: str, create_new: bool, dryrun: bool) -> str:
    if spotify_arg:
        for site in ["spotify.com", "spotify:"]:
            if site in spotify_arg:
                try:
                    return url_to_id(spotify_arg, "sp")
                except ValueError as e:
                    # URL yanlışsa daha açıklayıcı hata mesajı vereceğiz
                    ytm2spt_logger.error(f"Spotify URL'si geçerli değil: {spotify_arg}")
                    raise ValueError(f"Geçerli bir Spotify çalma listesi URL'si değil. Lütfen kontrol edin: {spotify_arg}")
        return spotify_arg
    
    elif spotify_playlist_name:
        if not create_new:
            user_playlists = sp.get_user_playlists()
            for playlist in user_playlists:
                if playlist["name"] == spotify_playlist_name:
                    ytm2spt_logger.info(f"Mevcut çalma listesi bulundu: {playlist['name']} (ID: {playlist['id']})")
                    return playlist["id"]
            ytm2spt_logger.info(f"'{spotify_playlist_name}' adında çalma listesi bulunamadı, yenisi oluşturuluyor")
        playlist_id = sp.create_playlist(spotify_playlist_name)
        ytm2spt_logger.info(f"Yeni çalma listesi oluşturuldu: {spotify_playlist_name} (ID: {playlist_id})")
        return playlist_id
    
    else:
        if not dryrun:
            playlist_name = yt.get_playlist_title()
            ytm2spt_logger.info(f"YouTube çalma listesi adı kullanılarak yeni Spotify çalma listesi oluşturuluyor: {playlist_name}")
            return sp.create_playlist(playlist_name)


def set_yt_thumbnail_as_sp_cover(dryrun: bool = False):
    thumbnail_url = yt.get_playlist_thumbnail()
    if not thumbnail_url:
        return
    request.urlretrieve(thumbnail_url, "thumbnail.jpg")

    if dryrun:
        return

    with open("thumbnail.jpg", "rb") as img:
        encoded_img = base64.b64encode(img.read())
        sp.set_playlist_cover(encoded_img)


def transfer_playlist(youtube_arg, spotify_arg, spotify_playlist_name, youtube_oauth, dryrun, create_new, limit):
    global yt, sp, ytm2spt_logger
    yt = YoutubeMusic(youtube_oauth)
    sp = Spotify()
    ytm2spt_logger = setup_logger(__name__)

    youtube_id = get_youtube_playlist_id(youtube_arg)
    ytm2spt_logger.info(f"YouTube Çalma Listesi ID: {youtube_id}")
    yt.set_playlist_id(youtube_id)
    ytm2spt_logger.info(f"YouTube Çalma Listesi Adı: {yt.get_playlist_title()}")
    
    if dryrun:
        ytm2spt_logger.info("Kuru çalıştırma modu etkin. Spotify'a hiçbir şarkı eklenmeyecek.")
        set_yt_thumbnail_as_sp_cover(dryrun=True)
        ytm2spt_logger.info("YouTube küçük resminden çalma listesi kapağı alındı")
    else:
        if not (spotify_arg or spotify_playlist_name):
            spotify_playlist_name = yt.get_playlist_title()
        spotify_id = get_spotify_playlist_id(spotify_arg, spotify_playlist_name, create_new, dryrun)
        ytm2spt_logger.info(f"Spotify Çalma Listesi ID: {spotify_id}")
        sp.set_playlist_id(spotify_id)
        ytm2spt_logger.info(f"Spotify Çalma Listesi Adı: {sp.get_playlist_name()}")

        try:
            set_yt_thumbnail_as_sp_cover()
            ytm2spt_logger.info("YouTube küçük resminden çalma listesi kapağı ayarlandı")
        except Exception as e:
            ytm2spt_logger.warning(str(e))
            ytm2spt_logger.warning("YouTube küçük resminden çalma listesi kapağı ayarlanamadı")

        if not create_new:
            sp.set_playlist_description()
            ytm2spt_logger.info("Çalma listesi açıklaması güncellendi")

            sp.empty_playlist()
            ytm2spt_logger.info("Mevcut çalma listesi boşaltıldı")

    songs = yt.get_songs_from_playlist(limit)
    ytm2spt_logger.info(f"YouTube Çalma Listesinden {len(songs)} şarkı alındı")
    
    total_songs_added = 0
    total_songs_found = 0
    songs_not_found = []
    connection_errors = 0  # Bağlantı hatası sayısını izleyelim

    for i, song in enumerate(songs, start=1):
        try:
            song_uri = sp.get_song_uri(song.artist, song.title)

            if not song_uri:
                ytm2spt_logger.error(f"{song.artist} - {song.title} bulunamadı!")
                songs_not_found.append(f"{i}. {song.artist} - {song.title}")
                continue
            else:
                total_songs_found += 1
            
            if dryrun:
                continue
            
            was_added = sp.add_song_to_playlist(song_uri)

            if was_added:
                ytm2spt_logger.info(
                    f'{song.artist} - {song.title} çalma listesine eklendi.')
                total_songs_added += 1
                
        except requests.exceptions.ConnectionError as e:
            # Bağlantı hatası durumunda bile devam et
            connection_errors += 1
            ytm2spt_logger.error(f"Bağlantı hatası: {str(e)}")
            ytm2spt_logger.info(f"Şarkı ekleme devam ediyor: {i}/{len(songs)}")
            # Kısa bir süre bekle
            time.sleep(2)
            continue
            
        except Exception as e:
            # Diğer hatalar için de devam et
            ytm2spt_logger.error(f"Şarkı işlenirken hata: {str(e)}")
            ytm2spt_logger.error(traceback.format_exc())
            continue
    
    if not dryrun:
        ytm2spt_logger.info(f'Toplam {len(songs)} şarkıdan {total_songs_added} şarkı eklendi')
        if connection_errors > 0:
            ytm2spt_logger.warning(f"{connection_errors} bağlantı hatası yaşandı")
    else:
        ytm2spt_logger.info(f'Toplam {len(songs)} şarkıdan {total_songs_found} şarkı bulundu')
    
    if songs_not_found:
        ytm2spt_logger.warning(f"Bulunamayan şarkılar:\n{chr(10).join(songs_not_found)}")
    
    # İşlem tamamlandı mesajı
    ytm2spt_logger.info("Aktarım işlemi tamamlandı")
    print("\n=== İŞLEM TAMAMLANDI ===")
    print(f"Toplam {len(songs)} şarkıdan {total_songs_added if not dryrun else total_songs_found} tanesi başarıyla işlendi")
    if connection_errors > 0:
        print(f"Not: İşlem sırasında {connection_errors} bağlantı hatası ile karşılaşıldı, ancak program çalışmaya devam etti")
    print("=========================")