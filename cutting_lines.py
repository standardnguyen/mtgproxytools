from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import red, black

# Set up page size (landscape 8.5x11 inches)
page_width, page_height = landscape(letter)

# Output PDF filename
output_filename = "template_cut_lines.pdf"

# Create canvas
c = canvas.Canvas(output_filename, pagesize=(page_width, page_height))
print(f"Page dimensions: {page_width} x {page_height}")

# Original center lines (keeping these)
c.setLineWidth(0.5)
c.setStrokeColor(black)
c.line(0, page_height / 2, page_width, page_height / 2)
c.line(page_width / 2, 0, page_width / 2, page_height)

# Define x coordinates for vertical dotted lines
x_coords = [
    191.9056404,
    13.3230757,
    387.4960683,
    208.9135037,
    583.0864963,
    404.5039317,
    778.6769243,
    600.0943596,
]

# Define y coordinates for horizontal dotted lines
y_coords = [
    589.4643884,
    323.0078633,
    288.9921367,
    22.53561163,
]

# Draw vertical dotted lines at specified x coordinates
c.setDash([2, 4])  # Set dash pattern: 2 points on, 4 points off
c.setLineWidth(0.5)
c.setStrokeColor(black)
for x in x_coords:
    c.line(x, 0, x, page_height)

# Draw horizontal dotted lines at specified y coordinates
for y in y_coords:
    c.line(0, y, page_width, y)

# Reset to solid lines
c.setDash([])

# Define points with their coordinates
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

# Draw red points
c.setFillColor(red)
point_radius = 3  # Radius of the points in points (1/72 inch)

for label, x, y in points:
    # Draw a red circle at each point
    c.circle(x, y, point_radius, stroke=0, fill=1)
    
    # Optionally add labels next to points
    c.setFillColor(black)
    c.setFont("Helvetica", 8)
    c.drawString(x + 5, y + 5, label)
    c.setFillColor(red)  # Reset to red for next point

# Save the PDF
c.save()
print(f"PDF generated: {output_filename}")
print("\nPoints plotted:")
for label, x, y in points:
    print(f"Point {label}: ({x}, {y})")