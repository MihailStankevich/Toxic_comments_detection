import os
import requests
import tempfile
import asyncio
import nest_asyncio
import django
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
from moderation.ml import text_model, image_model
from moderation.models import DeletedComment, Owner, BlockedUser

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Ensure asyncio compatibility
nest_asyncio.apply()

# Function to predict text comment
def predict_comment(comment, model):
    prediction = model.predict([comment])  # Using sklearn-based model
    label_mapping = {0: "Non-offensive", 1: "Offensive"}
    return label_mapping.get(prediction[0], "Unknown")

# Function to classify profile image
def classify_image(image_path, model):
    # Preprocess image for PyTorch model
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    
    img = Image.open(image_path).convert("RGB")
    
    # Define the image transformations (resizing and normalization)
    transform = transforms.Compose([
        transforms.Resize(256),         # Resize to 256 for consistency with your training
        transforms.CenterCrop(224),     # Center crop to 224
        transforms.ToTensor(),          # Convert image to Tensor
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])  # Normalization for ImageNet pre-trained models
    ])
    
    # Apply transformations
    img_tensor = transform(img).unsqueeze(0).to(device)
    
    # Make prediction
    with torch.no_grad():
        outputs = model(img_tensor)
        _, preds = torch.max(outputs, 1)
    
    return "Spam" if preds.item() == 1 else "Non-Spam"

# Asynchronous message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type == "supergroup" and update.message.reply_to_message:
        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

        # Check if user is blocked
        blocked_user_queryset = BlockedUser.objects.filter(
            username=update.message.from_user.username.lower(),
            owner=owner,
        ).select_related("owner")
        blocked_user = await sync_to_async(blocked_user_queryset.first)()

        if blocked_user and blocked_user.is_active():
            await update.message.delete()
            return

        # Process comment text
        original_message = update.message.reply_to_message
        comment_result = predict_comment(update.message.text, text_model)
        print(f"Comment prediction for {update.message.text}: {comment_result}")
        if comment_result == "Offensive":
            post_text = original_message.caption[:20] if original_message.caption else original_message.text[:20] or "No text"
            sent_from = update.message.from_user
            profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
            await sync_to_async(DeletedComment.objects.create)(
                post=post_text.lower(),
                comment=update.message.text.lower(),
                user=update.message.from_user.username.lower(),
                channel_id=str(update.message.chat.id),
                owner=owner,
                detected_by="Comment text",
                profile_link=profile_link,
            )
            await update.message.delete()
            print(f"The comment -{update.message.text}- was deleted (offensive text).")
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
                        image_result = classify_image(temp_file.name, image_model)
                        print(f"Profile image classification for {update.message.from_user.username}: {image_result}")
                        if image_result == "Spam":
                            post_text = original_message.caption[:20] if original_message.caption else original_message.text[:20] or "No text"
                            sent_from = update.message.from_user
                            profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                            await sync_to_async(DeletedComment.objects.create)(
                                post=post_text.lower(),
                                comment=update.message.text.lower(),
                                user=update.message.from_user.username.lower(),
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
