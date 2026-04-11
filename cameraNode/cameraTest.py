import cv2
from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog

# Create a hidden root window to prevent a blank Tkinter window from appearing
root = tk.Tk()
root.withdraw()

# Open the file explorer prompt
file_path = filedialog.askopenfilename(title="Select a YOLO model")

print(f"Selected file: {file_path}")

# Load a lightweight model (YOLO11n or YOLOv8n)
model = YOLO(file_path) 

# Initialize camera (0 is typically the default Pi camera)
cap = cv2.VideoCapture(0)

while cap.isOpened():
    success, frame = cap.read()
    if success:
        # Run YOLO inference on the frame
        # 'show=True' uses the built-in Ultralytics viewer, 
        # or use cv2.imshow for more control.
        results = model.predict(frame, conf=0.5)
        
        # Visualize the results on the frame
        annotated_frame = results[0].plot()

        # Display the output window
        cv2.imshow("YOLO Real-Time Demo", annotated_frame)

        # Break the loop if 'q' is pressed
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    else:
        break

cap.release()
cv2.destroyAllWindows()