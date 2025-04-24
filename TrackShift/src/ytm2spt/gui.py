import os
import sys
import json
import traceback
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget\
    , QLabel, QLineEdit, QCheckBox, QSpinBox, QTextEdit, QPushButton\
    , QVBoxLayout, QFormLayout, QHBoxLayout, QDialog, QButtonGroup\
    , QRadioButton, QGroupBox, QMessageBox, QMenuBar, QMenu, QTabWidget\
    , QProgressBar, QListWidget, QListWidgetItem, QDateTimeEdit, QComboBox
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QSettings, QThread, Signal, QDateTime
from PySide6 import QtCore
from ytmusicapi import setup_oauth

from .transfer import transfer_playlist
from .utils import Translator

SETTINGS = QSettings(QSettings.IniFormat, QSettings.UserScope, "YTM2SPT", "config")
YTOAUTH_PATH = os.path.join(os.path.dirname(SETTINGS.fileName()), "oauth.json")


def init_settings():
    keys = SETTINGS.allKeys()
    if "SPOTIFY_USER_ID" not in keys:
        SETTINGS.setValue("SPOTIFY_USER_ID", "")
    if "SPOTIFY_CLIENT_ID" not in keys:
        SETTINGS.setValue("SPOTIFY_CLIENT_ID", "")
    if "SPOTIFY_CLIENT_SECRET" not in keys:
        SETTINGS.setValue("SPOTIFY_CLIENT_SECRET", "")
    if "SPOTIFY_REDIRECT_URI" not in keys:
        SETTINGS.setValue("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    if "language" not in keys:
        SETTINGS.setValue("language", "tr")  # Varsayılan dil Türkçe

    SETTINGS.sync()
    
    if not is_valid_settings():
        settings_dialog = SpotifySettingsDialog()
        settings_dialog.exec()
        if is_valid_settings():
            SETTINGS.sync()
        else:
            SETTINGS.clear()
            exit()


def is_valid_settings():
    return SETTINGS.value("SPOTIFY_USER_ID") != "" \
    and SETTINGS.value("SPOTIFY_CLIENT_ID") != "" \
    and SETTINGS.value("SPOTIFY_CLIENT_SECRET") != "" \
    and SETTINGS.value("SPOTIFY_REDIRECT_URI") != ""


class SpotifySettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Translator.translate("spotify_settings_title"))
        self.setMinimumWidth(350)

        layout = QFormLayout(self)

        # "Daha fazla bilgi için tıkla" kısmını kaldırıyorum
        # info_label = QLabel()
        # info_label.setWordWrap(True)
        # info_label.setText(Translator.translate("more_info"))
        # info_label.setOpenExternalLinks(True)
        # layout.addRow(info_label)

        self.user_id_input = QLineEdit()
        self.user_id_input.setText(SETTINGS.value("SPOTIFY_USER_ID", defaultValue=""))
        # self.user_id_input.setPlaceholderText("Bu e-posta değildir")
        layout.addRow(Translator.translate("user_id"), self.user_id_input)

        self.client_id_input = QLineEdit()
        self.client_id_input.setText(SETTINGS.value("SPOTIFY_CLIENT_ID", defaultValue=""))
        layout.addRow("Client ID", self.client_id_input)

        self.client_secret_input = QLineEdit()
        self.client_secret_input.setText(SETTINGS.value("SPOTIFY_CLIENT_SECRET", defaultValue=""))
        layout.addRow("Client Secret", self.client_secret_input)

        self.redirect_uri_input = QLineEdit()
        self.redirect_uri_input.setText(SETTINGS.value("SPOTIFY_REDIRECT_URI", defaultValue=""))
        layout.addRow(Translator.translate("redirect_uri"), self.redirect_uri_input)

        self.save_button = QPushButton(Translator.translate("save"))
        self.save_button.clicked.connect(self.save_settings)
        layout.addRow(self.save_button)

    def save_settings(self):
        SETTINGS.setValue("SPOTIFY_USER_ID", self.user_id_input.text())
        SETTINGS.setValue("SPOTIFY_CLIENT_ID", self.client_id_input.text())
        SETTINGS.setValue("SPOTIFY_CLIENT_SECRET", self.client_secret_input.text())
        SETTINGS.setValue("SPOTIFY_REDIRECT_URI", self.redirect_uri_input.text())
        if not is_valid_settings():
            QMessageBox.warning(self, Translator.translate("error"), Translator.translate("fill_all_fields"))
            return
        SETTINGS.sync()
        self.close()


class YouTubeSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Translator.translate("youtube_settings_title"))
        self.setMinimumWidth(500)  # Increased width for better readability

        layout = QVBoxLayout(self)

        # Improved information section with better formatting
        info_box = QGroupBox(Translator.translate("information"))
        info_layout = QVBoxLayout(info_box)
        
        info_label = QLabel(Translator.translate("private_playlists_only"))
        info_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(info_label)
        
        help_label = QLabel(Translator.translate("youtube_cookies_help"))
        help_label.setWordWrap(True)
        info_layout.addWidget(help_label)
        
        layout.addWidget(info_box)

        # Cookie input methods in tabs for better organization
        auth_tabs = QTabWidget()
        
        # Tab 1: Manual cookie entry
        cookie_tab = QWidget()
        cookie_layout = QVBoxLayout(cookie_tab)
        
        manual_label = QLabel(Translator.translate("manual_cookie_entry"))
        manual_label.setWordWrap(True)
        cookie_layout.addWidget(manual_label)
        
        # Cookie step-by-step instructions
        steps_label = QLabel(Translator.translate("cookie_steps"))
        steps_label.setWordWrap(True)
        cookie_layout.addWidget(steps_label)
        
        # Cookie input fields
        form_layout = QFormLayout()
        
        self.sid_cookie = QLineEdit()
        self.sid_cookie.setPlaceholderText("xxxxxxxxxxx")
        form_layout.addRow("__Secure-3PSID:", self.sid_cookie)
        
        self.psid_cookie = QLineEdit()
        self.psid_cookie.setPlaceholderText("xxxxxxxxxxx")
        form_layout.addRow("__Secure-3PSIDCC:", self.psid_cookie)
        
        self.papisid_cookie = QLineEdit()
        self.papisid_cookie.setPlaceholderText("xxxxxxxxxxx")
        form_layout.addRow("__Secure-3PAPISID:", self.papisid_cookie)
        
        cookie_layout.addLayout(form_layout)
        
        # Save button with icon or styling
        self.save_cookies_button = QPushButton(Translator.translate("save_cookies"))
        self.save_cookies_button.clicked.connect(self.save_cookies)
        self.save_cookies_button.setStyleSheet("font-weight: bold;")
        cookie_layout.addWidget(self.save_cookies_button)
        
        auth_tabs.addTab(cookie_tab, Translator.translate("manual_cookie_method"))
        
        # Tab 2: OAuth method
        oauth_tab = QWidget()
        oauth_layout = QVBoxLayout(oauth_tab)
        
        oauth_info = QLabel(Translator.translate("oauth_method_info"))
        oauth_info.setWordWrap(True)
        oauth_layout.addWidget(oauth_info)
        
        self.oauth_button = QPushButton(Translator.translate("get_youtube_auth"))
        self.oauth_button.clicked.connect(self.get_youtube_auth)
        self.oauth_button.setStyleSheet("font-weight: bold;")
        oauth_layout.addWidget(self.oauth_button)
        
        oauth_layout.addStretch()
        auth_tabs.addTab(oauth_tab, Translator.translate("oauth_method"))
        
        layout.addWidget(auth_tabs)

        # Status message with better visibility
        status_box = QGroupBox(Translator.translate("status"))
        status_layout = QVBoxLayout(status_box)
        
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.message_label.setStyleSheet("padding: 5px; background-color: #f0f0f0; border-radius: 3px;")
        
        if os.path.exists(YTOAUTH_PATH):
            self.message_label.setText(Translator.translate("youtube_auth_saved") + YTOAUTH_PATH)
            self.message_label.setStyleSheet("padding: 5px; background-color: #e6ffe6; border-radius: 3px;")
        else:
            self.message_label.setText(Translator.translate("youtube_auth_not_found"))
        
        status_layout.addWidget(self.message_label)
        layout.addWidget(status_box)

    # Rest of the methods remain the same
    def save_cookies(self):
        """Kullanıcının girdiği çerezleri kaydeder."""
        try:
            # Çerezlerin boş olup olmadığını kontrol et
            if not self.sid_cookie.text() or not self.psid_cookie.text() or not self.papisid_cookie.text():
                self.message_label.setText(Translator.translate("cookies_empty"))
                return
                
            # ytmusicapi için gerekli format
            headers = {
                'Cookie': f'__Secure-3PSID={self.sid_cookie.text()}; __Secure-3PAPISID={self.papisid_cookie.text()}; __Secure-3PSIDCC={self.psid_cookie.text()}'
            }
            
            with open(YTOAUTH_PATH, 'w') as f:
                json.dump(headers, f, indent=2)
            
            self.message_label.setText(Translator.translate("youtube_auth_saved") + YTOAUTH_PATH)
            self.message_label.setStyleSheet("padding: 5px; background-color: #e6ffe6; border-radius: 3px;")
            print(Translator.translate("youtube_auth_success"))
            QtCore.QTimer.singleShot(2000, self.close)
            
        except Exception as e:
            self.message_label.setText(f"{Translator.translate('error')}: {str(e)}")
            self.message_label.setStyleSheet("padding: 5px; background-color: #ffe6e6; border-radius: 3px;")
            print(traceback.format_exc())
            
    def get_youtube_auth(self):
        try:
            # YouTube OAuth kurulumunu başlat
            setup_oauth(YTOAUTH_PATH)
            
            # Dosya oluşturuldu mu kontrol et
            if os.path.exists(YTOAUTH_PATH):
                self.message_label.setText(Translator.translate("youtube_auth_saved") + YTOAUTH_PATH)
                self.message_label.setStyleSheet("padding: 5px; background-color: #e6ffe6; border-radius: 3px;")
                print(Translator.translate("youtube_auth_success"))
                QtCore.QTimer.singleShot(2000, self.close)
            else:
                self.message_label.setText(Translator.translate("youtube_auth_failed"))
                self.message_label.setStyleSheet("padding: 5px; background-color: #ffe6e6; border-radius: 3px;")
        except Exception as e:
            self.message_label.setText(f"{Translator.translate('error')}: {str(e)}")
            self.message_label.setStyleSheet("padding: 5px; background-color: #ffe6e6; border-radius: 3px;")
            print(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(Translator.translate("main_window_title"))
        self.worker = None  # Worker thread'i sınıf değişkeni olarak tanımlayalım
        self.transfer_history = []  # Transfer geçmişi için liste
        
        # Menü oluşturma
        self.create_menus()
        
        # Ana widget oluşturma ve bir TabWidget ekleyelim
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Tab widget oluşturma
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Ana transfer sekmesi
        transfer_tab = QWidget()
        layout = QVBoxLayout(transfer_tab)
        self.tab_widget.addTab(transfer_tab, Translator.translate("transfer_tab"))
        
        # Geçmiş sekmesi
        history_tab = QWidget()
        history_layout = QVBoxLayout(history_tab)
        self.history_list = QListWidget()
        history_layout.addWidget(QLabel(Translator.translate("transfer_history")))
        history_layout.addWidget(self.history_list)
        self.tab_widget.addTab(history_tab, Translator.translate("history_tab"))
        
        # Zamanlama sekmesi
        schedule_tab = QWidget()
        schedule_layout = QVBoxLayout(schedule_tab)
        schedule_layout.addWidget(QLabel(Translator.translate("scheduled_transfers")))
        
        schedule_form = QFormLayout()
        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # 1 saat sonrası
        self.schedule_datetime.setCalendarPopup(True)
        schedule_form.addRow(Translator.translate("schedule_time"), self.schedule_datetime)
        
        self.schedule_playlist = QComboBox()
        schedule_form.addRow(Translator.translate("select_playlist"), self.schedule_playlist)
        
        self.schedule_button = QPushButton(Translator.translate("add_schedule"))
        self.schedule_button.clicked.connect(self.add_scheduled_transfer)
        
        schedule_layout.addLayout(schedule_form)
        schedule_layout.addWidget(self.schedule_button)
        
        self.scheduled_list = QListWidget()
        schedule_layout.addWidget(self.scheduled_list)
        
        self.tab_widget.addTab(schedule_tab, Translator.translate("schedule_tab"))

        # Settings buttons
        settings_layout = QHBoxLayout()
        self.sp_settings_button = QPushButton(Translator.translate("spotify_settings"))
        self.sp_settings_button.clicked.connect(self.open_spotify_settings)
        settings_layout.addWidget(self.sp_settings_button)

        self.yt_settings_button = QPushButton(Translator.translate("youtube_settings"))
        self.yt_settings_button.clicked.connect(self.open_youtube_settings)
        settings_layout.addWidget(self.yt_settings_button)
        layout.addLayout(settings_layout)
        
        # Yön seçimi için radio butonlar
        direction_group = QGroupBox(Translator.translate("transfer_direction"))
        direction_layout = QHBoxLayout(direction_group)
        self.direction_group = QButtonGroup(self)
        
        self.yt_to_sp_radio = QRadioButton(Translator.translate("youtube_to_spotify"))
        self.sp_to_yt_radio = QRadioButton(Translator.translate("spotify_to_youtube"))
        self.direction_group.addButton(self.yt_to_sp_radio)
        self.direction_group.addButton(self.sp_to_yt_radio)
        
        self.yt_to_sp_radio.setChecked(True)  # Varsayılan
        
        direction_layout.addWidget(self.yt_to_sp_radio)
        direction_layout.addWidget(self.sp_to_yt_radio)
        layout.addWidget(direction_group)
        
        # YouTube
        yt_group = QGroupBox(Translator.translate("youtube_group"))
        yt_layout = QVBoxLayout(yt_group)
        yt_layout.addWidget(QLabel(Translator.translate("playlist_url_or_id")))
        self.yt_input = QLineEdit()
        self.yt_input.textChanged.connect(self.update_command)
        yt_layout.addWidget(self.yt_input)

        self.yt_private_checkbox = QCheckBox(Translator.translate("private_playlist"))
        self.yt_private_checkbox.stateChanged.connect(self.yt_private_toggled)
        yt_layout.addWidget(self.yt_private_checkbox)
        layout.addWidget(yt_group)
        
        # Spotify
        self.sp_group = QGroupBox(Translator.translate("spotify_group"))
        self.sp_group.setCheckable(True)
        self.sp_group.setChecked(False)
        self.sp_group.clicked.connect(self.update_command)
        sp_layout = QVBoxLayout(self.sp_group)

        # Radio buttons for Spotify input choice
        self.spotify_choice_group = QButtonGroup(self)
        self.use_name_radio = QRadioButton(Translator.translate("use_playlist_name"))
        self.use_url_radio = QRadioButton(Translator.translate("use_playlist_url"))
        self.spotify_choice_group.addButton(self.use_name_radio)
        self.spotify_choice_group.addButton(self.use_url_radio)
        sp_layout.addWidget(self.use_name_radio)
        sp_layout.addWidget(self.use_url_radio)
        
        # Spotify input widgets
        self.sp_url_label = QLabel(Translator.translate("playlist_url_or_id"))
        sp_layout.addWidget(self.sp_url_label)
        self.sp_input = QLineEdit()
        self.sp_input.textChanged.connect(self.update_command)
        sp_layout.addWidget(self.sp_input)
        
        self.sp_name_label = QLabel(Translator.translate("playlist_name"))
        sp_layout.addWidget(self.sp_name_label)
        self.spname_input = QLineEdit()
        # self.spname_input.setPlaceholderText("Varsayılan: YouTube'dan")
        self.spname_input.textChanged.connect(self.update_command)
        sp_layout.addWidget(self.spname_input)
        self.create_new_checkbox = QCheckBox(Translator.translate("create_new_playlist"))
        self.create_new_checkbox.stateChanged.connect(self.update_command)
        sp_layout.addWidget(self.create_new_checkbox)
        
        # Connect radio buttons to change visibility
        self.use_url_radio.toggled.connect(self.toggle_spotify_inputs)
        self.use_name_radio.toggled.connect(self.toggle_spotify_inputs)

        layout.addWidget(self.sp_group)

        # Other Options
        self.other_group = QGroupBox(Translator.translate("other_options"))
        self.other_group.setCheckable(True)
        self.other_group.setChecked(False)
        self.other_group.clicked.connect(self.update_command)
        other_layout = QVBoxLayout(self.other_group)
        
        top_options = QHBoxLayout()
        
        # Limit
        self.limit_input = QSpinBox()
        self.limit_input.setRange(0, 1000000)
        self.limit_input.valueChanged.connect(self.update_command)
        limit_layout = QFormLayout()
        limit_layout.addRow(Translator.translate("limit"), self.limit_input)
        top_options.addLayout(limit_layout)
        
        # Dry run checkbox
        self.dryrun_checkbox = QCheckBox(Translator.translate("dry_run"))
        self.dryrun_checkbox.stateChanged.connect(self.update_command)
        top_options.addWidget(self.dryrun_checkbox)
        
        # Mevcut şarkıları koruma
        self.keep_existing_checkbox = QCheckBox(Translator.translate("keep_existing"))
        self.keep_existing_checkbox.stateChanged.connect(self.update_command)
        top_options.addWidget(self.keep_existing_checkbox)
        
        other_layout.addLayout(top_options)
        
        # Şarkı eşleştirme iyileştirmesi
        matching_options = QGroupBox(Translator.translate("matching_options"))
        matching_layout = QVBoxLayout(matching_options)
        
        self.match_title_artist_checkbox = QCheckBox(Translator.translate("match_title_artist"))
        self.match_title_artist_checkbox.setChecked(True)
        matching_layout.addWidget(self.match_title_artist_checkbox)
        
        self.match_fuzzy_checkbox = QCheckBox(Translator.translate("match_fuzzy"))
        matching_layout.addWidget(self.match_fuzzy_checkbox)
        
        self.match_duration_checkbox = QCheckBox(Translator.translate("match_duration"))
        matching_layout.addWidget(self.match_duration_checkbox)
        
        other_layout.addWidget(matching_options)
        
        # Hata toleransı
        error_options = QGroupBox(Translator.translate("error_handling"))
        error_layout = QVBoxLayout(error_options)
        
        self.continue_on_error_checkbox = QCheckBox(Translator.translate("continue_on_error"))
        self.continue_on_error_checkbox.setChecked(True)
        error_layout.addWidget(self.continue_on_error_checkbox)
        
        self.retry_count_input = QSpinBox()
        self.retry_count_input.setRange(0, 10)
        self.retry_count_input.setValue(3)
        retry_layout = QFormLayout()
        retry_layout.addRow(Translator.translate("retry_count"), self.retry_count_input)
        error_layout.addLayout(retry_layout)
        
        other_layout.addWidget(error_options)
        
        layout.addWidget(self.other_group)
        
        # İlerleme çubuğu
        progress_group = QGroupBox(Translator.translate("progress"))
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel(Translator.translate("ready"))
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_group)
        
        # Command
        cmd_group = QGroupBox(Translator.translate("command"))
        cmd_layout = QVBoxLayout(cmd_group)

        # Create text box to display command
        self.cmd_textbox = QTextEdit()
        self.cmd_textbox.setReadOnly(True)
        cmd_layout.addWidget(self.cmd_textbox)
        
        # Çoklu çalma listesi transferi butonu
        multi_transfer_layout = QHBoxLayout()
        self.multi_transfer_button = QPushButton(Translator.translate("multi_transfer"))
        self.multi_transfer_button.clicked.connect(self.show_multi_transfer_dialog)
        multi_transfer_layout.addWidget(self.multi_transfer_button)
        
        # Create button to run the command
        self.run_button = QPushButton(Translator.translate("run_command"))
        self.run_button.clicked.connect(self.run_command)
        multi_transfer_layout.addWidget(self.run_button)
        
        cmd_layout.addLayout(multi_transfer_layout)

        layout.addWidget(cmd_group)

        # Set default selection
        self.use_name_radio.setChecked(True)
        self.toggle_spotify_inputs()
        self.update_command()
    
    def create_menus(self):
        """Menü oluşturan fonksiyon"""
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)
        
        # Dil menüsü
        language_menu = QMenu(Translator.translate("language_menu"), self)
        menubar.addMenu(language_menu)
        
        # Dil seçenekleri ekleme
        for lang_code, lang_name in Translator.LANGUAGES.items():
            lang_action = QAction(lang_name, self)
            lang_action.setCheckable(True)
            # Mevcut dili işaretle
            if lang_code == Translator.get_current_language():
                lang_action.setChecked(True)
            # Eylem tetiklendiğinde dili değiştir
            lang_action.triggered.connect(lambda checked, code=lang_code: self.change_language(code))
            language_menu.addAction(lang_action)
    
    def change_language(self, lang_code):
        """Dili değiştiren fonksiyon"""
        Translator.set_language(lang_code)
        # Update all UI elements with new translations
        self.refresh_ui_translations()
        QMessageBox.information(self, Translator.translate("info"), Translator.translate("language_changed"))
    
    def refresh_ui_translations(self):
        """Tüm arayüz elemanlarını güncel dile göre yeniler"""
        # Window title
        self.setWindowTitle(Translator.translate("main_window_title"))
        
        # Recreate menus with new language
        self.menuBar().clear()
        self.create_menus()
        
        # Settings buttons
        self.sp_settings_button.setText(Translator.translate("spotify_settings"))
        self.yt_settings_button.setText(Translator.translate("youtube_settings"))
        
        # Find all group boxes
        groups = self.findChildren(QGroupBox)
        yt_group = None
        cmd_group = None
        
        # Update group titles
        for group in groups:
            if group == self.sp_group:
                group.setTitle(Translator.translate("spotify_group"))
            elif group == self.other_group:
                group.setTitle(Translator.translate("other_options"))
            elif "YouTube" in group.title() or "Youtube" in group.title():
                group.setTitle(Translator.translate("youtube_group"))
                yt_group = group
            elif Translator.translate("command") in group.title() or "Command" in group.title():
                group.setTitle(Translator.translate("command"))
                cmd_group = group
        
        # YouTube group elements
        if yt_group:
            labels = yt_group.findChildren(QLabel)
            if labels:
                for label in labels:
                    if "URL" in label.text() or "Id" in label.text() or "ID" in label.text():
                        label.setText(Translator.translate("playlist_url_or_id"))
            self.yt_private_checkbox.setText(Translator.translate("private_playlist"))
        
        # Spotify radio buttons and labels
        self.use_name_radio.setText(Translator.translate("use_playlist_name"))
        self.use_url_radio.setText(Translator.translate("use_playlist_url"))
        self.sp_url_label.setText(Translator.translate("playlist_url_or_id"))
        self.sp_name_label.setText(Translator.translate("playlist_name"))
        self.create_new_checkbox.setText(Translator.translate("create_new_playlist"))
        
        # Other options
        forms = self.other_group.findChildren(QFormLayout)
        if forms:
            for form in forms:
                for i in range(form.rowCount()):
                    label = form.itemAt(i, QFormLayout.LabelRole)
                    if label and label.widget() and "Limit" in label.widget().text():
                        label.widget().setText(Translator.translate("limit"))
        
        self.dryrun_checkbox.setText(Translator.translate("dry_run"))
        
        # Run button
        self.run_button.setText(
            Translator.translate("stop_command") 
            if Translator.translate("stop_command") in self.run_button.text() 
            else Translator.translate("run_command")
        )
        
        # Update command text
        self.update_command()
    
    def toggle_spotify_inputs(self):
        use_url = self.use_url_radio.isChecked()
        self.sp_url_label.setVisible(use_url)
        self.sp_input.setVisible(use_url)
        self.sp_name_label.setVisible(not use_url)
        self.spname_input.setVisible(not use_url)
        self.create_new_checkbox.setVisible(not use_url)
        self.update_command()
    
    def update_command(self):
        command = "YTM2SPT"
        
        if self.yt_input.text().strip():
            command += f" -yt \"{self.yt_input.text().strip()}\""
        else:
            command = Translator.translate("youtube_required")
            self.cmd_textbox.setText(command)
            return
        
        if self.sp_group.isChecked():
            if self.use_url_radio.isChecked() and self.sp_input.text().strip():
                command += f" -sp \"{self.sp_input.text().strip()}\""
            elif self.use_name_radio.isChecked() and self.spname_input.text().strip():
                command += f" -spname \"{self.spname_input.text().strip()}\""
        
            if self.use_name_radio.isChecked() and self.create_new_checkbox.isChecked():
                command += " -n"
        
        if self.yt_private_checkbox.isChecked():
            command += f' -ytauth "{YTOAUTH_PATH}"'
        
        if self.other_group.isChecked():
            if self.dryrun_checkbox.isChecked():
                command += " -d"
            
            if self.limit_input.value() > 0:
                command += f" -l {self.limit_input.value()}"
        
        self.cmd_textbox.setText(command)
        
    def run_command(self):
        if Translator.translate("stop_command") in self.run_button.text():
            self.worker.terminate()
            self.run_button.setText(Translator.translate("run_command"))
            return
        else:
            self.run_button.setText(Translator.translate("stop_command"))
        # Get the input values
        youtube_arg = self.yt_input.text().strip()
        if not youtube_arg:
            self.cmd_textbox.setText(Translator.translate("youtube_required"))
            QMessageBox.warning(self, Translator.translate("error"), Translator.translate("error_running_ytm2spt"))
            return
        
        if self.use_url_radio.isChecked():
            spotify_arg = self.sp_input.text().strip()
            spotify_playlist_name = None
        else:
            spotify_arg = None
            spotify_playlist_name = self.spname_input.text().strip()
        
        youtube_oauth = YTOAUTH_PATH if self.yt_private_checkbox.isChecked() else None
        dry_run = self.dryrun_checkbox.isChecked()
        create_new = self.create_new_checkbox.isChecked()
        limit = self.limit_input.value() if self.limit_input.value() > 0 else None

        # Run TrackShift
        self.worker = RunCommandWorker(youtube_arg, spotify_arg, spotify_playlist_name, youtube_oauth, dry_run, create_new, limit)
        self.worker.completed.connect(self.run_finished)
        self.worker.error.connect(self.run_error)
        self.worker.start()

    def run_finished(self):
        QMessageBox.information(self, Translator.translate("info"), Translator.translate("ytm2spt_completed"))
        self.run_button.setText(Translator.translate("run_command"))


    def run_error(self, error):
        self.cmd_textbox.setText(Translator.translate("error_running_command") + error)
        QMessageBox.warning(self, Translator.translate("error"), Translator.translate("error_running_ytm2spt"))
        self.run_button.setText(Translator.translate("run_command"))

    def open_spotify_settings(self):
        settings_dialog = SpotifySettingsDialog(self)
        settings_dialog.exec()

    def open_youtube_settings(self):
        settings_dialog = YouTubeSettingsDialog(self)
        settings_dialog.exec()
    
    def yt_private_toggled(self):
        self.update_command()
        if self.yt_private_checkbox.isChecked():
            if not os.path.exists(YTOAUTH_PATH):
                self.open_youtube_settings()

    def closeEvent(self, event):
        # Pencere kapatılmadan önce çalışan thread'leri düzgün şekilde sonlandıralım
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()  # Thread'in sonlanmasını bekle
        event.accept()

    def add_scheduled_transfer(self):
        """Zamanlanmış transfer ekler"""
        # Mevcut ayarları al
        schedule_time = self.schedule_datetime.dateTime()
        
        # Şu anki zamandan önce mi kontrol et
        if schedule_time <= QDateTime.currentDateTime():
            QMessageBox.warning(self, Translator.translate("error"), 
                               Translator.translate("schedule_future_time"))
            return
        
        # Zamanlama bilgisini listede göster
        item_text = f"{schedule_time.toString('dd.MM.yyyy HH:mm')} - {self.yt_input.text()}"
        self.scheduled_list.addItem(item_text)
        
        QMessageBox.information(self, Translator.translate("info"), 
                              Translator.translate("schedule_added"))
    
    def show_multi_transfer_dialog(self):
        """Çoklu transfer dialog penceresini gösterir"""
        dialog = QDialog(self)
        dialog.setWindowTitle(Translator.translate("multi_transfer"))
        layout = QVBoxLayout(dialog)
        
        # Kaynak listesi
        layout.addWidget(QLabel(Translator.translate("source_playlists")))
        source_list = QListWidget()
        layout.addWidget(source_list)
        
        # Test için örnek ekle
        source_list.addItem("YouTube: Müzik Listem")
        source_list.addItem("Spotify: Favorilerim")
        
        # Hedef listesi
        layout.addWidget(QLabel(Translator.translate("target_playlists")))
        target_list = QListWidget()
        layout.addWidget(target_list)
        
        # Test için örnek ekle
        target_list.addItem("Spotify: Yeni Müzikler")
        
        # Butonlar
        button_layout = QHBoxLayout()
        add_button = QPushButton(Translator.translate("add"))
        run_all_button = QPushButton(Translator.translate("run_all"))
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(run_all_button)
        layout.addLayout(button_layout)
        
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        dialog.exec()


