import telebot
from telebot import types
import json
import os
import requests
from datetime import datetime
import threading
import time
import random

# 你的 Telegram 机器人 Token
TOKEN = '7757726285:AAFa3ZYCnKAnUisc_baJ_EtcH61EeL1naYc'
bot = telebot.TeleBot(TOKEN)

# 用户数据文件
USERS_FILE = 'users.json'

# 商品数据文件
PRODUCTS_FILE = 'products.json'

# 销售记录文件
SALES_FILE = 'sales.json'

# 管理员ID
admin_id = 7171193338

# 钱包地址（十六进制格式）
WALLET_ADDRESS = "TLR7wR8Up114W4GuVFPm4nisc83CCCCCCC"

# 假设的 API 端点和密钥
API_ENDPOINT = "https://api.trongrid.io/v1/accounts/{address}/transactions"
API_KEY = "6e66755b-4693-44de-89d4-feed535cfd81"

# 加载用户数据
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("用户数据文件格式错误，初始化为空字典。")
                return {}
    else:
        print("用户数据文件不存在，初始化为空字典。")
        return {}

# 保存用户数据
def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# 加载商品数据
def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("商品数据文件格式错误，初始化为空字典。")
                return {}
    else:
        print("商品数据文件不存在，初始化为空字典。")
        return {}

# 保存商品数据
def save_products(products):
    with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

