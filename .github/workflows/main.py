import os
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.storage.jsonstore import JsonStore
import requests

class ELkwAppUI(TabbedPanel):
    def __init__(self, **kwargs):
        super(ELkwAppUI, self).__init__(**kwargs)
        self.do_default_tab = False

        self.store = JsonStore('elkw_settings.json')

        # --- TAB 1: DASHBOARD ---
        self.tab_dashboard = TabbedPanelItem(text='Tracker')
        dash_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        dash_layout.add_widget(Label(
            text="🚛 Atlas E-Lkw Tracker", 
            font_size='22sp', 
            size_hint_y=None, 
            height=50,
            color=(0.1, 0.8, 1.0, 1)
        ))

        input_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50, spacing=10)
        self.input_quota = TextInput(text='280.0', multiline=False, hint_text='E-Kontingent (km)')
        self.input_odo = TextInput(text='15420.0', multiline=False, hint_text='Tacho Start')
        input_layout.add_widget(self.input_quota)
        input_layout.add_widget(self.input_odo)
        dash_layout.add_widget(input_layout)

        self.info_label = Label(
            text="Status: Bereit zum Start\nFahrstrecke: 0.0 km\nLenkzeit: 0 Min", 
            font_size='16sp',
            halign='center',
            valign='middle'
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        dash_layout.add_widget(self.info_label)

        self.btn_start = Button(
            text="SCHICHT STARTEN", 
            background_color=(0.1, 0.7, 0.2, 1),
            font_size='18sp',
            size_hint_y=None, 
            height=70
        )
        self.btn_start.bind(on_press=self.start_shift)
        dash_layout.add_widget(self.btn_start)

        self.btn_pause = Button(
            text="PAUSE BESTÄTIGEN", 
            background_color=(0.9, 0.6, 0.1, 1),
            font_size='18sp',
            size_hint_y=None, 
            height=70
        )
        self.btn_pause.bind(on_press=self.confirm_pause)
        dash_layout.add_widget(self.btn_pause)

        self.btn_stop = Button(
            text="SCHICHT BEENDEN", 
            background_color=(0.8, 0.2, 0.2, 1),
            font_size='18sp',
            size_hint_y=None, 
            height=70
        )
        self.btn_stop.bind(on_press=self.stop_shift)
        dash_layout.add_widget(self.btn_stop)

        self.tab_dashboard.add_widget(dash_layout)
        self.add_widget(self.tab_dashboard)

        # --- TAB 2: EINSTELLUNGEN ---
        self.tab_settings = TabbedPanelItem(text='Einstellungen')
        settings_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        settings_layout.add_widget(Label(text="Telegram Bot Konfiguration", font_size='18sp', size_hint_y=None, height=40))

        settings_layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=30))
        saved_token = self.store.get('telegram')['token'] if self.store.exists('telegram') else "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSHfJE"
        self.input_token = TextInput(text=saved_token, multiline=False, hint_text='Bot Token hier eingeben')
        settings_layout.add_widget(self.input_token)

        settings_layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=30))
        saved_chat = self.store.get('telegram')['chat_id'] if self.store.exists('telegram') else "8941361378"
        self.input_chat = TextInput(text=saved_chat, multiline=False, hint_text='Chat ID hier eingeben')
        settings_layout.add_widget(self.input_chat)

        btn_save = Button(
            text="EINSTELLUNGEN SPEICHERN",
            background_color=(0.2, 0.5, 0.8, 1),
            font_size='16sp',
            size_hint_y=None,
            height=60
        )
        btn_save.bind(on_press=self.save_settings)
        settings_layout.add_widget(btn_save)
        settings_layout.add_widget(Label(text=""))

        self.tab_settings.add_widget(settings_layout)
        self.add_widget(self.tab_settings)

        self.shift_active = False
        self.total_km = 0.0
        self.driving_seconds = 0
        self.paused_seconds = 0

    def save_settings(self, instance):
        self.store.put('telegram', token=self.input_token.text.strip(), chat_id=self.input_chat.text.strip())
        print("Einstellungen gespeichert.")

    def send_telegram(self, message):
        if self.store.exists('telegram'):
            token = self.store.get('telegram')['token']
            chat_id = self.store.get('telegram')['chat_id']
            if token and chat_id:
                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
                try:
                    requests.post(url, json=payload, timeout=5)
                except Exception as e:
                    print(f"Telegram Fehler: {e}")

    def start_shift(self, instance):
        if not self.shift_active:
            self.shift_active = True
            try:
                self.quota = float(self.input_quota.text)
                self.tacho = float(self.input_odo.text)
            except ValueError:
                self.quota = 280.0
                self.tacho = 15420.0
            
            self.total_km = 0.0
            self.driving_seconds = 0
            self.paused_seconds = 0
            
            self.info_label.text = f"🟢 SCHICHT LÄUFT\nKontingent: {self.quota} km\nTacho: {self.tacho} km"
            self.send_telegram(f"🚛 *E-Schicht gestartet*\nKontingent: `{self.quota} km`\nTacho: `{self.tacho} km`")

    def confirm_pause(self, instance):
        if self.shift_active:
            self.paused_seconds += 300
            self.info_label.text += "\n☕ Pause manuell bestätigt!"
            self.send_telegram("☕ *Pause bestätigt* (Manuell via App)")

    def stop_shift(self, instance):
        if self.shift_active:
            self.shift_active = False
            self.info_label.text = f"🔴 Schicht beendet.\nGefahren: {self.total_km:.1f} km"
            self.send_telegram(f"📋 *Schicht beendet*\nGefahren: `{self.total_km:.1f} km`")

class ELkwTrackerApp(App):
    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = (0.1, 0.1, 0.1, 1)
        return ELkwAppUI()

if __name__ == '__main__':
    ELkwTrackerApp().run()
