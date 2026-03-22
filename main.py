import threading
import pyttsx3
import requests
import os
import queue
import speech_recognition as sr
from plyer import tts  # For Android TTS
from kivy.utils import platform # To detect OS
from kivy.clock import Clock
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField
from kivymd.uix.fitimage import FitImage
from kivymd.uix.card import MDCard
from kivymd.uix.filemanager import MDFileManager

class RosMosAndroid(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        # Default Model set to Gemma 2B
        self.selected_model = "Gemma 2B" 
        
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 1.0 
        
        self.file_manager = MDFileManager(exit_manager=self.exit_manager, select_path=self.select_path)
        self.root_layout = MDBoxLayout(orientation='vertical')

        # --- TOP BAR ---
        self.top_bar = MDBoxLayout(adaptive_height=True, padding=dp(10), spacing=dp(5))
        self.top_bar.add_widget(MDLabel(text="🔥 Ros-Mos AI", font_style="H6", bold=True, adaptive_width=True))
        self.top_bar.add_widget(MDBoxLayout()) 
        self.top_bar.add_widget(MDIconButton(icon="robot", on_release=self.open_model_menu))
        self.top_bar.add_widget(MDIconButton(icon="palette", on_release=self.open_theme_menu))
        self.top_bar.add_widget(MDIconButton(icon="broom", on_release=self.clear_chat))
        self.root_layout.add_widget(self.top_bar)

        # --- CHAT AREA ---
        self.scroll = MDScrollView()
        self.chat_list = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(15), padding=dp(10))
        self.scroll.add_widget(self.chat_list)
        self.root_layout.add_widget(self.scroll)

        # --- STATUS HUD ---
        self.status_label = MDLabel(text=f"Ready | Model: {self.selected_model}", theme_text_color="Hint", halign="center", adaptive_height=True, font_style="Caption")
        self.root_layout.add_widget(self.status_label)

        # --- INPUT BAR ---
        self.input_bar = MDBoxLayout(adaptive_height=True, padding=dp(8), spacing=dp(8))
        self.input_bar.add_widget(MDIconButton(icon="image-plus", on_release=self.open_file_manager))
        self.text_input = MDTextField(hint_text="Ask Ros-Mos...", mode="round", size_hint_x=0.7)
        self.input_bar.add_widget(self.text_input)
        self.mic_btn = MDIconButton(icon="microphone", on_release=self.start_listening)
        self.input_bar.add_widget(self.mic_btn)
        self.send_btn = MDIconButton(icon="send", on_release=self.send_message)
        self.input_bar.add_widget(self.send_btn)
        self.root_layout.add_widget(self.input_bar)

        return self.root_layout

    def on_start(self):
        self.speech_queue = queue.Queue()
        threading.Thread(target=self._speech_worker, daemon=True).start()

    def _speech_worker(self):
        """Background loop for Windows (pyttsx3) and Android (plyer)."""
        engine = None
        
        # Only initialize pyttsx3 if we are on a desktop platform
        if platform not in ['android', 'ios']:
            try:
                engine = pyttsx3.init()
                voices = engine.getProperty('voices')
                for voice in voices:
                    if "female" in voice.name.lower() or "zira" in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.setProperty('rate', 180)
            except Exception as e:
                print(f"Desktop TTS Error: {e}")

        while True:
            text = self.speech_queue.get()
            if text:
                try:
                    if platform == 'android':
                        # Use system TTS for Android
                        tts.speak(text)
                    else:
                        # Use pyttsx3 for Windows
                        if engine:
                            engine.say(text)
                            engine.runAndWait()
                except Exception as e:
                    print(f"Speech Loop Error: {e}")
                finally:
                    self.speech_queue.task_done()

    def speak(self, text):
        if hasattr(self, 'speech_queue'):
            self.speech_queue.put(text)

    def add_bubble(self, text, is_user=False, image_path=None):
        container = MDBoxLayout(adaptive_height=True, spacing=dp(10), orientation='horizontal', padding=[dp(5), 0])
        logo_src = "user.jpg" if is_user else "ai.jpg"
        
        if not os.path.exists(logo_src):
            logo_src = "account-circle" if is_user else "robot-vacuum"

        avatar = FitImage(source=logo_src, size_hint=(None, None), size=(dp(40), dp(40)), radius=dp(20))
        bubble = MDCard(
            orientation="vertical", adaptive_height=True, padding=dp(12),
            size_hint=(None, None), width=min(dp(280), self.root_layout.width * 0.75),
            md_bg_color=(0.14, 0.38, 0.92, 1) if is_user else (0.25, 0.25, 0.25, 1),
            radius=[dp(15), dp(15), (0 if is_user else dp(15)), (dp(15) if is_user else 0)],
            elevation=1
        )
        
        if image_path:
            bubble.add_widget(FitImage(source=image_path, size_hint_y=None, height=dp(180), radius=dp(10)))
        
        msg_label = MDLabel(text=text, theme_text_color="Custom", text_color=(1,1,1,1), adaptive_height=True)
        bubble.add_widget(msg_label)

        if is_user:
            container.add_widget(MDBoxLayout()) 
            container.add_widget(bubble)
            container.add_widget(avatar)
        else:
            container.add_widget(avatar)
            container.add_widget(bubble)
            container.add_widget(MDBoxLayout()) 

        self.chat_list.add_widget(container)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0))

    def start_listening(self, *args):
        self.mic_btn.icon = "microphone-settings"
        self.mic_btn.icon_color = (1, 0, 0, 1)
        self.update_status("Listening...")
        
        def listen_thread():
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
                    Clock.schedule_once(lambda dt: self.update_status("Recognizing..."))
                    text = self.recognizer.recognize_google(audio)
                    Clock.schedule_once(lambda dt: self.auto_send(text))
            except Exception:
                Clock.schedule_once(lambda dt: self.update_status("Mic Error or Timeout"))
            finally:
                Clock.schedule_once(lambda dt: self.reset_mic_ui())

        threading.Thread(target=listen_thread, daemon=True).start()

    def auto_send(self, text):
        self.text_input.text = text
        self.send_message()

    def reset_mic_ui(self):
        self.mic_btn.icon = "microphone"
        self.mic_btn.icon_color = (1, 1, 1, 1) if self.theme_cls.theme_style == "Dark" else (0, 0, 0, 1)

    def update_status(self, text):
        self.status_label.text = text

    def send_message(self, *args):
        msg = self.text_input.text.strip()
        if msg:
            self.add_bubble(msg, is_user=True)
            self.text_input.text = ""
            threading.Thread(target=self.fetch_ai_response, args=(msg,), daemon=True).start()

    def fetch_ai_response(self, prompt):
        url = "http://192.168.1.4/api/generate"
        model_map = {"Mistral": "mistral", "Moondream": "moondream", "Gemma 2B": "gemma:2b"}
        selected = model_map.get(self.selected_model, "gemma:2b")
        
        payload = {
            "model": selected, "prompt": prompt,
            "system": "You are Ros-Mos, a female AI assistant created by Udit Tomar. Keep responses helpful and concise.",
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=20)
            reply = response.json().get('response', '...')
        except:
            reply = "I'm offline. Is Ollama running?"

        Clock.schedule_once(lambda dt: self.add_bubble(reply, is_user=False))
        self.speak(reply)

    def open_model_menu(self, button):
        items = [{"text": m, "viewclass": "OneLineListItem", "on_release": lambda x=m: self.set_model(x)} 
                 for m in ["Mistral", "Moondream", "Gemma 2B"]]
        self.menu = MDDropdownMenu(caller=button, items=items, width_mult=3)
        self.menu.open()

    def set_model(self, model_name):
        self.selected_model = model_name
        self.menu.dismiss()
        self.update_status(f"Using {model_name}")

    def open_theme_menu(self, button):
        items = [{"text": t, "viewclass": "OneLineListItem", "on_release": lambda x=t: self.set_theme(x)} 
                 for t in ["Light", "Dark"]]
        self.theme_menu = MDDropdownMenu(caller=button, items=items, width_mult=2)
        self.theme_menu.open()

    def set_theme(self, theme):
        self.theme_cls.theme_style = theme
        self.theme_menu.dismiss()
        self.reset_mic_ui()

    def open_file_manager(self, *args):
        self.file_manager.show(os.path.expanduser("~"))

    def select_path(self, path):
        self.exit_manager()
        self.add_bubble("Uploaded image.", is_user=True, image_path=path)

    def exit_manager(self, *args):
        self.file_manager.close()

    def clear_chat(self, *args):
        self.chat_list.clear_widgets()

if __name__ == "__main__":
    RosMosAndroid().run()