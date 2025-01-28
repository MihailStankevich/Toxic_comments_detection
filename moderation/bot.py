import requests
import tensorflow as tf
import os
import django
from dotenv import load_dotenv
import tempfile
import nest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError, TelegramError
import time
from datetime import datetime, timedelta
#############

#############
# Set DJANGO_SETTINGS_MODULE

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelmoderation.settings')
django.setup()
from moderation.ml import model, image_model
from moderation.models import DeletedComment , Owner, BlockedUser
load_dotenv()
token = os.getenv('TOKEN')

nest_asyncio.apply()
good = ['irr_i_ssa', 'maxsugarfree', 'xxxxxsssqq', 'igorekbuy']
def predict_comment(comment, model):

    #comment_vector = vectorizer.transform([comment])

    prediction = model.predict([comment])

    label_mapping = {0: "Non-offensive", 1: "Offensive"}
    return label_mapping.get(prediction[0], "Unknown")

def classify_image(image_path, model):
    img = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
    img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
    img_array = tf.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array)
    return "Spam" if prediction[0][0] > 0.5 else "Non-Spam"

def retry(func):
    async def wrapper(*args, **kwargs):
        max_retries = 5  # Increase retry attempts if needed
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except RetryAfter as e:
                print(f"RetryAfter error: Waiting for {e.retry_after} seconds...")
                await asyncio.sleep(e.retry_after)  # Wait as instructed by Telegram
            except (TimedOut, NetworkError) as e:
                print(f"Retrying... Attempt {attempt + 1} due to: {str(e)}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except TelegramError as e:
                print(f"Unhandled TelegramError: {e}")
                break  # Exit loop for unrecoverable errors
        print("Max retries reached. Giving up.")
        return None
    return wrapper


# Apply retry logic to get_user_profile_photos
@retry
async def get_user_profile_photos(bot, user_id):
    return await bot.get_user_profile_photos(user_id=user_id)



async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if update.message.chat.type == "supergroup" and update.message.reply_to_message and update.message:
        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))
        username = update.message.from_user.username
        if username:
            username = username.lower()
        else:
            username = "unknown_user"
        blocked_user_queryset = (BlockedUser .objects.filter)(
            username=username,
            owner=owner
        ).select_related('owner') 
        
        blocked_user = await sync_to_async(blocked_user_queryset.first)() 

        if blocked_user and blocked_user.is_active():
            #await update.message.reply_text("You are blocked from commenting.")
            await update.message.delete()
            return  

        
        original_message = update.message.reply_to_message
        print(f"Message from supergroup {owner.username}: {update.message.text}")
        result = predict_comment(update.message.text, model)
        print(result)


        if username in good:
            pass
        else:
            try:
                user_id = update.message.from_user.id
                profile_photos = await get_user_profile_photos(context.bot, user_id)

                if profile_photos and profile_photos.photos:
                    largest_photo = max(profile_photos.photos[0], key=lambda x: x.width)
                    file = await context.bot.get_file(largest_photo.file_id)
                    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
                        await file.download_to_drive(temp_file.name) 
                        image_result = classify_image(temp_file.name, image_model)

                        print(f"Image result: {image_result}")

                        if image_result == 'Spam':
                            if original_message.caption:
                                post_text = f"{original_message.caption[:20]}..."
                            elif original_message.text:
                                post_text = f"{original_message.text[:20]}..."
                            else:
                                post_text = "No text"
                            sent_from = update.message.from_user
                            profile_link = f"tg://user?id={sent_from.id}"
                            await sync_to_async(DeletedComment.objects.create)(
                                post=post_text.lower(),
                                comment=update.message.text.lower(),
                                user=username,
                                channel_id=str(update.message.chat.id),
                                owner = owner,
                                detected_by = 'Profile picture',
                                profile_link=profile_link
                            )
                            await update.message.delete()
                            print(f'The comment -{update.message.text}- was deleted because it had been classified as spam by image')

                    
                else:
                    print("No profile photo available.")
                    # Schedule a second check for comments posted within the first few seconds
                    post_time = original_message.date
                    comment_time = update.message.date
                    if (comment_time - post_time) < timedelta(seconds=10):
                        asyncio.create_task(delayed_check(user_id, update, context))
                    
            except Exception as e:
                print(f"Error handling profile photo logic: {e}")
    else:
        print("Received an update without a message.")

async def delayed_check(user_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(7)
    try:
        # Process profile photo again after delay
        profile_photos = await context.bot.get_user_profile_photos(user_id=user_id)

        if profile_photos and profile_photos.photos:
            largest_photo = max(profile_photos.photos[0], key=lambda x: x.width)
            file = await context.bot.get_file(largest_photo.file_id)
            with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
                await file.download_to_drive(temp_file.name)
                image_result = classify_image(temp_file.name, image_model)

                print(f"Image result: {image_result}")

                if image_result == "spam":
                    post_text = update.message.caption[:20] if update.message.caption else update.message.text[:20] or "No text"
                    sent_from = update.message.from_user
                    profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                    await sync_to_async(DeletedComment.objects.create)(
                        post=post_text.lower(),
                        comment=update.message.text.lower(),
                        user=update.message.from_user.username.lower() if update.message.from_user.username else "unknown_user",
                        channel_id=str(update.message.chat.id),
                        owner=await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id)),
                        detected_by="Profile picture",
                        profile_link=profile_link,
                    )
                    await update.message.delete()
        else:
            print("No profile photo available.")
                    
    except Exception as e:
        print(f"Error handling profile photo logic: {e}")
    else:
        print("Received an update without a message.")
# Main function to set up the bot
async def main():

    TOKEN = token

    # Create the application
    application = Application.builder().token(TOKEN).build()

    # Add a message handler to listen for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())



