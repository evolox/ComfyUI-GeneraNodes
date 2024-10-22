import cv2
import torch
import numpy as np

from .densepose import HumanHeightDetector

class ImageTransformer:
    def __init__(self):
        self.image = None

    def load_image(self, image_path=None, image: np.ndarray = None):
        if image_path:
            self.image = cv2.imread(image_path)
            if self.image is None:
                raise FileNotFoundError(f"Image not found at path: {image_path}")
        else:
            self.image = image
            if self.image is None:
                raise ValueError("Provided image array is None")
        if self.image is None:
            raise FileNotFoundError("Can't load an image")

    def get_transformed_image(self, M):
        if self.image is None:
            raise ValueError("No image loaded to transform.")

        output_size = (self.image.shape[1], self.image.shape[0])

        try:
            transformed_image = cv2.warpPerspective(
                self.image,
                M,
                output_size,
                flags=cv2.INTER_LANCZOS4,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=(0, 0, 0)
            )
        except cv2.error as e:
            print(f"OpenCV error during warpPerspective: {e}")
            raise

        return transformed_image

class GeneraImageTransformer:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE", ),
                "densePoseImage": ("IMAGE", ),
                "height": ("INT", ),
            },
            "optional": {},
        }

    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "process"
    CATEGORY = "Genera/ImageProcessing"

    def process(self, images, densePoseImage, height):
        if isinstance(images, torch.Tensor):
            if images.ndim != 4:
                raise ValueError(f"Expected images to have 4 dimensions (Batch, W, H, C), but got {images.ndim} dimensions")
            images_np = images.detach().cpu().numpy()
        elif isinstance(images, np.ndarray):
            images_np = images
        else:
            raise TypeError(f"Unsupported type for images: {type(images)}")

        if images_np.ndim != 4:
            raise ValueError(f"Expected images to have 4 dimensions (Batch, W, H, C), but got {images_np.ndim} dimensions")

        transformer = ImageTransformer()
        transformer.load_image(image=images_np[0])

        M = np.array([
            [1.0, 0.0, .0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)

        try:
            transformed_image = transformer.get_transformed_image(M)
        except cv2.error as e:
            print(f"OpenCV error during warpPerspective: {e}")
            raise
        except ValueError as e:
            print(f"Value error during warpPerspective: {e}")
            raise
        
        print(images.shape)
        print(densePoseImage.shape)
        
        detector = HumanHeightDetector(densePoseImage.detach().cpu().numpy()[0])
        top, botom, head_bottom = detector.do_measurments()
        
        detector.cv_image = self._resize_with_aspect_ratio(transformed_image, width=512)
        transformed_image = detector.visualize()
        
        result_image = torch.from_numpy(transformed_image).unsqueeze(0)

        return (result_image, )
    
    def _resize_with_aspect_ratio(self, image, width=None, height=None, inter=cv2.INTER_LANCZOS4):
        h, w = image.shape[:2]
        if width is None and height is None:
            return image

        if width is not None:
            ratio = width / float(w)
            dim = (width, int(h * ratio))
        else:
            ratio = height / float(h)
            dim = (int(w * ratio), height)

        return cv2.resize(image, dim, interpolation=inter)


# Исправленные маппинги узлов
NODE_CLASS_MAPPINGS = {
    "GeneraImageTransformer": GeneraImageTransformer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeneraImageTransformer": "[Genera] Image Transformer",
}