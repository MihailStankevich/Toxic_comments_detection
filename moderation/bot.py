import requests
from openai import OpenAI
import tensorflow as tf
import sklearn
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
import re
#############

#############
# Set DJANGO_SETTINGS_MODULE

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelmoderation.settings')
django.setup()
from moderation.ml import model, image_model, vectorizer
from moderation.models import DeletedComment , Owner, BlockedUser
load_dotenv()
token = os.getenv('TOKEN')
api_key = os.getenv('OPENAI_API_KEY')
nest_asyncio.apply()
good = {'irr_i_ssa', 'maxsugarfree', 'xxxxxsssqq', 'igorekbuy', 'abaim', 'matras13', 'sacramentozz', 'sd_crown', 'fedor_sidorov19', 'no_nameyou', 'dizel_1', 'alexpikc', 'alexandru9996', 'criminal_stant', 'danilkaysin11', 'evgeniy_100011', 'skqzgraf', 'lllllllllllllllllliiilll', 'calaider', 'samanhafix', 'grigorypd', 'flaksuspq', 'ne_v_s3ti', 'vejderprikhozhanin', 'pontussss', 'ekaterina_burkina', 'turkovvvvv', '	savitaarrr', 'jmotbond', 'ilyailyailyailyailyai', 'vinata87'}
good_id = {1743466232, 7401964075, 395389772, 431482609, 7895115780, 1094599216, 5930100195, 1378388456, 5295539479, 1402712721}
bad = ['оленька', 'милена', 'ангелина', 'анюта', 'стася', 'стасюша']
bad_username = {'vasiliseo', 'vasiopew', 'alekseisapog'}
bad_id = {7637080567}

def predict_nick(nick, vectorizer, model):
    # Vectorize the input comment
    comment_vector = vectorizer.transform([nick])
    
    # Predict the class
    prediction = model.predict(comment_vector)
    
    # If needed, add a mapping for labels
    label_mapping = {0: "Non-spam", 1: "Spam"}
    return label_mapping.get(prediction[0], "Unknown")

def classify_image(image_path, model):
    img = tf.keras.preprocessing.image.load_img(image_path, target_size=(224, 224))
    img_array = tf.keras.preprocessing.image.img_to_array(img) / 255.0
    img_array = tf.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array)
    return "Spam" if prediction[0][0] > 0.5 else "Non-Spam"

def retry(func):
    async def wrapper(*args, **kwargs):
        max_retries = 5 
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

def is_suspicious_spam(text):

    cyrillic_pattern = r'[\u0400-\u04FF]'  # Cyrillic letters
    latin_pattern = r'[A-Za-z]'            # Latin letters
    special_unicode = r'[\u1D00-\u1D7F]'   # Small caps & phonetic extensions


    cyrillic_count = len(re.findall(cyrillic_pattern, text))
    latin_count = len(re.findall(latin_pattern, text))
    special_count = len(re.findall(special_unicode, text))

    if cyrillic_count > 0 and latin_count > 0 and special_count == 0:
        return False  # Normal mixed comment

    # Flag spam-like mixed text (Cyrillic + special Unicode) or heavy special characters
    if (cyrillic_count > 0 and special_count > 0) or special_count > 2:
        return True  # Spam detected

    return False 

# Load OpenAI API key from environment variable
client = OpenAI(
    api_key=api_key
)
def classify_nickname_and_comment(nickname, text_comment):
    prompt = f""" You are a professional spam detector.
      You are specialist in betting spam, 18+ spam and sales (russian and english languages). 
      However, casual discussions about betting, odds, and matches are NOT spam.
      Classify the following nickname and text comment as either 'spam' or 'not spam':\n\nNickname: {nickname}\nText Comment: {text_comment}\nClassification:"""
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o-mini"  ,
        max_tokens=5,
        temperature=0.0
    )

    classification = response.choices[0].message.content.strip().lower()
    if 'spam' in classification:
        if 'not' in classification:
            return 'not spam'
        return 'spam'
    else:
        return 'unknown'  # Handle unexpected outputs
# Apply retry logic to get_user_profile_photos
@retry
async def get_user_profile_photos(bot, user_id):
    return await bot.get_user_profile_photos(user_id=user_id)

async def delete_comment(update, context, post_text, comment, user_id, owner, detected_by, profile_link, delay=0):
    if delay > 0:
        await asyncio.sleep(delay)

    await sync_to_async(DeletedComment.objects.create)(
        post=post_text.lower(),
        comment=comment.lower(),
        user=user_id,
        channel_id=str(update.message.chat.id),
        owner=owner,
        detected_by=detected_by,
        profile_link=profile_link
    )
    await update.message.delete()
    print(f'The comment/by -{comment}- was deleted because it had been classified as spam by {detected_by}')

