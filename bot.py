import os
import json
import time
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# 日志配置，方便排查问题
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 从环境变量获取配置，也可直接修改默认值（生产环境建议用环境变量）
TOKEN = os.getenv("TG_BOT_TOKEN")  # 必设，Telegram Bot 的令牌
ADMIN_ID = int(os.getenv("ADMIN_ID", 778899))  # 管理员ID，默认778899，可通过环境变量覆盖

# 校验必要配置
if not TOKEN:
    raise ValueError("请设置 TG_BOT_TOKEN 环境变量（Telegram Bot 令牌）")

# 状态常量（对话流程用）
SELECTING_PRODUCT, SELECTING_PAYMENT, ENTERING_EMAIL, CONFIRMING_ORDER, PAYMENT_WAITING = range(5)
ADDING_PRODUCT, EDITING_PRODUCT_TITLE, EDITING_PRODUCT_DESC, EDITING_PRODUCT_PRICE, EDITING_PRODUCT_PAYMENT = range(5, 10)

# 数据文件路径（会自动创建）
ORDERS_FILE = "orders.json"
PRODUCTS_FILE = "products.json"

# 支持的付款方式（可扩展）
PAYMENT_METHODS = {
    "rmb": "人民币",
    "usd": "美元",
    "crypto": "虚拟货币"
}

# ======================== 工具函数 ========================
def is_admin(user_id: int) -> bool:
    """校验是否为管理员"""
    return user_id == ADMIN_ID

def load_products() -> dict:
    """加载商品数据，无数据则返回默认商品"""
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "product_default": {
                "name": "基础素材包",
                "description": "包含50+设计素材，适合入门项目",
                "prices": {
                    "rmb": 29.9,
                    "usd": 4.99,
                    "crypto": 0.005
                },
                "payment_methods": ["rmb", "usd", "crypto"],
                "id": "product_default"
            }
        }

def save_products(products: dict) -> None:
    """保存商品数据到文件"""
    try:
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"保存商品失败: {str(e)}")

