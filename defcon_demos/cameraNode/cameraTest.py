import cv2 # needed for computer vision and camera access
import threading # needed to run the camera capture on a background thread
from ultralytics import YOLO # needed to load the YOLO model and run predictions
import tkinter as tk # needed to create a hidden root window for the file dialog
from tkinter import filedialog # needed to open a file explorer dialog to select the YOLO model file


class LatestFrameCapture:
    """
    Runs camera capture on a background thread, always keeping only the
    most recent frame.  The main thread never blocks waiting on a stale
    buffer, it just reads whatever arrived last.
    """

    def __init__(self, src=0):
        """
        Basic Init method

        Args:
            src (int, optional): Which camera to use. Defaults to 0.
        """

        self.cap = cv2.VideoCapture(src)
        self.lock = threading.Lock()
        self.frame = None
        self.running = True
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        """
        Background reader to read and store the latest frame from the camera into self.frame
        """

        while self.running:
            ok, frame = self.cap.read()
            if ok:
                with self.lock:
                    self.frame = frame

    def read(self):
        """
        helper method to read and store the latest frame

        Returns:
            frame: the latest frame from the camera, or None if no frame is available
        """

        with self.lock:
            return self.frame is not None, (self.frame.copy() if self.frame is not None else None)

    def release(self):
        """
        release the camera and stop the background thread
        """
        
        self.running = False
        self._thread.join()
        self.cap.release()


# Create a hidden root window to prevent a blank Tkinter window from appearing
root = tk.Tk()
root.withdraw()

# Open the file explorer prompt
file_path = filedialog.askopenfilename(title="Select a YOLO model")
print(f"Selected file: {file_path}")

model = YOLO(file_path)
cap = LatestFrameCapture(0)

while True:
    success, frame = cap.read()
    if not success:
        continue

    results = model.predict(frame, conf=0.5)
    annotated_frame = results[0].plot()

    cv2.imshow("YOLO Real-Time Demo", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
