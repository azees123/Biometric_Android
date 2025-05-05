from datetime import datetime
import os
import pickle

from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.clock import mainthread

from android.storage import app_storage_path
from android.permissions import request_permissions, Permission
from android import activity, mActivity
from jnius import autoclass, cast

user_db = {}
APP_PATH = app_storage_path()
os.makedirs(APP_PATH, exist_ok=True)
DB_FILE = os.path.join(APP_PATH, 'user_db.pkl')

class FingerprintApp(App):
    def build(self):
        request_permissions([Permission.READ_EXTERNAL_STORAGE])
        self.load_user_db()

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.add_widget(Label(text="Fingerprint Authentication System", size_hint=(1, 0.1)))

        register_button = Button(text="Register User", size_hint=(1, 0.1))
        register_button.bind(on_press=self.register_user)
        self.layout.add_widget(register_button)

        verify_button = Button(text="Verify Fingerprint", size_hint=(1, 0.1))
        verify_button.bind(on_press=self.verify_fingerprint)
        self.layout.add_widget(verify_button)

        activity.bind(on_activity_result=self.on_activity_result)

        return self.layout

    def load_user_db(self):
        global user_db
        if os.path.exists(DB_FILE):
            with open(DB_FILE, 'rb') as f:
                user_db = pickle.load(f)

    def save_user_db(self):
        with open(DB_FILE, 'wb') as f:
            pickle.dump(user_db, f)

    def open_gallery(self, callback):
        self._file_callback = callback
        Intent = autoclass('android.content.Intent')
        intent = Intent(Intent.ACTION_GET_CONTENT)
        intent.setType("image/*")
        intent.addCategory(Intent.CATEGORY_OPENABLE)
        mActivity.startActivityForResult(intent, 1001)

    @mainthread
    def on_activity_result(self, requestCode, resultCode, intent):
        if requestCode == 1001 and resultCode == -1:
            uri = intent.getData()
            context = cast('android.content.Context', mActivity.getApplicationContext())
            content_resolver = context.getContentResolver()
            input_stream = content_resolver.openInputStream(uri)
            image_path = os.path.join(APP_PATH, f"fingerprint_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
            with open(image_path, 'wb') as f:
                f.write(input_stream.read())
            input_stream.close()

            if hasattr(self, '_file_callback') and self._file_callback:
                self._file_callback(image_path)

    def save_user_details(self, name, phone, reg_no, aadhaar_no, photo_path, fingerprint_image_path):
        if reg_no in user_db:
            self.show_popup("Error", "User already registered.")
            return False
        user_db[reg_no] = {
            'name': name,
            'phone': phone,
            'aadhaar_no': aadhaar_no,
            'photo': photo_path,
            'fingerprint': fingerprint_image_path,
            'verified': False,
            'registration_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_user_db()
        self.show_popup("Success", f"User {name} registered.")
        return True

    def check_fingerprint(self, reg_no, fingerprint_image_path):
        if reg_no not in user_db:
            self.show_popup("Denied", "Registration number not found.")
            return
        user = user_db[reg_no]
        if user['verified']:
            self.show_popup("Alert", "User already verified once.")
            return
        if user['fingerprint'] == fingerprint_image_path:
            user['verified'] = True
            self.save_user_db()
            self.show_popup("Access Granted", "Fingerprint verified.")
        else:
            self.show_popup("Access Denied", "Fingerprint does not match.")

    def register_user(self, instance):
        self.register_layout = BoxLayout(orientation='vertical', spacing=10)
        self.name_input = TextInput(hint_text="Name")
        self.phone_input = TextInput(hint_text="Phone")
        self.reg_no_input = TextInput(hint_text="Registration Number")
        self.aadhaar_input = TextInput(hint_text="Aadhaar Number")

        self.register_layout.add_widget(self.name_input)
        self.register_layout.add_widget(self.phone_input)
        self.register_layout.add_widget(self.reg_no_input)
        self.register_layout.add_widget(self.aadhaar_input)

        btn = Button(text="Select Fingerprint", size_hint=(1, None), height=40)
        btn.bind(on_press=lambda x: self.capture_and_register())
        self.register_layout.add_widget(btn)

        self.popup = Popup(title="Register", content=self.register_layout, size_hint=(0.9, 0.7))
        self.popup.open()

    def capture_and_register(self):
        name = self.name_input.text.strip()
        phone = self.phone_input.text.strip()
        reg_no = self.reg_no_input.text.strip()
        aadhaar_no = self.aadhaar_input.text.strip()
        if not all([name, phone, reg_no, aadhaar_no]):
            self.show_popup("Error", "Please fill all fields.")
            return

        self.popup.dismiss()

        def after_image_selected(image_path):
            photo_path = os.path.join(APP_PATH, f"{name}_photo.png")  # Simulated photo path
            self.save_user_details(name, phone, reg_no, aadhaar_no, photo_path, image_path)

        self.open_gallery(after_image_selected)

    def verify_fingerprint(self, instance):
        self.verify_layout = BoxLayout(orientation='vertical', spacing=10)
        self.reg_no_verify_input = TextInput(hint_text="Enter registration number")
        self.verify_layout.add_widget(self.reg_no_verify_input)

        btn = Button(text="Select Fingerprint", size_hint=(1, None), height=40)
        btn.bind(on_press=self.capture_for_verification)
        self.verify_layout.add_widget(btn)

        self.popup = Popup(title="Verify", content=self.verify_layout, size_hint=(0.9, 0.5))
        self.popup.open()

    def capture_for_verification(self, instance):
        reg_no = self.reg_no_verify_input.text.strip()
        self.popup.dismiss()

        def after_image_selected(image_path):
            self.check_fingerprint(reg_no, image_path)

        self.open_gallery(after_image_selected)

    def show_popup(self, title, message):
        box = BoxLayout(orientation='vertical', padding=10)
        box.add_widget(Label(text=message))
        btn = Button(text="Close", size_hint=(1, 0.2))
        btn.bind(on_press=lambda x: popup.dismiss())
        box.add_widget(btn)
        popup = Popup(title=title, content=box, size_hint=(0.8, 0.4))
        popup.open()

if __name__ == '__main__':
    FingerprintApp().run()
