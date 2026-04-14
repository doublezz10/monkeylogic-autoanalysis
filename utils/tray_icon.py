"""
System tray icon utilities for MonkeyLogic watcher.

Creates a simple but recognizable monkey face icon programmatically.
"""

from PIL import Image, ImageDraw


def create_monkey_icon(size: int = 64) -> Image.Image:
    """
    Create a simple monkey face icon.
    
    Draws a circular monkey face with ears and a simple expression.
    
    Args:
        size: Icon size in pixels (default 64)
    
    Returns:
        PIL Image of monkey face
    """
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    face_radius = int(size * 0.35)
    
    # Colors
    face_color = (139, 90, 43, 255)      # Brown monkey face
    ear_color = (165, 105, 55, 255)      # Slightly darker ears
    inner_ear = (210, 180, 140, 255)    # Tan inner ear
    face_highlight = (180, 130, 80, 255) # Lighter face center
    
    # Draw ears (circles on sides)
    ear_radius = int(size * 0.15)
    ear_offset = int(size * 0.28)
    
    # Left ear
    draw.ellipse([
        center - ear_offset - ear_radius,
        center - ear_radius,
        center - ear_offset + ear_radius,
        center + ear_radius
    ], fill=ear_color)
    draw.ellipse([
        center - ear_offset - ear_radius + 3,
        center - ear_radius + 3,
        center - ear_offset + ear_radius - 3,
        center + ear_radius - 3
    ], fill=inner_ear)
    
    # Right ear
    draw.ellipse([
        center + ear_offset - ear_radius,
        center - ear_radius,
        center + ear_offset + ear_radius,
        center + ear_radius
    ], fill=ear_color)
    draw.ellipse([
        center + ear_offset - ear_radius + 3,
        center - ear_radius + 3,
        center + ear_offset + ear_radius - 3,
        center + ear_radius - 3
    ], fill=inner_ear)
    
    # Draw main face (circle)
    draw.ellipse([
        center - face_radius,
        center - face_radius,
        center + face_radius,
        center + face_radius
    ], fill=face_color)
    
    # Face highlight (lighter center)
    highlight_radius = int(face_radius * 0.7)
    draw.ellipse([
        center - highlight_radius,
        center - highlight_radius,
        center + highlight_radius,
        center + highlight_radius
    ], fill=face_highlight)
    
    # Draw eyes (simple dots)
    eye_radius = int(size * 0.06)
    eye_y = center - int(size * 0.05)
    eye_offset = int(size * 0.15)
    
    draw.ellipse([
        center - eye_offset - eye_radius,
        eye_y - eye_radius,
        center - eye_offset + eye_radius,
        eye_y + eye_radius
    ], fill=(50, 30, 10, 255))
    
    draw.ellipse([
        center + eye_offset - eye_radius,
        eye_y - eye_radius,
        center + eye_offset + eye_radius,
        eye_y + eye_radius
    ], fill=(50, 30, 10, 255))
    
    # Draw nose (oval)
    nose_width = int(size * 0.12)
    nose_height = int(size * 0.08)
    nose_y = center + int(size * 0.08)
    
    draw.ellipse([
        center - nose_width,
        nose_y - nose_height,
        center + nose_width,
        nose_y + nose_height
    ], fill=(80, 50, 25, 255))
    
    # Draw nostrils
    nostril_radius = int(size * 0.025)
    nostril_offset = int(size * 0.04)
    nostril_y = nose_y
    
    draw.ellipse([
        center - nostril_offset - nostril_radius,
        nostril_y - nostril_radius,
        center - nostril_offset + nostril_radius,
        nostril_y + nostril_radius
    ], fill=(40, 20, 5, 255))
    
    draw.ellipse([
        center + nostril_offset - nostril_radius,
        nostril_y - nostril_radius,
        center + nostril_offset + nostril_radius,
        nostril_y + nostril_radius
    ], fill=(40, 20, 5, 255))
    
    # Draw mouth (simple smile arc)
    mouth_width = int(size * 0.15)
    mouth_height = int(size * 0.08)
    mouth_y = center + int(size * 0.2)
    
    draw.arc([
        center - mouth_width,
        mouth_y - mouth_height,
        center + mouth_width,
        mouth_y + mouth_height
    ], start=0, end=180, fill=(80, 50, 25, 255), width=2)
    
    return img


def create_working_icon(size: int = 64) -> Image.Image:
    """
    Create an alternate "working" monkey icon (with dots indicating activity).
    
    Shows small dots next to the monkey to indicate polling/working.
    """
    # Start with base monkey
    img = create_monkey_icon(size)
    draw = ImageDraw.Draw(img)
    
    # Add small activity dots in corner
    dot_radius = int(size * 0.04)
    dot_x = size - int(size * 0.15)
    dot_y = int(size * 0.15)
    
    # Three dots to indicate "working"
    for i in range(3):
        color = (100, 200, 100, 255) if i < 2 else (200, 200, 100, 255)
        draw.ellipse([
            dot_x - dot_radius + (i * int(size * 0.08)),
            dot_y - dot_radius,
            dot_x + dot_radius + (i * int(size * 0.08)),
            dot_y + dot_radius
        ], fill=color)
    
    return img


if __name__ == "__main__":
    # Test - create and save icons
    icon = create_monkey_icon(64)
    icon.save("monkey_icon.png")
    
    working = create_working_icon(64)
    working.save("monkey_icon_working.png")
    
    print("Icons created: monkey_icon.png, monkey_icon_working.png")
