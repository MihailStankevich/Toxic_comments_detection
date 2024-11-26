
import nest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from moderation.ml import model, vectorizer
from moderation.models import DeletedComment 
def predict_comment(comment, vectorizer, model):
    # Vectorize the input comment
    comment_vector = vectorizer.transform([comment])
    
    # Predict the class
    prediction = model.predict(comment_vector)
    
    # If needed, add a mapping for labels
    label_mapping = {0: "Non-offensive", 1: "Offensive"}
    return label_mapping.get(prediction[0], "Unknown")


nest_asyncio.apply()
deleted_messages = []
# Function to handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if update.message.chat.type == "supergroup":
        original_message = update.message.reply_to_message
        print(f"Message from supergroup: {update.message.text}")
        print(f"Original post text: {original_message.text}")
        result = predict_comment(update.message.text, vectorizer, model)
        print(result)
        print(update.message.from_user.username)
        
        
        if result == "Offensive":
            
            await sync_to_async(DeletedComment.objects.create)(
                post=original_message.text,
                comment=update.message.text,
                user=update.message.from_user.username,
                channel_id=str(update.message.chat.id)
            )
            await update.message.delete()
            deleted_messages.append(update.message.text)
            print(f'The comment -{update.message.text}- was deleted')
            print("Channel id = ", update.message.chat.id)
        
        

# Main function to set up the bot
async def main():
    # Your bot token
    TOKEN = "8189505850:AAHtY32aECsTE9ODhQIHLiE2uLJV4htXU8E"

    # Create the application
    application = Application.builder().token(TOKEN).build()

    # Add a message handler to listen for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling the bot
    await application.run_polling()

# Run the bot
if __name__ == "__main__":
    asyncio.run(main())



