import math
import kivy
from kivy.animation import Clock
from kivy.app import App
from kivy.uix.image import AsyncImage, Image
from kivy.uix.filechooser import FileChooserListView
import pandas as pd
import numpy as np
from scipy.optimize import curve_fit

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy import platform
from kivy.factory import Factory

import requests
from kivy.core.window import Window

# Updated Android permission imports
if platform == 'android':
    from android.permissions import Permission, check_permission, request_permissions
    from android.storage import primary_external_storage_path
    from jnius import autoclass, PythonJavaClass, java_method

from kivy.uix.filechooser import FileChooserIconLayout
from kivy.lang import Builder
from plyer import filechooser
import shutil
from kivy.network.urlrequest import UrlRequest
from kivy.graphics import Color, Rectangle
import os

kivy.require('2.0.0')

class ImageProcessorApp(App):
    
    def build(self):
        # Request permissions on app start for Android
        if platform == 'android':
            self.request_android_permissions()

        root_folder = self.user_data_dir
        uploads_folder = os.path.join(root_folder, 'uploads')

        # Create the uploads folder if it doesn't exist
        os.makedirs(uploads_folder, exist_ok=True)
        
        self.title = 'Image Processor App'
        self.query_layout = BoxLayout(orientation='vertical')
        layout = BoxLayout(orientation='vertical')  
         
        # Image display
        image_layout = BoxLayout(size_hint=(1, 1))
        self.image_display = AsyncImage(allow_stretch=True, keep_ratio=True)
        image_layout.add_widget(self.image_display)
        layout.add_widget(image_layout)

        self.concentration_display = Label(text="", size_hint=(1, 0.1), height=50, markup=True, bold=True)
        layout.add_widget(self.concentration_display)

        # URL input for developer only
        self.url_input = TextInput(text='', multiline=False, size_hint=(1, 0.1))

        button = Button(text='LOAD IMAGE', size_hint=(1, 0.1), markup=True, bold=True)
        button.bind(on_press=self.open_native_gallery)
        layout.add_widget(button)
        
        # Show Table Data button
        show_table_button = Button(text='SHOW RELATIVE CHANGE', size_hint=(1, 0.1), markup=True, bold=True)
        show_table_button.bind(on_release=self.show_table_data)
        layout.add_widget(show_table_button)

        # Initialize the table data content
        self.table_data_content = BoxLayout(orientation='vertical', spacing=10)
        self.table_data_popup = Popup(title='TABLE', content=self.table_data_content, size_hint=(0.8, 0.6))
        
        # Input for unknown object
        self.unknown_object_input = TextInput(text='', multiline=False, size_hint=(1, 0.1), halign='center')
        unknown_object_label = Label(text="[b]ENTER LABEL NUMBER OF SAMPLE:[/b]", size_hint=(1, 0.1), markup=True)
        unknown_object_layout = BoxLayout(orientation='vertical',size_hint=(1,0.2))
        unknown_object_layout.add_widget(unknown_object_label)
        unknown_object_layout.add_widget(self.unknown_object_input)
        layout.add_widget(unknown_object_layout)
        
        # Submit button for unknown concentrations
        self.submit_button = Button(text='SUMBIT', on_press=self.submit_concentrations, size_hint=(1, 0.1), markup=True, bold=True)
        layout.add_widget(self.submit_button)
        
        return layout

    def request_android_permissions(self):
        """Request necessary Android permissions"""
        if platform == 'android':
            permissions = [
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.CAMERA,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE
            ]
            request_permissions(permissions, self.handle_permissions)

    def handle_permissions(self, permissions, grant_results):
        """Handle permission request results"""
        granted_permissions = [perm for perm, granted in zip(permissions, grant_results) if granted]
        denied_permissions = [perm for perm, granted in zip(permissions, grant_results) if not granted]
        
        if denied_permissions:
            self.show_error_popup("Permissions Required", 
                                f"Some permissions were denied: {denied_permissions}. "
                                "The app may not function properly.")
        
    def check_permissions(self):
        """Check if required permissions are granted"""
        if platform != 'android':
            return True
            
        required_permissions = [
            Permission.READ_EXTERNAL_STORAGE,
            Permission.WRITE_EXTERNAL_STORAGE
        ]
        
        return all(check_permission(perm) for perm in required_permissions)
        
    def open_native_gallery(self, instance):
        def handle_selection(selection):
            if selection:
                image_path = selection[0]
                Clock.schedule_once(lambda dt: self.load_image(None, image_path))

        def bind_on_submit(selection):
            if platform != 'android' or self.check_permissions():
                if selection:
                    Clock.schedule_once(lambda dt: self.load_image(None, selection[0]))
            else:
                self.request_android_permissions()
                self.show_error_popup("Permissions Required", 
                                    "Please grant storage permissions to access images.")

        filechooser.open_file(title='<b>CHOOSE IMAGE</b>', on_selection=bind_on_submit)
    
    def load_image(self, instance, selected_file, *args):
        if selected_file:
            image_path = selected_file
            self.image_display.source = image_path
            self.image_path = image_path

            # Define the constant path
            path = "/process_image"

            # Get the user-entered URL
            url = self.url_input.text.strip()

            if not url:
                # Default base URL
                base_url = "https://*****.azurewebsites.net"
            else:
                base_url = url

            # Combine the base URL with the constant path
            url = base_url + path
            
            file_path = self.image_path
            files = {'file': open(file_path, 'rb')}
            response = requests.post(url, files=files)

            if response is None:
                self.show_error_popup("No Response", "No response received from the server.")

            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    object_data = {}
                    for row in data['object_table']:
                        object_number = row['Object']
                        signal_area  = round(row['Signal'], 2)
                        object_data[object_number] = signal_area

                    df = pd.DataFrame(list(object_data.items()), columns=['Object', 'Relative Change'])
                    self.object_table = df

                    processed_image_url = data.get('processed_image_url')
                    processed_image_url= base_url + processed_image_url
                    if processed_image_url:
                        try:
                            self.image_display.source = processed_image_url
                        except Exception as e:
                            self.show_error_popup("Image Display Error", f"Error displaying image: {e}")
                    else:
                        self.show_error_popup("No Processed Image URL", "No processed image URL received from the server.")

                except ValueError:
                        self.show_error_popup("Server Error", "Please check the URL and try again.")

    def show_table_data(self, instance):
        if hasattr(self, 'object_table') and isinstance(self.object_table, pd.DataFrame) and not self.object_table.empty:
            content = BoxLayout(orientation='vertical')
            table_label = Label(text=self.object_table[['Object', 'Relative Change']].to_string(index=False))
            content.add_widget(table_label)
            close_button = Button(text='CLOSE',size_hint=(0.2, 0.2))
            content.add_widget(close_button)
            popup = Popup(title='TABLE', content=content, size_hint=(0.8, 0.6))
            close_button.bind(on_release=popup.dismiss)
            popup.open()
        else:
            self.show_error_popup("No Table Data", "Please process an image.")     
            
    def submit_concentrations(self, instance):
        global unknown_object
        unknown_object = int(self.unknown_object_input.text) if self.unknown_object_input.text else None
        if unknown_object is None:
            self.show_error_popup("Unknown Object Missing", "Enter a valid object number.")
            return
        self.unknown_object = unknown_object
        self.concentrations(instance)
        instance.disabled = False
            
    def concentrations(self, instance):
        concentrations = []
        query_layout = BoxLayout(orientation='vertical')

        for i in range(len(self.object_table)):
            if self.object_table.at[i, 'Object'] == unknown_object:
                concentrations.append(None)
                continue    
            concentration_input = TextInput(text='', multiline=False, input_filter='float')
            concentration_label = Label(text=f"Value of {self.object_table.at[i, 'Object']}: ")
            concentration_layout = BoxLayout(orientation='horizontal')
            concentration_layout.add_widget(concentration_label)
            concentration_layout.add_widget(concentration_input)
            query_layout.add_widget(concentration_layout)
            concentrations.append(concentration_input)

        content = BoxLayout(orientation='vertical', size_hint=(1, 1))

        with content.canvas.before:
            Color(0, 0, 0, 0)
            Rectangle(pos=content.pos, size=content.size)

        content.add_widget(query_layout)
        
        submit_button = Button(text='SUBMIT', size_hint=(0.3, 0.1))
        content.add_widget(submit_button)
        
        popup = Popup(title='CONCENTRATIONS lOWER TO HIGHER', content=content, auto_dismiss=False, size_hint=(None, None))
        popup.size = (Window.width * 0.6, Window.height * 0.6)
        submit_button.bind(on_release=lambda x: self.process_concentrations(popup, concentrations))
        popup.open()
        
    def process_concentrations(self, popup, concentrations):
        entered_concentrations = []

        for concentration in concentrations:  
            if concentration is not None:
                entered_concentrations.append(float(concentration.text) if concentration.text else None)
            else:
                entered_concentrations.append(None)
        
        xData = [c for c in entered_concentrations if c is not None]
        yData = ([self.object_table.at[i, 'Relative Change'] for i in range(len(self.object_table)) if self.object_table.at[i, 'Object'] != unknown_object])        
        
        if all(concentration is None for concentration in entered_concentrations):
            static_values = [0, 0.1, 0.5, 1]
            remaining_length = len(entered_concentrations) - len(static_values)

            if remaining_length > 0:
                even_numbers = [2 * i for i in range(1, remaining_length + 2)]
                xData = static_values + even_numbers
            else:
                xData = static_values[:len(entered_concentrations) - 1]

            xData = xData[:len(entered_concentrations) - 1]

            yData = sorted([self.object_table.at[i, 'Relative Change'] for i in range(len(self.object_table)) if self.object_table.at[i, 'Object'] != unknown_object], reverse=False)
       
        popup.dismiss()    
    
        def func(xdata, A, B, C, D):
            return ((A-D)/(1.0+((xdata/C)**B))) + D

        yData_normalized = np.array(yData) / 100.0

        initialParameters = np.array([0.0, 0.1, 0.2, 1.0])

        popt, _ = curve_fit(func, xData, yData_normalized,maxfev=100000)

        A, B, C, D = popt

        modelPredictions = func(xData, A, B, C, D)

        modelPredictions_original = modelPredictions * 100.0
                  
        def inverse_func(y, A, B, C, D):
            return C * ((A - D) / (y - D) - 1) ** (1 / B)                        
        
        unknown_percentage_change = self.object_table.loc[self.object_table['Object'] == unknown_object, 'Relative Change'].iloc[0] / 100.0

        unknown_concentration_normalized = inverse_func(unknown_percentage_change, A, B, C, D)

        if math.isnan(unknown_concentration_normalized) or unknown_concentration_normalized < 0:
            interpolated_concentration = f"The interpolated concentration for {unknown_object} is: 0"
        else:           
            if unknown_concentration_normalized > 2:
                concentration_status = "[color=ff0000]Toxic[/color]"
            else:
                concentration_status = "[color=00ff00]Normal[/color]"
            
            interpolated_concentration = f"CONCENTRATION FOR {unknown_object} IS: [b]{unknown_concentration_normalized:.3f}[/b], STATUS: {concentration_status}"

        self.concentration_display.text = interpolated_concentration
        
        popup.dismiss()

    def show_error_popup(self, title, message):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text=message))
        ok_button = Button(text='OK', size_hint=(0.2, 0.1))
        content.add_widget(ok_button)
        popup = Popup(title=title, content=content, auto_dismiss=True, size_hint=(None, None))
        popup.size = (Window.width * 0.6, Window.height * 0.6) 
        ok_button.bind(on_release=popup.dismiss)
        popup.open()

if __name__ == '__main__':
    ImageProcessorApp().run()
