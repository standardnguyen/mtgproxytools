from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from PIL import Image
import os
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO

# Set up page size (landscape 8.5x11 inches)
page_width, page_height = landscape(letter)

# Input template PDF and output filename
template_pdf = "template_cut_lines.pdf"
output_dir = "./output"
output_filename = os.path.join(output_dir, "cards_with_fronts.pdf")

# Create output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Check if template PDF exists
if not os.path.exists(template_pdf):
    print(f"Template PDF not found: {template_pdf}")
    print("Please run the original script first to generate the template.")
    exit(1)

# Define points with their coordinates (same as original)
points = [
    ("A", 102.614358, 456.2361258),
    ("B", 298.204786, 456.2361258),
    ("C", 493.795214, 456.2361258),
    ("D", 689.385642, 456.2361258),
    ("E", 102.614358, 155.7638742),
    ("F", 298.204786, 155.7638742),
    ("G", 493.795214, 155.7638742),
    ("H", 689.385642, 155.7638742)
]

# Directory containing front images
fronts_dir = "./assets/fronts"

# Get all image files from the fronts directory
image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
front_images = []

if os.path.exists(fronts_dir):
    for filename in os.listdir(fronts_dir):
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            front_images.append(os.path.join(fronts_dir, filename))
    
    # Sort the images for consistent ordering
    front_images.sort()
    print(f"Found {len(front_images)} images in {fronts_dir}")
    for img in front_images:
        print(f"  - {os.path.basename(img)}")
else:
    print(f"Directory not found: {fronts_dir}")
    exit(1)

# Check if we have exactly 8 images
if len(front_images) != 8:
    print(f"Warning: Found {len(front_images)} images, but expected 8.")
    if len(front_images) == 0:
        print("No images found. Exiting.")
        exit(1)
    elif len(front_images) < 8:
        print(f"Will use the available {len(front_images)} images.")
    else:
        print("Will use the first 8 images.")
        front_images = front_images[:8]

# Create a new canvas in memory to draw the card fronts
packet = BytesIO()
overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))

# Target width in mm and convert to points (1 mm = 72/25.4 points)
target_width_mm = 69.35
target_width_points = target_width_mm * 72 / 25.4

# Process each image and place it at corresponding point
for i, (label, x, y) in enumerate(points):
    if i < len(front_images):
        image_path = front_images[i]
        
        try:
            # Open and process the image
            img = Image.open(image_path)
            
            # Calculate the aspect ratio to maintain proportions
            aspect_ratio = img.height / img.width
            target_height_points = target_width_points * aspect_ratio
            
            print(f"Processing {os.path.basename(image_path)}:")
            print(f"  Original size: {img.width} x {img.height}")
            print(f"  Target size in points: {target_width_points:.2f} x {target_height_points:.2f}")
            print(f"  Target size in mm: {target_width_mm} x {target_width_mm * aspect_ratio:.2f}")
            
            # Calculate position to center the image on the point
            img_x = x - (target_width_points / 2)
            img_y = y - (target_height_points / 2)
            
            # Draw the image on the overlay canvas
            overlay_canvas.drawImage(image_path,
                                   img_x, img_y,
                                   width=target_width_points,
                                   height=target_height_points)
            
            print(f"  Placed at point {label}: center ({x}, {y}), image at ({img_x:.2f}, {img_y:.2f})")
            
        except Exception as e:
            print(f"Error processing {os.path.basename(image_path)}: {e}")
            continue
    else:
        print(f"No image available for point {label}")

# Save the overlay canvas
overlay_canvas.save()
packet.seek(0)

# Read the template PDF
template_reader = PdfReader(template_pdf)
overlay_reader = PdfReader(packet)

# Create output PDF writer
output_writer = PdfWriter()

# Merge the template with the overlay
template_page = template_reader.pages[0]
if len(overlay_reader.pages) > 0:
    overlay_page = overlay_reader.pages[0]
    template_page.merge_page(overlay_page)

# Add the merged page to output
output_writer.add_page(template_page)

# Write the final PDF
with open(output_filename, 'wb') as output_file:
    output_writer.write(output_file)

print(f"\nPDF generated: {output_filename}")
print(f"Template '{template_pdf}' used as base with card fronts overlaid.")
print(f"Processed {min(len(front_images), 8)} images from {fronts_dir}")