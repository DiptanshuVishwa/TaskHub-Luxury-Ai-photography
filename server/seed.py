from db import supabase

def seed_db():
    print("Seeding database...")
    
    # Create Admin
    admin_data = {
        "email": "demo_admin@taskhub.com",
        "name": "Admin User",
        "role": "admin"
    }
    admin = supabase.table('users').select('*').eq('email', admin_data['email']).execute().data
    if not admin:
        admin = supabase.table('users').insert(admin_data).execute().data[0]
    else:
        admin = admin[0]

    # Create User
    user_data = {
        "email": "demo_user@taskhub.com",
        "name": "Demo Creator",
        "role": "user"
    }
    user = supabase.table('users').select('*').eq('email', user_data['email']).execute().data
    if not user:
        user = supabase.table('users').insert(user_data).execute().data[0]
    else:
        user = user[0]

    # Create Task
    task_data = {
        "title": "Luxury Watch Campaign",
        "description": "Generate high-quality luxury photos of this gold watch.",
        "product_image_url": "/generated_samples/01-white-background.png",
        "status": "submitted", # Marked as submitted as requested
        "created_by": admin['id'],
        "assigned_to": user['id']
    }
    
    # Check if task already exists for this user to avoid duplicates
    existing_tasks = supabase.table('tasks').select('*').eq('assigned_to', user['id']).execute().data
    if not existing_tasks:
        task = supabase.table('tasks').insert(task_data).execute().data[0]
        
        # Insert 8 Seeded Images
        seeded_images = [
            {"file": "01-white-background.png", "type": "white_background", "angle": "white_background_1"},
            {"file": "02-marble-luxury.png", "type": "theme", "angle": "theme_1"},
            {"file": "03-velvet-luxury.png", "type": "theme", "angle": "theme_2"},
            {"file": "04-beach-luxury.png", "type": "creative", "angle": "creative_1"},
            {"file": "05-cinematic-editorial.png", "type": "creative", "angle": "creative_2"},
            {"file": "06-model-front.png", "type": "model", "angle": "front"},
            {"file": "07-model-side.png", "type": "model", "angle": "side_45"},
            {"file": "08-model-closeup.png", "type": "model", "angle": "closeup"},
        ]
        
        for img in seeded_images:
            supabase.table('generated_images').insert({
                "task_id": task['id'],
                "image_type": img['type'],
                "image_url": f"/generated_samples/{img['file']}",
                "prompt_used": f"Seeded demo generation for {img['type']}",
                "metadata": {"source": "demo_seed"},
                "angle": img['angle'],
                "is_final": True
            }).execute()
            
        print("Inserted task and 8 demo images.")
    else:
        print("Demo task already exists.")

    print("Seeding complete.")

if __name__ == '__main__':
    seed_db()
