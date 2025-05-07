from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from android.storage import app_storage_path
from plyer import filechooser
import os
import pickle
from datetime import datetime
import platform

# Safe toast import
try:
    from plyer import toast
except ImportError:
    toast = None

user_db = {}
APP_PATH = app_storage_path()
os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')


class FingerprintApp(App):
    def build(self):
        self.load_user_db()

        self.main_layout = BoxLayout(orientation='vertical')
        self.scroll = ScrollView()
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        self.title_label = Label(text="Fingerprint Authentication System", size_hint_y=None, height=50)
        self.layout.add_widget(self.title_label)

        self.register_button = Button(text="Register User", size_hint_y=None, height=50)
        self.register_button.bind(on_press=self.register_user)
        self.layout.add_widget(self.register_button)

        self.verify_button = Button(text="Verify Fingerprint", size_hint_y=None, height=50)
        self.verify_button.bind(on_press=self.verify_fingerprint)
        self.layout.add_widget(self.verify_button)

        self.scroll.add_widget(self.layout)
        self.main_layout.add_widget(self.scroll)
        return self.main_layout

    def load_user_db(self):
        global user_db
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'rb') as f:
                user_db = pickle.load(f)

    def save_user_db(self):
        with open(DB_FILE, 'wb') as f:
            pickle.dump(user_db, f)

    def show_popup_message(self, message):
        print(f"TOAST: {message}")
        if toast and platform.system() == 'Android':
            try:
                toast.show(message=message)
            except Exception as e:
                print(f"[Toast Error]: {e}")
        else:
            print(f"[INFO]: {message}")

    def capture_fingerprint(self, image_path):
        return f"fingerprint_data_from_{os.path.basename(image_path)}"

    def save_user_details(self, name, phone, reg_no, photo_path, fingerprint_data):
        if reg_no in user_db:
            self.show_popup_message("This registration number already exists.")
            return False
        user_db[reg_no] = {
            'name': name,
            'phone': phone,
            'photo': photo_path,
            'fingerprint': fingerprint_data,
            'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_user_db()
        self.show_popup_message(f"User {name} registered successfully.")
        return True

    def send_alert_to_admin(self, name, reg_no, time, registration_timestamp=None):
        if registration_timestamp:
            message = f"ALERT: {name} ({reg_no}) verified again at {time}. Registered: {registration_timestamp}"
        else:
            message = f"ALERT: Unregistered fingerprint! Name: {name}, Reg: {reg_no}, Time: {time}"
        self.show_popup_message(message)

    def check_fingerprint(self, fingerprint_data, reg_no):
        if reg_no not in user_db:
            self.send_alert_to_admin("Unknown", reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

        if user_db[reg_no]['verified']:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                     user_db[reg_no]['registration_timestamp'])
            return False

        if fingerprint_data == user_db[reg_no]['fingerprint']:
            user_db[reg_no]['verified'] = True
            self.save_user_db()
            self.show_popup_message("Fingerprint verified successfully.")
            return True
        else:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

    def open_filechooser(self, callback):
        filechooser.open_file(on_selection=callback)

    def register_user(self, instance):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="Register User", size_hint_y=None, height=50))

        self.name_input = TextInput(hint_text="Enter name", size_hint_y=None, height=40)
        self.phone_input = TextInput(hint_text="Enter phone", size_hint_y=None, height=40)
        self.reg_no_input = TextInput(hint_text="Enter registration number", size_hint_y=None, height=40)

        submit_button = Button(text="Choose Fingerprint Image", size_hint_y=None, height=50)
        submit_button.bind(on_press=lambda x: self.choose_image_for_registration())

        self.layout.add_widget(self.name_input)
        self.layout.add_widget(self.phone_input)
        self.layout.add_widget(self.reg_no_input)
        self.layout.add_widget(submit_button)

    def choose_image_for_registration(self):
        self.open_filechooser(self.after_image_selected)

    def after_image_selected(self, selected_files):
        if selected_files:
            image_path = selected_files[0]
            name = self.name_input.text
            phone = self.phone_input.text
            reg_no = self.reg_no_input.text
            fingerprint_data = self.capture_fingerprint(image_path)
            self.save_user_details(name, phone, reg_no, image_path, fingerprint_data)

    def verify_fingerprint(self, instance):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="Verify Fingerprint", size_hint_y=None, height=50))

        self.reg_no_verify_input = TextInput(hint_text="Enter registration number", size_hint_y=None, height=40)
        verify_button = Button(text="Choose Fingerprint Image", size_hint_y=None, height=50)
        verify_button.bind(on_press=self.select_fingerprint_image_for_verification)

        self.layout.add_widget(self.reg_no_verify_input)
        self.layout.add_widget(verify_button)

    def select_fingerprint_image_for_verification(self, instance):
        self.open_filechooser(self.after_image_for_verification)

    def after_image_for_verification(self, selected_files):
        if selected_files:
            image_path = selected_files[0]
            reg_no = self.reg_no_verify_input.text
            fingerprint_data = self.capture_fingerprint(image_path)
            self.check_fingerprint(fingerprint_data, reg_no)


if __name__ == '__main__':
    FingerprintApp().run()