async def delete_edited_comment(update, context, post_text, comment, user_id, owner, detected_by, profile_link, delay=0):
    if delay > 0:
        await asyncio.sleep(delay)

    await sync_to_async(DeletedComment.objects.create)(
        post=post_text.lower(),
        comment=comment.lower(),
        user=user_id,
        channel_id=str(update.edited_message.chat.id),
        owner=owner,
        detected_by=detected_by,
        profile_link=profile_link
    )
    await update.edited_message.delete()
    print(f'The comment/by -{comment}- was deleted because it had been classified as spam by {detected_by}')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if  update.message and update.message.chat and update.message.reply_to_message and update.message.chat.type == "supergroup" :
        # Checking if the owner is in the database. if not - return
        try:
            await asyncio.sleep(0.1)
            owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))
        except:
            return
        #checking if the user is in the good list or if i have amrked him as good(permament block )
        user_id = update.message.from_user.id
        username = update.message.from_user.username.lower() if update.message.from_user.username else "unknown_user"
        print(f"Message from supergroup : {update.message.text}")

        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))
        blocked_user_queryset = (BlockedUser .objects.filter)(
            username=user_id,
            owner=owner
        ).select_related('owner') 
        blocked_user = await sync_to_async(blocked_user_queryset.first)() 
        #checking if the user is in the good list or if i have amrked him as good(permament block )
        if username in good or update.message.from_user.id in good_id or (blocked_user and blocked_user.is_active()):
            pass
        else:
            #first of all checking the image
            try:  
                profile_photos = await get_user_profile_photos(context.bot, user_id)
                if profile_photos and profile_photos.photos:
                    largest_photo = max(profile_photos.photos[0], key=lambda x: x.width)
                    file = await context.bot.get_file(largest_photo.file_id)
                    
                    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
                        await file.download_to_drive(temp_file.name)
                        image_result = classify_image(temp_file.name, image_model)
                        print(f"Image result: {image_result}")

                        original_message = update.message.reply_to_message

                        if image_result == 'Spam':
                            if original_message.caption:
                                post_text = f"{original_message.caption[:20]}..."
                            elif original_message.text:
                                post_text = f"{original_message.text[:20]}..."
                            else:
                                post_text = "No text"

                            sent_from = update.message.from_user
                            profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                            comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                            await delete_comment(update, context, post_text, comment_text, user_id, owner, 'Profile picture', profile_link)
                            return  # Stop further processing

                else:
                    print("No profile photo available.")
                    # Schedule a second check for comments posted within the first few seconds
                    original_message = update.message.reply_to_message
                    post_time = original_message.date
                    comment_time = update.message.date
                     #if it was sent in the first 1.8 seconds - delete it
                    if (comment_time - post_time) < timedelta(seconds=1.8):
                        original_message = update.message.reply_to_message
                        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

                        if original_message.caption:
                            post_text = f"{original_message.caption[:20]}..."
                        elif original_message.text:
                            post_text = f"{original_message.text[:20]}..."
                        else:
                            post_text = "No text"
                        sent_from = update.message.from_user
                        profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                        comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                        await delete_comment(update, context, post_text, comment_text, user_id, owner, '2sec check', profile_link)
                        return
                    #if it was sent in the first 10 seconds - check the profile picture again
                    if (comment_time - post_time) < timedelta(seconds=10):
                        asyncio.create_task(delayed_check(user_id, update, context))
                    

            except Exception as e:
                print(f"Error checking profile  picture: {e}")

            #check for the inline buttons
            try:   
                has_inline_buttons = update.message.reply_markup and update.message.reply_markup.inline_keyboard
                if has_inline_buttons:
                    original_message = update.message.reply_to_message
                    owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

                    if original_message.caption:
                        post_text = f"{original_message.caption[:20]}..."
                    elif original_message.text:
                        post_text = f"{original_message.text[:20]}..."
                    else:
                        post_text = "No text"
                    sent_from = update.message.from_user
                    profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                    await sync_to_async(DeletedComment.objects.create)(
                        post=post_text.lower(),
                        comment=(update.message.text.lower()[:300] if update.message.text else "No text") + f" by {username}",
                        user=user_id,
                        channel_id=str(update.message.chat.id),
                        owner = owner,
                        detected_by = 'Inline buttons',
                        profile_link=profile_link
                    )
                    await update.message.delete()
                    print(f'The comment/by -{update.message.text if update.message.text else username}- was deleted because it had been classified as spam by inline buttons')
                    return
                
            except Exception as e:
                print(f"Error checking inline buttons: {e}")

            #checking nickname and text
            try:     
                original_message = update.message.reply_to_message
                post_time = original_message.date
                comment_time = update.message.date
                #if it was sent in the first 1.8 seconds - delete it
                  
                nickname = update.message.from_user.full_name.lower() if update.message.from_user.full_name else "unknown_nickname"
                text = update.message.text if update.message.text else "No text"

                if is_suspicious_spam(text):
                    original_message = update.message.reply_to_message
                    owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

                    if original_message.caption:
                        post_text = f"{original_message.caption[:20]}..."
                    elif original_message.text:
                        post_text = f"{original_message.text[:20]}..."
                    else:
                        post_text = "No text"
                    sent_from = update.message.from_user
                    profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                    comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                    await delete_comment(update, context, post_text, comment_text, user_id, owner, f'Symbols: {nickname[:19]}', profile_link)
                    return
                
                if (comment_time - post_time) < timedelta(minutes=10):
                    ai_result = classify_nickname_and_comment(nickname, text)
                    print(f"AI result for {nickname}: {ai_result}")

                    if ai_result == "spam":
                        original_message = update.message.reply_to_message
                        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

                        if original_message.caption:
                            post_text = f"{original_message.caption[:20]}..."
                        elif original_message.text:
                            post_text = f"{original_message.text[:20]}..."
                        else:
                            post_text = "No text"
                        sent_from = update.message.from_user
                        profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                        comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                        await delete_comment(update, context, post_text, comment_text, user_id, owner, f'AI: {nickname[:19]}', profile_link)
                        return
                    
                else:
                    nickname_result = predict_nick(nickname, vectorizer, model)
                    print(f"Nickname result for {nickname}: {nickname_result}")
                    if nickname_result == "Spam":
                        original_message = update.message.reply_to_message
                        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

                        if original_message.caption:
                            post_text = f"{original_message.caption[:20]}..."
                        elif original_message.text:
                            post_text = f"{original_message.text[:20]}..."
                        else:
                            post_text = "No text"
                        sent_from = update.message.from_user
                        profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                        comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                        await delete_comment(update, context, post_text, comment_text, user_id, owner, f'Nickname: {nickname[:19]}', profile_link)
                        return
                
                if nickname in bad or username in bad_username or user_id in bad_id or ' sliv' in nickname or 'sliv ' in nickname: 
                    original_message = update.message.reply_to_message
                    owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

                    if original_message.caption:
                        post_text = f"{original_message.caption[:20]}..."
                    elif original_message.text:
                        post_text = f"{original_message.text[:20]}..."
                    else:
                        post_text = "No text"
                    sent_from = update.message.from_user
                    profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                    comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                    asyncio.create_task(delete_comment(update, context, post_text, comment_text, user_id, owner, f'Nickname: {nickname[:19]}', profile_link, delay=6))
                    return
                
            except Exception as e:
                print(f"Error checking nickname: {e}")

    elif hasattr(update, "edited_message") and update.edited_message and update.edited_message.chat and update.edited_message.reply_to_message and update.edited_message.chat.type == "supergroup":
        try:
            await asyncio.sleep(0.1)
            owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.edited_message.chat.id))
        except:
            return
        #checking if the user is in the good list or if i have amrked him as good(permament block )
        user_id = update.edited_message.from_user.id
        username = update.edited_message.from_user.username.lower() if update.edited_message.from_user.username else "unknown_user"
        print(f"Message from supergroup : {update.edited_message.text}")

        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.edited_message.chat.id))
        blocked_user_queryset = (BlockedUser .objects.filter)(
            username=user_id,
            owner=owner
        ).select_related('owner') 
        blocked_user = await sync_to_async(blocked_user_queryset.first)() 
        #checking if the user is in the good list or if i have amrked him as good(permament block )
        if username in good or update.edited_message.from_user.id in good_id or (blocked_user and blocked_user.is_active()):
            pass
        else:           
            try:
                nickname = update.edited_message.from_user.full_name.lower() if update.edited_message.from_user.full_name else "unknown_nickname"
                text = update.edited_message.text if update.edited_message.text else "No text"

                ai_result = classify_nickname_and_comment(nickname, text)
                print(f"AI result for edited message by {nickname}: {ai_result}")

                if ai_result == "spam":
                    original_message = update.edited_message.reply_to_message

                    if original_message.caption:
                        post_text = f"{original_message.caption[:20]}..."
                    elif original_message.text:
                        post_text = f"{original_message.text[:20]}..."
                    else:
                        post_text = "No text"
                    sent_from = update.edited_message.from_user
                    profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                    comment_text = (update.edited_message.text[:300] if update.edited_message.text else "No text") + f" by {username}"
                    await delete_edited_comment(update, context, post_text, comment_text, user_id, owner, f'AI: {nickname[:19]}', profile_link)
                    return
            except Exception as e:
                print(f"Error checking edited message: {e}")
        
async def delayed_check(user_id, update: Update, context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(12)
    owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))
    username = update.message.from_user.username.lower() if update.message.from_user.username else "unknown_user"
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

                original_message = update.message.reply_to_message
                if image_result == "Spam":
                    if original_message.caption:
                        post_text = f"{original_message.caption[:20]}..."
                    elif original_message.text:
                        post_text = f"{original_message.text[:20]}..."
                    else:
                        post_text = "No text"

                    sent_from = update.message.from_user
                    profile_link = f"https://t.me/{sent_from.username}" if sent_from.username else f"tg://user?id={sent_from.id}"
                    comment_text = (update.message.text[:300] if update.message.text else "No text") + f" by {username}"
                    await delete_comment(update, context, post_text, comment_text, user_id, owner, 'Image', profile_link)
                    return
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
    application.add_handler(MessageHandler(filters.ALL, handle_message, block=False)) # mesage handler for all messages
    # Start polling the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())



