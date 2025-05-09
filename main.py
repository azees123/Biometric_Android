import os
import sqlite3
import hashlib
from datetime import datetime

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.utils import platform
from plyer import filechooser

# Request Android permissions if needed
if platform == 'android':
    from android.permissions import request_permissions, Permission
    from android.storage import app_storage_path
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
    DB_PATH = os.path.join(app_storage_path(), "users.db")
else:
    DB_PATH = "users.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        emp_id TEXT UNIQUE,
        phone TEXT,
        fingerprint_hash TEXT,
        fingerprint_name TEXT
    )''')
    conn.commit()
    conn.close()


def hash_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        return None


class FingerprintApp(App):
    def build(self):
        init_db()
        self.fingerprint_path = None

        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        register_btn = Button(text="Register", size_hint=(1, 0.2))
        register_btn.bind(on_press=self.open_register_popup)
        layout.add_widget(register_btn)

        verify_btn = Button(text="Verify", size_hint=(1, 0.2))
        verify_btn.bind(on_press=self.open_verify_popup)
        layout.add_widget(verify_btn)

        return layout

    def open_register_popup(self, instance):
        self.fingerprint_path = None

        self.reg_layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        self.name_input = TextInput(hint_text="Enter Name", size_hint=(1, None), height=40)
        self.emp_id_input = TextInput(hint_text="Enter Employee ID", size_hint=(1, None), height=40)
        self.phone_input = TextInput(hint_text="Enter Phone Number", size_hint=(1, None), height=40)

        self.select_fp_btn = Button(text="Select Fingerprint Image", size_hint=(1, None), height=40)
        self.select_fp_btn.bind(on_press=self.select_fingerprint)

        self.fp_label = Label(text="", size_hint=(1, None), height=30)

        submit_btn = Button(text="Submit", size_hint=(1, None), height=50)
        submit_btn.bind(on_press=self.register_user)

        self.reg_layout.add_widget(self.name_input)
        self.reg_layout.add_widget(self.emp_id_input)
        self.reg_layout.add_widget(self.phone_input)
        self.reg_layout.add_widget(self.select_fp_btn)
        self.reg_layout.add_widget(self.fp_label)
        self.reg_layout.add_widget(submit_btn)

        self.popup = Popup(title="Register User", content=self.reg_layout, size_hint=(0.9, 0.8))
        self.popup.open()

    def select_fingerprint(self, instance):
        filechooser.open_file(on_selection=self.set_fingerprint_path)

    def set_fingerprint_path(self, selection):
        if selection:
            self.fingerprint_path = selection[0]
            self.fp_label.text = f"Selected: {os.path.basename(self.fingerprint_path)}"

    def register_user(self, instance):
        name = self.name_input.text.strip()
        emp_id = self.emp_id_input.text.strip()
        phone = self.phone_input.text.strip()

        if not all([name, emp_id, phone, self.fingerprint_path]):
            self.show_popup("Error", "Please fill all fields and select a fingerprint.")
            return

        fingerprint_hash = hash_file(self.fingerprint_path)
        if not fingerprint_hash:
            self.show_popup("Error", "Failed to read fingerprint file.")
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("INSERT INTO users (name, emp_id, phone, fingerprint_hash, fingerprint_name) VALUES (?, ?, ?, ?, ?)",
                      (name, emp_id, phone, fingerprint_hash, os.path.basename(self.fingerprint_path)))
            conn.commit()
            conn.close()

            self.popup.dismiss()
            self.show_popup("Success", "User registered successfully.")
        except sqlite3.IntegrityError:
            self.show_popup("Error", "Employee ID already exists.")
        except Exception as e:
            self.show_popup("Error", str(e))

    def open_verify_popup(self, instance):
        filechooser.open_file(on_selection=self.verify_fingerprint)

    def verify_fingerprint(self, selection):
        if not selection or not os.path.exists(selection[0]):
            self.show_popup("Error", "No fingerprint file selected or file not found.")
            return

        fingerprint_hash = hash_file(selection[0])
        if not fingerprint_hash:
            self.show_popup("Error", "Could not read the fingerprint file.")
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name, emp_id, fingerprint_hash FROM users")
        users = c.fetchall()
        conn.close()

        for user in users:
            if fingerprint_hash == user[2]:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = f"Verified!\nName: {user[0]}\nEmp ID: {user[1]}\nTime: {timestamp}"
                self.show_popup("Access Granted", msg)
                return

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.show_popup("Access Denied", f"Unknown fingerprint.\nTime: {timestamp}")

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
  
