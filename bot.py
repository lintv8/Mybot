以下是修复后的完整代码，已将 ADMIN_ID 环境变量值设置为 778899（你可根据实际需求在环境变量中修改，代码里也保留了从环境变量读取的逻辑，方便灵活调整 ），同时完善了环境变量校验等，确保代码可运行：
import os
import json
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量读取配置，若未设置则用默认值（这里演示设为778899，实际建议用环境变量管理）
TOKEN = os.getenv("TG_BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "778899")  # 管理员ID，默认设为778899
ADMIN_ID = int(ADMIN_ID)  # 转为整型，符合 Telegram ID 通常为数字的特点

# 确保机器人令牌已设置
if not TOKEN:
    raise ValueError("请设置 TG_BOT_TOKEN 环境变量")

# 状态常量
SELECTING_PRODUCT, SELECTING_PAYMENT, ENTERING_EMAIL, CONFIRMING_ORDER, PAYMENT_WAITING = range(5)
ADDING_PRODUCT, EDITING_PRODUCT_TITLE, EDITING_PRODUCT_DESC, EDITING_PRODUCT_PRICE, EDITING_PRODUCT_PAYMENT = range(5, 10)

# 数据文件路径
ORDERS_FILE = "orders.json"
PRODUCTS_FILE = "products.json"

# 付款方式常量
PAYMENT_METHODS = {
    "rmb": "人民币",
    "usd": "美元",
    "crypto": "虚拟货币"
}

# 权限校验函数
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# 加载商品数据
def load_products() -> dict:
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
                    "crypto": 0.01
                },
                "payment_methods": ["rmb", "usd", "crypto"],
                "id": "product1"
            }
        }

# 保存商品数据
def save_products(products: dict) -> None:
    """保存商品数据"""
    try:
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存商品失败: {str(e)}")

# 加载订单数据
def load_orders() -> list:
    """加载订单数据"""
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# 保存新订单
def save_order(order: dict) -> None:
    """保存新订单"""
    try:
        orders = load_orders()
        orders.append(order)
        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=2)
    except Exception as e:
        logger.error(f"保存订单失败: {str(e)}")

# 更新订单状态
def update_order(order_id: str, status: str) -> None:
    """更新订单状态"""
    try:
        orders = load_orders()
        for order in orders:
            if order["id"] == order_id:
                order["status"] = status
                order["updated_at"] = time.time()
                break
        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=2)
    except Exception as e:
        logger.error(f"更新订单失败: {str(e)}")

# 首页
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/start命令"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("浏览商品", callback_data="show_products")],
        [InlineKeyboardButton("查询订单", callback_data="check_orders")]
    ]
    if is_admin(update.effective_user.id):
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
async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """管理员管理商品"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await query.answer("您没有权限执行此操作", show_alert=True)
        return
    
    await query.answer()
    products = load_products()
    
    keyboard = [[InlineKeyboardButton("添加新商品", callback_data="add_product")]]
    
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
async def add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """开始添加新商品流程"""
    query = update.callback_query
    await query.answer()
    
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
async def handle_product_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理商品标题输入"""
    product = context.user_data["new_product"]
    product["name"] = update.message.text
    
    await update.message.reply_text("请输入商品的介绍：")
    return EDITING_PRODUCT_DESC

# 处理商品描述输入
async def handle_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理商品描述输入"""
    product = context.user_data["new_product"]
    product["description"] = update.message.text
    
    await update.message.reply_text("请输入商品价格（格式：货币类型:价格，例如 rmb:50 usd:7 crypto:0.01）：\n支持的货币：rmb(人民币), usd(美元), crypto(虚拟货币)")
    return EDITING_PRODUCT_PRICE

# 处理商品价格输入
async def handle_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """处理商品价格输入"""
    product = context.user_data["new_product"]
    price_input = update.message.text
    
    try:
        price_parts = price_input.split()
        for part in price_parts:
            currency, value = part.split(":")
            if currency in PAYMENT_METHODS:
                product["prices"][currency] = float(value)
                product["payment_methods"].append(currency)
        
        if not product["payment_methods"]:
            await update.message.reply_text("未识别到有效价格，请重新输入（格式：货币类型:价格，例如 rmb:50 usd:7）：")
            return EDITING_PRODUCT_PRICE
        
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
async def confirm_save_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """确认保存商品"""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    new_product = context.user_data["new_product"]
    
    product_id = f"product_{int(time.time())}"
    new_product["id"] = product_id
    
    products[product_id] = new_product
    save_products(products)
    
    await query.edit_message_text(f"商品《{new_product['name']}》已成功添加！")
    await manage_products(update, context)
    return ConversationHandler.END

# 展示商品列表
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """展示商品列表"""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    keyboard = []
    for product_id, product in products.items():
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
async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """选择付款方式"""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[1]
    products = load_products()
    product = products[product_id]
    context.user_data["selected_product"] = product
    
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
async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """获取用户邮箱"""
    import re
    email = update.message.text
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    if not re.match(email_pattern, email):
        await update.message.reply_text("请输入有效的邮箱地址（例如：example@domain.com）：")
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
async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """确认订单并生成付款信息"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    product = context.user_data["selected_product"]
    email = context.user_data["email"]
    payment_method = context.user_data["selected_payment"]
    price = product["prices"][payment_method]
    
    order_id = f"order_{int(time.time())}_{user.id}"
    
    order = {
        "id": order_id,
        "user_id": user.id,
        "user_name": user.full_name or user.username,
        "product": product,
        "email": email,
        "payment_method": payment_method,
        "amount": price,
        "status": "pending",
        "created_at": time.time(),
        "updated_at": time.time()
    }
    
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
    
    # 收款信息（请替换为实际信息）
    payment_info = {
        "rmb": "支付宝：123456789（张三）\n微信：wechat123（张三）",
        "usd": "PayPal：example@paypal.com",
        "crypto": "BTC地址：1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    }
    
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

# 标记订单为已付款
async def mark_as_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """标记订单为已付款"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.split("_")[1]
    update_order(order_id, "paid")
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"用户已标记订单 #{order_id} 为已付款，请核实并处理。"
