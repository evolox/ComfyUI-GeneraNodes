import json
import os
import uuid
import logging
from google.cloud import pubsub_v1
from google.cloud import storage
import requests
from PIL import Image
from io import BytesIO
import numpy as np

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

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE",
                    "IMAGE",)  # Static 4 return slots
    RETURN_NAMES = ("Preview 1", "Preview 2", "Preview 3", "Preview 4")
    FUNCTION = "process"
    OUTPUT_NODE = True
    CATEGORY = "Genera"

    def __init__(self):
        logging.info("Initializing BatchPreviewer...")
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_name = "projects/genera-408110/topics/space-previewer"
        self.subscription_id = "projects/genera-408110/subscriptions/space-previewer-result-sub"
        self.bucket_client = storage.Client()
        logging.info("BatchPreviewer initialized successfully.")

    def process(self, prompt, seeds):
        logging.info("Processing job with prompt and seeds.")
        # Step a: Parse seeds
        seed_numbers = [int(seed.strip())
                        for seed in seeds.split(",") if seed.strip().isdigit()]
        logging.info(f"Parsed seeds: {seed_numbers}")

        # Step b: Load workflow from space_preview_v3.json
        try:
            with open(workflow_file_path) as f:
                base_workflow = json.load(f)
            logging.info("Loaded base workflow successfully.")
        except Exception as e:
            logging.error(f"Error loading workflow: {e}")
            return (None, None, None, None)

        jobs = []
        job_ids = set()

        # Step c: Modify workflow per seed
        # Limit to a max of 4 seeds to match return slots
        for seed in seed_numbers[:4]:
            workflow = base_workflow.copy()
            # Insert prompt text at key "530"
            if "530" in workflow:
                workflow["530"]["inputs"]["text"] = prompt
                logging.info(
                    f"Inserted prompt text into workflow for seed {seed}.")

            # Insert seed at key "81"
            if "81" in workflow:
                workflow["81"]["inputs"]["noise_seed"] = seed
                logging.info(f"Inserted seed {seed} into workflow.")

            # Step d: Add UUID as job id
            job_id = str(uuid.uuid4())
            job_ids.add(job_id)
            job = {
                "id": job_id,
                "workflow": workflow
            }
            jobs.append(job)
            logging.info(f"Created job with ID {job_id} for seed {seed}.")

            # Publish job to Pub/Sub topic
            try:
                message = json.dumps(job).encode("utf-8")
                self.publisher.publish(self.topic_name, message, job_id=job_id)
                logging.info(f"Published job with ID {job_id} to Pub/Sub.")
            except Exception as e:
                logging.error(f"Error publishing job {job_id}: {e}")

        # Step f: Subscribe to results and wait for all responses
        received_images = {}

        def callback(message):
            try:
                data = json.loads(message.data.decode("utf-8"))
                job_id = data["id"]
                if job_id in job_ids:
                    sas_url = data["url"]
                    logging.info(f"Received message for job ID {
                                 job_id} with SAS URL.")

                    # Download image from SAS URL
                    response = requests.get(sas_url)
                    if response.status_code == 200:
                        received_images[job_id] = response.content
                        logging.info(f"Downloaded image for job ID {job_id}.")
                    else:
                        logging.error(f"Failed to download image for job ID {
                                      job_id}. Status code: {response.status_code}")

                    message.ack()
                    # Remove job_id from the waiting list
                    job_ids.remove(job_id)
                else:
                    logging.warning(f"Received message for unknown job ID {
                                    job_id}. Ignoring.")
                    message.ack()  # Acknowledge non-matching messages as well

            except Exception as e:
                logging.error(f"Error processing message: {e}")
                message.nack()

        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_id, callback=callback)

        # Wait for all jobs to complete
        try:
            with self.subscriber:
                logging.info("Listening for responses from Pub/Sub...")
                while job_ids:  # Continue waiting until all job_ids are received
                    # Adjust timeout as necessary
                    streaming_pull_future.result(timeout=30)
        except Exception as e:
            logging.error(f"Error while waiting for responses: {e}")
            streaming_pull_future.cancel()

        # Step h: Collect up to 4 images and fill empty slots with None
        images = []

        for job in jobs[:4]:  # Collect a maximum of 4 images
            job_id = job["id"]
            if job_id in received_images:
                try:
                    # Convert image content to PIL format and then to numpy array
                    image_data = received_images[job_id]
                    image = Image.open(BytesIO(image_data))
                    # Convert to NumPy array if required by ComfyUI
                    image_np = np.array(image)
                    images.append(image_np)
                    logging.info(f"Image processed for job ID {job_id}.")
                except Exception as e:
                    logging.error(
                        f"Error processing image for job ID {job_id}: {e}")
                    images.append(None)
            else:
                images.append(None)

        # Ensure the return format has exactly 4 items
        result_images = tuple(images + [None] * (4 - len(images)))
        logging.info(
            f"Returning {len([img for img in result_images if img is not None])} images.")

        return result_images  # Return a tuple with exactly 4 items


NODE_CLASS_MAPPINGS = {
    "Genera.BatchPreviewer": BatchPreviewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.BatchPreviewer": "Batch Previewer",
}
