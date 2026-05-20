# Email templates for TaskHub notifications
import urllib.parse
from config import Config

def get_base_template(content_html):
    """
    Returns a unified luxury dark-mode responsive template.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TaskHub Notification</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #0c0a09;
                color: #e7e5e4;
                margin: 0;
                padding: 0;
                -webkit-font-smoothing: antialiased;
            }}
            .wrapper {{
                width: 100%;
                background-color: #0c0a09;
                padding: 40px 0;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background-color: #1c1917;
                border: 1px solid #2e2a24;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            }}
            .header {{
                background: linear-gradient(135deg, #1c1917 0%, #2e2a24 100%);
                padding: 30px 40px;
                border-bottom: 1px solid #2e2a24;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
                font-weight: 800;
                letter-spacing: -0.05em;
                color: #f5f5f4;
            }}
            .header h1 span {{
                color: #eab308; /* Luxury Gold accent */
            }}
            .content {{
                padding: 40px;
                line-height: 1.6;
                font-size: 15px;
            }}
            .content p {{
                margin: 0 0 20px 0;
                color: #a8a29e;
            }}
            .content h2 {{
                margin: 0 0 15px 0;
                font-size: 18px;
                font-weight: 700;
                color: #f5f5f4;
            }}
            .card {{
                background-color: #171412;
                border: 1px solid #2e2a24;
                border-radius: 12px;
                padding: 24px;
                margin-bottom: 30px;
            }}
            .card-item {{
                margin-bottom: 12px;
                font-size: 14px;
            }}
            .card-item:last-child {{
                margin-bottom: 0;
            }}
            .card-label {{
                font-weight: 600;
                color: #78716c;
                display: block;
                text-transform: uppercase;
                font-size: 11px;
                letter-spacing: 0.05em;
                margin-bottom: 4px;
            }}
            .card-value {{
                color: #f5f5f4;
                font-size: 14px;
            }}
            .btn-container {{
                text-align: center;
                margin: 30px 0 10px 0;
            }}
            .btn {{
                display: inline-block;
                background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%);
                color: #0c0a09 !important;
                text-decoration: none;
                font-weight: 700;
                padding: 14px 32px;
                border-radius: 9999px;
                font-size: 14px;
                box-shadow: 0 4px 12px rgba(234, 179, 8, 0.2);
                transition: transform 0.2s ease;
            }}
            .footer {{
                background-color: #171412;
                padding: 20px 40px;
                text-align: center;
                border-top: 1px solid #2e2a24;
                font-size: 12px;
                color: #57534e;
            }}
            .footer a {{
                color: #a8a29e;
                text-decoration: none;
            }}
            .preview-img {{
                width: 100%;
                max-height: 250px;
                object-cover: cover;
                border-radius: 8px;
                border: 1px solid #2e2a24;
                margin-top: 12px;
            }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="header">
                    <h1>Task<span>Hub</span></h1>
                </div>
                <div class="content">
                    {content_html}
                </div>
                <div class="footer">
                    <p>TaskHub Luxury AI Product Photography Studio &bull; <a href="{Config.FRONTEND_URL}">Access Portal</a></p>
                    <p>&copy; 2026 TaskHub. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

def get_task_assigned_email(task_title, task_description, product_image_url, task_id):
    frontend_url = Config.FRONTEND_URL or "http://localhost:3000"
    task_link = f"{frontend_url}/tasks/{task_id}"
    
    # Handle local vs remote preview image urls
    if product_image_url.startswith('/'):
        img_src = f"{frontend_url}{product_image_url}"
    else:
        img_src = product_image_url

    content = f"""
    <h2>New Campaign Assigned</h2>
    <p>Greetings, Creator. A premium product photography campaign has been assigned to your workspace. Use the AI Studio to synthesize the 8 required DSLR-quality photo variations.</p>
    
    <div class="card">
        <div class="card-item">
            <span class="card-label">Campaign Title</span>
            <span class="card-value" style="font-size: 16px; font-weight: 700;">{task_title}</span>
        </div>
        <div class="card-item">
            <span class="card-label">Instructions</span>
            <span class="card-value">{task_description or "No special directions specified."}</span>
        </div>
        <div class="card-item">
            <span class="card-label">Original Template</span>
            <img src="{img_src}" class="preview-img" alt="Product Template" />
        </div>
    </div>
    
    <p>Please enter the AI Studio inside your creative workspace to synthesize and submit the asset portfolio.</p>
    
    <div class="btn-container">
        <a href="{task_link}" class="btn">Launch AI Studio</a>
    </div>
    """
    return get_base_template(content)

def get_task_submitted_email(task_title, user_name, task_id):
    frontend_url = Config.FRONTEND_URL or "http://localhost:3000"
    review_link = f"{frontend_url}/tasks/{task_id}"

    content = f"""
    <h2>Campaign Submitted for Review</h2>
    <p>Administrative Alert: A product photography campaign has been completed and submitted by a creator.</p>
    
    <div class="card">
        <div class="card-item">
            <span class="card-label">Campaign Title</span>
            <span class="card-value" style="font-size: 16px; font-weight: 700;">{task_title}</span>
        </div>
        <div class="card-item">
            <span class="card-label">Submitted By</span>
            <span class="card-value">{user_name}</span>
        </div>
        <div class="card-item">
            <span class="card-label">Asset Quantity</span>
            <span class="card-value">8 DSLR AI Generations (Fulfillment Complete)</span>
        </div>
    </div>
    
    <p>Please review the generated white background, marble, velvet, creative landscape, and model wearing perspectives. You can either accept or request a revision workflow.</p>
    
    <div class="btn-container">
        <a href="{review_link}" class="btn">Review Assets</a>
    </div>
    """
    return get_base_template(content)

def get_task_accepted_email(task_title, admin_feedback=None):
    content = f"""
    <h2>Campaign Assets Approved!</h2>
    <p>Congratulations, Creator! Your synthesized photography assets have been reviewed and fully approved by the Administration.</p>
    
    <div class="card">
        <div class="card-item">
            <span class="card-label">Campaign Title</span>
            <span class="card-value" style="font-size: 16px; font-weight: 700;">{task_title}</span>
        </div>
        <div class="card-item">
            <span class="card-label">Fulfillment Status</span>
            <span class="card-value" style="color: #10b981; font-weight: 700;">Accepted / Completed</span>
        </div>
        {"<div class='card-item'><span class='card-label'>Feedback</span><span class='card-value'>" + admin_feedback + "</span></div>" if admin_feedback else ""}
    </div>
    
    <p>Your work has met all DSLR visual clarity, product consistency, and photorealism standards. Thank you for your creative execution!</p>
    """
    return get_base_template(content)

def get_task_revision_email(task_title, notes):
    content = f"""
    <h2>Revision Requested for Campaign</h2>
    <p>Notice: The Administration has reviewed your generated assets and requested revisions for your campaign.</p>
    
    <div class="card">
        <div class="card-item">
            <span class="card-label">Campaign Title</span>
            <span class="card-value" style="font-size: 16px; font-weight: 700;">{task_title}</span>
        </div>
        <div class="card-item">
            <span class="card-label">Status</span>
            <span class="card-value" style="color: #f97316; font-weight: 700;">Revision Requested</span>
        </div>
        <div class="card-item">
            <span class="card-label">Required Modifications</span>
            <span class="card-value" style="color: #f5f5f4; font-weight: 600; font-style: italic;">"{notes or "Please check the comments and regenerate."}"</span>
        </div>
    </div>
    
    <p>Please access your creative workspace, clear the requested images, adjust your prompt directives, and regenerate to match the feedback.</p>
    """
    return get_base_template(content)
