import threading
from queue import Queue
from visca_over_ip import Camera
import time

class VISCAControlThread(threading.Thread):
    def __init__(self, camera: Camera,
                  ptQueue: Queue,
                  zoomQueue: Queue,
                  focusQueue: Queue,
                  controlQueue: Queue
                ):
        threading.Thread.__init__(self)
        self.camera = camera
        self.ptQueue = ptQueue
        self.zoomQueue = zoomQueue
        self.focusQueue = focusQueue
        self.controlQueue = controlQueue
        self.running = True

    def run(self):
        print("VISCA Control Thread Started")
        while self.running:
            if self.controlQueue.qsize() > 0:
                control = self.controlQueue.get
                if control == 'exit':
                    self.running = False
                self.controlQueue.task_done()
                with self.controlQueue.mutex:
                    self.controlQueue.queue.clear()
            start_time = time.time()
            if self.ptQueue.qsize() > 0:
                ptSpeed = self.ptQueue.get()
                print(f"Pan Speed: {ptSpeed[0]}, Tilt Speed: {ptSpeed[1]}")
                self.camera.pantilt(ptSpeed[0], ptSpeed[1])
                self.ptQueue.task_done()
                print(f"Time taken: {time.time() - start_time}")
            if self.zoomQueue.qsize() > 0:
                zoomSpeed = self.zoomQueue.get()
                self.camera.zoom(zoomSpeed)
                self.zoomQueue.task_done()
            time.sleep(0.01)

    def stop(self):
        self.running = False
        self.controlQueue.put('exit')