import os
import sys
sys.path.insert(0, '/tmp')
import requests
import tempfile
import asyncio
import nest_asyncio
import django
from transformers import ViTImageProcessor
import torch
from PIL import Image
from torchvision import transforms
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "channelmoderation.settings")
django.setup()

# Import models from `init.py` after Django setup
from moderation.ml import image_processor, image_model
from moderation.models import DeletedComment, Owner, BlockedUser

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Ensure asyncio compatibility
nest_asyncio.apply()

# Function to predict text comment
class_names = ['not_spam', 'spam']

# Preprocess the image
def preprocess_image(img_path, processor):
    img = Image.open(img_path)
    inputs = processor(images=img, return_tensors="pt")
    return inputs

# Define function to predict image class
def classify_image(img_path, model, processor):
    inputs = preprocess_image(img_path, processor)
    
    # Perform inference
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Get the predicted class
    logits = outputs.logits
    predicted_class_idx = logits.argmax(-1).item()
    confidence = torch.softmax(logits, dim=1)[0][predicted_class_idx].item()
    return class_names[predicted_class_idx], confidence

# Asynchronous message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "supergroup" and update.message.reply_to_message:
        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))
        username = update.message.from_user.username
        if username:
            username = username.lower()
        else:
            username = "unknown_user"
        # Check if user is blocked
        blocked_user_queryset = BlockedUser.objects.filter(
            username=username,
            owner=owner,
        ).select_related("owner")
        blocked_user = await sync_to_async(blocked_user_queryset.first)()

        if blocked_user and blocked_user.is_active():
            await update.message.delete()
            return

        # Process comment text
        original_message = update.message.reply_to_message
        if original_message:
            pass
        else:
            try:
                # Process profile photo
                user_id = update.message.from_user.id
                profile_photos = await context.bot.get_user_profile_photos(user_id=user_id)

                if profile_photos.photos:
                    largest_photo = max(profile_photos.photos[0], key=lambda x: x.width)
                    file = await context.bot.get_file(largest_photo.file_id)
                    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
                        await file.download_to_drive(temp_file.name)
                        image_result, confidence = classify_image(temp_file.name, image_model, image_processor)
                        print(f"Image result: {image_result} with confidence: {confidence:.2f}")

                        if image_result == "spam" and confidence > 0.8:
                            post_text = original_message.caption[:20] if original_message.caption else original_message.text[:20] or "No text"
                            sent_from = update.message.from_user
                            profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                            await sync_to_async(DeletedComment.objects.create)(
                                post=post_text.lower(),
                                comment=update.message.text.lower(),
                                user=username,
                                channel_id=str(update.message.chat.id),
                                owner=owner,
                                detected_by="Profile picture",
                                profile_link=profile_link,
                            )
                            await update.message.delete()
                            print(f"The comment -{update.message.text}- was deleted (spam profile picture).")
                else:
                    print("No profile photo available.")
            except Exception as e:
                print(f"Error handling profile photo logic: {e}")

# Main function
async def main():
    # Create the application
    application = Application.builder().token(TOKEN).build()

    # Add a message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
