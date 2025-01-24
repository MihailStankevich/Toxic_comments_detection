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
import numpy as np
from tensorflow.keras.preprocessing import image
##############
#  try to do by hashing
##############
# Set DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'channelmoderation.settings')
django.setup()
from moderation.ml import image_model
from moderation.models import DeletedComment , Owner, BlockedUser
load_dotenv()
token = os.getenv('TOKEN')

class_names = ['not_spam', 'spam']
def preprocess_image(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img)
    img_array = img_array / 255.0  # Rescale pixel values
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    return img_array

# Define function to predict image class
def classify_image(img_path):
    img_array = preprocess_image(img_path)
    
    # Prepare input tensor
    input_details = image_model.get_input_details()
    output_details = image_model.get_output_details()
    
    # Set the tensor to the input data
    image_model.set_tensor(input_details[0]['index'], img_array)
    
    # Run inference
    image_model.invoke()
    
    # Get the outputt
    predictions = image_model.get_tensor(output_details[0]['index'])
    predicted_class = np.argmax(predictions, axis=1)[0]
    confidence = predictions[0][predicted_class]
    return class_names[predicted_class], confidence

nest_asyncio.apply()

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
        print(f"Message from supergroup: {update.message.text}")


        if not original_message:
            pass
            '''
            print("Owner: ",owner)

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
                comment=update.message.text.lower(),
                user=username,
                channel_id=str(update.message.chat.id),
                owner = owner,
                detected_by = 'Comment text',
                profile_link=profile_link
            )
            await update.message.delete()
            print(f'The comment -{update.message.text}- was deleted because it had been classified as spam/offensive by text')
            
            #checking the profile image
            '''
        else:
            try:
                user_id = update.message.from_user.id
                profile_photos = await context.bot.get_user_profile_photos(user_id=user_id)

                if profile_photos.photos:
                    largest_photo = max(profile_photos.photos[0], key=lambda x: x.width)
                    file = await context.bot.get_file(largest_photo.file_id)
                    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
                        await file.download_to_drive(temp_file.name) 
                        image_result, confidence = classify_image(temp_file.name, image_model)

                        print(f"Image result: {image_result} with confidence: {confidence:.2f}")

                        if image_result == 'spam' and confidence > 0.8:
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
                    
            except Exception as e:
                print(f"Error handling profile photo logic: {e}")
        

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



