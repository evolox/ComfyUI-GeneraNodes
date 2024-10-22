import cv2
import numpy as np

class ImageTransformer:
    def __init__(self):
        self.image = None
        self.resized_image = None
        self.scale_factor = 1.0
        self.interpolation = cv2.INTER_AREA

    def load_image(self, image_path=None, image: np.ndarray = None):
        if image_path:
            self.image = cv2.imread(image_path)
        else:
            self.image = image
        if self.image is None:
            raise FileNotFoundError("Can't load an image")

    def resize_image(self, max_size):
        height, width = self.image.shape[:2]
        if width > height:
            self.scale_factor = max_size / width
        else:
            self.scale_factor = max_size / height

        if self.scale_factor < 1.0:
            self.interpolation = cv2.INTER_AREA
        elif self.scale_factor > 1.0:
            self.interpolation = cv2.INTER_CUBIC
        else:
            self.interpolation = cv2.INTER_LINEAR

        self.resized_image = cv2.resize(
            self.image, None, fx=self.scale_factor, fy=self.scale_factor, interpolation=self.interpolation)
        return self.resized_image

    def get_resized_image(self):
        return self.resized_image

    def get_original_image(self):
        return self.image

    def get_scale_factor(self):
        return self.scale_factor

    def get_transformed_image(self, M, output_size):
        transformed_image = cv2.warpPerspective(
            self.resized_image,
            M,
            output_size,
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0)
        )
        return transformed_image
    
class GeneraImageTransformer:
    def __init__(self):
        pass
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "image": ("IMAGE", ),
                "densePoseImage": ("IMAGE", ),
                "height": ("INT", ),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "process"
    OUTPUT_NODE = True
    CATEGORY = "Genera.ImageProcessing"

    def upload_to_gcp_storage(self, image, densePoseImage, height):
        return {image}

NODE_CLASS_MAPPINGS = {
    "Genera.ImageProcessing.ImageTransformer": GeneraImageTransformer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.ImageProcessing": "[Genera] Image Transformer",
}