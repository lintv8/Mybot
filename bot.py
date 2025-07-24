import os
import json
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# 从环境变量读取配置
TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")  # 管理员的Telegram ID

# 确保ADMIN_ID已设置
if not ADMIN_ID:
    raise ValueError("请设置ADMIN_ID环境变量")
ADMIN_ID = int(ADMIN_ID)

# 状态常量
SELECTING_PRODUCT, SELECTING_PAYMENT, ENTERING_EMAIL, CONFIRMING_ORDER, PAYMENT_WAITING = range(5)
# 商品管理状态
ADDING_PRODUCT, EDITING_PRODUCT_TITLE, EDITING_PRODUCT_DESC, EDITING_PRODUCT_PRICE, EDITING_PRODUCT_PAYMENT = range(5, 10)

# 数据文件路径
ORDERS_FILE = "orders.json"
PRODUCTS_FILE = "products.json"

# 付款方式常量
PAYMENT_METHODS = {
    "rmb": "人民币",
    "usd": "美元",
    "pliso": "PLISO虚拟币"
}

# 加载商品数据
def load_products():
    """加载商品数据"""
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 初始默认商品
        return {
            "product1": {
                "name": "高级素材包",
                "description": "包含100+高质量设计素材，适用于各种项目",
                "prices": {
                    "rmb": 50.0,
                    "usd": 7.0,
                    "pliso": 5.0
                },
                "payment_methods": ["rmb", "usd", "pliso"],  # 支持的付款方式
                "id": "product1"
            }
        }

# 保存商品数据
def save_products(products):
    """保存商品数据"""
    with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2, ensure_ascii=False)

# 加载订单数据
def load_orders():
    """加载订单数据"""
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 保存新订单
def save_order(order):
    """保存新订单"""
    orders = load_orders()
    orders.append(order)
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2)

# 更新订单状态
def update_order(order_id, status):
    """更新订单状态"""
    orders = load_orders()
    for order in orders:
        if order["id"] == order_id:
            order["status"] = status
            order["updated_at"] = time.time()
            break
    with open(ORDERS_FILE, "w") as f:
        json.dump(orders, f, indent=2)

