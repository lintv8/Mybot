import os
import smtplib
from email.mime.text import MIMEText
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
from dotenv import load_dotenv

load_dotenv()

# Gmail 邮箱设置
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 商品列表（示例）
PRODUCTS = {
    "product1": "https://downloadlink.com/file1.zip",
    "product2": "ABC-DEF-1234-CODE",  # 兑换码
}

# 状态常量
SELECT_PRODUCT, ENTER_EMAIL, WAIT_PAYMENT = range(3)

# 订单临时缓存
user_orders = {}

# 发送邮件函数
def send_email(to_email, subject, content):
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())

# /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "欢迎选购，请输入你要购买的产品编号：\n"
    for k in PRODUCTS:
        text += f"- {k}\n"
    await update.message.reply_text(text)
    return SELECT_PRODUCT

# 用户输入商品编号
async def select_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product = update.message.text.strip()
    if product not in PRODUCTS:
        await update.message.reply_text("产品不存在，请重新输入。")
        return SELECT_PRODUCT
    context.user_data["product"] = product
    await update.message.reply_text("请输入你的邮箱地址：")
    return ENTER_EMAIL

# 用户输入邮箱
async def enter_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    context.user_data["email"] = email
    await update.message.reply_text(
        f"请付款后回复「已付款」，我们将把产品发送到 {email}\n（提示：目前不接入支付，仅手动确认）"
    )
    return WAIT_PAYMENT

# 用户手动确认付款
async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = context.user_data["email"]
    product_key = context.user_data["product"]
    content = PRODUCTS[product_key]

    try:
        send_email(
            email,
            "感谢购买 - 虚拟产品已发送",
            f"你购买的商品（{product_key}）如下：\n\n{content}",
        )
        await update.message.reply_text("已成功发送邮件，请查收（如未收到请查垃圾箱）。")
    except Exception as e:
        await update.message.reply_text("发送邮件失败，请联系管理员。\n错误信息：" + str(e))

    return ConversationHandler.END

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("订单已取消。")
    return ConversationHandler.END

# 主函数
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_product)],
            ENTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_email)],
            WAIT_PAYMENT: [MessageHandler(filters.Regex("已付款"), confirm_payment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()
