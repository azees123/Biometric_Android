from datetime import datetime
import pickle
import os
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserIconView
from kivy.core.window import Window
from android.storage import app_storage_path
from android.permissions import request_permissions, Permission
from kivy.uix.scrollview import ScrollView

user_db = {}
APP_PATH = app_storage_path()
os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')


class FingerprintApp(App):
    def build(self):
        self.load_user_db()
        request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        self.title_label = Label(text="Fingerprint Authentication", font_size=20, size_hint=(1, 0.15))
        self.layout.add_widget(self.title_label)

        self.register_button = Button(text="Register", size_hint=(1, 0.15))
        self.register_button.bind(on_press=self.register_user)
        self.layout.add_widget(self.register_button)

        self.verify_button = Button(text="Verify Fingerprint", size_hint=(1, 0.15))
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

    def save_user_details(self, name, phone, reg_no, photo_path, fingerprint_data, dob, aadhar_no):
        if reg_no in user_db:
            return False
        user_db[reg_no] = {
            'name': name, 'phone': phone, 'photo': photo_path,
            'fingerprint': fingerprint_data, 'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'dob': dob, 'aadhar_no': aadhar_no
        }
        self.send_registration_message(name, reg_no, user_db[reg_no]['registration_timestamp'])
        self.save_user_db()
        return True

    def send_registration_message(self, name, reg_no, timestamp):
        print(f"User {name} with registration number {reg_no} registered at {timestamp}")

    def capture_fingerprint(self, reg_no):
        return f"fingerprint_{reg_no}_data"

    def open_filechooser(self, callback):
        chooser = FileChooserIconView()
        chooser.bind(on_selection=lambda x, y: self.on_file_select(callback))
        self.filechooser_popup = Popup(title="Select Fingerprint Image", content=chooser, size_hint=(0.9, 0.9))
        self.filechooser_popup.open()

    def on_file_select(self, callback):
        selected = self.filechooser_popup.content.selection
        if selected:
            callback(selected[0])
        self.filechooser_popup.dismiss()

    def send_alert_to_admin(self, name, reg_no, time, registration_timestamp=None):
        if registration_timestamp:
            msg = f"[ALERT] {name} ({reg_no}) tried to verify again at {time}.\nRegistered: {registration_timestamp}"
        else:
            msg = f"[ALERT] Unregistered fingerprint!\nName: {name}, Reg No: {reg_no}, Time: {time}"

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=msg, size_hint_y=None, height=150))
        btn = Button(text="Close", size_hint_y=None, height=50)
        btn.bind(on_press=lambda x: self.alert_popup.dismiss())
        layout.add_widget(btn)

        self.alert_popup = Popup(title="Admin Alert", content=layout, size_hint=(0.85, 0.5))
        self.alert_popup.open()

    def check_fingerprint(self, fingerprint_data, reg_no):
        if reg_no not in user_db:
            self.send_alert_to_admin("Unknown", reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

        user = user_db[reg_no]
        if user['verified']:
            self.send_alert_to_admin(user['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user['registration_timestamp'])
            return False

        if fingerprint_data == user['fingerprint']:
            user['verified'] = True
            self.save_user_db()
            return True
        else:
            self.send_alert_to_admin(user['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

    def register_user(self, instance):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        self.name_input = TextInput(hint_text="Name", size_hint_y=None, height=40)
        self.phone_input = TextInput(hint_text="Phone", size_hint_y=None, height=40)
        self.reg_input = TextInput(hint_text="Registration No", size_hint_y=None, height=40)
        self.dob_spinner = Spinner(text="Select DOB", values=["2025", "2024", "2023", "2022"], size_hint_y=None, height=40)
        self.aadhar_input = TextInput(hint_text="Aadhar No", size_hint_y=None, height=40)

        for widget in [self.name_input, self.phone_input, self.reg_input, self.dob_spinner, self.aadhar_input]:
            layout.add_widget(widget)

        submit = Button(text="Continue", size_hint_y=None, height=50)
        submit.bind(on_press=lambda x: self.capture_and_register())
        layout.add_widget(submit)

        scroll = ScrollView(size_hint=(1, 1))
        scroll.add_widget(layout)

        self.popup = Popup(title="Register User", content=scroll, size_hint=(0.9, 0.9))
        self.popup.open()

    def capture_and_register(self):
        name = self.name_input.text
        phone = self.phone_input.text
        reg_no = self.reg_input.text
        dob = self.dob_spinner.text
        aadhar_no = self.aadhar_input.text

        if reg_no in user_db:
            self.show_popup_message("Error", "Registration number already exists.")
            return

        self.popup.dismiss()

        def after_image(path):
            fingerprint_data = self.capture_fingerprint(reg_no)
            if self.save_user_details(name, phone, reg_no, path, fingerprint_data, dob, aadhar_no):
                self.show_popup_message("Success", f"{name} registered successfully.")
            else:
                self.show_popup_message("Error", "Registration failed.")

        self.open_filechooser(after_image)

    def verify_fingerprint(self, instance):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.verify_input = TextInput(hint_text="Enter Reg No", size_hint_y=None, height=40)
        layout.add_widget(self.verify_input)

        btn = Button(text="Verify", size_hint_y=None, height=50)
        btn.bind(on_press=self.perform_fingerprint_verification)
        layout.add_widget(btn)

        self.popup = Popup(title="Verify Fingerprint", content=layout, size_hint=(0.8, 0.4))
        self.popup.open()

    def perform_fingerprint_verification(self, instance):
        reg_no = self.verify_input.text.strip()
        fingerprint_data = self.capture_fingerprint(reg_no)

        if self.check_fingerprint(fingerprint_data, reg_no):
            self.show_popup_message("Access Granted", "Fingerprint verified.")
        else:
            self.show_popup_message("Access Denied", "Verification failed.")

    def show_popup_message(self, title, message):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=message))
        btn = Button(text="Close", size_hint_y=None, height=50)
        btn.bind(on_press=lambda x: self.message_popup.dismiss())
        layout.add_widget(btn)

        self.message_popup = Popup(title=title, content=layout, size_hint=(0.8, 0.4))
        self.message_popup.open()


if __name__ == "__main__":
    FingerprintApp().run()
