import requests
import tensorflow as tf
import os
from dotenv import load_dotenv

import nest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from moderation.ml import model, image_model
from moderation.models import DeletedComment , Owner, BlockedUser
load_dotenv()
token = os.getenv('TOKEN')
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

nest_asyncio.apply()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if update.message.chat.type == "supergroup":
        owner = await sync_to_async(Owner.objects.get)(channel_id=str(update.message.chat.id))

        blocked_user_queryset = (BlockedUser .objects.filter)(
            username=update.message.from_user.username.lower(),
            owner=owner
        ).select_related('owner') 
        
        blocked_user = await sync_to_async(blocked_user_queryset.first)() 

        if blocked_user and blocked_user.is_active():
            await update.message.reply_text("You are blocked from commenting.")
            await update.message.delete()
            return  

        
        original_message = update.message.reply_to_message
        print(f"Message from supergroup: {update.message.text}")
        result = predict_comment(update.message.text, model)
        print(result)

        #### test of downloading avatar
        
        #### end of test  
        if result == "Offensive":
            print("Owner: ",owner)

            if original_message.caption:
                post_text = f"{original_message.caption[:20]}..."
            elif original_message.text:
                post_text = f"{original_message.text[:20]}..."
            else:
                post_text = "No text"
            await sync_to_async(DeletedComment.objects.create)(
                post=post_text.lower(),
                comment=update.message.text.lower(),
                user=update.message.from_user.username.lower(),
                channel_id=str(update.message.chat.id),
                owner = owner,
                detected_by = 'Comment text'
            )
            await update.message.delete()
            print(f'The comment -{update.message.text}- was deleted because it had been classified as spam/offensive by text')
            
            #checking the profile image
        else:
            try:
                user_id = update.message.from_user.id
                profile_photos = await context.bot.get_user_profile_photos(user_id=user_id)

                if profile_photos.photos:
                    largest_photo = max(profile_photos.photos[0], key=lambda x: x.width)
                    file = await context.bot.get_file(largest_photo.file_id)
                    photo_path = f"profile_photos/{user_id}_profile_photo.jpg"
                    await file.download_to_drive(photo_path)

                    image_result = classify_image(photo_path, image_model)

                    os.remove(photo_path)  # Clean up from my directory
                    print(f"Image result: {image_result}")

                    if image_result == 'Spam':
                        if original_message.caption:
                            post_text = f"{original_message.caption[:20]}..."
                        elif original_message.text:
                            post_text = f"{original_message.text[:20]}..."
                        else:
                            post_text = "No text"
                        await sync_to_async(DeletedComment.objects.create)(
                            post=post_text.lower(),
                            comment=update.message.text.lower(),
                            user=update.message.from_user.username.lower(),
                            channel_id=str(update.message.chat.id),
                            owner = owner,
                            detected_by = 'Profile picture'
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



