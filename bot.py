from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """用户取消订单流程"""
    query = update.callback_query
    await query.answer()

    # 从回调数据提取订单ID
    order_id = query.data.split("_")[-1] if "_" in query.data else ""
    
    if order_id:
        # 更新订单状态
        update_order(order_id, "cancelled")

        # 通知管理员
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"❌ 用户取消了订单 #{order_id}"
        )

        # 给用户反馈并提供返回按钮
        await query.edit_message_text(
            text=f"✅ 订单已取消（订单号：{order_id}）\n欢迎随时再次选购～",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("返回首页", callback_data="back_to_start")]
            ])
        )
    else:
        # 如果无法识别订单号
        await query.edit_message_text(
            text="⚠️ 订单取消失败：无法识别订单编号。",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("返回首页", callback_data="back_to_start")]
            ])
        )

    return ConversationHandler.END
