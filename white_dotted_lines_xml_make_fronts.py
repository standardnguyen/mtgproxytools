import xml.etree.ElementTree as ET
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black
from PIL import Image
import os
import shutil
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO
import subprocess
import sys

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

def create_page_with_cards(page_card_ids, page_width, page_height, fronts_dir):
    """Create a single page with up to 8 cards using card IDs"""
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
    
    overlay_canvas.save()
    packet.seek(0)
    return packet

def create_edge_lines_overlay(page_width, page_height):
    """Create an overlay with dotted lines at the edges for specific Y coordinates"""
    # Define y coordinates for horizontal dotted lines (from reference code)
    y_coords = [
        580.9604567,
        331.511795,
        280.488205,
        31.03954328,
    ]
    
    # Create a canvas in memory for the lines
    packet = BytesIO()
    lines_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))
    
    # Set up line properties (same as reference code)
    lines_canvas.setDash([4, 1])  # Set dash pattern: 4 points on, 1 point off
    lines_canvas.setLineWidth(0.5)
    lines_canvas.setStrokeColor(black)
    
    # Define edge margins (1-2 inches from each side)
    left_margin = 72  # 1 inch from left edge
    right_margin = 72  # 1 inch from right edge
    edge_line_length = 144  # 2 inches long
    
    # Draw horizontal dotted lines at edges for each Y coordinate
    for y in y_coords:
        # Left edge line
        lines_canvas.line(left_margin, y, left_margin + edge_line_length, y)
        # Right edge line  
        lines_canvas.line(page_width - right_margin - edge_line_length, y, page_width - right_margin, y)
    
    # Reset to solid lines
    lines_canvas.setDash([])
    lines_canvas.save()
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
    
    # Load template PDF
    template_reader = PdfReader(template_pdf)
    template_page = template_reader.pages[0]
    
    # Generate uncompressed pages
    print("\nGenerating uncompressed PDFs with edge lines...")
    uncompressed_files = []
    
    for page_num in range(total_pages):
        start_slot = page_num * cards_per_page
        end_slot = min(start_slot + cards_per_page, len(slot_list))
        page_card_ids = slot_list[start_slot:end_slot]
        
        print(f"Page {page_num + 1}: slots {start_slot}-{end_slot - 1}")
        
        # Create overlay with cards (now uses card IDs)
        cards_overlay_packet = create_page_with_cards(page_card_ids, page_width, page_height, fronts_dir)
        
        # Create overlay with edge lines
        lines_overlay_packet = create_edge_lines_overlay(page_width, page_height)
        
        # Merge template with cards overlay first
        cards_overlay_reader = PdfReader(cards_overlay_packet)
        output_writer = PdfWriter()
        
        # Copy template page and merge with cards overlay
        merged_page = template_page
        if len(cards_overlay_reader.pages) > 0:
            cards_overlay_page = cards_overlay_reader.pages[0]
            merged_page = template_page
            merged_page.merge_page(cards_overlay_page)
        
        # Then merge with lines overlay (lines on top)
        lines_overlay_reader = PdfReader(lines_overlay_packet)
        if len(lines_overlay_reader.pages) > 0:
            lines_overlay_page = lines_overlay_reader.pages[0]
            merged_page.merge_page(lines_overlay_page)
        
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
    print(f"Added edge lines on first and last pages only at Y coordinates: 580.96, 331.51, 280.49, 31.04")

if __name__ == "__main__":
    main()