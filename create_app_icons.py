from PIL import Image
import os

def create_app_icons():
    """Create app icons in different sizes for PWA"""
    
    # Path to the source icon
    source_icon = 'static/images/icon.png'
    
    # Icon sizes needed for PWA
    icon_sizes = [
        (72, 'icon-72x72.png'),
        (96, 'icon-96x96.png'),
        (128, 'icon-128x128.png'),
        (144, 'icon-144x144.png'),
        (152, 'icon-152x152.png'),
        (192, 'icon-192x192.png'),
        (384, 'icon-384x384.png'),
        (512, 'icon-512x512.png'),
        (70, 'icon-70x70.png'),      # For Microsoft tiles
        (150, 'icon-150x150.png'),    # For Microsoft tiles
        (310, 'icon-310x310.png')     # For Microsoft tiles
    ]
    
    try:
        # Open the source image
        with Image.open(source_icon) as img:
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Create each icon size
            for size, filename in icon_sizes:
                # Resize image
                resized_img = img.resize((size, size), Image.Resampling.LANCZOS)
                
                # Save the new icon
                output_path = f'static/images/{filename}'
                resized_img.save(output_path, 'PNG')
                print(f"Created: {output_path} ({size}x{size})")
                
        print("\n✅ All app icons created successfully!")
        
    except FileNotFoundError:
        print(f"❌ Error: Source icon '{source_icon}' not found!")
    except Exception as e:
        print(f"❌ Error creating icons: {e}")

if __name__ == "__main__":
    create_app_icons()
