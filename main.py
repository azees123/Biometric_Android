import os
import sqlite3
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.core.window import Window
from plyer import filechooser
from kivy.utils import platform

# Handle permissions on Android
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 name TEXT,
                 emp_id TEXT UNIQUE,
                 phone TEXT,
                 fingerprint_path TEXT
             )''')
    conn.commit()
    conn.close()

class FingerprintApp(App):
    def build(self):
        init_db()
        self.fingerprint_path = None

        # Create the main layout
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        # Register button
        register_btn = Button(text="Register", size_hint=(1, 0.2))
        register_btn.bind(on_press=self.open_register_popup)
        layout.add_widget(register_btn)

        # Verify button
        verify_btn = Button(text="Verify", size_hint=(1, 0.2))
        verify_btn.bind(on_press=self.open_verify_popup)
        layout.add_widget(verify_btn)

        # Label for displaying verification result
        self.result_label = Label(text="Verification Status will be shown here.", size_hint=(1, 0.1))
        layout.add_widget(self.result_label)

        return layout

    def open_register_popup(self, instance):
        self.reg_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.name_input = TextInput(hint_text="Enter Name", size_hint=(1, None), height=40)
        self.emp_id_input = TextInput(hint_text="Enter Employee ID", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter Phone Number", size_hint=(1, None), height=40)

        self.select_fp_btn = Button(text="Select Fingerprint Image", size_hint=(1, None), height=40)
        self.select_fp_btn.bind(on_press=self.select_fingerprint)

        submit_btn = Button(text="Submit", size_hint=(1, None), height=50)
        submit_btn.bind(on_press=self.register_user)

        self.reg_layout.add_widget(self.name_input)
        self.reg_layout.add_widget(self.emp_id_input)
        self.reg_layout.add_widget(self.phone_input)
        self.reg_layout.add_widget(self.select_fp_btn)
        self.reg_layout.add_widget(submit_btn)

        self.popup = Popup(title="Register User", content=self.reg_layout, size_hint=(0.9, 0.8))
        self.popup.open()

    def select_fingerprint(self, instance):
        filechooser.open_file(on_selection=self.set_fingerprint_path, filters=["*.png", "*.jpg", "*.jpeg", "*.bmp"])

    def set_fingerprint_path(self, selection):
        if selection:
            self.fingerprint_path = selection[0]
            self.select_fp_btn.text = f"Selected: {os.path.basename(self.fingerprint_path)}"
            print(f"Fingerprint selected: {self.fingerprint_path}")  # DEBUG

    def register_user(self, instance):
        name = self.name_input.text.strip()
        emp_id = self.emp_id_input.text.strip()
        phone = self.phone_input.text.strip()

        if not all([name, emp_id, phone, self.fingerprint_path]):
            self.show_popup("Error", "Please fill all fields and select a fingerprint.")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO users (name, emp_id, phone, fingerprint_path) VALUES (?, ?, ?, ?)",
                      (name, emp_id, phone, self.fingerprint_path))
            conn.commit()
            conn.close()
            self.popup.dismiss()
            self.show_popup("Success", "User registered successfully.")
        except sqlite3.IntegrityError:
            self.show_popup("Error", "Employee ID already exists.")

    def open_verify_popup(self, instance):
        # Show a pop-up before starting the verification process
        self.result_label.text = "Verifying fingerprint, please wait..."
        # Open file chooser to allow the user to select a fingerprint image for verification
        filechooser.open_file(on_selection=self.verify_fingerprint, filters=["*.png", "*.jpg", "*.jpeg", "*.bmp"])

    def verify_fingerprint(self, selection):
        try:
            if not selection:
                self.result_label.text = "No file selected. Please select a fingerprint."
                return

            selected_fp = os.path.basename(selection[0])
            print(f"Selected fingerprint file: {selected_fp}")  # DEBUG

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT name, emp_id, fingerprint_path FROM users")
            users = c.fetchall()
            conn.close()

            matched_user = None
            for user in users:
                stored_fp = os.path.basename(user[2])
                print(f"Comparing with stored fingerprint: {stored_fp}")  # DEBUG
                if stored_fp == selected_fp:
                    matched_user = user
                    break

            if matched_user:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.result_label.text = f"Access Granted!\nName: {matched_user[0]}\nEmp ID: {matched_user[1]}\nTime: {timestamp}"
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.result_label.text = f"Access Denied.\nUnknown fingerprint.\nTime: {timestamp}"

        except Exception as e:
            self.result_label.text = f"An error occurred: {str(e)}"
            print("Error during verification:", str(e))  # DEBUG

    def show_popup(self, title, message):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=message))
        close_btn = Button(text="Close", size_hint=(1, 0.3))
        layout.add_widget(close_btn)

        popup = Popup(title=title, content=layout, size_hint=(0.8, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    FingerprintApp().run()
