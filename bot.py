import os
import smtplib
from email.mime.text import MIMEText
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# 状态定义
EMAIL, PAYMENT = range(2)

# 读取发货内容
def get_next_code():
    with open("codes.txt", "r") as f:
        codes = f.readlines()
    if not codes:
        return None
    code = codes[0].strip()
    with open("codes.txt", "w") as f:
        f.writelines(codes[1:])
    return code

# 发邮件函数
def send_email(to_email, code):
    from_email = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    msg = MIMEText(f"感谢购买，您的兑换码/下载链接为：\n\n{code}")
    msg["Subject"] = "发货成功"
    msg["From"] = from_email
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(from_email, password)
        server.send_message(msg)

# 开始下单
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("欢迎购买，请输入您的邮箱：")
    return EMAIL

# 用户输入邮箱
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["email"] = update.message.text
    await update.message.reply_text("请完成付款后，输入 /paid 命令通知我发货。")
    return PAYMENT

# 用户付款完成
async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = context.user_data.get("email")
    code = get_next_code()
    if not code:
        await update.message.reply_text("库存已空，请联系管理员。")
        return ConversationHandler.END
    send_email(email, code)
    await update.message.reply_text(f"已发送至邮箱 {email}，感谢购买！")
    return ConversationHandler.END

# 取消操作
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("已取消订单。", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# 主函数
def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            PAYMENT: [CommandHandler("paid", paid)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    print("Bot started...")
    application.run_polling()

if __name__ == "__main__":
    main()