# 首页
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理/start命令"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("浏览商品", callback_data="show_products")],
        [InlineKeyboardButton("查询订单", callback_data="check_orders")]
    ]
    if update.effective_user.id == ADMIN_ID:
        keyboard.extend([
            [InlineKeyboardButton("管理订单", callback_data="manage_orders")],
            [InlineKeyboardButton("管理商品", callback_data="manage_products")]
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        rf"您好，{user.mention_html()}！欢迎使用虚拟商品商店机器人。",
        reply_markup=reply_markup
    )

# 商品管理 - 主界面
async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员管理商品"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # 验证是否为管理员
    if user_id != ADMIN_ID:
        if query:
            await query.answer("您没有权限执行此操作", show_alert=True)
        else:
            await update.message.reply_text("您没有权限执行此操作")
        return
    
    await query.answer()
    products = load_products()
    
    keyboard = []
    # 添加商品按钮
    keyboard.append([InlineKeyboardButton("添加新商品", callback_data="add_product")])
    
    # 现有商品列表
    for product_id, product in products.items():
        keyboard.append([InlineKeyboardButton(
            f"编辑: {product['name']}",
            callback_data=f"edit_product_{product_id}"
        )])
    
    keyboard.append([InlineKeyboardButton("返回首页", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="商品管理：",
        reply_markup=reply_markup
    )

# 添加新商品
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """开始添加新商品流程"""
    query = update.callback_query
    await query.answer()
    
    # 生成临时商品ID
    temp_id = f"temp_{int(time.time())}"
    context.user_data["current_product_id"] = temp_id
    context.user_data["new_product"] = {
        "id": temp_id,
        "name": "",
        "description": "",
        "prices": {},
        "payment_methods": []
    }
    
    await query.edit_message_text(text="请输入新商品的标题：")
    return ADDING_PRODUCT

# 处理商品标题输入
async def handle_product_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理商品标题输入"""
    product = context.user_data["new_product"]
    product["name"] = update.message.text
    
    await update.message.reply_text("请输入商品的介绍：")
    return EDITING_PRODUCT_DESC

# 处理商品描述输入
async def handle_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理商品描述输入"""
    product = context.user_data["new_product"]
    product["description"] = update.message.text
    
    await update.message.reply_text("请输入商品价格（格式：货币类型:价格，例如 rmb:50 usd:7 pliso:5）：\n支持的货币：rmb(人民币), usd(美元), pliso(虚拟币)")
    return EDITING_PRODUCT_PRICE

# 处理商品价格输入
async def handle_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理商品价格输入"""
    product = context.user_data["new_product"]
    price_input = update.message.text
    
    try:
        # 解析价格输入
        price_parts = price_input.split()
        for part in price_parts:
            currency, value = part.split(":")
            if currency in PAYMENT_METHODS:
                product["prices"][currency] = float(value)
                product["payment_methods"].append(currency)
        
        if not product["payment_methods"]:
            await update.message.reply_text("未识别到有效价格，请重新输入（格式：货币类型:价格，例如 rmb:50 usd:7）：")
            return EDITING_PRODUCT_PRICE
        
        # 显示确认信息
        price_text = "\n".join([f"{PAYMENT_METHODS[c]}: {v}" for c, v in product["prices"].items()])
        keyboard = [
            [InlineKeyboardButton("确认保存", callback_data="confirm_save_product")],
            [InlineKeyboardButton("重新输入价格", callback_data="retry_product_price")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            text=f"商品信息确认：\n"
                 f"标题：{product['name']}\n"
                 f"介绍：{product['description']}\n"
                 f"价格：\n{price_text}",
            reply_markup=reply_markup
        )
        return EDITING_PRODUCT_PAYMENT
    
    except Exception as e:
        await update.message.reply_text(f"格式错误，请重新输入（格式：货币类型:价格，例如 rmb:50 usd:7）：\n错误：{str(e)}")
        return EDITING_PRODUCT_PRICE

# 确认保存商品
async def confirm_save_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """确认保存商品"""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    new_product = context.user_data["new_product"]
    
    # 生成正式商品ID
    product_id = f"product_{int(time.time())}"
    new_product["id"] = product_id
    
    # 保存商品
    products[product_id] = new_product
    save_products(products)
    
    await query.edit_message_text(f"商品《{new_product['name']}》已成功添加！")
    # 返回商品管理页面
    await manage_products(update, context)
    return ConversationHandler.END

# 展示商品列表
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """展示商品列表"""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    keyboard = []
    for product_id, product in products.items():
        # 显示支持的付款方式
        payment_text = "/".join([PAYMENT_METHODS[m] for m in product["payment_methods"]])
        keyboard.append([InlineKeyboardButton(
            f"{product['name']} ({payment_text})",
            callback_data=f"select_{product_id}"
        )])
    keyboard.append([InlineKeyboardButton("返回首页", callback_data="back_to_start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="请选择您要购买的商品：",
        reply_markup=reply_markup
    )
    return SELECTING_PRODUCT

# 选择付款方式
async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """选择付款方式"""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[1]
    products = load_products()
    product = products[product_id]
    context.user_data["selected_product"] = product
    
    # 显示可用的付款方式
    keyboard = []
    for method in product["payment_methods"]:
        keyboard.append([InlineKeyboardButton(
            f"{PAYMENT_METHODS[method]} - {product['prices'][method]}",
            callback_data=f"payment_{method}"
        )])
    keyboard.append([InlineKeyboardButton("返回商品列表", callback_data="show_products")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text=f"您选择了：{product['name']}\n"
             f"描述：{product['description']}\n\n"
             f"请选择付款方式：",
        reply_markup=reply_markup
    )
    return SELECTING_PAYMENT

# 处理付款方式选择
async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理付款方式选择"""
    query = update.callback_query
    await query.answer()
    
    payment_method = query.data.split("_")[1]
    context.user_data["selected_payment"] = payment_method
    
    await query.edit_message_text(
        text="请输入您的邮箱地址，以便我们发送商品给您："
    )
    return ENTERING_EMAIL

# 获取用户邮箱
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """获取用户邮箱"""
    email = update.message.text
    # 简单验证邮箱格式
    if "@" not in email:
        await update.message.reply_text("请输入有效的邮箱地址（包含@符号）：")
        return ENTERING_EMAIL
    
    context.user_data["email"] = email
    product = context.user_data["selected_product"]
    payment_method = context.user_data["selected_payment"]
    price = product["prices"][payment_method]
    
    keyboard = [
        [InlineKeyboardButton("确认购买", callback_data="confirm_order")],
        [InlineKeyboardButton("取消", callback_data="cancel_order")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        text=f"请确认您的订单信息：\n"
             f"商品：{product['name']}\n"
             f"付款方式：{PAYMENT_METHODS[payment_method]}\n"
             f"价格：{price} {payment_method}\n"
             f"接收邮箱：{email}\n",
        reply_markup=reply_markup
    )
    return CONFIRMING_ORDER

# 确认订单并生成付款信息
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """确认订单并生成付款信息"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    product = context.user_data["selected_product"]
    email = context.user_data["email"]
    payment_method = context.user_data["selected_payment"]
    price = product["prices"][payment_method]
    
    # 生成订单ID
    order_id = f"order_{int(time.time())}_{user.id}"
    
    # 创建订单
    order = {
        "id": order_id,
        "user_id": user.id,
        "user_name": user.full_name or user.username,
        "product": product,
        "email": email,
        "payment_method": payment_method,
        "amount": price,
        "status": "pending",  # pending, paid, completed, cancelled
        "created_at": time.time(),
        "updated_at": time.time()
    }
    
    # 保存订单
    save_order(order)
    
    # 向管理员发送新订单通知
    admin_message = f"新订单 #{order_id}\n" \
                   f"用户：{user.full_name} (ID: {user.id})\n" \
                   f"商品：{product['name']}\n" \
                   f"付款方式：{PAYMENT_METHODS[payment_method]}\n" \
                   f"金额：{price}\n" \
                   f"邮箱：{email}"
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_message
    )
    
    # 不同付款方式的收款信息（实际应用中请替换为你的真实收款信息）
    payment_info = {
        "rmb": "支付宝：123456789（张三）\n微信：wechat123（张三）",
        "usd": "PayPal：example@paypal.com",
        "pliso": "PLISO地址：PLISO_ADDRESS_HERE"
    }
    
    # 显示付款信息
    keyboard = [
        [InlineKeyboardButton("已付款", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("取消订单", callback_data=f"cancel_{order_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text=f"订单创建成功！订单号：{order_id}\n\n"
             f"请按照以下方式付款 {price} {PAYMENT_METHODS[payment_method]}：\n"
             f"{payment_info[payment_method]}\n\n"
             f"付款完成后请点击下方'已付款'按钮，我们会尽快处理您的订单。",
        reply_markup=reply_markup
    )
    
    context.user_data["current_order_id"] = order_id
    return PAYMENT_WAITING

# 其他函数保持不变（mark_as_paid, cancel_order, check_orders等）
async def mark_as_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """标记订单为已付款"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.split("_")[1]
    update_order(order_id, "paid")
    
    # 通知管理员
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"用户已标记订单 #{order_id} 为已付款，请核实并处理。"
    )
    
    await query.edit_message_text(
        text=f"已收到您的付款通知，我们将尽快核实您的付款。\n"
             f"一旦确认，我们会将商品发送到您的邮箱：{context.user_data['email']}\n"
             f"您可以随时使用 /check_orders 命令查询订单状态。"
    )
    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消订单"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("cancel_order"):
        # 取消未确认的订单
        await query.edit_message_text("订单已取消。")
    else:
        # 取消已创建的订单
        order_id = query.data.split("_")[1]
        update_order(order_id, "cancelled")
        
        # 通知管理员
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"订单 #{order_id} 已被用户取消。"
        )
        
        await query.edit_message_text(f"订单 #{order_id} 已取消。")
    
    return ConversationHandler.END

async def check_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """查询用户的订单"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    orders = load_orders()
    user_orders = [order for order in orders if order["user_id"] == user_id]
    
    if not user_orders:
        text = "您没有任何订单。"
        keyboard = [[InlineKeyboardButton("浏览商品", callback_data="show_products")]]
    else:
        text = "您的订单列表：\n\n"
        for order in sorted(user_orders, key=lambda x: x["created_at"], reverse=True):
            status_text = {
                "pending": "等待付款",
                "paid": "已付款，处理中",
                "completed": "已完成",
                "cancelled": "已取消"
            }.get(order["status"], order["status"])
            
            text += f"订单号：{order['id'][-8:]}\n"  # 显示订单号后8位
            text += f"商品：{order['product']['name']}\n"
            text += f"付款方式：{PAYMENT_METHODS[order['payment_method']]}\n"
            text += f"状态：{status_text}\n"
            text += f"时间：{time.strftime('%Y-%m-%d %H:%M', time.localtime(order['created_at']))}\n\n"
        
        keyboard = [
            [InlineKeyboardButton("浏览商品", callback_data="show_products")],
            [InlineKeyboardButton("返回首页", callback_data="back_to_start")]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.edit_message_text(text=text, reply_markup=reply_markup)
    else:
        await message.reply_text(text=text, reply_markup=reply_markup)

async def manage_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """管理员管理订单"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # 验证是否为管理员
    if user_id != ADMIN_ID:
        if query:
            await query.answer("您没有权限执行此操作", show_alert=True)
        else:
            await update.message.reply_text("您没有权限执行此操作")
        return
    
    await query.answer()
    
    orders = load_orders()
    # 按创建时间排序，最新的在前
    orders = sorted(orders, key=lambda x: x["created_at"], reverse=True)
    
    keyboard = []
    for order in orders[:10]:  # 只显示最近10个订单
        status_text = {
            "pending": "等待付款",
            "paid": "已付款",
            "completed": "已完成",
            "cancelled": "已取消"
        }.get(order["status"], order["status"])
        
        keyboard.append([InlineKeyboardButton(
            f"订单 {order['id'][-8:]} - {status_text}",
            callback_data=f"order_details_{order['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("返回首页", callback_data="back_to_start")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="订单管理 - 最近10个订单：",
        reply_markup=reply_markup
    )

async def order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """显示订单详情（管理员）"""
    query = update.callback_query
    await query.answer()
    
    # 验证是否为管理员
    if update.effective_user.id != ADMIN_ID:
        await query.answer("您没有权限执行此操作", show_alert=True)
        return
    
    order_id = query.data.split("_")[2]
    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    
    if not order:
        await query.edit_message_text("订单不存在")
        return
    
    # 构建状态按钮
    status_buttons = []
    current_status = order["status"]
    
    if current_status != "completed":
        status_buttons.append(InlineKeyboardButton(
            "标记为已完成",
            callback_data=f"mark_completed_{order_id}"
        ))
    
    if current_status != "cancelled":
        status_buttons.append(InlineKeyboardButton(
            "标记为已取消",
            callback_data=f"mark_cancelled_{order_id}"
        ))
    
    keyboard = [status_buttons] if status_buttons else []
    keyboard.append([InlineKeyboardButton("返回订单列表", callback_data="manage_orders")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    status_text = {
        "pending": "等待付款",
        "paid": "已付款",
        "completed": "已完成",
        "cancelled": "已取消"
    }.get(order["status"], order["status"])
    
    await query.edit_message_text(
        text=f"订单详情 #{order_id}\n\n"
             f"用户：{order['user_name']} (ID: {order['user_id']})\n"
             f"商品：{order['product']['name']}\n"
             f"付款方式：{PAYMENT_METHODS[order['payment_method']]}\n"
             f"金额：{order['amount']}\n"
             f"邮箱：{order['email']}\n"
             f"状态：{status_text}\n"
             f"创建时间：{time.strftime('%Y-%m-%d %H:%M', time.localtime(order['created_at']))}\n"
             f"更新时间：{time.strftime('%Y-%m-%d %H:%M', time.localtime(order['updated_at']))}",
        reply_markup=reply_markup
    )

async def update_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """更新订单状态（管理员操作）"""
    query = update.callback_query
    await query.answer()
    
    # 验证是否为管理员
    if update.effective_user.id != ADMIN_ID:
        await query.answer("您没有权限执行此操作", show_alert=True)
        return
    
    parts = query.data.split("_")
    status = parts[1]
    order_id = "_".join(parts[2:])  # 处理包含下划线的订单ID
    
    update_order(order_id, status)
    
    # 通知用户订单状态已更新
    orders = load_orders()
    order = next((o for o in orders if o["id"] == order_id), None)
    
    if order:
        status_text = "已完成" if status == "completed" else "已取消"
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=f"您的订单 #{order_id[-8:]} 已{status_text}。\n"
                 f"如果已完成，商品已发送至您的邮箱：{order['email']}"
        )
    
    await query.edit_message_text(f"订单 #{order_id} 已标记为{status}。")
    # 返回订单管理列表
    await manage_orders(update, context)

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """返回首页"""
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """取消当前操作"""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("操作已取消。")
    else:
        await update.message.reply_text("操作已取消。")
    return ConversationHandler.END

def main():
    """主函数"""
    application = ApplicationBuilder().token(TOKEN).build()
    
    # 购买流程的对话处理器
    buy_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_products, pattern="^show_products$")],
        states={
            SELECTING_PRODUCT: [CallbackQueryHandler(select_payment_method, pattern="^select_")],
            SELECTING_PAYMENT: [CallbackQueryHandler(handle_payment_selection, pattern="^payment_")],
            ENTERING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_email)],
            CONFIRMING_ORDER: [
                CallbackQueryHandler(confirm_order, pattern="^confirm_order$"),
                CallbackQueryHandler(cancel_order, pattern="^cancel_order$")
            ],
            PAYMENT_WAITING: [
                CallbackQueryHandler(mark_as_paid, pattern="^paid_"),
                CallbackQueryHandler(cancel_order, pattern="^cancel_")
            ]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # 商品管理的对话处理器
    product_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_product, pattern="^add_product$")],
        states={
            ADDING_PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_title)],
            EDITING_PRODUCT_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_desc)],
            EDITING_PRODUCT_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_product_price),
                CallbackQueryHandler(handle_product_price, pattern="^retry_product_price$")
            ],
            EDITING_PRODUCT_PAYMENT: [CallbackQueryHandler(confirm_save_product, pattern="^confirm_save_product$")]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    # 注册命令处理器
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("check_orders", check_orders))
    application.add_handler(buy_conv_handler)
    application.add_handler(product_conv_handler)
    
    # 注册回调处理器
    application.add_handler(CallbackQueryHandler(back_to_start, pattern="^back_to_start$"))
    application.add_handler(CallbackQueryHandler(check_orders, pattern="^check_orders$"))
    application.add_handler(CallbackQueryHandler(manage_orders, pattern="^manage_orders$"))
    application.add_handler(CallbackQueryHandler(manage_products, pattern="^manage_products$"))
    application.add_handler(CallbackQueryHandler(order_details, pattern="^order_details_"))
    application.add_handler(CallbackQueryHandler(update_order_status, pattern="^mark_"))
    
    # 启动机器人
    application.run_polling()

if __name__ == "__main__":
    main()
