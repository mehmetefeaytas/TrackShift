@echo off
echo YTM2SPT icin cevre degiskenleri ayarlaniyor...

rem Spotify API kimlik bilgilerinizi buraya ekleyin
set SPOTIFY_CLIENT_ID=YOUR_CLIENT_ID_HERE
set SPOTIFY_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
set SPOTIFY_USER_ID=YOUR_SPOTIFY_USERNAME
set SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback

echo Cevre degiskenleri basariyla ayarlandi!
echo Bu degiskenleri kullanmak icin bu komut dosyasini calistirin: '. ./env.bat'
