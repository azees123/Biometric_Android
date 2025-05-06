from datetime import datetime
import pickle
import os

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.camera import Camera
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from plyer import filechooser
from android.permissions import request_permissions, Permission

user_db = {}
APP_PATH = os.path.join(os.path.expanduser("~"), "fingerprint_app")
os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')

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

    def save_user_details(self, name, phone, reg_no, photo_path, fingerprint_path):
        if reg_no in user_db:
            print("Fingerprint already registered!")
            return False
        user_db[reg_no] = {
            'name': name,
            'phone': phone,
            'photo': photo_path,
            'fingerprint': fingerprint_path,
            'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        print("User details saved successfully.")
        self.send_registration_message(name, reg_no, user_db[reg_no]['registration_timestamp'])
        self.save_user_db()
        return True

    def send_registration_message(self, name, reg_no, timestamp):
        message = f"User {name} with registration number {reg_no} registered successfully at {timestamp}."
        print("REGISTRATION SUCCESS MESSAGE:")
        print(message)

    def send_alert_to_admin(self, name, reg_no, time, registration_timestamp=None):
        if registration_timestamp:
            message = f"ALERT: User {name} with registration number {reg_no} tried to verify again at {time}. Registration timestamp: {registration_timestamp}"
        else:
            message = f"ALERT: Unregistered fingerprint attempted! Name: {name}, Registration Number: {reg_no}, Time: {time}"
        print("ALERT SENT TO ADMIN:")
        print(message)

        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_layout.add_widget(Label(text=message, size_hint=(1, None), height=100))
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        close_button.bind(on_press=self.close_alert_popup)
        popup_layout.add_widget(close_button)

        self.popup = Popup(title="Admin Alert", content=popup_layout, size_hint=(0.8, 0.4), auto_dismiss=True)
        self.popup.open()

    def close_alert_popup(self, instance):
        if hasattr(self, 'popup') and self.popup:
            self.popup.dismiss()

    def open_camera(self, name, callback):
        self.camera_layout = BoxLayout(orientation='vertical')
        self.camera = Camera(play=True)
        self.camera.resolution = (640, 480)
        self.camera_layout.add_widget(self.camera)

        self.capture_button = Button(text="Capture Photo", size_hint=(1, 0.2))
        self.capture_button.bind(on_press=lambda x: self.capture_photo(name, callback))
        self.camera_layout.add_widget(self.capture_button)

        self.camera_popup = Popup(title="Capture Photo", content=self.camera_layout, size_hint=(0.9, 0.9))
        self.camera_popup.open()

    def capture_photo(self, name, callback):
        texture = self.camera.texture
        if texture:
            photo_path = os.path.join(APP_PATH, f"{name}_photo.png")
            image = CoreImage(texture)
            image.save(photo_path)
            print(f"Photo of {name} saved at {photo_path}")
            self.photo_path = photo_path
            callback()
        else:
            print("Failed to capture photo.")
        self.camera.play = False
        self.camera_popup.dismiss()

    def register_user(self, instance):
        self.popup_register = BoxLayout(orientation='vertical', spacing=10)

        self.name_input = TextInput(hint_text="Enter your name", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter your phone number", size_hint=(1, None), height=40)
        self.reg_no_input = TextInput(hint_text="Enter your registration number", size_hint=(1, None), height=40)

        self.popup_register.add_widget(self.name_input)
        self.popup_register.add_widget(self.phone_input)
        self.popup_register.add_widget(self.reg_no_input)

        submit_button = Button(text="Continue", size_hint=(1, None), height=50)
        submit_button.bind(on_press=lambda x: self.capture_and_register())
        self.popup_register.add_widget(submit_button)

        self.popup = Popup(title="Register User", content=self.popup_register, size_hint=(0.8, 0.7))
        self.popup.open()

    def capture_and_register(self):
        name = self.name_input.text
        phone = self.phone_input.text
        reg_no = self.reg_no_input.text

        if not name or not phone or not reg_no:
            self.show_popup_message("Input Error", "All fields are required.")
            return

        if reg_no in user_db:
            self.show_popup_message("Error", "This registration number already exists.")
            return

        self.popup.dismiss()

        def after_photo():
            self.select_fingerprint_image(lambda fingerprint_path: self.save_registration_data(name, phone, reg_no, self.photo_path, fingerprint_path))

        self.open_camera(name, after_photo)

    def save_registration_data(self, name, phone, reg_no, photo_path, fingerprint_path):
        if self.save_user_details(name, phone, reg_no, photo_path, fingerprint_path):
            self.show_popup_message("Success", f"User {name} registered successfully.")

    def verify_fingerprint(self, instance):
        self.popup_verify = BoxLayout(orientation='vertical', spacing=10)

        self.reg_no_verify_input = TextInput(hint_text="Enter registration number", size_hint=(1, None), height=40)
        self.popup_verify.add_widget(self.reg_no_verify_input)

        verify_btn = Button(text="Select Fingerprint", size_hint=(1, None), height=50)
        verify_btn.bind(on_press=lambda x: self.select_fingerprint_image(
            lambda path: self.check_fingerprint_path(path, self.reg_no_verify_input.text)))
        self.popup_verify.add_widget(verify_btn)

        self.popup = Popup(title="Verify Fingerprint", content=self.popup_verify, size_hint=(0.8, 0.6))
        self.popup.open()

    def select_fingerprint_image(self, callback):
        def on_permissions_callback(permissions, grants):
            if all(grants):
                try:
                    filechooser.open_file(on_selection=lambda path: self.handle_file_selection(path, callback),
                                          filters=["*.png", "*.jpg", "*.jpeg"])
                except Exception as e:
                    self.show_popup_message("Error", f"File chooser failed: {str(e)}")
            else:
                self.show_popup_message("Permission Denied", "Cannot access storage without permission.")

        request_permissions([Permission.READ_EXTERNAL_STORAGE], on_permissions_callback)

    def handle_file_selection(self, path, callback):
        if path:
            callback(path[0])
        else:
            self.show_popup_message("Error", "No file selected.")

    def check_fingerprint_path(self, selected_path, reg_no):
        time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if reg_no not in user_db:
            self.show_popup_message("Access Denied", f"Unknown Register\nTimestamp: {time_now}")
            return

        stored_path = user_db[reg_no]['fingerprint']
        if os.path.abspath(selected_path) == os.path.abspath(stored_path):
            user = user_db[reg_no]
            self.show_popup_message("Access Granted", f"Name: {user['name']}\nReg No: {reg_no}\nTimestamp: {time_now}")
        else:
            self.show_popup_message("Access Denied", f"Fingerprint mismatch\nTimestamp: {time_now}")

    def show_popup_message(self, title, message):
        popup_message = BoxLayout(orientation='vertical', padding=10)
        popup_message.add_widget(Label(text=message))
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        close_button.bind(on_press=lambda x: self.popup.dismiss())
        popup_message.add_widget(close_button)

        self.popup = Popup(title=title, content=popup_message, size_hint=(0.7, 0.3))
        self.popup.open()

if __name__ == '__main__':
    FingerprintApp().run()
