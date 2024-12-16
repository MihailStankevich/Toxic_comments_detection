
import nest_asyncio
import asyncio
from asgiref.sync import sync_to_async
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from moderation.ml import model
from moderation.models import DeletedComment , Owner, BlockedUser
def predict_comment(comment, model):

    #comment_vector = vectorizer.transform([comment])

    prediction = model.predict([comment])

    label_mapping = {0: "Non-offensive", 1: "Offensive"}
    return label_mapping.get(prediction[0], "Unknown")


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
                owner = owner
            )
            await update.message.delete()
            print(f'The comment -{update.message.text}- was deleted')
        
        

# Main function to set up the bot
async def main():

    TOKEN = "8189505850:AAHtY32aECsTE9ODhQIHLiE2uLJV4htXU8E"

    # Create the application
    application = Application.builder().token(TOKEN).build()

    # Add a message handler to listen for all text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start polling the bot
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())



