#!/usr/bin/env python3

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from PIL import Image
import sys
import os

def create_pdf_with_images(image_path, output_path="output.pdf"):
    """
    Creates an 8.5x11 inch PDF with 9 copies of the input image arranged in a 3x3 grid.
    The center image is positioned at the exact center of the page.
    
    Args:
        image_path (str): Path to the PNG image file
        output_path (str): Path for the output PDF file
    """
    
    # Check if image file exists
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' not found.")
        return False
    
    # Verify it's a PNG file
    try:
        with Image.open(image_path) as img:
            if img.format != 'PNG':
                print(f"Warning: File is {img.format}, not PNG. Proceeding anyway...")
    except Exception as e:
        print(f"Error opening image: {e}")
        return False
    
    # Create PDF canvas
    c = canvas.Canvas(output_path, pagesize=letter)
    page_width, page_height = letter  # 8.5x11 inches in points
    
    # Image dimensions in points (1 inch = 72 points)
    img_width = 2.5 * inch
    img_height = 3.5 * inch
    
    # Calculate center position
    center_x = (page_width - img_width) / 2
    center_y = (page_height - img_height) / 2
    
    # Define positions for all 9 images
    # Grid layout: 3 columns, 3 rows
    positions = [
        # Top row
        (0.5 * inch, page_height - 3.75 * inch),        # top-left
        (center_x, page_height - 3.75 * inch),          # top-center  
        (page_width - 3 * inch, page_height - 3.75 * inch),  # top-right
        
        # Middle row
        (0.5 * inch, center_y),                         # middle-left
        (center_x, center_y),                           # CENTER (exact center)
        (page_width - 3 * inch, center_y),             # middle-right
        
        # Bottom row
        (0.5 * inch, 0.25 * inch),                      # bottom-left
        (center_x, 0.25 * inch),                        # bottom-center
        (page_width - 3 * inch, 0.25 * inch),          # bottom-right
    ]
    
    # Draw all 9 images
    for i, (x, y) in enumerate(positions):
        try:
            c.drawImage(image_path, x, y, width=img_width, height=img_height)
            print(f"Placed image {i+1}/9 at position ({x/inch:.2f}\", {y/inch:.2f}\")")
        except Exception as e:
            print(f"Error placing image {i+1}: {e}")
            return False
    
    # Save the PDF
    c.save()
    print(f"\nPDF created successfully: {output_path}")
    print(f"Page size: 8.5\" x 11\"")
    print(f"Image size: 2.5\" x 3.5\" (9 copies)")
    print(f"Center image positioned at exact center of page")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_generator.py <image_path> [output_path]")
        print("Example: python pdf_generator.py my_image.png my_grid.pdf")
        sys.exit(1)
    
    image_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.pdf"
    
    print(f"Input image: {image_path}")
    print(f"Output PDF: {output_path}")
    print("Creating PDF with 3x3 grid layout...\n")
    
    success = create_pdf_with_images(image_path, output_path)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
