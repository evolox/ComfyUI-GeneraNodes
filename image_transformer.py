import cv2
import torch
import numpy as np

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
                "densePoseImage": ("IMAGE", ),  # Если не используется, можно удалить
                # "height": ("INT", ),  # Удалено, так как функционал resize_image удалён
            },
            "optional": {},
        }

    RETURN_TYPES = ("IMAGE", )
    FUNCTION = "process"
    CATEGORY = "Genera/ImageProcessing"

    def process(self, images, densePoseImage, height=None):  # height по умолчанию None
        # print(f"Received image shape: {images.shape}")

        if isinstance(images, torch.Tensor):
            if images.ndim != 4:
                raise ValueError(f"Expected images to have 4 dimensions (Batch, W, H, C), but got {images.ndim} dimensions")
            images_np = images.detach().cpu().numpy()
            # print(f"Converted torch.Tensor to numpy array with shape: {images_np.shape}")
        elif isinstance(images, np.ndarray):
            images_np = images
            # print(f"Received numpy array with shape: {images_np.shape}")
        else:
            raise TypeError(f"Unsupported type for images: {type(images)}")

        if images_np.ndim != 4:
            raise ValueError(f"Expected images to have 4 dimensions (Batch, W, H, C), but got {images_np.ndim} dimensions")

        first_image = images_np[0]
        # print(f"First image shape (W, H, C): {first_image.shape}")

        if first_image.ndim != 3:
            raise ValueError(f"Expected first image to have 3 dimensions (W, H, C), but got {first_image.ndim} dimensions")

        first_image_hwc = first_image

        transformer = ImageTransformer()
        transformer.load_image(image=first_image_hwc)

        M = np.array([
            [1.0, 0.0, .0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float32)
        # print(f"Transformation matrix M:\n{M}")

        try:
            transformed_image = transformer.get_transformed_image(M)
        except cv2.error as e:
            print(f"OpenCV error during warpPerspective: {e}")
            raise
        except ValueError as e:
            print(f"Value error during warpPerspective: {e}")
            raise

        if transformed_image.ndim == 2: # grayscale
            transformed_image = np.expand_dims(transformed_image, axis=2)

        if transformed_image.shape[2] == 1:
            transformed_image = np.repeat(transformed_image, 3, axis=2)
            print(f"Converted single channel to three channels, new shape: {transformed_image.shape}")

        if isinstance(images, torch.Tensor):
            transformed_tensor = torch.from_numpy(transformed_image).unsqueeze(0)
            # print(f"Converted transformed image to torch.Tensor with shape: {transformed_tensor.shape}")

        return (transformed_tensor, )

# Исправленные маппинги узлов
NODE_CLASS_MAPPINGS = {
    "GeneraImageTransformer": GeneraImageTransformer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "GeneraImageTransformer": "[Genera] Image Transformer",
}