import os
import json
import threading
import time
import random
import math
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.graphics import Color, Rectangle
from kivy.storage.jsonstore import JsonStore
import requests

# Sprachausgabe & GPS für Android
try:
    from plyer import tts
except ImportError:
    tts = None

try:
    from plyer import gps
except ImportError:
    gps = None

class MatrixBackground(FloatLayout):
    """Cyberpunk Matrix-Hintergrund"""
    def __init__(self, **kwargs):
        super(MatrixBackground, self).__init__(**kwargs)
        with self.canvas.before:
            Color(0.02, 0.06, 0.03, 1)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_canvas, pos=self._update_canvas)

        self.matrix_lbl = Label(
            text="01011001 11001001 010101 ... ATLAS GPS ACTIVE",
            font_size='13sp',
            color=(0.1, 0.8, 0.2, 0.25),
            halign='left',
            valign='top'
        )
        self.matrix_lbl.bind(size=self.matrix_lbl.setter('text_size'))
        self.add_widget(self.matrix_lbl)
        
        threading.Thread(target=self.update_matrix, daemon=True).start()

    def _update_canvas(self, instance, value):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.pos

    def update_matrix(self):
        while True:
            try:
                lines = []
                for _ in range(18):
                    line = "".join(random.choice(["0", "1", " ", "A", "F", "E", "X", "CH", "DE", "⚡"]) for _ in range(40))
                    lines.append(line)
                self.matrix_lbl.text = "\n".join(lines)
            except:
                pass
            time.sleep(0.5)