def load_orders() -> list:
    """加载订单数据，无数据则返回空列表"""
    try:
        with open(ORDERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_order(order: dict) -> None:
    """保存新订单"""
    try:
        orders = load_orders()
        orders.append(order)
        with open(ORDERS_FILE, "w") as f:
            json.dump(orders, f, indent=2)
    except Exception as e:
        logger.error(f"保存订单失败: {str(e)}")

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

# ======================== 对话处理 ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start 命令，机器人首页"""
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("浏览商品", callback_data="show_products")],
        [InlineKeyboardButton("查询订单", callback_data="check_orders")]
    ]
    if is_admin(user.id):
        keyboard.extend([
            [InlineKeyboardButton("管理订单", callback_data="manage_orders")],
            [InlineKeyboardButton("管理商品", callback_data="manage_products")]
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(
        rf"您好，{user.mention_html()}！欢迎使用虚拟商品商店机器人～",
        reply_markup=reply_markup
    )

# ---------- 商品管理 ----------
async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """管理员商品管理入口"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        await query.answer("您没有管理员权限", show_alert=True)
        return
    
    await query.answer()
    products = load_products()
    
    keyboard = [[InlineKeyboardButton("添加新商品", callback_data="add_product")]]
    for product_id, product in products.items():
        keyboard.append([InlineKeyboardButton(
            f"编辑: {product['name']}",
            callback_data=f"edit_product_{product_id}"
        )])
    keyboard.append([InlineKeyboardButton("返回首页", callback_data="back_to_start")])
    
    await query.edit_message_text(
        text="商品管理界面",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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

async def handle_product_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收商品标题"""
    product = context.user_data["new_product"]
    product["name"] = update.message.text
    await update.message.reply_text("请输入商品描述（介绍内容）：")
    return EDITING_PRODUCT_DESC

async def handle_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """接收商品描述"""
    product = context.user_data["new_product"]
    product["description"] = update.message.text
    await update.message.reply_text(
        "请输入价格（格式：货币类型:价格 ，多组用空格分隔，如 `rmb:39.9 usd:5.99`）\n"
        f"支持的货币：{', '.join(PAYMENT_METHODS.keys())}"
    )
    return EDITING_PRODUCT_PRICE

async def handle_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """解析商品价格"""
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
            await update.message.reply_text("未识别到有效价格，请重新输入！")
            return EDITING_PRODUCT_PRICE
        
        price_text = "\n".join([f"{PAYMENT_METHODS[c]}: {v}" for c, v in product["prices"].items()])
        keyboard = [
            [InlineKeyboardButton("确认保存", callback_data="confirm_save_product")],
            [InlineKeyboardButton("重新输入", callback_data="retry_product_price")]
        ]
        await update.message.reply_text(
            text=f"商品预览：\n"
                 f"标题：{product['name']}\n"
                 f"描述：{product['description']}\n"
                 f"价格：\n{price_text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return EDITING_PRODUCT_PAYMENT
    
    except Exception as e:
        await update.message.reply_text(f"格式错误！示例：`rmb:39.9 usd:5.99`\n错误：{str(e)}")
        return EDITING_PRODUCT_PRICE

async def confirm_save_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """确认保存新商品"""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    new_product = context.user_data["new_product"]
    
    product_id = f"product_{int(time.time())}"
    new_product["id"] = product_id
    products[product_id] = new_product
    save_products(products)
    
    await query.edit_message_text(f"商品「{new_product['name']}」添加成功！")
    await manage_products(update, context)
    return ConversationHandler.END

# ---------- 商品展示与购买 ----------
async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """展示可购买商品列表"""
    query = update.callback_query
    await query.answer()
    
    products = load_products()
    keyboard = []
    for product_id, product in products.items():
        payment_text = "/".join([PAYMENT_METHODS[m] for m in product["payment_methods"]])
        keyboard.append([InlineKeyboardButton(
            f"{product['name']}（{payment_text}）",
            callback_data=f"select_{product_id}"
        )])
    keyboard.append([InlineKeyboardButton("返回首页", callback_data="back_to_start")])
    
    await query.edit_message_text(
        text="选择要购买的商品：",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_PRODUCT

async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """选择商品的付款方式"""
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
    
    await query.edit_message_text(
        text=f"商品：{product['name']}\n描述：{product['description']}\n\n选择付款方式：",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return SELECTING_PAYMENT

async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """确认付款方式，进入邮箱填写"""
    query = update.callback_query
    await query.answer()
    
    payment_method = query.data.split("_")[1]
    context.user_data["selected_payment"] = payment_method
    await query.edit_message_text(text="请输入接收商品的邮箱：")
    return ENTERING_EMAIL

async def get_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """校验并保存用户邮箱"""
    import re
    email = update.message.text
    email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    
    if not re.match(email_pattern, email):
        await update.message.reply_text("邮箱格式错误！请重新输入（如：example@domain.com）")
        return ENTERING_EMAIL
    
    context.user_data["email"] = email
    product = context.user_data["selected_product"]
    payment_method = context.user_data["selected_payment"]
    price = product["prices"][payment_method]
    
    keyboard = [
        [InlineKeyboardButton("确认购买", callback_data="confirm_order")],
        [InlineKeyboardButton("取消", callback_data="cancel_order")]
    ]
    await update.message.reply_text(
        text=f"订单预览：\n"
             f"商品：{product['name']}\n"
             f"付款方式：{PAYMENT_METHODS[payment_method]}\n"
             f"价格：{price} {payment_method}\n"
             f"邮箱：{email}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMING_ORDER

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """创建订单，通知管理员并引导付款"""
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
    
    # 给管理员发通知
    admin_msg = f"新订单 #{order_id}\n" \
                f"用户：{user.full_name}（ID: {user.id}）\n" \
                f"商品：{product['name']}\n" \
                f"付款方式：{PAYMENT_METHODS[payment_method]}\n" \
                f"金额：{price}\n" \
                f"邮箱：{email}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    
    # 模拟收款信息（需替换为实际收款方式）
    payment_info = {
        "rmb": "支付宝：your_alipay@xxx.com（姓名：XXX）",
        "usd": "PayPal：your_paypal@xxx.com",
        "crypto": "BTC地址：1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa"
    }
    
    keyboard = [
        [InlineKeyboardButton("已付款", callback_data=f"paid_{order_id}")],
        [InlineKeyboardButton("取消订单", callback_data=f"cancel_{order_id}")]
    ]
    await query.edit_message_text(
        text=f"订单创建成功！订单号：{order_id}\n\n"
             f"请按以下方式付款 {price} {PAYMENT_METHODS[payment_method]}：\n"
             f"{payment_info[payment_method]}\n\n"
             f"付款后点「已付款」通知我们~",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data["current_order_id"] = order_id
    return PAYMENT_WAITING

# ---------- 订单状态处理 ----------
async def mark_as_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """用户标记订单为已付款"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.split("_")[1]
    update_order(order_id, "paid")
    
    # 通知管理员
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"用户标记订单 #{order_id} 为已付款，请核实~"
    )
    
    await query.edit_message_text(
        text=f"已收到付款通知！我们会尽快核实，商品将发送到邮箱：{context.user_data.get('email', '未知')}\n"
             f"可通过 /check_orders 查询进度~"
    )
    return ConversationHandler.END

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """取消订单"""
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.split("_")[-1] if "_" in query.data else ""
    if order_id:
        update_order(order_id, "cancelled")
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"订单 #{order_id} 被用户取消~"
        )
        await query.edit_message_text(f"订单 #{order_id}
