import math
import cv2
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from PIL import Image, ImageTk
from ultralytics import YOLO

class ScentinelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Arsenic Sensor Detection and Analysis")
        # Load YOLO model from the same directory as this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(script_dir, "best.pt")
        self.model = YOLO(model_path)
        self.image = None
        self.image1 = None
        self.gray_image = None
        self.enhanced_gray = None
        self.object_table = None
        self.new_object_table = None
        self.unknown_object = None
        self.concentrations = []
        self.popt = None
        self.xData = []
        self.yData_normalized = []
        self.max_area = None

        self.setup_gui()

    def setup_gui(self):
        self.frame = ttk.Frame(self.root, padding=10)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.btn_select = ttk.Button(self.frame, text="Select Image", command=self.select_image)
        self.btn_select.pack(pady=5)

        self.canvas = tk.Canvas(self.frame, width=512, height=480, bg='gray')
        self.canvas.pack(pady=5)

        self.table_frame = ttk.Frame(self.frame)
        self.table_frame.pack(pady=5)

        self.btn_concentration = ttk.Button(self.frame, text="Input Concentrations", command=self.input_concentrations, state=tk.DISABLED)
        self.btn_concentration.pack(pady=5)

        self.btn_fit = ttk.Button(self.frame, text="Fit Curve & Estimate", command=self.fit_curve, state=tk.DISABLED)
        self.btn_fit.pack(pady=5)

    def select_image(self):
        image_path = filedialog.askopenfilename()
        if not image_path or not os.path.isfile(image_path):
            messagebox.showerror("Error", "File not found!")
            return

        self.image = cv2.imread(image_path)
        self.image1 = cv2.imread(image_path)
        self.process_image()
        self.display_image(self.image1)
        self.btn_detect.config(state=tk.NORMAL)

    def process_image(self):
        # Rotate if landscape
        if self.image.shape[1] < self.image.shape[0] / 2:
            self.image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE)
        # Resize
        self.image = self.image_resize(self.image, width=640, height=640)

    def image_resize(self, image, width=None, height=None, inter=cv2.INTER_AREA):
        dim = None
        (h, w) = image.shape[:2]
        if width is None and height is None:
            return image
        if width is None:
            r = height / float(h)
            dim = (int(w * r), height)
        else:
            r = width / float(w)
            dim = (width, int(h * r))
        resized = cv2.resize(image, dim, interpolation=inter)
        return resized

    def display_image(self, img):
        # Convert to RGB for display
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        # Fit image to canvas size while maintaining aspect ratio
        canvas_width, canvas_height = 640, 640
        img_pil.thumbnail((canvas_width, canvas_height), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(img_pil)
        self.canvas.create_image(240, 240, image=self.tk_img)

    def calculate_bg_ratio_intensity(self, img, mask):
        # Split the image into color channels
        b, g, r = cv2.split(img)
        
        # Avoid division by zero by adding a small value to green channel
        #g = g.astype(float) + 0.001
        if np.all(g == 0):
            mean_ratio = 0
        else:
            g = g.astype(float) + 0.001
            # Calculate blue/green ratio
            ratio = b.astype(float) / g
        
            # Calculate mean B/G ratio in the masked region
            mean_ratio = cv2.mean(ratio, mask=mask)[0]
        
        return mean_ratio

    def run_detection(self):
        results = self.model(self.image, conf=0.05, iou=0.01, agnostic_nms=True)
        object_table = pd.DataFrame(columns=['Object', 'Area', 'Signal'])

        orig_height, orig_width = self.image1.shape[:2]
        proc_height, proc_width = self.image.shape[:2]
        scale_x = orig_width / proc_width
        scale_y = orig_height / proc_height

        for i, box in enumerate(results[0].boxes):
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            orig_x1 = int(x1 * scale_x)
            orig_y1 = int(y1 * scale_y)
            orig_x2 = int(x2 * scale_x)
            orig_y2 = int(y2 * scale_y)
            x_center = int((orig_x1 + orig_x2) / 2)
            y_center = int((orig_y1 + orig_y2) / 2)
            radius = int((orig_x2 - orig_x1 + orig_y2 - orig_y1) / 4)
            cv2.circle(self.image1, (x_center, y_center), radius, (255, 0, 0), 8)
            font_scale = radius / 30
            thickness = max(1, int(radius / 8))
            cv2.putText(self.image1, str(i+1), (x_center-10, y_center+10),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)
            area = (x2 - x1) * (y2 - y1)
            mask = np.zeros(self.image.shape[:2], dtype=np.uint8)
            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)
            
            # Use calculate_bg_ratio_intensity instead of mean intensity
            bg_ratio = self.calculate_bg_ratio_intensity(self.image, mask)
            signal_value = bg_ratio * area
            '''
            # Calculate mean intensity over all RGB channels
            mean_intensity = cv2.mean(self.image, mask=mask)[:3]  # (B, G, R)
            intensity_sum = np.mean(mean_intensity) * area
            signal_value = intensity_sum / 3  # Average over RGB channels
            '''
            new_data = pd.DataFrame({'Object': [i+1], 'Area': [area], 'Signal': [signal_value]})
            object_table = pd.concat([object_table, new_data], ignore_index=True)

        self.max_area = object_table['Area'].max()
        object_table['Signal/Unit_Area'] = object_table['Signal'] / self.max_area
        max_obj = object_table['Signal/Unit_Area'].max()
        for i in range(len(object_table)):
            object_table.at[i, 'Relative Difference'] = (((max_obj) - (object_table.at[i, 'Signal/Unit_Area'])) / (max_obj))*100
        object_table = object_table.sort_values(by='Relative Difference', ascending=True)
        self.new_object_table = object_table[object_table['Relative Difference']>=0].reset_index(drop=True)
        self.object_table = object_table.drop(['Area', 'Signal'], axis=1)
        self.display_image(self.image1)
        self.display_table(self.object_table)
        self.btn_concentration.config(state=tk.NORMAL)

    def select_image(self):
        image_path = filedialog.askopenfilename()
        if not image_path or not os.path.isfile(image_path):
            messagebox.showerror("Error", "File not found!")
            return
        self.image = cv2.imread(image_path)
        self.image1 = cv2.imread(image_path)
        self.process_image()
        self.display_image(self.image1)
        # Run detection automatically when image is loaded
        self.run_detection()
        # Remove the detect button from the setup since we don't need it

    def display_table(self, df):
        for widget in self.table_frame.winfo_children():
            widget.destroy()
        cols = list(df.columns)
        tree = ttk.Treeview(self.table_frame, columns=cols, show='headings', height=5)
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120)
        for _, row in df.iterrows():
            tree.insert('', tk.END, values=list(row))
        tree.pack()

    def input_concentrations(self):
        if self.new_object_table is None or self.new_object_table.empty:
            messagebox.showerror("Error", "No objects detected.")
            return
        obj_numbers = self.new_object_table['Object'].tolist()
        unknown_object = simpledialog.askinteger("Unknown Object", f"Enter the object number whose concentration is unknown:\nAvailable: {obj_numbers}")
        if unknown_object not in obj_numbers:
            messagebox.showerror("Error", "Invalid object number.")
            return
        self.unknown_object = unknown_object
        self.concentrations = []
        for i in range(len(self.new_object_table)):
            obj = self.new_object_table.at[i, 'Object']
            if obj == unknown_object:
                self.concentrations.append(None)
                continue
            concentration = simpledialog.askstring("Concentration Input", f"Enter concentration for object {obj}:")
            if not concentration:
                messagebox.showerror("Error", "Concentration required.")
                return
            if concentration == '0':
                concentration = '0.000001'
            try:
                self.concentrations.append(float(concentration))
            except ValueError:
                messagebox.showerror("Error", "Invalid concentration value.")
                return
        self.btn_fit.config(state=tk.NORMAL)

    def fit_curve(self):
        xData = [c for c in self.concentrations if c is not None]
        yData = self.new_object_table[(self.new_object_table['Object'] != self.unknown_object)]['Relative Difference'].tolist()
        yData_normalized = np.array(yData) / 100.0
        def func(xdata, A, B, C, D):
            return ((A-D)/(1.0+((xdata/C)**B))) + D
        initialParameters = np.array([0.0, 0.1, 0.2, 1.0])
        try:
            popt, _ = curve_fit(func, xData, yData_normalized, maxfev=200000)
        except Exception as e:
            messagebox.showerror("Curve Fit Error", str(e))
            return
        self.popt = popt
        A, B, C, D = popt
        modelPredictions = func(xData, A, B, C, D)
        absError = modelPredictions - yData_normalized
        SE = np.square(absError)
        MSE = np.mean(SE)
        RMSE = np.sqrt(MSE)
        yMean = np.mean(yData_normalized)
        totalVariation = np.sum(np.square(yData_normalized - yMean))
        Rsquared = 1.0 - (MSE / totalVariation)
        self.xData = xData
        self.yData_normalized = yData_normalized
        self.show_fit_results(A, B, C, D, RMSE, Rsquared)
        self.plot_curve()
        self.estimate_unknown()

    def show_fit_results(self, A, B, C, D, RMSE, Rsquared):
        msg = f"Fitted Parameters: {A:.4f}, {B:.4f}, {C:.4f}, {D:.4f}\nRMSE: {RMSE:.4f}\nR-squared: {Rsquared:.4f}"
        messagebox.showinfo("Curve Fit Results", msg)

    def plot_curve(self):
        def func(xdata, A, B, C, D):
            return ((A-D)/(1.0+((xdata/C)**B))) + D
        f = plt.figure(figsize=(8, 6), dpi=100)
        axes = f.add_subplot(111)
        axes.plot(self.xData, self.yData_normalized, 'D', label='Data Points')
        xModel = np.linspace(min(self.xData), max(self.xData), 1000)
        yModel = func(xModel, *self.popt)
        axes.plot(xModel, yModel, 'r', label='Fitted Curve')
        axes.set_xlabel('Concentration(ppm)', fontweight='bold', fontsize=14)
        axes.set_ylabel('BL Signal', fontweight='bold', fontsize=14)
        plt.legend()
        plt.show()

    def estimate_unknown(self):
        def inverse_func(y, A, B, C, D):
            return C * ((A - D) / (y - D) - 1) ** (1 / B)
        unknown_percentage_change = self.new_object_table[self.new_object_table['Object'] == self.unknown_object]['Relative Difference'].iloc[0] / 100.0
        A, B, C, D = self.popt
        try:
            unknown_concentration_normalized = inverse_func(unknown_percentage_change, A, B, C, D)
        except Exception:
            unknown_concentration_normalized = float('nan')
        if math.isnan(unknown_concentration_normalized) or unknown_concentration_normalized < 0:
            result = f"The interpolated concentration of drug for object {self.unknown_object} is: 0"
        else:
            result = f"The interpolated concentration of drug for object {self.unknown_object} is: {unknown_concentration_normalized:.6f}"
        messagebox.showinfo("Unknown Concentration", result)

if __name__ == "__main__":
    root = tk.Tk()
    app = ScentinelApp(root)
    root.mainloop()
