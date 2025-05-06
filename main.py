import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserIconView
import pickle
import os
import hashlib
from datetime import datetime

DATA_FILE = "users.pkl"  # Save in current directory

def hash_image(filepath):
    with open(filepath, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

class BimetricApp(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.name_input = TextInput(hint_text='Name')
        self.aadhaar_input = TextInput(hint_text='Aadhaar')
        self.contact_input = TextInput(hint_text='Contact')
        self.empid_input = TextInput(hint_text='Employee ID')

        self.day_spinner = Spinner(text='Day', values=[str(i) for i in range(1, 32)])
        self.month_spinner = Spinner(text='Month', values=[str(i) for i in range(1, 13)])
        self.year_spinner = Spinner(text='Year', values=[str(y) for y in range(1960, datetime.now().year + 1)])

        self.fingerprint_path = ""
        self.fingerprint_button = Button(text='Select Fingerprint Image (Gallery)')
        self.fingerprint_button.bind(on_press=self.select_fingerprint)

        self.register_btn = Button(text='Register')
        self.register_btn.bind(on_press=self.register_user)

        self.verify_btn = Button(text='Verify')
        self.verify_btn.bind(on_press=self.verify_user)

        # Add widgets
        for widget in [self.name_input, self.aadhaar_input, self.contact_input,
                       self.empid_input, self.day_spinner, self.month_spinner,
                       self.year_spinner, self.fingerprint_button,
                       self.register_btn, self.verify_btn]:
            self.add_widget(widget)

    def select_fingerprint(self, instance):
        chooser = FileChooserIconView()
        popup = Popup(title="Choose Fingerprint Image", content=chooser, size_hint=(0.9, 0.9))

        def on_selection(*args):
            if chooser.selection:
                self.fingerprint_path = chooser.selection[0]
                self.fingerprint_button.text = f"Selected: {os.path.basename(self.fingerprint_path)}"
                popup.dismiss()

        chooser.bind(on_submit=on_selection)
        popup.open()

    def register_user(self, instance):
        if not self.fingerprint_path:
            self.show_popup("Error", "Please select a fingerprint image.")
            return

        dob = f"{self.day_spinner.text.zfill(2)}/{self.month_spinner.text.zfill(2)}/{self.year_spinner.text}"
        user_data = {
            'name': self.name_input.text,
            'aadhaar': self.aadhaar_input.text,
            'contact': self.contact_input.text,
            'dob': dob,
            'empid': self.empid_input.text,
            'timestamp': str(datetime.now()),
            'fingerprint_hash': hash_image(self.fingerprint_path)
        }

        users = self.load_users()

        users.append(user_data)
        self.save_users(users)

        self.clear_fields()
        self.show_popup("Success", f"User {user_data['name']} successfully registered!")

    def verify_user(self, instance):
        chooser = FileChooserIconView()
        popup = Popup(title="Select Fingerprint to Verify", content=chooser, size_hint=(0.9, 0.9))

        def on_selection(*args):
            if chooser.selection:
                selected_fp = chooser.selection[0]
                popup.dismiss()
                self.check_fingerprint(selected_fp)

        chooser.bind(on_submit=on_selection)
        popup.open()

    def check_fingerprint(self, filepath):
        fp_hash = hash_image(filepath)
        users = self.load_users()

        for user in users:
            if user['fingerprint_hash'] == fp_hash:
                self.show_popup("Verified", f"User: {user['name']}\nTime: {datetime.now()}\nEmp ID: {user['empid']}")
                return

        self.show_popup("Unregistered", f"Unknown user\nTime: {datetime.now()}")

    def clear_fields(self):
        self.name_input.text = ''
        self.aadhaar_input.text = ''
        self.contact_input.text = ''
        self.empid_input.text = ''
        self.day_spinner.text = 'Day'
        self.month_spinner.text = 'Month'
        self.year_spinner.text = 'Year'
        self.fingerprint_button.text = 'Select Fingerprint Image (Gallery)'
        self.fingerprint_path = ''

    def show_popup(self, title, message):
        popup = Popup(title=title,
                      content=Label(text=message),
                      size_hint=(0.6, 0.4))
        popup.open()

    def load_users(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'rb') as f:
                return pickle.load(f)
        return []

    def save_users(self, users):
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(users, f)

class MainApp(App):
    def build(self):
        return BimetricApp()

if __name__ == '__main__':
    MainApp().run()
