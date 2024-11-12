import json
import uuid
import logging
from google.cloud import pubsub_v1
from google.cloud import storage
import requests

# Set up logging
logging.basicConfig(level=logging.INFO)


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

    RETURN_TYPES = ("IMAGE", "IMAGE", "IMAGE", "IMAGE",)
    RETURN_NAMES = ("Preview 1", "Preview 2", "Preview 3", "Preview 4")
    FUNCTION = "process"
    OUTPUT_NODE = True
    CATEGORY = "Genera"

    def __init__(self):
        logging.info("Initializing BatchPreviewer...")
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()
        self.topic_name = "projects/your-project-id/topics/space_preview"
        self.result_topic_name = "projects/your-project-id/subscriptions/space_preview_result"
        self.bucket_client = storage.Client()
        logging.info("BatchPreviewer initialized successfully.")

    def process(self, prompt, seeds):
        logging.info("Processing job with prompt and seeds.")
        # Step a: Parse seeds
        seed_numbers = [int(seed.strip())
                        for seed in seeds.split(",") if seed.strip().isdigit()]
        logging.info(f"Parsed seeds: {seed_numbers}")

        # Step b: Load workflow from space_preview_api.json
        try:
            with open('./space_preview_api.json') as f:
                base_workflow = json.load(f)
            logging.info("Loaded base workflow successfully.")
        except Exception as e:
            logging.error(f"Error loading workflow: {e}")
            return []

        jobs = []

        # Step c: Modify workflow per seed
        for seed in seed_numbers:
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
                sas_url = data["sas_url"]
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
            except Exception as e:
                logging.error(
                    f"Error processing message for job ID {job_id}: {e}")
                message.nack()

        streaming_pull_future = self.subscriber.subscribe(
            self.result_topic_name, callback=callback)

        # Wait for all jobs to complete
        try:
            with self.subscriber:
                logging.info("Listening for responses from Pub/Sub...")
                # Adjust timeout as necessary
                streaming_pull_future.result(timeout=300)
        except Exception as e:
            logging.error(f"Error while waiting for responses: {e}")
            streaming_pull_future.cancel()

        # Step h: Return max 4 downloaded images
        images = [received_images[job["id"]]
                  for job in jobs if job["id"] in received_images]
        logging.info(f"Returning {len(images[:4])} images.")
        return images[:4]  # Return up to 4 images


NODE_CLASS_MAPPINGS = {
    "Genera.BatchPreviewer": BatchPreviewer,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Genera.BatchPreviewer": "Batch Previewer",
}
