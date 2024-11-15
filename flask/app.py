
import cv2
#from matplotlib import pyplot as plt
from networkx import selfloop_edges
from stardist.models import StarDist2D
from csbdeep.utils import normalize
from skimage.measure import regionprops
import pandas as pd
import numpy as np
from flask import Flask, app, request, jsonify, send_file, url_for, abort
from werkzeug.utils import secure_filename
import os
#from flask import send_file, abort

app = Flask(__name__)

# Define main directory and create folders
main_directory = os.path.dirname(os.path.abspath(__file__))
upload_folder = os.path.join(main_directory, 'uploads')
temp_folder = os.path.join(main_directory, 'temp')

for folder in [upload_folder, temp_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.config['uploads'] = upload_folder
app.config['TEMP_FOLDER'] = temp_folder
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
object_table_data = None

@app.route('/process_image', methods=['POST'])
def process_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part', 'message': 'Please upload a file.'})

    selected_file = request.files['file']

    if selected_file.filename == '':
        return jsonify({'error': 'No selected file', 'message': 'Please select a file.'})

    if selected_file:
        filename = secure_filename(selected_file.filename)
        image_path = os.path.join(upload_folder, filename)
        selected_file.save(image_path)

        # Load the image
        image = cv2.imread(image_path)

        # Rotate the image if it is in landscape mode
        if image.shape[1] < 200:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)

        def image_resize(image, width = None, height = None, inter = cv2.INTER_AREA):
            # initialize the dimensions of the image to be resized and grab the image size
            dim = None
            (h, w) = image.shape[:2]

            # if both the width and height are None, then return the original image
            if width is None and height is None:
                return image

            # check to see if the width is None
            if width is None:
                # calculate the ratio of the height and construct the
                # dimensions
                r = height / float(h)
                dim = (int(w * r), height)

            # otherwise, the height is None
            else:
                # calculate the ratio of the width and construct the dimensions
                r = width / float(w)
                dim = (width, int(h * r))

            # resize the image
            resized = cv2.resize(image, dim, interpolation = inter)

            # return the resized image
            return resized

        if image.shape[0] > 1000 or image.shape[1] > 1000:
            image = image_resize(image, width=800, height=800)
        else:
            pass
        
        # Convert image to 16-bit grayscale
        image1 = image
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        #manual Operation
        brightness = 1.5
        # Adjusts the contrast by scaling the pixel values
        contrast = 2 
        image = cv2.addWeighted(image, contrast, np.zeros(image.shape, image.dtype), 0, brightness) 
        #image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Normalize the blue channel
        blue_channel=image
        blue_channel_norm = normalize(blue_channel, 1, 99.8, axis=None)

        # Load the AI model
        model = StarDist2D.from_pretrained('Versatile (fluorescent nuclei)')

        # Predict objects
        labels, _ = model.predict_instances(blue_channel_norm,nms_thresh=0.01, prob_thresh=0.67)

        # Get properties of labeled objects
        props = regionprops(labels)

        # Create data table to store object properties
        object_table = pd.DataFrame(columns=['Object', 'Area'])

        # Draw boundry around objects and label with numbers
        for i, prop in enumerate(props):
            y1, x1, y2, x2 = prop.bbox
            x_center = int((x1 + x2) / 2)
            y_center = int((y1 + y2) / 2)
            radius = int((x2 - x1 + y2 - y1) / 4)
            cv2.circle(image1, (x_center, y_center), radius, (255, 255, 255), 3)
            font_scale = radius / 30  # Adjust the divisor to control the font size
            thickness = int(radius / 8)  # Adjust the divisor to control the thickness of the text

            cv2.putText(image1, str(i+1), (x_center-10, y_center+10), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 255), thickness)
            # Calculate mean Signal and area of objects and store in data table
            label = i + 1
            intensity_sum = 0
            pixel_count = 0
            for coord in prop.coords:
                intensity_sum += blue_channel[coord[0], coord[1]]
                pixel_count += 1
            mean_intensity = intensity_sum
            area = prop.area
            new_data = pd.DataFrame({'Object': [label],'Area': [area],'Signal': [mean_intensity]})
            object_table = pd.concat([object_table, new_data], ignore_index=True)

        # Calculate difference in Signal for each object
        max_area = object_table['Area'].max()
        object_table['Signal/Unit_Area'] = object_table['Signal'] / max_area
        object_table['Signal'] = object_table['Signal'] / max_area
        max_obj = object_table['Signal/Unit_Area'].max()
        for i in range(len(object_table)):
            #object_table.at[i, 'Relative Difference'] = ((max_composite_metric - object_table.at[i, 'Signal'])/max_composite_metric)*100
            object_table.at[i, 'Signal/Unit_Area'] = (((max_obj) - (object_table.at[i, 'Signal/Unit_Area'])) / (max_obj))*100

        # Sort the table by Relative Percentage Change in ascending order
        object_table = object_table.sort_values(by='Signal/Unit_Area', ascending=True)
        
        #if want to include 0% change objects(as somtimes there are no objects with change)
        new_object_table = object_table[object_table['Signal/Unit_Area'] >= 0]

        # Set the new_object_table attribute
        object_table = new_object_table

        # Create a white canvas to overlay labels
        processed_image = image1.copy()

        # Save the processed image
        output_image_path = image_path.replace('.', '_processed.')  # Save with a different name
        cv2.imwrite(output_image_path, processed_image)

        # Construct the response
        processed_image_url = url_for('get_processed_image', filename=os.path.basename(output_image_path))
        print(processed_image_url)
        print(object_table.to_dict(orient='records'))
        
        response = {
            'message': 'Image processed successfully',
            'processed_image_url': processed_image_url,
            'object_table': object_table.to_dict(orient='records')
        }

        return jsonify(response)
    else:
        return jsonify({'error': 'No Image Uploaded', 'message': 'Please upload an image before processing.'})
    
@app.route('/processed_image/<filename>', methods=['GET'])
def get_processed_image(filename):
    processed_image_path = os.path.join(app.config['uploads'], filename)
    if os.path.exists(processed_image_path):
        return send_file(processed_image_path, mimetype='image/jpeg')
    else:
        abort(404, description='Image not found')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
