import json
import os
import uuid
import logging
from google.cloud import pubsub_v1
from google.cloud import storage
import requests
import time
from PIL import Image, ImageSequence, ImageOps
import numpy as np
import torch
from io import BytesIO
import folder_paths

# Set up logging
logging.basicConfig(level=logging.INFO)

workflow_file_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'space_preview_v4.json')
config_file_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'gcp_config.json')
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config_file_path


def pil2tensor(img):
    output_images = []
    output_masks = []
    for i in ImageSequence.Iterator(img):
        i = ImageOps.exif_transpose(i)
        if i.mode == 'I':
            i = i.point(lambda i: i * (1 / 255))
        image = i.convert("RGB")
        image = np.array(image).astype(np.float32) / 255.0
        image = torch.from_numpy(image)[None,]
        if 'A' in i.getbands():
            mask = np.array(i.getchannel('A')).astype(np.float32) / 255.0
            mask = 1. - torch.from_numpy(mask)
        else:
            mask = torch.zeros((64, 64), dtype=torch.float32, device="cpu")
        output_images.append(image)
        output_masks.append(mask.unsqueeze(0))

    if len(output_images) > 1:
        output_image = torch.cat(output_images, dim=0)
        output_mask = torch.cat(output_masks, dim=0)
    else:
        output_image = output_images[0]
        output_mask = output_masks[0]

    return (output_image, output_mask)


def load_image(image_source):
    if image_source.startswith('http'):
        print(image_source)
        response = requests.get(image_source)
        img = Image.open(BytesIO(response.content))
        file_name = image_source.split('/')[-1]
    else:
        img = Image.open(image_source)
        file_name = os.path.basename(image_source)
    return img, file_name


class BatchPreviewer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {
                    "multiline": True,
                    "default": "",
                }),
                "seeds": ("STRING", {
                    "multiline": False,
                    "default": "",
                }),
                "lora_name": (folder_paths.get_filename_list("loras"), {"tooltip": "The name of the LoRA."}),
                "strength_model": ("FLOAT", {"default": 1.0, "min": -100.0, "max": 100.0, "step": 0.01, "tooltip": "How strongly to modify the diffusion model. This value can be negative."}),
            },
        }

    # Define each image individually
    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("image 1", "image 2", "image 3", "image 4")
    FUNCTION = "process"
    OUTPUT_NODE = True
    CATEGORY = "Genera"

    def __init__(self):
        logging.info("Initializing BatchPreviewer...")
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_name = "projects/genera-408110/topics/space-previewer"
        self.subscription_id = "projects/genera-408110/subscriptions/space-previewer-result-sub"
        storage_client = storage.Client()
        self.bucket = storage_client.bucket("space-previewer")
        logging.info("BatchPreviewer initialized successfully.")

    def process(self, prompt, seeds, lora_name, strength_model):
        logging.info("Processing job with prompt and seeds.")

        lora_path = folder_paths.get_full_path_or_raise("loras", lora_name)
        # Destination in the bucket
        destination_blob_name = f"loras/{lora_name}"
        blob = self.bucket.blob(destination_blob_name)

        # Check if the blob already exists
        if not blob.exists():
            # Upload the file if it does not exist
            blob.upload_from_filename(lora_path)
            print(f"File {lora_name} uploaded to {destination_blob_name}.")
        else:
            print(f"File {lora_name} already exists at {
                  destination_blob_name}, skipping upload.")

        # Parse seeds
        seed_numbers = [int(seed.strip())
                        for seed in seeds.split(",") if seed.strip().isdigit()]
        logging.info(f"Parsed seeds: {seed_numbers}")

        # Load workflow from JSON file
        try:
            with open(workflow_file_path) as f:
                base_workflow = json.load(f)
            logging.info("Loaded base workflow successfully.")
        except Exception as e:
            logging.error(f"Error loading workflow: {e}")
            return []

        jobs = []
        job_ids = set()

        # Modify workflow per seed
        for seed in seed_numbers:
            workflow = base_workflow.copy()

            if "530" in workflow:
                workflow["530"]["inputs"]["text"] = prompt
            if "81" in workflow:
                workflow["81"]["inputs"]["noise_seed"] = seed
            if "517" in workflow:
                workflow["517"]["inputs"]["lora_name"] = lora_name
                workflow["517"]["inputs"]["strength_model"] = strength_model
            if "532" in workflow:
                workflow["532"]["inputs"]["filename_prefix"] = str(uuid.uuid4())[
                    :4]

            job_id = str(uuid.uuid4())
            job_ids.add(job_id)
            job = {
                "id": job_id,
                "workflow": workflow,
                "uploads": {"loras": [lora_name]},
            }
            jobs.append(job)

            # Publish job to Pub/Sub
            try:
                message = json.dumps(job).encode("utf-8")
                self.publisher.publish(self.topic_name, message, job_id=job_id)
                logging.info(f"Published job with ID {job_id} to Pub/Sub.")
            except Exception as e:
                logging.error(f"Error publishing job {job_id}: {e}")

        received_images = []

        def callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                job_id = data["id"]
                if job_id in job_ids:
                    url = data["url"]

                    img, name = load_image(url)
                    img_out, mask_out = pil2tensor(img)
                    received_images.append(img_out)

                    message.ack()
                    job_ids.remove(job_id)
                else:
                    message.ack()

            except Exception as e:
                logging.error(f"Error processing message: {e}")
                message.nack()

        # Listen for responses with timeout mechanism
        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_id, callback=callback)
        timeout = 5  # Time to wait between checks
        max_wait_time = 300  # Total max wait time (adjust as needed)
        elapsed_time = 0

        logging.info("Listening for responses from Pub/Sub...")
        while job_ids and elapsed_time < max_wait_time:
            time.sleep(timeout)
            elapsed_time += timeout

        streaming_pull_future.cancel()  # Stop the subscription

        # Return images separately for compatibility
        return tuple(received_images)


NODE_CLASS_MAPPINGS = {
    "Genera.BatchPreviewer": BatchPreviewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.BatchPreviewer": "Batch Previewer",
}
