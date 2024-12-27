import numpy as np
import base64
from io import BytesIO
from PIL import Image


class MaskDrawer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "image_data": ("STRING", {"default": "", "multiline": True}),
            },
        }

    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("drawn_mask",)
    FUNCTION = "process_mask"
    CATEGORY = "Genera"

    def process_mask(self, image_data=None, mask_data=None):
        """
        Processes image and mask data from the frontend.
        """
        if not image_data:
            raise ValueError("No image data provided.")

        # Decode the uploaded image
        image_bytes = base64.b64decode(image_data.split(",")[1])
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)

        # Decode mask data if provided
        if mask_data:
            mask_bytes = base64.b64decode(mask_data.split(",")[1])
            mask_image = Image.open(BytesIO(mask_bytes)).convert("L")
            mask = np.array(mask_image)
        else:
            # If no mask data, create an empty mask
            mask = np.zeros((image_np.shape[0], image_np.shape[1]), dtype=np.uint8)

        return (mask,)


NODE_CLASS_MAPPINGS = {
    "Genera.MaskDrawer": MaskDrawer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.MaskDrawer": "Mask Drawer",
}