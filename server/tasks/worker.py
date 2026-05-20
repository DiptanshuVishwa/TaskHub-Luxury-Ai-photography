import time
import replicate
import resend
from celery_worker import celery_app
from config import Config
from db import supabase

resend.api_key = Config.RESEND_API_KEY

@celery_app.task(bind=True)
def generate_image_task(self, task_id, image_type, prompt, original_image_url, angle=None):
    try:
        print(f"Starting generation for task {task_id}, type {image_type}, angle {angle}")
        
        # We simulate the generation by using replicate if an API token is present and it's a real run.
        # Wait, the assignment mentions real AI generation using replicate API image-to-image workflow.
        # "background removal, foreground preservation... DSLR-quality outputs"
        
        # If this is a real replicate call:
        output = replicate.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5d1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": prompt,
                "image": original_image_url,
                "prompt_strength": 0.8,
                "num_inference_steps": 30,
                "guidance_scale": 7.5
            }
        )
        # The output is a list of URLs usually
        generated_url = output[0] if isinstance(output, list) else output

        # Save to DB
        supabase.table("generated_images").insert({
            "task_id": task_id,
            "image_type": image_type,
            "image_url": generated_url,
            "prompt_used": prompt,
            "angle": angle,
            "metadata": {"source": "replicate"}
        }).execute()

        return {"status": "success", "url": generated_url}
        
    except Exception as e:
        print(f"Generation failed: {str(e)}")
        # Handle fallback if needed, but the prompt says fallback on frontend or backend?
        # "If live AI generation fails: fallback gracefully to seeded demo images"
        # We can implement fallback in the backend or frontend.
        self.update_state(state='FAILURE', meta={'exc': str(e)})
        raise e

@celery_app.task
def send_email_task(to_email, subject, html_content):
    try:
        response = resend.Emails.send({
            "from": "TaskHub <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        })
        print(f"Email sent to {to_email}: {response}")
        return True
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return False