class ELkwAppUI(TabbedPanel):
    def __init__(self, **kwargs):
        super(ELkwAppUI, self).__init__(**kwargs)
        self.do_default_tab = False

        self.store = JsonStore('elkw_settings.json')
        self.aktives_ziel = {"ziel": None}
        self.europa_grenzen = self.lade_europa_grenzen()
        
        self.shift_active = False
        self.gefahren_km = 0.0
        self.last_lat = None
        self.last_lon = None

        # GPS initialisieren
        self.init_gps()

        # --- TAB 1: DASHBOARD ---
        self.tab_dashboard = TabbedPanelItem(text='Atlas v1.2 [GPS]')
        
        dash_root = MatrixBackground(size_hint=(1, 1))
        dash_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        dash_layout.add_widget(Label(
            text="[ AT-LAS // E-LKW GPS TRACKER ]", 
            font_size='20sp', 
            bold=True,
            size_hint_y=None, 
            height=40,
            color=(0.1, 0.95, 0.3, 1)
        ))

        input_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=45, spacing=15)
        self.input_quota = TextInput(text='280.0', multiline=False, hint_text='E-Kontingent (km)')
        self.input_odo = TextInput(text='15420.0', multiline=False, hint_text='Tacho Start')
        input_layout.add_widget(self.input_quota)
        input_layout.add_widget(self.input_odo)
        dash_layout.add_widget(input_layout)

        self.info_label = Label(
            text="STATUS: GPS BEREIT\nWarte auf Schichtstart...", 
            font_size='16sp',
            halign='center',
            valign='middle',
            color=(0.9, 0.9, 0.9, 1)
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        dash_layout.add_widget(self.info_label)

        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=65, spacing=15)
        
        self.btn_start = Button(text="SCHICHT STARTEN", background_color=(0.1, 0.6, 0.2, 1), font_size='16sp', bold=True)
        self.btn_start.bind(on_press=self.start_shift)
        
        self.btn_pause = Button(text="PAUSE", background_color=(0.8, 0.5, 0.1, 1), font_size='16sp', bold=True)
        self.btn_pause.bind(on_press=self.confirm_pause)
        
        self.btn_stop = Button(text="SCHICHT BEENDEN", background_color=(0.7, 0.2, 0.2, 1), font_size='16sp', bold=True)
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
        settings_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)

        settings_layout.add_widget(Label(text="Telegram Bot Konfiguration", font_size='18sp', size_hint_y=None, height=35, color=(0.1, 0.9, 0.3, 1)))

        settings_layout.add_widget(Label(text="Bot Token:", size_hint_y=None, height=25))
        saved_token = self.store.get('telegram')['token'] if self.store.exists('telegram') else "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSH"
        self.input_token = TextInput(text=saved_token, multiline=False, size_hint_y=None, height=45)
        settings_layout.add_widget(self.input_token)

        settings_layout.add_widget(Label(text="Chat ID:", size_hint_y=None, height=25))
        saved_chat = self.store.get('telegram')['chat_id'] if self.store.exists('telegram') else "8941361378"
        self.input_chat = TextInput(text=saved_chat, multiline=False, size_hint_y=None, height=45)
        settings_layout.add_widget(self.input_chat)

        btn_save = Button(
            text="EINSTELLUNGEN SPEICHERN",
            background_color=(0.2, 0.4, 0.7, 1),
            font_size='16sp',
            size_hint_y=None,
            height=55
        )
        btn_save.bind(on_press=self.save_settings)
        settings_layout.add_widget(btn_save)

        self.tab_settings.add_widget(settings_layout)
        self.add_widget(self.tab_settings)

        threading.Thread(target=self.background_telegram_listener, daemon=True).start()

    def init_gps(self):
        """Initialisiert den GPS-Sensor"""
        if gps:
            try:
                gps.configure(on_location=self.on_gps_location, on_status=self.on_gps_status)
            except Exception as e:
                print(f"GPS Init Fehler: {e}")

    def start_gps(self):
        if gps:
            try:
                # Intervall: Alle 1 Sekunde oder 5 Meter Positionswechsel
                gps.start(minTime=1000, minDistance=5)
            except Exception as e:
                print(f"GPS Start Fehler: {e}")

    def stop_gps(self):
        if gps:
            try:
                gps.stop()
            except Exception as e:
                print(f"GPS Stop Fehler: {e}")

    def on_gps_status(self, accesstype, status):
        print(f"GPS Status: {accesstype} - {status}")

    def on_gps_location(self, **kwargs):
        """Wird aufgerufen, sobald das Handy neue GPS-Koordinaten empfängt"""
        if not self.shift_active:
            return

        lat = kwargs.get('lat')
        lon = kwargs.get('lon')

        if lat and lon:
            if self.last_lat is not None and self.last_lon is not None:
                # Distanz zum vorherigen Punkt berechnen (Haversine-Formel)
                dist = self.calculate_distance(self.last_lat, self.last_lon, lat, lon)
                if dist < 5.0: # Filter gegen GPS-Sprünge (max 5km pro Messung)
                    self.gefahren_km += dist
            
            self.last_lat = lat
            self.last_lon = lon

            # Display im Haupt-Thread aktualisieren
            try:
                self.info_label.text = f"🟢 SCHICHT AKTIV [GPS]\nKontingent: {self.quota} km | Gefahren: {self.gefahren_km:.1f} km\nLat/Lon: {lat:.4f}, {lon:.4f}"
            except:
                pass

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Berechnet die Entfernung in Kilometern zwischen zwei GPS-Punkten"""
        R = 6371.0 # Erdradius in km
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def lade_europa_grenzen(self):
        try:
            if os.path.exists('europa_grenzen.json'):
                with open('europa_grenzen.json', 'r', encoding='utf-8') as f:
                    return json.load(f).get("grenzen", [])
        except Exception as e:
            print(f"Grenz-Ladefehler: {e}")
        return []

    def speak(self, text):
        try:
            if tts:
                tts.speak(text)
        except Exception as e:
            print(f"TTS Fehler: {e}")

    def save_settings(self, instance):
        self.store.put('telegram', token=self.input_token.text.strip(), chat_id=self.input_chat.text.strip())
        self.speak("Einstellungen gespeichert.")

    def send_telegram(self, message):
        if self.store.exists('telegram'):
            token = self.store.get('telegram')['token']
            chat_id = self.store.get('telegram')['chat_id']
        else:
            token = "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSH"
            chat_id = "8941361378"

        if token and chat_id:
            try:
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=5)
            except Exception as e:
                print(f"Telegram Fehler: {e}")

    def background_telegram_listener(self):
        offset = None
        while True:
            try:
                token = self.store.get('telegram')['token'] if self.store.exists('telegram') else "8413301731:AAE0Ob6OAvgcwi04aTr9dDq_ZlgcdFSH"
                response = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"timeout": 10, "offset": offset}, timeout=15)
                data = response.json()
                if data and "result" in data:
                    for update in data["result"]:
                        offset = update["update_id"] + 1
                        if "message" in update and "text" in update["message"]:
                            msg = update["message"]["text"].strip()
                            msg_lower = msg.lower()
                            
                            if msg_lower.startswith("/ziel"):
                                ziel = msg.replace("/ziel", "").strip()
                                self.aktives_ziel["ziel"] = ziel
                                self.send_telegram(f"🎯 **Ziel aktualisiert:** `{ziel}` (Schicht läuft ungestört weiter)")
                                self.speak(f"Ziel auf {ziel} gesetzt.")
            except Exception as e:
                print(f"Listener Fehler: {e}")
            time.sleep(2)

    def start_shift(self, instance):
        if not self.shift_active:
            self.shift_active = True
            try:
                self.quota = float(self.input_quota.text)
                self.tacho_start = float(self.input_odo.text)
            except ValueError:
                self.quota = 280.0
                self.tacho_start = 15420.0
            
            self.gefahren_km = 0.0
            self.last_lat = None
            self.last_lon = None

            self.info_label.text = f"🟢 SCHICHT AKTIV [GPS]\nKontingent: {self.quota} km | Gefahren: 0.0 km"
            self.send_telegram(f"🚛 *Atlas E-Schicht V1.2 gestartet*\nKontingent: `{self.quota} km`")
            self.speak("Schicht gestartet. GPS aktiv.")

            # GPS-Hardware starten
            self.start_gps()

    def confirm_pause(self, instance):
        if self.shift_active:
            self.send_telegram("☕ *Pause bestätigt*")
            self.speak("Pause registriert.")

    def stop_shift(self, instance):
        if self.shift_active:
            self.shift_active = False
            self.stop_gps()
            
            final_km = self.gefahren_km
            self.info_label.text = f"🔴 Schicht beendet.\nGefahren: {final_km:.1f} km"
            self.send_telegram(f"📋 *Schicht beendet.*\nGefahren gesamt: `{final_km:.1f} km`")
            self.speak(f"Schicht beendet. Gefahren: {final_km:.1f} Kilometer.")
            self.gefahren_km = 0.0

class ELkwTrackerApp(App):
    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = (0.02, 0.05, 0.03, 1)
        return ELkwAppUI()

if __name__ == '__main__':
    ELkwTrackerApp().run()
