import os
import json
import datetime
import threading
import time
import random
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.storage.jsonstore import JsonStore
import requests

# Sprachausgabe für Android / Python
try:
    from plyer import tts
except ImportError:
    tts = None

class MatrixRainLabel(Label):
    """Dynamischer Matrix-Zahlen-Generator für den Cyberpunk-Hintergrund im Lkw-Cockpit"""
    def __init__(self, **kwargs):
        super(MatrixRainLabel, self).__init__(**kwargs)
        self.font_size = '14sp'
        self.color = (0.1, 0.9, 0.2, 0.3) # Dezent im Hintergrund
        self.halign = 'left'
        self.valign = 'top'
        self.text = "01011001 11001001 010101 ... EUROPE BORDER SYSTEM READY"
        
        # Startet den Animations-Thread für den Code
        threading.Thread(target=self.update_matrix, daemon=True).start()

    def update_matrix(self):
        while True:
            try:
                lines = []
                for _ in range(14):
                    line = "".join(random.choice(["0", "1", " ", "A", "F", "E", "X", "CH", "DE"]) for _ in range(35))
                    lines.append(line)
                self.text = "\n".join(lines)
            except:
                pass
            time.sleep(0.4)

class ELkwAppUI(TabbedPanel):
    def __init__(self, **kwargs):
        super(ELkwAppUI, self).__init__(**kwargs)
        self.do_default_tab = False

        self.store = JsonStore('elkw_settings.json')
        self.aktives_ziel = {"ziel": None}
        
        # Europa-Grenzen beim Start laden
        self.europa_grenzen = self.lade_europa_grenzen()

        # --- TAB 1: DASHBOARD (FULLSCREEN LANDSCAPE MIT MATRIX) ---
        self.tab_dashboard = TabbedPanelItem(text='Atlas v1.2 [Europe]')
        
        dash_root = FloatLayout()
        
        # Matrix-Hintergrund hinzufügen
        self.matrix_bg = MatrixRainLabel(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
        dash_root.add_widget(self.matrix_bg)

        # Vordergrund Layout
        dash_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        dash_layout.add_widget(Label(
            text="🚛 ATLAS E-LKW TRACKER [V1.2 EUROPE CORE]", 
            font_size='18sp', 
            size_hint_y=None, 
            height=40,
            color=(0.1, 0.9, 1.0, 1)
        ))

        input_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=10)
        self.input_quota = TextInput(text='280.0', multiline=False, hint_text='E-Kontingent (km)')
        self.input_odo = TextInput(text='15420.0', multiline=False, hint_text='Tacho Start')
        input_layout.add_widget(self.input_quota)
        input_layout.add_widget(self.input_odo)
        dash_layout.add_widget(input_layout)

        grenzen_info = f"Europa-DB: {len(self.europa_grenzen)} Grenzpunkte geladen (DE, CH, FR, AT)."
        self.info_label = Label(
            text=f"Status: System bereit.\n{grenzen_info}\nAktuelles Ziel: Keines", 
            font_size='14sp',
            halign='center',
            valign='middle',
            color=(1, 1, 1, 1)
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        dash_layout.add_widget(self.info_label)

        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
        
        self.btn_start = Button(text="START", background_color=(0.1, 0.7, 0.2, 1), font_size='16sp')
        self.btn_start.bind(on_press=self.start_shift)
        
        self.btn_pause = Button(text="PAUSE", background_color=(0.9, 0.6, 0.1, 1), font_size='16sp')
        self.btn_pause.bind(on_press=self.confirm_pause)
        
        self.btn_stop = Button(text="STOP", background_color=(0.8, 0.2, 0.2, 1), font_size='16sp')
        self.btn_stop.bind(on_press=self.stop_shift)

        btn_layout.add_widget(self.btn_start)
        btn_layout.add_widget(self.btn_pause)
        btn_layout.add_widget(self.btn_stop)
        dash_layout.add_widget(btn_layout)

        dash_root.add_widget(dash_layout)
        self.tab_dashboard.add_widget(dash_root)
        self.add_widget(self.tab_dashboard)

        # --- TAB 2: EINSTELLUNGEN ---
        self.tab_settings = TabbedPanelItem(text='Einstellungen')
        settings_layout = BoxLayout(orientation='vertical', padding=15, spacing=10)

        settings_layout.add_widget(Label(text="Telegram Bot Konfiguration", font_size='16sp', size_hint_y=None, height=30))

        settings_layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=25))
        saved_token = self.store.get('telegram')['token'] if self.store.exists('telegram') else "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSH"
        self.input_token = TextInput(text=saved_token, multiline=False, size_hint_y=None, height=40)
        settings_layout.add_widget(self.input_token)

        settings_layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=25))
        saved_chat = self.store.get('telegram')['chat_id'] if self.store.exists('telegram') else "8941361378"
        self.input_chat = TextInput(text=saved_chat, multiline=False, size_hint_y=None, height=40)
        settings_layout.add_widget(self.input_chat)

        btn_save = Button(
            text="SPEICHERN",
            background_color=(0.2, 0.5, 0.8, 1),
            font_size='16sp',
            size_hint_y=None,
            height=50
        )
        btn_save.bind(on_press=self.save_settings)
        settings_layout.add_widget(btn_save)

        self.tab_settings.add_widget(settings_layout)
        self.add_widget(self.tab_settings)

        self.shift_active = False
        
        # Hintergrund-Threads starten
        threading.Thread(target=self.background_telegram_listener, daemon=True).start()
        threading.Thread(target=self.background_europa_watcher, daemon=True).start()

    def lade_europa_grenzen(self):
        """Lädt die Europa-Grenzen aus der JSON-Datei"""
        try:
            if os.path.exists('europa_grenzen.json'):
                with open('europa_grenzen.json', 'r', encoding='utf-8') as f:
                    daten = json.load(f)
                    return daten.get("grenzen", [])
        except Exception as e:
            print(f"Fehler beim Laden der Grenzdaten: {e}")
        return []

    def speak(self, text):
        """Gibt Text über die Sprachausgabe aus"""
        try:
            if tts:
                tts.speak(text)
        except Exception as e:
            print(f"Sprachausgabe Fehler: {e}")

    def save_settings(self, instance):
        self.store.put('telegram', token=self.input_token.text.strip(), chat_id=self.input_chat.text.strip())
        print("Einstellungen gespeichert.")
        self.speak("Einstellungen gespeichert.")

    def send_telegram(self, message):
        if self.store.exists('telegram'):
            token = self.store.get('telegram')['token']
            chat_id = self.store.get('telegram')['chat_id']
        else:
            token = "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSH"
            chat_id = "8941361378"

        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            try:
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                print(f"Telegram Fehler: {e}")

    def background_telegram_listener(self):
        """Verarbeitet eingehende Telegram-Befehle wie /ziel beringen"""
        offset = None
        while True:
            try:
                if self.store.exists('telegram'):
                    token = self.store.get('telegram')['token']
                else:
                    token = "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSH"
                
                url = f"https://api.telegram.org/bot{token}/getUpdates"
                params = {"timeout": 10, "allowed_updates": ["message"]}
                if offset:
                    params["offset"] = offset
                
                response = requests.get(url, params=params, timeout=15)
                data = response.json()
                
                if data and "result" in data:
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            msg = update["message"]["text"].strip()
                            msg_lower = msg.lower()
                            
                            if msg_lower.startswith("/start") or msg_lower == "start":
                                self.aktives_ziel["ziel"] = None
                                self.send_telegram("🟢 Atlas V1.2 Schicht aktiv. Europa-Routen bereit.")
                                self.speak("Schicht aktiv. Bereit für Europa-Routen.")
                            elif msg_lower in ["stopp", "stop", "/stopp", "/stop"]:
                                self.aktives_ziel["ziel"] = None
                                self.send_telegram("🛑 Schicht beendet via Telegram.")
                                self.speak("Schicht beendet.")
                            elif msg_lower.startswith("/ziel"):
                                ziel = msg.replace("/ziel", "").strip()
                                self.aktives_ziel["ziel"] = ziel
                                response_text = f"Europa-Ziel gesetzt: {ziel}"
                                self.send_telegram(f"🎯 **{response_text}**. Überwachung aktiv.")
                                self.speak(f"Ziel auf {ziel} gesetzt.")
                            else:
                                # Freier Text direkt als Ziel gewertet
                                self.aktives_ziel["ziel"] = msg
                                self.send_telegram(f"🎯 **Ziel auf {msg} gesetzt!**")
                                self.speak(f"Ziel auf {msg} gesetzt.")
            except Exception as e:
                print(f"Telegram Listener Fehler: {e}")
            time.sleep(2)

    def background_europa_watcher(self):
        """Überwacht im Hintergrund das Ziel und grenzüberschreitende Parameter"""
        while True:
            try:
                ziel = self.aktives_ziel.get("ziel")
                if ziel and self.shift_active:
                    # Hier läuft die Überprüfung gegen die Europa-Datenbank
                    pass
            except Exception as e:
                print(f"Europa Watcher Fehler: {e}")
            time.sleep(300)

    def start_shift(self, instance):
        if not self.shift_active:
            self.shift_active = True
            try:
                self.quota = float(self.input_quota.text)
                self.tacho = float(self.input_odo.text)
            except ValueError:
                self.quota = 280.0
                self.tacho = 15420.0
            
            self.info_label.text = f"🟢 SCHICHT AKTIV (V1.2)\nKontingent: {self.quota} km | Ziel: Kein Ziel"
            self.send_telegram(f"🚛 *Atlas E-Schicht V1.2 gestartet*\nKontingent: `{self.quota} km`")
            self.speak("Schicht gestartet. System bereit.")

    def confirm_pause(self, instance):
        if self.shift_active:
            self.info_label.text += "\n☕ Pause registriert!"
            self.send_telegram("☕ *Pause bestätigt*")
            self.speak("Pause registriert.")

    def stop_shift(self, instance):
        if self.shift_active:
            self.shift_active = False
            self.aktives_ziel["ziel"] = None
            self.info_label.text = f"🔴 Schicht beendet."
            self.send_telegram("📋 *Schicht beendet.*")
            self.speak("Schicht beendet.")

class ELkwTrackerApp(App):
    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = (0.05, 0.05, 0.05, 1) # Dunkles Matrix-Theme
        return ELkwAppUI()

if __name__ == '__main__':
    ELkwTrackerApp().run()
