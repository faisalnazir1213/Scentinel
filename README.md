# Scentinel App
The Luminescent BioSensor Analysis application(Scentinel App) offers a user-friendly interface for uploading an image of a Luminescent sensor. It then analyzes the various wells' signal responses and converts them into quantitative values. Using these values, the unknown concentration of the sample is estimated through statistical analysis.

# Build Tools
Code is written in Python using mainly the kivy library and Flask, built on Linux using Buildozer, and the image segmentation part is performed on the server (Azure)

# App with your Server Address
To test the app with a custom server(local as well) you can download it from the below link and enter the server address manually<br />
1. One way is to deploy the Flask folder to Azure as a web app and use the custom address from Azure<br />
2. Otherwise run the flask.py in your python IDE(from flask folder) and use the IP address directly<br />

https://drive.google.com/file/d/10f9xIdZ5dqhwib-6kpyFWxD1eA3f-s8L/view?usp=sharing<br />

# Android(Apk) Files (no server address required, but the subscription will expire)

https://drive.google.com/file/d/1gN8H9p4lOC7P7AtP-DKNN-R80PfJFSfj/view?usp=sharing<br />

# Working of App
After loading the image, it took some seconds to process and display back the image

![App_Demo](https://github.com/faisalnazir1213/Scentinel/assets/66552427/a5c7b491-dbb9-49b3-aa06-1b96dd588ee3)<br />

# App Requirements<br />

•	Android platform<br />
•	Access to media files<br />
•	Internet Connectivity<br />

# Usage

1. Open the app and load your image.
2. Click the ‘Show Relative Changes' button to view the values of each well
3. Enter the sample well number in the box and submit it (do this only at the end).
4. In a new prompt enter calibration solution concentrations (0, 1, 2, 3, 4...) and submit to see the tentative concentration of the sample.


<img width="488" alt="Layout" src="https://github.com/faisalnazir1213/Scentinel/assets/66552427/efc473a9-5feb-4d12-8b1d-bc5a579b997b">

# Other Information
a. The processed image will be displayed as labeled objects. Processing is based on network quality (while processing it will show just a dark screen).<br />
b. The highest value of Relative Change or lower values in signal means the most inhibition of bacteria/most toxic effect.<br />
c. If it shows extra boxes after the highest concentration, enter any value more than the higher concentration they are noisy pixels due to light. <br />
d. If there is no internet connection, or if there is a server-side issue which can happen due to upgradation, the app will crash.<br />


# Further details of libraries and modules
<!-- 
# Image Segmentation
https://github.com/stardist/stardist/
-->
# Buildozer
#https://buildozer.readthedocs.io/en/latest/installation.html <br />
https://buildozer.readthedocs.io/en/latest/quickstart.html  <br />

# Kivy 
https://kivy.org/doc/stable/guide/basic.html

# Flask to server Guide (Azure)
https://medium.datadriveninvestor.com/deploying-flask-web-app-on-microsoft-azure-89cea17e9114

#Python
3.10.14(Conda)

<!-- https://drive.google.com/file/d/16YoRcfn2EU35itPo5yYxtPmKU9CwhYLT/view?usp=sharing<br /> 
-->