class RunCommandWorker(QThread):
    completed = Signal()
    error = Signal(str)

    def __init__(self, youtube_arg, spotify_arg, spotify_playlist_name, youtube_oauth, dry_run, create_new, limit):
        super().__init__()
        self.youtube_arg = youtube_arg
        self.spotify_arg = spotify_arg
        self.spotify_playlist_name = spotify_playlist_name
        self.youtube_oauth = youtube_oauth
        self.dry_run = dry_run
        self.create_new = create_new
        self.limit = limit
    
    def run(self):
        try:
            # Ortam değişkenlerini ayarla
            os.environ["SPOTIFY_USER_ID"] = SETTINGS.value("SPOTIFY_USER_ID")
            os.environ["SPOTIFY_CLIENT_ID"] = SETTINGS.value("SPOTIFY_CLIENT_ID")
            os.environ["SPOTIFY_CLIENT_SECRET"] = SETTINGS.value("SPOTIFY_CLIENT_SECRET")
            os.environ["SPOTIFY_REDIRECT_URI"] = SETTINGS.value("SPOTIFY_REDIRECT_URI")
            
            # Daha fazla hata ayıklama bilgisi
            print(f"SPOTIFY_USER_ID: {os.environ['SPOTIFY_USER_ID']}")
            print(f"SPOTIFY_REDIRECT_URI: {os.environ['SPOTIFY_REDIRECT_URI']}")
            print(f"YouTube arg: {self.youtube_arg}")
            
            transfer_playlist(self.youtube_arg, self.spotify_arg, self.spotify_playlist_name, self.youtube_oauth, self.dry_run, self.create_new, self.limit)
            self.completed.emit()
        except Exception as e:
            print(f"HATA OLUŞTU: {type(e).__name__}: {str(e)}")
            print(traceback.format_exc())
            self.error.emit(str(e))


def main():
    # Create the application
    app = QApplication(sys.argv)

    # Initialize settings
    init_settings()

    # Create the main window
    window = MainWindow()
    window.setMinimumWidth(400)
    window.show()

    print("TrackShift'ye Hoş Geldiniz!")

    # Run the event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()