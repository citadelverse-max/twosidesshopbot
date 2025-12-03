import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

API_TOKEN = "8486226213:AAHPHbonxvL2_vXORpOFRzL9NdUqcc9MJtI"
ADMIN_ID = 6347698601   # сюда будет приходить заказ (замени!)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ==============================
#   БАЗА ТОВАРОВ
# ==============================

PRODUCTS = {
    1: {
        "name": "Футболка MERCH",
        "price": 450,
        "desc": "Стильная футболка с логотипом.",
        "photo": "https://i.ibb.co/SDp16b3K/194979235591-21.webp"
    },
    2: {
        "name": "Худи MERCH",
        "price": 900,
        "desc": "Тёплое и удобное худи.",
        "photo": "https://i.ibb.co/q38kY32s/image.jpg"
    },
    3: {
        "name": "Кепка MERCH",
        "price": 350,
        "desc": "Универсальная кепка.",
        "photo": "https://i.ibb.co/8L5nW1LX/1.jpg"
    }
}

# Корзины пользователей: user_id -> {product_id: qty}
CART = {}


# ==============================
#   КОМАНДА START
# ==============================
@dp.message(Command("start"))
async def start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Открыть магазин", callback_data="open_shop")]
    ])
    await message.answer("Привет! Добро пожаловать в магазин мерча.\nНажми кнопку ниже.", reply_markup=kb)


# ==============================
#   КАТАЛОГ / КАРТОЧКИ ТОВАРОВ
# ==============================
@dp.callback_query(lambda c: c.data == "open_shop")
@dp.message(Command("shop"))
async def show_shop(obj):
    if isinstance(obj, CallbackQuery):
        message = obj.message
    else:
        message = obj

    kb = InlineKeyboardBuilder()
    for pid, item in PRODUCTS.items():
        kb.button(text=f"{item['name']} — {item['price']} грн", callback_data=f"product_{pid}")
    kb.adjust(1)

    await message.answer("🛍 Каталог товаров:", reply_markup=kb.as_markup())


# ==============================
#   ОТКРЫТЬ КАРТОЧКУ ТОВАРА
# ==============================
@dp.callback_query(lambda c: c.data.startswith("product_"))
async def open_product(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])
    product = PRODUCTS[pid]

    # кнопки товара
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"minus_{pid}"),
            InlineKeyboardButton(text="1", callback_data="none"),
            InlineKeyboardButton(text="➕", callback_data=f"plus_{pid}")
        ],
        [InlineKeyboardButton(text="🛒 В корзину", callback_data=f"addcart_{pid}")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="open_shop")]
    ])

    await callback.message.answer_photo(
        product["photo"],
        caption=f"**{product['name']}**\nЦена: {product['price']} грн\n\n{product['desc']}",
        reply_markup=kb,
        parse_mode="Markdown"
    )


# ==============================
#   РЕГУЛИРОВКА КОЛИЧЕСТВА
# ==============================
@dp.callback_query(lambda c: c.data.startswith(("plus_", "minus_")))
async def change_qty(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])

    # создаём корзину, если нет
    CART.setdefault(callback.from_user.id, {})
    CART[callback.from_user.id].setdefault(pid, 1)

    # изменяем количество
    if callback.data.startswith("plus_"):
        CART[callback.from_user.id][pid] += 1
    elif callback.data.startswith("minus_") and CART[callback.from_user.id][pid] > 1:
        CART[callback.from_user.id][pid] -= 1

    await callback.answer(f"Количество: {CART[callback.from_user.id][pid]}", show_alert=False)


# ==============================
#   ДОБАВИТЬ В КОРЗИНУ
# ==============================
@dp.callback_query(lambda c: c.data.startswith("addcart_"))
async def add_to_cart(callback: CallbackQuery):
    pid = int(callback.data.split("_")[1])

    CART.setdefault(callback.from_user.id, {})
    CART[callback.from_user.id].setdefault(pid, 1)

    await callback.answer("Добавлено в корзину!")
    await callback.message.answer("✔ Товар добавлен в корзину.\nЧтобы оформить заказ — /cart")


# ==============================
#   ОТКРЫТЬ КОРЗИНУ
# ==============================
@dp.message(Command("cart"))
async def show_cart(message: types.Message):
    user_id = message.from_user.id

    if user_id not in CART or not CART[user_id]:
        await message.answer("🛒 Ваша корзина пуста.")
        return

    text = "🛒 *Ваша корзина:*\n\n"
    total = 0

    for pid, qty in CART[user_id].items():
        item = PRODUCTS[pid]
        line = f"{item['name']} × {qty} = {item['price'] * qty} грн\n"
        text += line
        total += item["price"] * qty

    text += f"\n**Общая сумма: {total} грн**"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Оформить заказ", callback_data="checkout")],
        [InlineKeyboardButton(text="🛍 Продолжить покупки", callback_data="open_shop")]
    ])

    await message.answer(text, parse_mode="Markdown", reply_markup=kb)


# ==============================
#   ОФОРМЛЕНИЕ ЗАКАЗА
# ==============================
@dp.callback_query(lambda c: c.data == "checkout")
async def checkout(callback: CallbackQuery):
    user_id = callback.from_user.id

    if user_id not in CART or not CART[user_id]:
        await callback.answer("Корзина пуста!")
        return

    # собираем заказ
    order_text = f"🆕 *Новый заказ от @{callback.from_user.username}:*\n\n"
    total = 0
    for pid, qty in CART[user_id].items():
        item = PRODUCTS[pid]
        order_text += f"{item['name']} × {qty} = {item['price'] * qty} грн\n"
        total += item["price"] * qty
    order_text += f"\n💰 *Итого: {total} грн*"

    # отправляем админу
    await bot.send_message(ADMIN_ID, order_text, parse_mode="Markdown")

    # очищаем корзину
    CART[user_id] = {}

    await callback.message.answer("🎉 Ваш заказ отправлен!\nМы скоро свяжемся с вами.")
    await callback.answer()


# ==============================
#   ЗАПУСК
# ==============================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
