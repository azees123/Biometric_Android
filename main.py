from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.spinner import Spinner
from datetime import datetime
import os
import pickle
from android.storage import app_storage_path

# Storage path and database file setup
APP_PATH = app_storage_path()
os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')

user_db = {}
temporary_fingerprint_data = None

class FingerprintApp(App):
    
    def build(self):
        self.load_user_db()
        
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        # Title
        self.title_label = Label(text="Fingerprint Authentication System", size_hint=(1, 0.1), font_size='20sp', color=(0, 0, 0, 1))
        self.layout.add_widget(self.title_label)

        # Register button
        self.register_button = Button(text="Register User", size_hint=(1, 0.1), background_color=(0.3, 0.6, 0.3, 1))
        self.register_button.bind(on_press=self.register_user)
        self.layout.add_widget(self.register_button)

        # Verify button
        self.verify_button = Button(text="Verify Fingerprint", size_hint=(1, 0.1), background_color=(0.3, 0.6, 0.3, 1))
        self.verify_button.bind(on_press=self.verify_fingerprint)
        self.layout.add_widget(self.verify_button)

        return self.layout

    def load_user_db(self):
        global user_db
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'rb') as f:
                user_db = pickle.load(f)
        else:
            user_db = {}

    def save_user_db(self):
        with open(DB_FILE, 'wb') as f:
            pickle.dump(user_db, f)

    def show_popup_message(self, title, message):
        popup_message = BoxLayout(orientation='vertical', padding=10)
        popup_message.add_widget(Label(text=message))
        close_button = Button(text="Close", size_hint=(1, None), height=50)
        close_button.bind(on_press=lambda x: self.popup.dismiss())
        popup_message.add_widget(close_button)

        self.popup = Popup(title=title, content=popup_message, size_hint=(0.7, 0.3))
        self.popup.open()

    def register_user(self, instance):
        self.popup_register = BoxLayout(orientation='vertical', spacing=10)

        # Inputs for user details
        self.name_input = TextInput(hint_text="Enter your name", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter your phone number", size_hint=(1, None), height=40)
        self.emp_id_input = TextInput(hint_text="Enter your employee ID", size_hint=(1, None), height=40)
        self.aadhaar_input = TextInput(hint_text="Enter Aadhaar Number (optional)", size_hint=(1, None), height=40)

        # Spinner for Date of Birth (DD/MM/YYYY)
        self.dob_spinner = Spinner(text="DD/MM/YYYY", values=("01/01/1990", "02/02/1991", "03/03/1992", "04/04/1993", "05/05/1999"), size_hint=(1, None), height=40)

        self.popup_register.add_widget(self.name_input)
        self.popup_register.add_widget(self.phone_input)
        self.popup_register.add_widget(self.emp_id_input)
        self.popup_register.add_widget(self.aadhaar_input)
        self.popup_register.add_widget(self.dob_spinner)

        # Select Fingerprint Image Button
        self.gallery_button = Button(text="Select Fingerprint Image", size_hint=(1, None), height=50)
        self.gallery_button.bind(on_press=self.select_image)
        self.popup_register.add_widget(self.gallery_button)

        # Submit button
        submit_button = Button(text="Continue", size_hint=(1, None), height=50)
        submit_button.bind(on_press=self.capture_and_register)
        self.popup_register.add_widget(submit_button)

        self.popup = Popup(title="Register User", content=self.popup_register, size_hint=(0.8, 0.7))
        self.popup.open()

    def capture_and_register(self, instance):
        name = self.name_input.text
        phone = self.phone_input.text
        emp_id = self.emp_id_input.text
        aadhaar = self.aadhaar_input.text
        dob = self.dob_spinner.text

        if not name or not phone or not emp_id:
            self.show_popup_message("Error", "Name, Phone, and Employee ID are required.")
            return

        if emp_id in user_db:
            self.show_popup_message("Error", "This employee ID already exists.")
            return

        # Save fingerprint image path
        fingerprint_data = self.fingerprint_image_path if hasattr(self, 'fingerprint_image_path') else None

        user_db[emp_id] = {
            'name': name,
            'phone': phone,
            'aadhaar': aadhaar,
            'dob': dob,
            'fingerprint': fingerprint_data,
            'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        self.save_user_db()
        self.show_popup_message("Success", f"User {name} registered successfully.\nTimestamp: {user_db[emp_id]['registration_timestamp']}")

    def select_image(self, instance):
        filechooser = FileChooserIconView()
        filechooser.bind(on_selection=lambda *x: self.load_image(filechooser.selection))

        image_popup = Popup(title="Select Fingerprint Image", content=filechooser, size_hint=(0.8, 0.8))
        image_popup.open()

    def load_image(self, selection):
        if selection:
            image_path = selection[0]
            self.fingerprint_image_path = image_path
            self.show_popup_message("Success", f"Fingerprint image selected:\n{image_path}")
        else:
            self.show_popup_message("Error", "No image selected.")

    def verify_fingerprint(self, instance):
        filechooser = FileChooserIconView()
        filechooser.bind(on_selection=lambda *x: self.perform_fingerprint_verification(filechooser.selection))

        self.popup = Popup(title="Select Fingerprint Image for Verification", content=filechooser, size_hint=(0.8, 0.8))
        self.popup.open()

    def perform_fingerprint_verification(self, selection):
        if not selection:
            self.show_popup_message("Error", "No fingerprint image selected.")
            return

        selected_fp = selection[0]

        for emp_id, data in user_db.items():
            if data.get("fingerprint") == selected_fp:
                self.show_popup_message("Access Granted", f"Fingerprint matched!\nName: {data['name']}\nEmployee ID: {emp_id}\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                return

        self.show_popup_message("Access Denied", f"No matching fingerprint found.\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    FingerprintApp().run()
