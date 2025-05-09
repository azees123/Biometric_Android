from datetime import datetime
import pickle
import os
import hashlib
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.core.image import Image as CoreImage
from kivy.utils import platform

try:
    from android.storage import app_storage_path
    APP_PATH = app_storage_path()
except ImportError:
    APP_PATH = os.path.expanduser("~/.fingerprint_app")

os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')

user_db = {}

class FingerprintApp(App):
    def build(self):
        self.load_user_db()
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        self.title_label = Label(text="Fingerprint Authentication System", size_hint=(1, 0.1))
        self.layout.add_widget(self.title_label)

        self.register_button = Button(text="Register User", size_hint=(1, 0.1))
        self.register_button.bind(on_press=self.register_user)
        self.layout.add_widget(self.register_button)

        self.verify_button = Button(text="Verify Fingerprint", size_hint=(1, 0.1))
        self.verify_button.bind(on_press=self.verify_fingerprint)
        self.layout.add_widget(self.verify_button)

        return self.layout

    def load_user_db(self):
        global user_db
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'rb') as f:
                user_db = pickle.load(f)

    def save_user_db(self):
        with open(DB_FILE, 'wb') as f:
            pickle.dump(user_db, f)

    def get_fingerprint_from_file(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
                return hashlib.sha256(data).hexdigest()
        except Exception as e:
            print(f"Error reading fingerprint file: {e}")
            return None

    def capture_fingerprint(self, reg_no, callback):
        # Android-safe fallback fingerprint file
        test_fp = os.path.join(APP_PATH, "test_fingerprint.png")
        if not os.path.exists(test_fp):
            with open(test_fp, 'wb') as f:
                f.write(os.urandom(512))  # fake fingerprint

        fingerprint_data = self.get_fingerprint_from_file(test_fp)
        if fingerprint_data:
            callback(fingerprint_data)
        else:
            self.show_popup_message("Error", "Failed to get fingerprint.")

    def save_user_details(self, name, phone, reg_no, photo_path, fingerprint_data):
        if reg_no in user_db:
            self.show_popup_message("Error", "Registration number already exists.")
            return False
        user_db[reg_no] = {
            'name': name,
            'phone': phone,
            'photo': photo_path,
            'fingerprint': fingerprint_data,
            'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.send_registration_message(name, reg_no, user_db[reg_no]['registration_timestamp'])
        self.save_user_db()
        return True

    def send_registration_message(self, name, reg_no, timestamp):
        print(f"[REGISTERED] User {name} ({reg_no}) at {timestamp}")

    def send_alert_to_admin(self, name, reg_no, time, registration_timestamp=None):
        if registration_timestamp:
            message = f"ALERT: User {name} with registration number {reg_no} tried to verify again at {time}. Registered: {registration_timestamp}"
        else:
            message = f"ALERT: Unregistered fingerprint attempt! Name: {name}, Reg No: {reg_no}, Time: {time}"

        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_layout.add_widget(Label(text=message))
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        popup = Popup(title="Admin Alert", content=popup_layout, size_hint=(0.8, 0.4))
        close_button.bind(on_press=popup.dismiss)
        popup_layout.add_widget(close_button)
        popup.open()

    def check_fingerprint(self, fingerprint_data, reg_no):
        if reg_no not in user_db:
            self.send_alert_to_admin("Unknown User", reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False
        if user_db[reg_no]['verified']:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                     user_db[reg_no]['registration_timestamp'])
            return False
        if fingerprint_data == user_db[reg_no]['fingerprint']:
            user_db[reg_no]['verified'] = True
            self.save_user_db()
            return True
        else:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

    def open_camera(self, name, callback):
        self.camera_layout = BoxLayout(orientation='vertical')
        self.camera = Camera(play=True)
        self.camera.resolution = (640, 480)
        self.camera_layout.add_widget(self.camera)

        capture_button = Button(text="Capture Photo", size_hint=(1, 0.2))
        capture_button.bind(on_press=lambda x: self.capture_photo(name, callback))
        self.camera_layout.add_widget(capture_button)

        self.camera_popup = Popup(title="Capture Photo", content=self.camera_layout, size_hint=(0.9, 0.9))
        self.camera_popup.open()

    def capture_photo(self, name, callback):
        texture = self.camera.texture
        if texture:
            photo_path = os.path.join(APP_PATH, f"{name}_photo.png")
            CoreImage(texture).save(photo_path, flipped=False)
            self.photo_path = photo_path
            print(f"Photo saved at {photo_path}")
            callback()
        else:
            print("Camera texture not found.")
        self.camera.play = False
        self.camera_popup.dismiss()

    def register_user(self, instance):
        popup_register = BoxLayout(orientation='vertical', spacing=10)

        self.name_input = TextInput(hint_text="Enter your name", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter your phone number", size_hint=(1, None), height=40)
        self.reg_no_input = TextInput(hint_text="Enter your registration number", size_hint=(1, None), height=40)

        popup_register.add_widget(self.name_input)
        popup_register.add_widget(self.phone_input)
        popup_register.add_widget(self.reg_no_input)

        submit_button = Button(text="Continue", size_hint=(1, None), height=50)
        submit_button.bind(on_press=lambda x: self.capture_and_register())
        popup_register.add_widget(submit_button)

        popup = Popup(title="Register User", content=popup_register, size_hint=(0.8, 0.7))
        popup.open()
        self.current_popup = popup

    def capture_and_register(self):
        name = self.name_input.text
        phone = self.phone_input.text
        reg_no = self.reg_no_input.text

        if not name or not phone or not reg_no:
            self.show_popup_message("Error", "Please fill in all fields.")
            return

        if reg_no in user_db:
            self.show_popup_message("Error", "Registration number already exists.")
            return

        self.current_popup.dismiss()

        def after_photo():
            self.capture_fingerprint(reg_no, lambda fingerprint_data: self.save_after_fingerprint(name, phone, reg_no, fingerprint_data))

        self.open_camera(name, after_photo)

    def save_after_fingerprint(self, name, phone, reg_no, fingerprint_data):
        if self.save_user_details(name, phone, reg_no, self.photo_path, fingerprint_data):
            self.show_popup_message("Success", f"User {name} registered successfully.")

    def verify_fingerprint(self, instance):
        popup_verify = BoxLayout(orientation='vertical', spacing=10)

        self.reg_no_verify_input = TextInput(hint_text="Enter registration number", size_hint=(1, None), height=40)
        popup_verify.add_widget(self.reg_no_verify_input)

        verify_btn = Button(text="Verify", size_hint=(1, None), height=50)
        verify_btn.bind(on_press=self.perform_fingerprint_verification)
        popup_verify.add_widget(verify_btn)

        popup = Popup(title="Verify Fingerprint", content=popup_verify, size_hint=(0.8, 0.6))
        popup.open()
        self.current_popup = popup

    def perform_fingerprint_verification(self, instance):
        reg_no = self.reg_no_verify_input.text
        self.current_popup.dismiss()

        def on_fingerprint_selected(fingerprint_data):
            if self.check_fingerprint(fingerprint_data, reg_no):
                self.show_popup_message("Access Granted", "Fingerprint verified successfully!")
            else:
                self.show_popup_message("Access Denied", "Fingerprint verification failed.")

        self.capture_fingerprint(reg_no, on_fingerprint_selected)

    def show_popup_message(self, title, message):
        layout = BoxLayout(orientation='vertical', padding=10)
        layout.add_widget(Label(text=message))
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        popup = Popup(title=title, content=layout, size_hint=(0.7, 0.3))
        close_button.bind(on_press=popup.dismiss)
        layout.add_widget(close_button)
        popup.open()

if __name__ == '__main__':
    FingerprintApp().run()