# 加载销售记录
def load_sales():
    if os.path.exists(SALES_FILE):
        with open(SALES_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# 保存销售记录
def save_sales(sales):
    with open(SALES_FILE, 'w', encoding='utf-8') as f:
        json.dump(sales, f, ensure_ascii=False, indent=4)

# 记录销售
def record_sale(user_id, region, product_name, quantity, total_price):
    sales = load_sales()
    sale_record = {
        "user_id": user_id,
        "region": region,
        "product": product_name,
        "quantity": quantity,
        "price": total_price,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    sales.append(sale_record)
    save_sales(sales)

# 初始化用户和商品列表
users = load_users()
products = load_products()

# 为每个用户分配一个唯一的小数标识符
def assign_decimal_identifier(user_id):
    if user_id not in users:
        users[user_id] = {'balance': 0.0, 'total_recharged': 0.0}  # 添加 total_recharged 字段
    save_users(users)

# 处理 /start 命令
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    assign_decimal_identifier(user_id)  # 确保分配 decimal_id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('查询余额', '充值', '提现', '购买商品', '查询库存')
    bot.send_message(message.chat.id, "欢迎使用钱包机器人！请选择一个操作：", reply_markup=markup)

# 查询余额
@bot.message_handler(func=lambda message: message.text == '查询余额')
def check_balance(message):
    user_id = str(message.from_user.id)
    assign_decimal_identifier(user_id)  # 确保分配 decimal_id
    balance = users[user_id]['balance']
    bot.send_message(message.chat.id, f"当前余额：{balance:.2f} TRX")

# 充值
@bot.message_handler(func=lambda message: message.text == '充值')
def request_recharge_amount(message):
    msg = bot.send_message(message.chat.id, "请输入您想充值的金额（不含小数部分）：")
    bot.register_next_step_handler(msg, process_recharge_amount)

def process_recharge_amount(message):
    try:
        user_id = str(message.from_user.id)
        assign_decimal_identifier(user_id)  # 确保分配 decimal_id
        amount = float(message.text)
        decimal_part = random.uniform(0.001, 0.1)  # 生成随机小数部分
        full_amount = amount + decimal_part  # 生成带小数标识符的金额
        users[user_id]['expected_decimal'] = round(decimal_part, 2)  # 存储预期的小数部分
        order_id = str(random.randint(100000, 999999))  # 生成随机订单ID
        users[user_id]['order_id'] = order_id  # 存储订单ID
        save_users(users)

        bot.send_message(
            message.chat.id,
            f"请将 {full_amount:.2f} TRX 充值到以下地址：\n`{WALLET_ADDRESS}`\n"
            f"（点击地址即可复制）\n"
            f"您的订单ID是：{order_id}。\n"
            "请在5分钟内完成支付。",
            parse_mode='Markdown'
        )

        # 启动定时器，5分钟后关闭订单
        threading.Timer(300, close_order, args=(user_id, order_id)).start()  # 300秒后调用close_order
    except ValueError:
        bot.send_message(message.chat.id, "请输入有效的金额。")

def close_order(user_id, order_id):
    if 'order_id' in users[user_id] and users[user_id]['order_id'] == order_id:
        del users[user_id]['order_id']  # 删除订单ID
        save_users(users)
        bot.send_message(user_id, f"订单 {order_id} 已关闭，因未在5分钟内完成支付。")

# 提现
@bot.message_handler(func=lambda message: message.text == '提现')
def withdraw(message):
    bot.send_message(message.chat.id, "请输入提现金额，例如：/withdraw 10")

# 购买商品
@bot.message_handler(func=lambda message: message.text == '购买商品')
def select_region(message):
    global products
    products = load_products()
    
    markup = types.InlineKeyboardMarkup()
    for region in products:
        markup.add(types.InlineKeyboardButton(region, callback_data=f"select_{region}"))
    bot.send_message(message.chat.id, "请选择地区：", reply_markup=markup)

# 处理地区选择
@bot.callback_query_handler(func=lambda call: call.data.startswith('select_'))
def show_products(call):
    region = call.data.split('_')[1]
    product_list = products.get(region, {})
    markup = types.InlineKeyboardMarkup()
    for name, details in product_list.items():
        price = details['price']
        stock = details['stock']
        markup.add(types.InlineKeyboardButton(f"{name} - {price:.2f} TRX (库存: {stock})", callback_data=f"buy_{region}_{name}"))
    bot.send_message(call.message.chat.id, f"商品列表：{region}", reply_markup=markup)

# 处理购买确认
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def confirm_purchase(call):
    _, region, product_name = call.data.split('_')
    product_details = products[region].get(product_name)
    if product_details is not None:
        price = product_details['price']
        stock = product_details['stock']
        if stock > 0:
            msg = bot.send_message(call.message.chat.id, f"您选择了：{region} - {product_name} - {price:.2f} TRX\n请输入购买数量：")
            bot.register_next_step_handler(msg, process_quantity, region, product_name, price)
        else:
            bot.send_message(call.message.chat.id, f"抱歉，{product_name} 库存不足。")

def process_quantity(message, region, product_name, price):
    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError("数量必须大于0")
        
        product_details = products[region][product_name]
        total_price = price * quantity
        
        if product_details['stock'] >= quantity:
            user_id = str(message.from_user.id)
            assign_decimal_identifier(user_id)  # 确保分配 decimal_id
                
            if users[user_id]['balance'] >= total_price:
                # 先检查所有文件是否存在
                files_to_send = []
                for i in range(quantity):
                    if i >= len(product_details['files']):
                        bot.send_message(message.chat.id, "抱歉，文件库存不足。")
                        return
                    file_path = product_details['files'][i]
                    if not os.path.isfile(file_path):
                        bot.send_message(message.chat.id, "抱歉，部分文件丢失，请联系管理员。")
                        return
                    files_to_send.append(file_path)

                # 扣款和更新库存
                users[user_id]['balance'] -= total_price
                product_details['stock'] -= quantity
                
                # 记录销售
                record_sale(user_id, region, product_name, quantity, total_price)
                
                # 发送文件并删除
                success_count = 0
                for file_path in files_to_send:
                    try:
                        with open(file_path, 'rb') as file:
                            bot.send_document(message.chat.id, file)
                        os.remove(file_path)  # 删除文件
                        product_details['files'].remove(file_path)  # 从列表中移除
                        success_count += 1
                    except Exception as e:
                        print(f"Error processing file {file_path}: {str(e)}")
                
                # 保存更新
                save_products(products)
                save_users(users)
                
                bot.send_message(
                    message.chat.id, 
                    f"购买成功！您已购买 {quantity} 个 {region} - {product_name}，"
                    f"花费 {total_price:.2f} TRX。\n"
                    f"成功发送 {success_count} 个文件。"
                )
            else:
                bot.send_message(message.chat.id, "余额不足，无法完成购买。请先充值。")
        else:
            bot.send_message(message.chat.id, f"抱歉，{product_name} 库存不足。")
    except ValueError:
        bot.send_message(message.chat.id, "请输入有效的购买数量。")
    except Exception as e:
        bot.send_message(message.chat.id, f"处理订单时出错：{str(e)}")
        print(f"Error in process_quantity: {str(e)}")

# 查询库存
@bot.message_handler(func=lambda message: message.text == '查询库存')
def check_inventory(message):
    inventory_message = "当前库存：\n"
    for region, items in products.items():
        inventory_message += f"\n{region}:\n"
        for name, details in items.items():
            price = details['price']
            stock = details['stock']
            inventory_message += f"  - {name}: {price:.2f} TRX (库存: {stock})\n"
    bot.send_message(message.chat.id, inventory_message)

# 销售统计功能
@bot.message_handler(commands=['sales_stats'])
def show_sales_stats(message):
    if message.from_user.id != admin_id:
        bot.send_message(message.chat.id, "您没有权限执行此操作。")
        return
    
    try:
        sales = load_sales()
        if not sales:
            bot.send_message(message.chat.id, "暂无销售记录。")
            return

        # 按地区和商品统计
        stats = {}
        total_revenue = 0.0
        
        for sale in sales:
            region = sale['region']
            product = sale['product']
            if region not in stats:
                stats[region] = {}
            if product not in stats[region]:
                stats[region][product] = {
                    'quantity': 0,
                    'revenue': 0.0
                }
            
            stats[region][product]['quantity'] += sale['quantity']
            stats[region][product]['revenue'] += sale['price']
            total_revenue += sale['price']

        # 生成报告
        report = "📊 销售统计报告\n\n"
        
        for region in stats:
            report += f"🌍 {region}:\n"
            region_total = 0.0
            for product, data in stats[region].items():
                report += (
                    f"  - {product}:\n"
                    f"    销量: {data['quantity']} 个\n"
                    f"    收入: {data['revenue']:.2f} TRX\n"
                )
                region_total += data['revenue']
            report += f"  📍 地区总收入: {region_total:.2f} TRX\n\n"
        
        report += f"💰 总收入: {total_revenue:.2f} TRX\n"
        report += f"📈 总订单数: {len(sales)} 笔"
        
        bot.send_message(message.chat.id, report)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"生成销售统计时出错：{str(e)}")
        print(f"Error in sales stats: {str(e)}")

# 添加商品流程
@bot.message_handler(commands=['add_product'])
def add_product_start(message):
    if message.from_user.id != admin_id:
        bot.send_message(message.chat.id, "您没有权限执行此操作。")
        return
    msg = bot.send_message(message.chat.id, "请输入地区：")
    bot.register_next_step_handler(msg, process_region)

def process_region(message):
    region = message.text
    msg = bot.send_message(message.chat.id, "请输入商品名称：")
    bot.register_next_step_handler(msg, process_product_name, region)

def process_product_name(message, region):
    product_name = message.text
    msg = bot.send_message(message.chat.id, "请输入商品价格：")
    bot.register_next_step_handler(msg, process_product_price, region, product_name)

def process_product_price(message, region, product_name):
    try:
        price = float(message.text)
        msg = bot.send_message(message.chat.id, "请输入库存数量：")
        bot.register_next_step_handler(msg, process_product_stock, region, product_name, price)
    except ValueError:
        bot.send_message(message.chat.id, "请输入有效的价格。")

def process_product_stock(message, region, product_name, price):
    try:
        stock = int(message.text)
        bot.send_message(message.chat.id, "请上传商品的ZIP文件（可以逐个上传），完成后发送 /done：")
        current_upload[message.chat.id] = {"region": region, "product_name": product_name, "price": price, "stock": stock, "files": []}
    except ValueError:
        bot.send_message(message.chat.id, "请输入有效的库存数量。")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.chat.id in current_upload:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        region = current_upload[message.chat.id]['region']
        region_path = os.path.join(BASE_SAVE_PATH, region)
        if not os.path.exists(region_path):
            os.makedirs(region_path)
        
        file_path = os.path.join(region_path, message.document.file_name)
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        current_upload[message.chat.id]['files'].append(file_path)
        bot.send_message(message.chat.id, f"文件 {message.document.file_name} 已添加。")
    else:
        bot.send_message(message.chat.id, "请先使用 /add_product 命令开始添加商品。")

@bot.message_handler(commands=['done'])
def finish_upload(message):
    if message.chat.id in current_upload:
        upload_info = current_upload.pop(message.chat.id)
        region = upload_info['region']
        product_name = upload_info['product_name']
        price = upload_info['price']
        stock = upload_info['stock']
        files = upload_info['files']
        
        if region not in products:
            products[region] = {}
        products[region][product_name] = {"price": price, "stock": stock, "files": files}
        
        save_products(products)
        
        bot.send_message(message.chat.id, f"商品 {product_name} 已成功添加，包含 {len(files)} 个文件。")
    else:
        bot.send_message(message.chat.id, "没有正在进行的上传。")

# 自动检测充值交易
def check_transactions():
    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(API_ENDPOINT.format(address=WALLET_ADDRESS), headers=headers)
    
    if response.status_code == 200:
        transactions = response.json().get('data', [])
        for tx in transactions:
            process_transaction(tx)

def process_transaction(tx):
    try:
        contract = tx.get('raw_data', {}).get('contract', [])
        if not contract:
            print("交易数据中缺少 'contract' 段")
            return
        
        parameter = contract[0].get('parameter', {})
        value = parameter.get('value', {})
        owner_address = value.get('owner_address', None)
        to_address = value.get('to_address', None)
        amount = value.get('amount', 0) / 1_000_000  # 转换为 TRX 单位
        
        if owner_address is None or to_address is None:
            print(f"交易数据中缺少 'owner_address' 或 'to_address' 段: {tx}")  # 打印完整的交易数据
            return
        
        # 验证交易
        if to_address == WALLET_ADDRESS:  # 确保是转到指定地址
            decimal_part = round(amount % 1, 2)  # 获取小数部分
            user_id = get_user_id_by_decimal(decimal_part)
            if user_id:
                users[user_id]['balance'] += amount  # 增加用户余额
                users[user_id]['total_recharged'] += amount  # 更新总充值金额
                del users[user_id]['expected_decimal']  # 清除预期的小数部分
                save_users(users)
                bot.send_message(user_id, f"您的账户已充值 {amount:.2f} TRX。")
            else:
                print(f"未找到用户ID，decimal_part: {decimal_part}")  # 调试信息
    except Exception as e:
        print(f"处理交易时出错：{str(e)}")

def get_user_id_by_decimal(decimal_part):
    for user_id, data in users.items():
        if data.get('expected_decimal') == decimal_part:
            return user_id
    return None

# 用户充值统计功能
@bot.message_handler(commands=['recharge_stats'])
def show_recharge_stats(message):
    if message.from_user.id != admin_id:
        bot.send_message(message.chat.id, "您没有权限执行此操作。")
        return
    
    stats_message = "用户充值统计：\n"
    for user_id, data in users.items():
        total_recharged = data.get('total_recharged', 0.0)
        stats_message += f"用户ID: {user_id} - 总充值: {total_recharged:.2f} TRX\n"
    
    bot.send_message(message.chat.id, stats_message)

# 定期检查交易
def start_transaction_check():
    while True:
        check_transactions()
        time.sleep(60)  # 每分钟检查一次

transaction_thread = threading.Thread(target=start_transaction_check)
transaction_thread.start()

# 启动机器人
bot.polling()