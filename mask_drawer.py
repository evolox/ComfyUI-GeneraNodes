import numpy as np
import cv2
import dearpygui.dearpygui as dpg

class MaskDrawer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "initial_mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("drawn_mask",)
    FUNCTION = "draw_mask"
    CATEGORY = "Genera"

    def __init__(self):
        self.mask = None
        self.drawing = False
        self.last_point = None

    def draw_mask(self, image, initial_mask=None):
        """
        Allows drawing on an image mask.
        """
        height, width, _ = image.shape
        mask = np.zeros((height, width), dtype=np.uint8)
        
        if initial_mask is not None:
            mask = initial_mask.copy()
        
        def mouse_callback(event, x, y, flags, param):
            nonlocal mask, self
            if event == cv2.EVENT_LBUTTONDOWN:
                self.drawing = True
                self.last_point = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE and self.drawing:
                if self.last_point:
                    cv2.line(mask, self.last_point, (x, y), 255, thickness=5)
                    self.last_point = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                self.drawing = False
                self.last_point = None

        cv2.namedWindow('Mask Drawer')
        cv2.setMouseCallback('Mask Drawer', mouse_callback)
        
        while True:
            preview = image.copy()
            preview[mask > 0] = (0, 255, 0)  # Highlight mask in green
            cv2.imshow('Mask Drawer', preview)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # ESC to exit
                break

        cv2.destroyAllWindows()
        self.mask = mask
        return (mask,)

NODE_CLASS_MAPPINGS = {
    "Genera.MaskDrawer": MaskDrawer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.MaskDrawer": "Mask Drawer",
}