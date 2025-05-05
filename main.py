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
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from android.storage import app_storage_path
from kivy.core.window import Window

user_db = {}
temporary_fingerprint_data = None

APP_PATH = app_storage_path()
os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')


class FingerprintApp(App):
    def build(self):
        self.load_user_db()

        self.layout = BoxLayout(orientation='vertical', padding=[10, 20], spacing=15, size_hint=(1, 1))

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

    def save_user_details(self, name, phone, reg_no, photo_path, fingerprint_data, dob, aadhar_no):
        if reg_no in user_db:
            print("Fingerprint already registered!")
            return False
        user_db[reg_no] = {
            'name': name,
            'phone': phone,
            'photo': photo_path,
            'fingerprint': fingerprint_data,
            'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'dob': dob,
            'aadhar_no': aadhar_no
        }
        print("User details saved successfully.")
        self.send_registration_message(name, reg_no, user_db[reg_no]['registration_timestamp'])
        self.save_user_db()
        return True

    def send_registration_message(self, name, reg_no, timestamp):
        message = f"User {name} with registration number {reg_no} registered successfully at {timestamp}."
        print("REGISTRATION SUCCESS MESSAGE:")
        print(message)

    def capture_fingerprint(self, reg_no):
        return f"fingerprint_{reg_no}_data"

    def open_filechooser(self, callback):
        self.filechooser_popup = FileChooserIconView()
        self.filechooser_popup.bind(on_selection=lambda x, y: self.on_file_select(callback))
        self.filechooser_popup_popup = Popup(title="Select Fingerprint Image", content=self.filechooser_popup, size_hint=(0.8, 0.8))
        self.filechooser_popup_popup.open()

    def on_file_select(self, callback):
        selected = self.filechooser_popup.selection
        if selected:
            image_path = selected[0]
            print(f"Fingerprint image selected from gallery: {image_path}")
            callback(image_path)
        self.filechooser_popup_popup.dismiss()

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

        self.popup = Popup(title="Admin Alert", content=popup_layout, size_hint=(0.85, 0.45), auto_dismiss=True)
        self.popup.open()

    def close_alert_popup(self, instance):
        if hasattr(self, 'popup') and self.popup:
            self.popup.dismiss()

    def check_fingerprint(self, fingerprint_data, reg_no):
        if reg_no not in user_db:
            print("Fingerprint not found in database!")
            self.send_alert_to_admin("Unknown User", reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

        if user_db[reg_no]['verified']:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_db[reg_no]['registration_timestamp'])
            return False

        if fingerprint_data == user_db[reg_no]['fingerprint']:
            user_db[reg_no]['verified'] = True
            self.save_user_db()
            print("Fingerprint verified successfully.")
            return True
        else:
            self.send_alert_to_admin(user_db[reg_no]['name'], reg_no, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            return False

    def register_user(self, instance):
        scroll_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))

        self.name_input = TextInput(hint_text="Enter your name", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter your phone number", size_hint=(1, None), height=40)
        self.reg_no_input = TextInput(hint_text="Enter your registration number", size_hint=(1, None), height=40)
        self.dob_spinner = Spinner(text="Select DOB", values=["2025", "2024", "2023", "2022", "2021", "2020"], size_hint=(1, None), height=40)
        self.aadhar_input = TextInput(hint_text="Enter Aadhar number", size_hint=(1, None), height=40)

        scroll_layout.add_widget(self.name_input)
        scroll_layout.add_widget(self.phone_input)
        scroll_layout.add_widget(self.reg_no_input)
        scroll_layout.add_widget(self.dob_spinner)
        scroll_layout.add_widget(self.aadhar_input)

        submit_button = Button(text="Continue", size_hint=(1, None), height=50)
        submit_button.bind(on_press=lambda x: self.capture_and_register())
        scroll_layout.add_widget(submit_button)

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(scroll_layout)

        self.popup = Popup(title="Register User", content=scroll_view, size_hint=(0.9, 0.9))
        self.popup.open()

    def capture_and_register(self):
        name = self.name_input.text
        phone = self.phone_input.text
        reg_no = self.reg_no_input.text
        dob = self.dob_spinner.text
        aadhar_no = self.aadhar_input.text

        if reg_no in user_db:
            self.show_popup_message("Error", "This registration number already exists.")
            return

        self.popup.dismiss()

        def after_image_selection(image_path):
            fingerprint_data = self.capture_fingerprint(reg_no)
            if self.save_user_details(name, phone, reg_no, image_path, fingerprint_data, dob, aadhar_no):
                self.show_popup_message("Success", f"User {name} registered successfully.")

        self.open_filechooser(after_image_selection)

    def verify_fingerprint(self, instance):
        scroll_layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        scroll_layout.bind(minimum_height=scroll_layout.setter('height'))

        self.reg_no_verify_input = TextInput(hint_text="Enter registration number", size_hint=(1, None), height=40)
        scroll_layout.add_widget(self.reg_no_verify_input)

        verify_btn = Button(text="Verify", size_hint=(1, None), height=50)
        verify_btn.bind(on_press=self.perform_fingerprint_verification)
        scroll_layout.add_widget(verify_btn)

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(scroll_layout)

        self.popup = Popup(title="Verify Fingerprint", content=scroll_view, size_hint=(0.8, 0.6))
        self.popup.open()

    def perform_fingerprint_verification(self, instance):
        reg_no = self.reg_no_verify_input.text
        fingerprint_data = self.capture_fingerprint(reg_no)

        if self.check_fingerprint(fingerprint_data, reg_no):
            self.show_popup_message("Access Granted", "Fingerprint verified successfully!")
        else:
            self.show_popup_message("Access Denied", "Fingerprint verification failed.")

    def show_popup_message(self, title, message):
        popup_message = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_message.add_widget(Label(text=message))
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        close_button.bind(on_press=lambda x: self.popup.dismiss())
        popup_message.add_widget(close_button)

        self.popup = Popup(title=title, content=popup_message, size_hint=(0.75, 0.35))
        self.popup.open()


if __name__ == '__main__':
    FingerprintApp().run()
