def _make_image(size: int = 64):
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle([4, 4, size - 4, size - 4], radius=14, fill=(37, 99, 235, 255))
    draw.rectangle([16, 22, size - 16, size - 22], outline=(255, 255, 255, 255), width=3)
    draw.line([16, 22, size // 2, size // 2 - 2, size - 16, 22], fill=(255, 255, 255, 255), width=3)
    return image


def build_tray(app):
    """Tạo pystray.Icon cho app. Import nội bộ để không cần GUI khi import module."""
    import pystray

    menu = pystray.Menu(
        pystray.MenuItem("Mở Settings", lambda: app.open_settings(), default=True),
        pystray.MenuItem(
            "Khởi động cùng máy",
            lambda: app.toggle_autostart(),
            checked=lambda item: app.autostart_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Thoát", lambda: app.quit()),
    )
    return pystray.Icon("ChatbotGmail", _make_image(), "Chatbot Gmail", menu)
