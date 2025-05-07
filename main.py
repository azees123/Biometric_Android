from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.uix.filechooser import FileChooserIconView
from kivy.core.image import Image as CoreImage
from android.permissions import request_permissions, Permission
from jnius import autoclass
from datetime import datetime
import pickle
import os

from kivy.clock import Clock
from kivy.core.window import Window
Window.softinput_mode = "below_target"

# Android classes for file picker
Intent = autoclass('android.content.Intent')
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Uri = autoclass('android.net.Uri')

# Global variables
user_db = {}
APP_PATH = "/sdcard/your_app_data"  # Customize your app's data storage path
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

    def save_user_details(self, name, phone, reg_no, fingerprint_image_path):
        if reg_no in user_db:
            print("Fingerprint already registered!")
            return False
        user_db[reg_no] = {
            'name': name,
            'phone': phone,
            'fingerprint': fingerprint_image_path,
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

    def check_fingerprint(self, fingerprint_image_path, reg_no):
        if reg_no not in user_db:
            print("Fingerprint not found in database!")
            self.send_alert_to_admin("Unknown User", reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

        if user_db[reg_no]['verified']:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_db[reg_no]['registration_timestamp'])
            return False

        if fingerprint_image_path == user_db[reg_no]['fingerprint']:
            user_db[reg_no]['verified'] = True
            self.save_user_db()
            print("Fingerprint verified successfully.")
            return True
        else:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

    def open_filechooser(self, callback):
        # Request permission to access storage
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

        # Use Android file picker
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")  # Filter only image files
        intent.addCategory(Intent.CATEGORY_OPENABLE)

        PythonActivity.mActivity.startActivityForResult(intent, 1)

    def on_activity_result(self, request_code, result_code, intent):
        if result_code == -1:  # RESULT_OK
            file_uri = intent.getData()
            # Convert URI to file path
            file_path = self.get_file_path_from_uri(file_uri)
            # Call the callback with the selected file path
            self.after_fingerprint_selected(file_path)

    def get_file_path_from_uri(self, uri):
        # Convert URI to actual file path on Android
        content_resolver = PythonActivity.mActivity.getContentResolver()
        cursor = content_resolver.query(uri, None, None, None, None)
        cursor.moveToFirst()
        index = cursor.getColumnIndex("_data")
        file_path = cursor.getString(index)
        cursor.close()
        return file_path

    def register_user(self, instance):
        self.popup_register = BoxLayout(orientation='vertical', spacing=10)

        self.name_input = TextInput(hint_text="Enter your name", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter your phone number", size_hint=(1, None), height=40)
        self.reg_no_input = TextInput(hint_text="Enter your registration number", size_hint=(1, None), height=40)

        self.popup_register.add_widget(self.name_input)
        self.popup_register.add_widget(self.phone_input)
        self.popup_register.add_widget(self.reg_no_input)

        submit_button = Button(text="Continue", size_hint=(1, None), height=50)
        submit_button.bind(on_press=lambda x: self.select_fingerprint_for_registration())
        self.popup_register.add_widget(submit_button)

        self.popup = Popup(title="Register User", content=self.popup_register, size_hint=(0.8, 0.7))
        self.popup.open()

    def select_fingerprint_for_registration(self):
        name = self.name_input.text
        phone = self.phone_input.text
        reg_no = self.reg_no_input.text

        if reg_no in user_db:
            self.show_popup_message("Error", "This registration number already exists.")
            return

        self.popup.dismiss()
        self.open_filechooser(self.after_fingerprint_selected)

    def after_fingerprint_selected(self, fingerprint_image_path):
        # Handle the fingerprint image path after it's selected from the gallery
        print(f"Selected fingerprint image path: {fingerprint_image_path}")
        # Save the user details and fingerprint image path
        if self.save_user_details(self.name_input.text, self.phone_input.text, self.reg_no_input.text, fingerprint_image_path):
            self.show_popup_message("Success", f"User {self.name_input.text} registered successfully.")

    def verify_fingerprint(self, instance):
        self.popup_verify = BoxLayout(orientation='vertical', spacing=10)

        self.reg_no_verify_input = TextInput(hint_text="Enter registration number", size_hint=(1, None), height=40)
        self.popup_verify.add_widget(self.reg_no_verify_input)

        verify_btn = Button(text="Verify", size_hint=(1, None), height=50)
        verify_btn.bind(on_press=self.select_fingerprint_for_verification)
        self.popup_verify.add_widget(verify_btn)

        self.popup = Popup(title="Verify Fingerprint", content=self.popup_verify, size_hint=(0.8, 0.6))
        self.popup.open()

    def select_fingerprint_for_verification(self, instance):
        reg_no = self.reg_no_verify_input.text
        self.open_filechooser(lambda fingerprint_image_path: self.verify_fingerprint_image(fingerprint_image_path, reg_no))

    def verify_fingerprint_image(self, fingerprint_image_path, reg_no):
        if self.check_fingerprint(fingerprint_image_path, reg_no):
            self.show_popup_message("Access Granted", "Fingerprint verified successfully!")
        else:
            self.show_popup_message("Access Denied", "Fingerprint verification failed.")

    def show_popup_message(self, title, message):
        def open_popup(dt):
            try:
                if hasattr(self, 'popup') and self.popup:
                    self.popup.dismiss()

                popup_message = BoxLayout(orientation='vertical', padding=10, spacing=10)
                popup_message.add_widget(Label(text=message, size_hint=(1, None), height=80))

                close_button = Button(text="Close", size_hint=(1, None), height=50)
                close_button.bind(on_press=lambda x: self.popup.dismiss())
                popup_message.add_widget(close_button)

                self.popup = Popup(
                    title=title,
                    content=popup_message,
                    size_hint=(0.75, 0.4),
                    auto_dismiss=False
                )
                self.popup.open()
            except Exception as e:
                print("Popup display error:", e)

        Clock.schedule_once(open_popup, 0.1)

if __name__ == '__main__':
    FingerprintApp().run()
