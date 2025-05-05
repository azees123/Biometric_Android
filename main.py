import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
import pickle
import os
from datetime import datetime
from plyer import filechooser
from kivy.utils import platform

# Request permissions for Android if required
if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])

    from android.storage import app_storage_path
    app_path = app_storage_path()
    data_file = os.path.join(app_path, 'data.pkl')
else:
    data_file = os.path.join(os.getcwd(), 'data.pkl')

# Load and Save Data
def load_data():
    if os.path.exists(data_file):
        with open(data_file, 'rb') as f:
            return pickle.load(f)
    return []

def save_data(data):
    with open(data_file, 'wb') as f:
        pickle.dump(data, f)

# Main Screen UI
class MainScreen(BoxLayout):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        anchor = AnchorLayout(anchor_x='center', anchor_y='center')
        button_layout = GridLayout(cols=1, spacing=20, size_hint=(None, None))
        button_layout.size = (200, 120)

        register_btn = Button(text='Register', size_hint=(None, None), size=(200, 50), on_press=self.register_screen)
        verify_btn = Button(text='Verify', size_hint=(None, None), size=(200, 50), on_press=self.verify_screen)

        button_layout.add_widget(register_btn)
        button_layout.add_widget(verify_btn)

        anchor.add_widget(button_layout)
        self.add_widget(anchor)

    def register_screen(self, instance):
        self.clear_widgets()
        self.add_widget(RegisterScreen(go_back_callback=self.back_to_main))

    def verify_screen(self, instance):
        self.clear_widgets()
        self.add_widget(VerifyScreen(go_back_callback=self.back_to_main))

    def back_to_main(self, *args):
        self.clear_widgets()
        self.__init__()

# Register Screen UI
class RegisterScreen(BoxLayout):
    def __init__(self, go_back_callback=None, **kwargs):
        super(RegisterScreen, self).__init__(orientation='vertical', **kwargs)
        self.go_back_callback = go_back_callback
        self.data = load_data()
        self.next_id = len(self.data) + 1

        self.inputs = {
            'name': TextInput(hint_text='Name'),
            'aadhaar': TextInput(hint_text='Aadhaar No'),
            'phone': TextInput(hint_text='Phone No'),
            'employee_id': TextInput(hint_text='Employee ID'),
        }

        self.add_widget(Label(text=f'ID: {self.next_id}'))
        for field in self.inputs.values():
            self.add_widget(field)

        self.dob_label = Label(text="DOB: Not selected")
        self.add_widget(self.dob_label)
        self.add_widget(Button(text='Select DOB', on_press=self.show_date_chooser))

        self.fp_path = None
        self.add_widget(Button(text='Select Fingerprint', on_press=self.select_fp))

        self.add_widget(Button(text='Submit', on_press=self.submit))
        self.add_widget(Button(text='Back', on_press=self.back_to_main))

    def show_date_chooser(self, instance):
        layout = BoxLayout(orientation='vertical')
        days = Spinner(text='1', values=[str(i) for i in range(1, 32)])
        months = Spinner(text='1', values=[str(i) for i in range(1, 13)])
        years = Spinner(text='2000', values=[str(i) for i in range(1950, 2025)])

        layout.add_widget(Label(text='Day'))
        layout.add_widget(days)
        layout.add_widget(Label(text='Month'))
        layout.add_widget(months)
        layout.add_widget(Label(text='Year'))
        layout.add_widget(years)

        confirm_btn = Button(text='Set DOB')
        layout.add_widget(confirm_btn)

        popup = Popup(title='Select DOB', content=layout, size_hint=(0.8, 0.8))

        def set_dob(instance):
            self.dob_label.text = f"DOB: {days.text}/{months.text}/{years.text}"
            self.selected_dob = f"{days.text}/{months.text}/{years.text}"
            popup.dismiss()

        confirm_btn.bind(on_press=set_dob)
        popup.open()

    def select_fp(self, instance):
        def got_fp_path(selection):
            if selection:
                self.fp_path = selection[0]
                self.show_popup("Fingerprint Selected", f"Selected file:\n{self.fp_path}")
            else:
                self.show_popup("Error", "No file selected")

        # Open file chooser to select fingerprint image
        filechooser.open_file(on_selection=got_fp_path)

    def submit(self, instance):
        if not self.fp_path:
            self.show_popup("Error", "Please select a fingerprint image")
            return

        record = {
            'id': self.next_id,
            'name': self.inputs['name'].text,
            'dob': getattr(self, 'selected_dob', 'Not Selected'),
            'aadhaar': self.inputs['aadhaar'].text,
            'phone': self.inputs['phone'].text,
            'employee_id': self.inputs['employee_id'].text,
            'fingerprint': self.fp_path
        }

        self.data.append(record)
        save_data(self.data)
        self.show_popup("Registered", f"{record['employee_id']} - {record['name']} at {datetime.now()}")

        for field in self.inputs.values():
            field.text = ''
        self.dob_label.text = "DOB: Not selected"
        self.selected_dob = None
        self.fp_path = None
        self.next_id += 1
        self.clear_widgets()
        self.__init__(go_back_callback=self.go_back_callback)

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def back_to_main(self, instance):
        if self.go_back_callback:
            self.go_back_callback()

# Verify Screen UI
class VerifyScreen(BoxLayout):
    def __init__(self, go_back_callback=None, **kwargs):
        super(VerifyScreen, self).__init__(orientation='vertical', **kwargs)
        self.go_back_callback = go_back_callback
        self.data = load_data()

        # Button to select fingerprint for verification
        self.select_fp_button = Button(text='Select Fingerprint to Verify', on_press=self.select_fp)
        self.add_widget(self.select_fp_button)

        self.add_widget(Button(text='Back', on_press=self.back_to_main))

    def select_fp(self, instance):
        def got_fp_path(selection):
            if selection:
                fp_path = selection[0]
                self.verify_fingerprint(fp_path)
            else:
                self.show_popup("Error", "No file selected")

        # Open file chooser to select fingerprint image
        filechooser.open_file(on_selection=got_fp_path)

    def verify_fingerprint(self, path):
        matched = False
        selected_filename = os.path.basename(path)

        # Loop through registered data and match fingerprints
        for record in self.data:
            if os.path.basename(record['fingerprint']) == selected_filename:
                self.show_popup("Verified", f"{record['name']} ({record['employee_id']})\nVerified at {datetime.now()}")
                matched = True
                break

        if not matched:
            self.show_popup("Unknown", f"Fingerprint not registered\nChecked at {datetime.now()}")

    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.6, 0.4))
        popup.open()

    def back_to_main(self, instance):
        if self.go_back_callback:
            self.go_back_callback()

# Main App Class
class BiometricApp(App):
    def build(self):
        return MainScreen()

if __name__ == '__main__':
    BiometricApp().run()
