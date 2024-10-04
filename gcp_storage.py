# original repo https://github.com/Fantaxico/ComfyUI-GCP-Storage
from google.cloud import storage
import folder_paths
from PIL import Image
import json
import os
import numpy as np

config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'gcp_config.json')
     
class upload_to_gcp_storage:
    def __init__(self):
        self.output_dir = folder_paths.get_output_directory()
        self.type = "output"
        self.compress_level = 4
        
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "file_name": ("STRING", {"multiline": False}),
                "test_name": ("STRING", {"multiline": False}),
                "bucket_name": ("STRING", {"default":"comfyui-batch-tester","multiline": False}),
                "config": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
            },
            "optional": {},
        }
    
    RETURN_TYPES = ()
    FUNCTION = "upload_to_gcp_storage"
    OUTPUT_NODE = True
    CATEGORY = "Genera"

    def upload_to_gcp_storage(self, images, file_name, test_name, bucket_name, config):
        gcp_service_json = os.path.join(os.path.abspath(__file__),"../gcp_config.json")
        print(f"Setting [GOOGLE_APPLICATION_CREDENTIALS] to {gcp_service_json}..")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_service_json

        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        if file_name == "0":  # If file_name is "0", create and upload config.json
            try:
                # Parse the config string into a JSON object
                config_data = json.loads(config)
            except json.JSONDecodeError as e:
                print(f"Error parsing config: {e}")
                return {"error": "Invalid JSON format in config string"}

            config_file = "config.json"
            config_file_path = os.path.join(self.output_dir, config_file)

            # Save the parsed config to config.json
            with open(config_file_path, 'w') as json_file:
                json.dump(config_data, json_file)

            # Upload config.json to GCP storage
            config_blob = bucket.blob(f"{test_name}/{config_file}")
            print(f"Uploading config.json to {bucket_name}/{test_name}/{config_file}..")
            config_blob.upload_from_filename(config_file_path)

        # Otherwise, proceed with the normal image upload flow
        file = f"{file_name}.png"
        subfolder = os.path.dirname(os.path.normpath(file))
        full_output_folder = os.path.join(self.output_dir, subfolder)
        full_file_path = os.path.join(full_output_folder, file)

        print(f"Saving file '{file_name}' to {full_file_path}..")
        results = save_images(self, images, file_name)

        blob = bucket.blob(f"{test_name}/{file}")
        print(f"Uploading image to {bucket_name}/{test_name}/{file}..")
        blob.upload_from_filename(full_file_path)

        return {"ui": {"images": results}}

def save_images(self, images, filename_prefix="ComfyUI"):
    full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0])
    results = list()
    for (batch_number, image) in enumerate(images):
        i = 255. * image.cpu().numpy()
        img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
        metadata = None
        file = f"{filename}.png"
        img.save(os.path.join(full_output_folder, file), pnginfo=metadata, compress_level=self.compress_level)
        results.append({
            "filename": file,
            "subfolder": subfolder,
            "type": self.type
        })

    return results

NODE_CLASS_MAPPINGS = {
    "Genera.GCPStorageNode": upload_to_gcp_storage,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.GCPStorageNode": "GCP Storage Upload",
}