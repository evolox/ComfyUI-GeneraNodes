import json
import os
import uuid
import logging
from google.cloud import pubsub_v1
import requests
import time
from PIL import Image
import numpy as np
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO)

workflow_file_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'space_preview_v3.json')
config_file_path = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'gcp_config.json')
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config_file_path


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
            },
        }

    RETURN_TYPES = ("IMAGE",)  # Define each image individually
    RETURN_NAMES = ("Preview Image",)
    FUNCTION = "process"
    OUTPUT_NODE = True
    CATEGORY = "Genera"

    def __init__(self):
        logging.info("Initializing BatchPreviewer...")
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_name = "projects/genera-408110/topics/space-previewer"
        self.subscription_id = "projects/genera-408110/subscriptions/space-previewer-result-sub"
        logging.info("BatchPreviewer initialized successfully.")

    def process(self, prompt, seeds):
        logging.info("Processing job with prompt and seeds.")

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

            job_id = str(uuid.uuid4())
            job_ids.add(job_id)
            job = {
                "id": job_id,
                "workflow": workflow
            }
            jobs.append(job)

            # Publish job to Pub/Sub
            try:
                message = json.dumps(job).encode("utf-8")
                self.publisher.publish(self.topic_name, message, job_id=job_id)
                logging.info(f"Published job with ID {job_id} to Pub/Sub.")
            except Exception as e:
                logging.error(f"Error publishing job {job_id}: {e}")

        received_images = {}

        def callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                job_id = data["id"]
                if job_id in job_ids:
                    sas_url = data["url"]

                    # Download image from SAS URL
                    response = requests.get(sas_url)
                    if response.status_code == 200:
                        # Convert image bytes to a NumPy array for compatibility
                        image = Image.open(BytesIO(response.content))
                        received_images[job_id] = np.array(image)
                        logging.info(
                            f"Downloaded and converted image for job ID {job_id}.")
                    else:
                        logging.error(f"Failed to download image for job ID {
                                      job_id}. Status code: {response.status_code}")

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

        # Return each image as a separate element in the tuple
        images = tuple(received_images[job["id"]]
                       for job in jobs if job["id"] in received_images)

        logging.info(f"Returning {len(images)} images.")

        return images  # Return images separately for compatibility


NODE_CLASS_MAPPINGS = {
    "Genera.BatchPreviewer": BatchPreviewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.BatchPreviewer": "Batch Previewer",
}
