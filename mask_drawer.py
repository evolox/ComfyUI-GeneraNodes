import os
import hashlib
import numpy as np
import torch
from PIL import Image, ImageOps, ImageSequence
import folder_paths, node_helpers


class MaskDrawer:
    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = [f for f in os.listdir(input_dir) if os.path.isfile(os.path.join(input_dir, f))]
        return {
            "required": {
                "image": (sorted(files), {"image_upload": True}),
            },
        }

    CATEGORY = "image"

    RETURN_TYPES = ("IMAGE", "MASK")
    RETURN_NAMES = ("loaded_image", "drawn_mask")
    FUNCTION = "process_image_and_mask"

    def process_image_and_mask(self, image, mask_data=None):
        """
        Load the image and process the mask drawn in the frontend.
        """
        # Load Image
        image_path = folder_paths.get_annotated_filepath(image)
        img = node_helpers.pillow(Image.open, image_path)

        output_images = []
        output_masks = []
        w, h = None, None

        excluded_formats = ['MPO']

        for i in ImageSequence.Iterator(img):
            i = node_helpers.pillow(ImageOps.exif_transpose, i)

            if i.mode == 'I':
                i = i.point(lambda i: i * (1 / 255))
            image = i.convert("RGB")

            if len(output_images) == 0:
                w = image.size[0]
                h = image.size[1]

            if image.size[0] != w or image.size[1] != h:
                continue

            image = np.array(image).astype(np.float32) / 255.0
            image = torch.from_numpy(image)[None,]

            if 'A' in i.getbands():
                mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
                mask = 1. - torch.from_numpy(mask)
            else:
                mask = torch.zeros((h, w), dtype=torch.float32, device="cpu")

            output_images.append(image)
            output_masks.append(mask.unsqueeze(0))

        if len(output_images) > 1 and img.format not in excluded_formats:
            output_image = torch.cat(output_images, dim=0)
            output_mask = torch.cat(output_masks, dim=0)
        else:
            output_image = output_images[0]
            output_mask = output_masks[0]

        # Handle drawn mask from frontend
        if mask_data:
            import base64
            from io import BytesIO
            mask_bytes = base64.b64decode(mask_data.split(",")[1])
            mask_image = Image.open(BytesIO(mask_bytes)).convert("L")
            frontend_mask = np.array(mask_image)
            frontend_mask = torch.from_numpy(frontend_mask).float() / 255.0
        else:
            frontend_mask = output_mask

        return (output_image, frontend_mask)

    @classmethod
    def IS_CHANGED(cls, image):
        image_path = folder_paths.get_annotated_filepath(image)
        m = hashlib.sha256()
        with open(image_path, 'rb') as f:
            m.update(f.read())
        return m.digest().hex()

    @classmethod
    def VALIDATE_INPUTS(cls, image):
        if not folder_paths.exists_annotated_filepath(image):
            return "Invalid image file: {}".format(image)
        return True


NODE_CLASS_MAPPINGS = {
    "Genera.MaskDrawer": MaskDrawer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.MaskDrawer": "Mask Drawer",
}