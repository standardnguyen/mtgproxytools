import xml.etree.ElementTree as ET
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import lightgrey
from PIL import Image
import os
import shutil
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
import subprocess
import sys

# Configuration for offset
DEFAULT_OFFSET_CM = 0.11  # Default offset in centimeters
OFFSET_POINTS = DEFAULT_OFFSET_CM * 10 * 72 / 25.4  # Convert cm to points (0.11cm ≈ 3.118 points)

def check_and_install_ghostscript():
    """Check if Ghostscript is available for PDF compression"""
    try:
        subprocess.run(['gs', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: Ghostscript not found. PDF compression will be skipped.")
        print("Install Ghostscript for PDF compression functionality.")
        return False

def parse_xml_cards(xml_path):
    """Parse the XML file and return card information"""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    cards = []
    for card_elem in root.find('fronts').findall('card'):
        # Skip empty cards
        if card_elem.find('id') is None or card_elem.find('slots') is None:
            continue
            
        card_id = card_elem.find('id').text
        slots_text = card_elem.find('slots').text
        name = card_elem.find('name').text
        query = card_elem.find('query').text if card_elem.find('query') is not None else ""
        
        # Parse slots
        slots = [int(slot.strip()) for slot in slots_text.split(',')]
        
        cards.append({
            'id': card_id,
            'slots': slots,
            'name': name,
            'query': query
        })
    
    return cards

def create_slot_list(cards):
    """Create a list where each index represents a slot and contains the card ID"""
    slot_list = []
    
    for card in cards:
        for slot in card['slots']:
            # Ensure we have enough slots in our list
            while len(slot_list) <= slot:
                slot_list.append(None)
            slot_list[slot] = card['id']
    
    return slot_list

def find_image_by_id(card_id, fronts_dir):
    """Find an image file that contains the given card ID in its filename"""
    if not card_id:
        return None
    
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
    
    for filename in os.listdir(fronts_dir):
        if any(filename.lower().endswith(ext) for ext in image_extensions):
            if card_id in filename:
                return filename
    
    return None

def check_images_exist(slot_list, fronts_dir):
    """Check if all required images exist by looking for card IDs in filenames"""
    missing_images = []
    existing_images = []
    
    for i, card_id in enumerate(slot_list):
        if card_id:
            image_filename = find_image_by_id(card_id, fronts_dir)
            if image_filename:
                existing_images.append(image_filename)
            else:
                missing_images.append((i, card_id))
    
    return missing_images, existing_images

def draw_edge_cut_lines(overlay_canvas, page_width, page_height, x_offset=OFFSET_POINTS):
    """Draw light gray dotted lines at the edges for cutting guides with offset"""
    # Define y coordinates for horizontal dotted lines (no change needed for horizontal lines' y-coords)
    y_coords = [
        580.9604567,
        331.511795,
        280.488205,
        31.03954328,
    ]
    
    # Define x coordinates for vertical dotted lines (these will be offset)
    x_coords = [
        191.9056404 + x_offset,
        13.3230757 + x_offset,
        387.4960683 + x_offset,
        208.9135037 + x_offset,
        583.0864963 + x_offset,
        404.5039317 + x_offset,
        778.6769243 + x_offset,
        600.0943596 + x_offset,
    ]
    
    # Set up line style - light gray dotted lines
    overlay_canvas.setDash([4, 1])  # Set dash pattern: 4 points on, 1 point off
    overlay_canvas.setLineWidth(0.5)
    overlay_canvas.setStrokeColor(lightgrey)
    
    # Horizontal lines: 2 inches (144 points) on each edge
    edge_width_horizontal = 2 * 72  # 144 points
    
    # Draw horizontal dotted lines only at the edges (2 inches from each side)
    # Apply offset to horizontal lines as well
    for y in y_coords:
        # Left edge (first 2 inches) - shifted right by offset
        overlay_canvas.line(0 + x_offset, y, edge_width_horizontal + x_offset, y)
        # Right edge (last 2 inches) - shifted right by offset
        overlay_canvas.line(page_width - edge_width_horizontal + x_offset, y, page_width + x_offset, y)
    
    # Vertical lines: 1 inch on each end, 2 inches in the middle
    edge_height_vertical = 1 * 72  # 72 points (1 inch)
    middle_height = 2 * 72  # 144 points (2 inches)
    middle_start = (page_height / 2) - (middle_height / 2)
    middle_end = (page_height / 2) + (middle_height / 2)
    
    # Draw vertical dotted lines (already offset in x_coords)
    for x in x_coords:
        # Bottom edge (first 1 inch)
        overlay_canvas.line(x, 0, x, edge_height_vertical)
        # Top edge (last 1 inch)
        overlay_canvas.line(x, page_height - edge_height_vertical, x, page_height)
        # Middle section (2 inches in the center)
        overlay_canvas.line(x, middle_start, x, middle_end)
    
    # Reset to solid lines and default color for any subsequent drawing
    overlay_canvas.setDash([])

def create_page_with_cards(page_card_ids, page_width, page_height, fronts_dir, x_offset=OFFSET_POINTS):
    """Create a single page with up to 8 cards using card IDs, with edge cut lines on top and offset"""
    # Define points with their coordinates (apply offset to x-coordinates)
    points = [
        ("A", 102.614358 + x_offset, 456.2361258),
        ("B", 298.204786 + x_offset, 456.2361258),
        ("C", 493.795214 + x_offset, 456.2361258),
        ("D", 689.385642 + x_offset, 456.2361258),
        ("E", 102.614358 + x_offset, 155.7638742),
        ("F", 298.204786 + x_offset, 155.7638742),
        ("G", 493.795214 + x_offset, 155.7638742),
        ("H", 689.385642 + x_offset, 155.7638742)
    ]
    
    # Create a canvas in memory
    packet = BytesIO()
    overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Target width in mm and convert to points
    target_width_mm = 69.35
    target_width_points = target_width_mm * 72 / 25.4
    
    # Process each image position
    for i, (label, x, y) in enumerate(points):
        if i < len(page_card_ids) and page_card_ids[i]:
            card_id = page_card_ids[i]
            
            # Find the image file for this card ID
            image_filename = find_image_by_id(card_id, fronts_dir)
            if not image_filename:
                print(f"  Warning: No image found for card ID {card_id}")
                continue
            
            image_path = os.path.join(fronts_dir, image_filename)
            
            try:
                # Open and process the image
                img = Image.open(image_path)
                
                # Calculate the aspect ratio to maintain proportions
                aspect_ratio = img.height / img.width
                target_height_points = target_width_points * aspect_ratio
                
                # Calculate position to center the image on the point
                img_x = x - (target_width_points / 2)
                img_y = y - (target_height_points / 2)
                
                # Draw the image on the overlay canvas
                overlay_canvas.drawImage(image_path,
                                       img_x, img_y,
                                       width=target_width_points,
                                       height=target_height_points)
                
                print(f"  Placed {image_filename} at point {label}")
                
            except Exception as e:
                print(f"  Error processing {image_filename}: {e}")
                continue
    
    # Draw edge cut lines ON TOP of the cards with the same offset
    draw_edge_cut_lines(overlay_canvas, page_width, page_height, x_offset)
    
    overlay_canvas.save()
    packet.seek(0)
    return packet

def compress_pdf(input_path, output_path):
    """Compress PDF to 1200 DPI using Ghostscript"""
    try:
        cmd = [
            'gs',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/prepress',
            '-dNOPAUSE',
            '-dQUIET',
            '-dBATCH',
            '-dColorImageResolution=1200',
            '-dGrayImageResolution=1200',
            '-dMonoImageResolution=1200',
            f'-sOutputFile={output_path}',
            input_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error compressing {input_path}: {e}")
        return False

def main():
    # Configuration
    xml_path = "assets/cards.xml"
    fronts_dir = "assets/fronts"
    template_pdf = "template_cut_lines.pdf"
    output_dir = "./output"
    uncompressed_dir = os.path.join(output_dir, "uncompressed_pdfs")
    compressed_dir = os.path.join(output_dir, "compressed_pdfs")
    final_pdf = os.path.join(output_dir, "fronts.pdf")
    
    # Offset configuration (can be modified here or passed as parameter)
    x_offset_cm = DEFAULT_OFFSET_CM  # Change this value to adjust offset
    x_offset_points = x_offset_cm * 10 * 72 / 25.4  # Convert cm to points
    
    print(f"Using horizontal offset: {x_offset_cm}cm ({x_offset_points:.2f} points)")
    
    # Set up page size (landscape 8.5x11 inches)
    page_width, page_height = landscape(letter)
    
    # Check if Ghostscript is available
    has_ghostscript = check_and_install_ghostscript()
    
    # Create/clean output directories
    if os.path.exists(uncompressed_dir):
        shutil.rmtree(uncompressed_dir)
    os.makedirs(uncompressed_dir, exist_ok=True)
    
    if os.path.exists(compressed_dir):
        shutil.rmtree(compressed_dir)
    os.makedirs(compressed_dir, exist_ok=True)
    
    # Check if required files exist
    if not os.path.exists(xml_path):
        print(f"XML file not found: {xml_path}")
        return
    
    if not os.path.exists(template_pdf):
        print(f"Template PDF not found: {template_pdf}")
        print("Please run the original script first to generate the template.")
        return
    
    if not os.path.exists(fronts_dir):
        print(f"Fronts directory not found: {fronts_dir}")
        return
    
    # Parse XML
    print("Parsing XML...")
    cards = parse_xml_cards(xml_path)
    print(f"Found {len(cards)} cards in XML")
    
    # Create slot list (now contains card IDs instead of filenames)
    slot_list = create_slot_list(cards)
    print(f"Total slots needed: {len(slot_list)}")
    
    # Check if all images exist (now searches by card ID)
    print("\nChecking images...")
    missing_images, existing_images = check_images_exist(slot_list, fronts_dir)
    
    if missing_images:
        print("ERROR: Missing images for card IDs:")
        for slot, card_id in missing_images:
            print(f"  Slot {slot}: {card_id}")
        return
    
    print(f"All required images found ({len(set(existing_images))} unique images)")
    
    # Calculate pages needed (8 cards per page)
    cards_per_page = 8
    total_pages = (len(slot_list) + cards_per_page - 1) // cards_per_page
    print(f"Will generate {total_pages} pages")
    
    # Generate uncompressed pages
    print("\nGenerating uncompressed PDFs with edge cut lines...")
    uncompressed_files = []
    
    for page_num in range(total_pages):
        start_slot = page_num * cards_per_page
        end_slot = min(start_slot + cards_per_page, len(slot_list))
        page_card_ids = slot_list[start_slot:end_slot]
        
        print(f"Page {page_num + 1}: slots {start_slot}-{end_slot - 1}")
        
        # Create overlay with cards and edge cut lines (with offset)
        overlay_packet = create_page_with_cards(page_card_ids, page_width, page_height, fronts_dir, x_offset_points)
        
        # Read template fresh for each page to avoid stacking
        template_reader = PdfReader(template_pdf)
        template_page = template_reader.pages[0]
        
        # Merge with overlay
        overlay_reader = PdfReader(overlay_packet)
        output_writer = PdfWriter()
        
        # Copy template page and merge with overlay
        merged_page = template_page
        if len(overlay_reader.pages) > 0:
            overlay_page = overlay_reader.pages[0]
            merged_page.merge_page(overlay_page)
        
        output_writer.add_page(merged_page)
        
        # Save uncompressed PDF
        uncompressed_file = os.path.join(uncompressed_dir, f"page_{page_num + 1:03d}.pdf")
        with open(uncompressed_file, 'wb') as output_file:
            output_writer.write(output_file)
        
        uncompressed_files.append(uncompressed_file)
        print(f"  Saved: {uncompressed_file}")
    
    # Compress PDFs if Ghostscript is available
    compressed_files = []
    if has_ghostscript:
        print("\nCompressing PDFs to 1200 DPI...")
        for uncompressed_file in uncompressed_files:
            filename = os.path.basename(uncompressed_file)
            compressed_file = os.path.join(compressed_dir, filename)
            
            if compress_pdf(uncompressed_file, compressed_file):
                compressed_files.append(compressed_file)
                print(f"  Compressed: {filename}")
            else:
                print(f"  Failed to compress: {filename}")
                # Use uncompressed version as fallback
                shutil.copy2(uncompressed_file, compressed_file)
                compressed_files.append(compressed_file)
    else:
        print("\nSkipping compression (Ghostscript not available)")
        # Copy uncompressed files to compressed directory
        for uncompressed_file in uncompressed_files:
            filename = os.path.basename(uncompressed_file)
            compressed_file = os.path.join(compressed_dir, filename)
            shutil.copy2(uncompressed_file, compressed_file)
            compressed_files.append(compressed_file)
    
    # Combine all pages into final PDF
    print(f"\nCombining {len(compressed_files)} pages into final PDF...")
    final_writer = PdfWriter()
    
    for compressed_file in sorted(compressed_files):
        reader = PdfReader(compressed_file)
        for page in reader.pages:
            final_writer.add_page(page)
    
    with open(final_pdf, 'wb') as output_file:
        final_writer.write(output_file)
    
    print(f"\nCompleted!")
    print(f"Final PDF: {final_pdf}")
    print(f"Uncompressed PDFs: {uncompressed_dir}")
    print(f"Compressed PDFs: {compressed_dir}")
    print(f"Total pages generated: {total_pages}")
    print(f"Total cards printed: {len(slot_list)}")
    print(f"Note: Light gray dotted lines added at edges for cutting guides")
    print(f"Note: Content shifted right by {x_offset_cm}cm")

if __name__ == "__main__":
    main()