// Stationery items database - ~200 Indian items with prices
const STATIONERY_ITEMS = [
  // WRITING - Pencils (30 items)
  { id: 1, name: 'HB Pencil (Cello)', category: 'Pencils', price: 5, image: '✏️' },
  { id: 2, name: 'HB Pencil (Faber-Castell)', category: 'Pencils', price: 8, image: '✏️' },
  { id: 3, name: 'HB Pencil (Staedtler)', category: 'Pencils', price: 12, image: '✏️' },
  { id: 4, name: '2B Pencil (Cello)', category: 'Pencils', price: 5, image: '✏️' },
  { id: 5, name: '2B Pencil (Faber-Castell)', category: 'Pencils', price: 8, image: '✏️' },
  { id: 6, name: 'HB Pencil Box (12 pcs)', category: 'Pencils', price: 40, image: '✏️' },
  { id: 7, name: 'Mechanical Pencil (0.5mm)', category: 'Pencils', price: 25, image: '✏️' },
  { id: 8, name: 'Mechanical Pencil (0.7mm)', category: 'Pencils', price: 30, image: '✏️' },
  { id: 9, name: 'Mechanical Lead (0.5mm)', category: 'Pencils', price: 20, image: '✏️' },
  { id: 10, name: 'Mechanical Lead (0.7mm)', category: 'Pencils', price: 25, image: '✏️' },
  { id: 11, name: 'Color Pencil Set (12 colors)', category: 'Pencils', price: 80, image: '✏️' },
  { id: 12, name: 'Color Pencil Set (24 colors)', category: 'Pencils', price: 150, image: '✏️' },
  { id: 13, name: 'Color Pencil (single)', category: 'Pencils', price: 10, image: '✏️' },
  { id: 14, name: 'Eraser Pencil', category: 'Pencils', price: 8, image: '✏️' },
  { id: 15, name: 'Pencil Sharpener (single)', category: 'Pencils', price: 10, image: '✏️' },
  { id: 16, name: 'Pencil Sharpener (metal)', category: 'Pencils', price: 20, image: '✏️' },
  { id: 17, name: 'Pencil Sharpener (electric)', category: 'Pencils', price: 150, image: '✏️' },
  { id: 18, name: 'Pencil Case (small)', category: 'Pencils', price: 30, image: '✏️' },
  { id: 19, name: 'Pencil Case (large)', category: 'Pencils', price: 80, image: '✏️' },
  { id: 20, name: 'Sketch Pencil Set', category: 'Pencils', price: 200, image: '✏️' },

  // PENS (35 items)
  { id: 21, name: 'Ballpoint Pen (Cello)', category: 'Pens', price: 8, image: '🖊️' },
  { id: 22, name: 'Ballpoint Pen (Reynolds)', category: 'Pens', price: 12, image: '🖊️' },
  { id: 23, name: 'Ballpoint Pen (Butter Flow)', category: 'Pens', price: 20, image: '🖊️' },
  { id: 24, name: 'Ballpoint Pen (Parker)', category: 'Pens', price: 80, image: '🖊️' },
  { id: 25, name: 'Gel Pen (Cello)', category: 'Pens', price: 10, image: '🖊️' },
  { id: 26, name: 'Gel Pen (Octane)', category: 'Pens', price: 25, image: '🖊️' },
  { id: 27, name: 'Gel Pen (Rotomac)', category: 'Pens', price: 15, image: '🖊️' },
  { id: 28, name: 'Gel Pen Set (10 pcs)', category: 'Pens', price: 100, image: '🖊️' },
  { id: 29, name: 'Fountain Pen (basic)', category: 'Pens', price: 50, image: '🖊️' },
  { id: 30, name: 'Fountain Pen (premium)', category: 'Pens', price: 300, image: '🖊️' },
  { id: 31, name: 'Fountain Pen Refill', category: 'Pens', price: 30, image: '🖊️' },
  { id: 32, name: 'Highlighter (single)', category: 'Pens', price: 15, image: '🖊️' },
  { id: 33, name: 'Highlighter Set (6 colors)', category: 'Pens', price: 80, image: '🖊️' },
  { id: 34, name: 'Marker (single)', category: 'Pens', price: 20, image: '🖊️' },
  { id: 35, name: 'Marker Set (12 colors)', category: 'Pens', price: 150, image: '🖊️' },
  { id: 36, name: 'Sketch Pen Set', category: 'Pens', price: 180, image: '🖊️' },
  { id: 37, name: 'Whiteboard Marker', category: 'Pens', price: 15, image: '🖊️' },
  { id: 38, name: 'Permanent Marker', category: 'Pens', price: 20, image: '🖊️' },
  { id: 39, name: 'Calligraphy Pen Set', category: 'Pens', price: 120, image: '🖊️' },
  { id: 40, name: 'Ink Refill', category: 'Pens', price: 25, image: '🖊️' },
  { id: 41, name: 'Pen Stand', category: 'Pens', price: 40, image: '🖊️' },
  { id: 42, name: 'Pen Case', category: 'Pens', price: 60, image: '🖊️' },

  // ERASERS & CORRECTION (15 items)
  { id: 43, name: 'Rubber Eraser (small)', category: 'Erasers', price: 5, image: '🗑️' },
  { id: 44, name: 'Rubber Eraser (large)', category: 'Erasers', price: 10, image: '🗑️' },
  { id: 45, name: 'Plastic Eraser', category: 'Erasers', price: 8, image: '🗑️' },
  { id: 46, name: 'Eraser Pack (10 pcs)', category: 'Erasers', price: 40, image: '🗑️' },
  { id: 47, name: 'Correction Tape', category: 'Erasers', price: 30, image: '🗑️' },
  { id: 48, name: 'Correction Fluid (White Out)', category: 'Erasers', price: 25, image: '🗑️' },
  { id: 49, name: 'Pen Eraser', category: 'Erasers', price: 15, image: '🗑️' },
  { id: 50, name: 'Eraser Refill', category: 'Erasers', price: 10, image: '🗑️' },

  // PAPER & NOTEBOOKS (40 items)
  { id: 51, name: 'Notebook (Single Line, 60 pages)', category: 'Notebooks', price: 30, image: '📓' },
  { id: 52, name: 'Notebook (Single Line, 100 pages)', category: 'Notebooks', price: 50, image: '📓' },
  { id: 53, name: 'Notebook (Single Line, 200 pages)', category: 'Notebooks', price: 90, image: '📓' },
  { id: 54, name: 'Notebook (Ruled, A4)', category: 'Notebooks', price: 80, image: '📓' },
  { id: 55, name: 'Notebook (Blank, A4)', category: 'Notebooks', price: 90, image: '📓' },
  { id: 56, name: 'Notebook (Graph, A4)', category: 'Notebooks', price: 85, image: '📓' },
  { id: 57, name: 'Exercise Book (60 pages)', category: 'Notebooks', price: 25, image: '📓' },
  { id: 58, name: 'Exercise Book (100 pages)', category: 'Notebooks', price: 40, image: '📓' },
  { id: 59, name: 'Exercise Book Pack (5 pcs)', category: 'Notebooks', price: 150, image: '📓' },
  { id: 60, name: 'Copy (Scribbling Book)', category: 'Notebooks', price: 15, image: '📓' },
  { id: 61, name: 'Lab Manual Notebook', category: 'Notebooks', price: 35, image: '📓' },
  { id: 62, name: 'Project File', category: 'Notebooks', price: 40, image: '📓' },
  { id: 63, name: 'Diary (A5)', category: 'Notebooks', price: 100, image: '📓' },
  { id: 64, name: 'Diary (A6)', category: 'Notebooks', price: 60, image: '📓' },
  { id: 65, name: 'Sticky Notes (100 sheets)', category: 'Notebooks', price: 25, image: '📓' },
  { id: 66, name: 'Sticky Notes Pack (5 pads)', category: 'Notebooks', price: 100, image: '📓' },
  { id: 67, name: 'Writing Paper (50 sheets)', category: 'Notebooks', price: 20, image: '📓' },
  { id: 68, name: 'Sketch Paper (50 sheets)', category: 'Notebooks', price: 80, image: '📓' },
  { id: 69, name: 'Graph Paper Pad', category: 'Notebooks', price: 40, image: '📓' },
  { id: 70, name: 'Tracing Paper Pad', category: 'Notebooks', price: 50, image: '📓' },
  { id: 71, name: 'Handwriting Practice Book', category: 'Notebooks', price: 35, image: '📓' },
  { id: 72, name: 'Calendar (Table)', category: 'Notebooks', price: 50, image: '📓' },
  { id: 73, name: 'Time Table', category: 'Notebooks', price: 10, image: '📓' },
  { id: 74, name: 'Note Pad', category: 'Notebooks', price: 30, image: '📓' },

  // GEOMETRY & MEASUREMENT (25 items)
  { id: 75, name: 'Scale (15 cm, plastic)', category: 'Geometry', price: 8, image: '📐' },
  { id: 76, name: 'Scale (30 cm, plastic)', category: 'Geometry', price: 12, image: '📐' },
  { id: 77, name: 'Scale (metal, 30 cm)', category: 'Geometry', price: 25, image: '📐' },
  { id: 78, name: 'Compass (basic)', category: 'Geometry', price: 25, image: '📐' },
  { id: 79, name: 'Compass (precision)', category: 'Geometry', price: 60, image: '📐' },
  { id: 80, name: 'Divider', category: 'Geometry', price: 20, image: '📐' },
  { id: 81, name: 'Protractor (180°)', category: 'Geometry', price: 15, image: '📐' },
  { id: 82, name: 'Protractor (360°)', category: 'Geometry', price: 20, image: '📐' },
  { id: 83, name: 'Set Square (45-45-90)', category: 'Geometry', price: 15, image: '📐' },
  { id: 84, name: 'Set Square (30-60-90)', category: 'Geometry', price: 15, image: '📐' },
  { id: 85, name: 'Set Square Pair', category: 'Geometry', price: 25, image: '📐' },
  { id: 86, name: 'Geometry Set (complete)', category: 'Geometry', price: 100, image: '📐' },
  { id: 87, name: 'Ruler Pack', category: 'Geometry', price: 40, image: '📐' },
  { id: 88, name: 'Compass Refill Lead', category: 'Geometry', price: 10, image: '📐' },
  { id: 89, name: 'Eraser (pencil-end)', category: 'Geometry', price: 5, image: '📐' },

  // ADHESIVES & BINDING (20 items)
  { id: 90, name: 'Glue Stick (small)', category: 'Adhesives', price: 15, image: '📎' },
  { id: 91, name: 'Glue Stick (large)', category: 'Adhesives', price: 25, image: '📎' },
  { id: 92, name: 'White Glue (bottle)', category: 'Adhesives', price: 30, image: '📎' },
  { id: 93, name: 'Liquid Adhesive (50ml)', category: 'Adhesives', price: 25, image: '📎' },
  { id: 94, name: 'Double Sided Tape', category: 'Adhesives', price: 20, image: '📎' },
  { id: 95, name: 'Masking Tape', category: 'Adhesives', price: 25, image: '📎' },
  { id: 96, name: 'Transparent Tape', category: 'Adhesives', price: 15, image: '📎' },
  { id: 97, name: 'Cello Tape Roll', category: 'Adhesives', price: 20, image: '📎' },
  { id: 98, name: 'Sticky Tape Pack', category: 'Adhesives', price: 80, image: '📎' },
  { id: 99, name: 'Binding Tape (brown)', category: 'Adhesives', price: 15, image: '📎' },
  { id: 100, name: 'Binding Clip (small)', category: 'Adhesives', price: 10, image: '📎' },
  { id: 101, name: 'Binding Clip (large)', category: 'Adhesives', price: 15, image: '📎' },
  { id: 102, name: 'Stapler (mini)', category: 'Adhesives', price: 40, image: '📎' },
  { id: 103, name: 'Stapler (standard)', category: 'Adhesives', price: 80, image: '📎' },
  { id: 104, name: 'Staples Pack (1000)', category: 'Adhesives', price: 25, image: '📎' },
  { id: 105, name: 'Staple Remover', category: 'Adhesives', price: 15, image: '📎' },
  { id: 106, name: 'Punch (single hole)', category: 'Adhesives', price: 30, image: '📎' },
  { id: 107, name: 'Punch (two hole)', category: 'Adhesives', price: 50, image: '📎' },
  { id: 108, name: 'Brads & Fasteners', category: 'Adhesives', price: 20, image: '📎' },

  // FOLDERS & FILES (20 items)
  { id: 109, name: 'File Folder (A4, single)', category: 'Folders', price: 15, image: '📁' },
  { id: 110, name: 'File Folder (A4, pack of 5)', category: 'Folders', price: 60, image: '📁' },
  { id: 111, name: 'Lever Arch File', category: 'Folders', price: 80, image: '📁' },
  { id: 112, name: 'Project File (cardboard)', category: 'Folders', price: 40, image: '📁' },
  { id: 113, name: 'Spiral File (plastic)', category: 'Folders', price: 50, image: '📁' },
  { id: 114, name: 'Report Cover (plastic)', category: 'Folders', price: 25, image: '📁' },
  { id: 115, name: 'Document Case', category: 'Folders', price: 60, image: '📁' },
  { id: 116, name: 'Magazine File', category: 'Folders', price: 40, image: '📁' },
  { id: 117, name: 'Envelopes (pack of 100)', category: 'Folders', price: 80, image: '📁' },
  { id: 118, name: 'OHP Sheets (pack)', category: 'Folders', price: 100, image: '📁' },
  { id: 119, name: 'Laminating Sheets (pack)', category: 'Folders', price: 120, image: '📁' },
  { id: 120, name: 'File Organizer', category: 'Folders', price: 150, image: '📁' },

  // DESK ACCESSORIES (25 items)
  { id: 121, name: 'Desk Organizer (plastic)', category: 'Desk', price: 80, image: '💼' },
  { id: 122, name: 'Pen Stand (ceramic)', category: 'Desk', price: 100, image: '💼' },
  { id: 123, name: 'Pencil Box (wood)', category: 'Desk', price: 120, image: '💼' },
  { id: 124, name: 'Desk Lamp', category: 'Desk', price: 300, image: '💼' },
  { id: 125, name: 'Desk Mat (plastic)', category: 'Desk', price: 80, image: '💼' },
  { id: 126, name: 'Desk Mat (cork)', category: 'Desk', price: 150, image: '💼' },
  { id: 127, name: 'Calculator (basic)', category: 'Desk', price: 100, image: '💼' },
  { id: 128, name: 'Scientific Calculator', category: 'Desk', price: 400, image: '💼' },
  { id: 129, name: 'Clock (table)', category: 'Desk', price: 150, image: '💼' },
  { id: 130, name: 'Memo Holder', category: 'Desk', price: 40, image: '💼' },
  { id: 131, name: 'Push Pins (pack of 20)', category: 'Desk', price: 15, image: '💼' },
  { id: 132, name: 'Thumbtacks (pack)', category: 'Desk', price: 10, image: '💼' },
  { id: 133, name: 'Desk Tidy', category: 'Desk', price: 100, image: '💼' },
  { id: 134, name: 'File Stand', category: 'Desk', price: 80, image: '💼' },
  { id: 135, name: 'Book Stand', category: 'Desk', price: 120, image: '💼' },
  { id: 136, name: 'Document Holder', category: 'Desk', price: 90, image: '💼' },
  { id: 137, name: 'Desk Phone Stand', category: 'Desk', price: 80, image: '💼' },
  { id: 138, name: 'Cable Organizer', category: 'Desk', price: 60, image: '💼' },

  // SPECIALTY ITEMS (20 items)
  { id: 139, name: 'Whiteboard (small)', category: 'Specialty', price: 150, image: '🎨' },
  { id: 140, name: 'Whiteboard (large)', category: 'Specialty', price: 300, image: '🎨' },
  { id: 141, name: 'Flip Chart Pad', category: 'Specialty', price: 200, image: '🎨' },
  { id: 142, name: 'Poster Board', category: 'Specialty', price: 30, image: '🎨' },
  { id: 143, name: 'Canvas Board', category: 'Specialty', price: 80, image: '🎨' },
  { id: 144, name: 'Watercolor Set', category: 'Specialty', price: 200, image: '🎨' },
  { id: 145, name: 'Acrylic Paint Set', category: 'Specialty', price: 250, image: '🎨' },
  { id: 146, name: 'Oil Paint Set', category: 'Specialty', price: 400, image: '🎨' },
  { id: 147, name: 'Paint Brush Set', category: 'Specialty', price: 120, image: '🎨' },
  { id: 148, name: 'Charcoal Pencils', category: 'Specialty', price: 80, image: '🎨' },
  { id: 149, name: 'Pastel Set', category: 'Specialty', price: 150, image: '🎨' },
  { id: 150, name: 'Palette', category: 'Specialty', price: 60, image: '🎨' },
  { id: 151, name: 'Easel (tabletop)', category: 'Specialty', price: 200, image: '🎨' },
  { id: 152, name: 'Craft Knife', category: 'Specialty', price: 30, image: '🎨' },
  { id: 153, name: 'Cutting Mat', category: 'Specialty', price: 100, image: '🎨' },
  { id: 154, name: 'Ruler Set (metal)', category: 'Specialty', price: 80, image: '🎨' },
  { id: 155, name: 'Stencil Set', category: 'Specialty', price: 60, image: '🎨' },
  { id: 156, name: 'Craft Scissors', category: 'Specialty', price: 50, image: '🎨' },
  { id: 157, name: 'Glitter & Embellishments', category: 'Specialty', price: 100, image: '🎨' },
  { id: 158, name: 'Stickers & Washi Tape', category: 'Specialty', price: 80, image: '🎨' },
];

// Plan recommendations based on total spending
const PLAN_RECOMMENDATIONS = {
  0: { plan: 'None', message: 'Add items to see recommendations' },
  1: { plan: 'Default (₹60/mo)', message: 'Basic coverage for everyday items', threshold: 200 },
  200: { plan: 'Deluxe (₹100/mo)', message: 'Recommended for moderate spenders', threshold: 500 },
  500: { plan: 'Ultra (₹200/mo)', message: 'Good for regular users', threshold: 1500 },
  1500: { plan: 'Efficiency (₹1000/mo)', message: 'Best for heavy users & artists', threshold: Infinity },
};

function getRecommendedPlan(total) {
  if (total < 200) return PLAN_RECOMMENDATIONS[0];
  if (total < 500) return PLAN_RECOMMENDATIONS[1];
  if (total < 1500) return PLAN_RECOMMENDATIONS[200];
  return PLAN_RECOMMENDATIONS[1500];
}

function searchItems(query) {
  const q = query.toLowerCase();
  return STATIONERY_ITEMS.filter(item =>
    item.name.toLowerCase().includes(q) ||
    item.category.toLowerCase().includes(q)
  );
}

function getItemsByCategory(category) {
  return STATIONERY_ITEMS.filter(item => item.category === category);
}

function getAllCategories() {
  return [...new Set(STATIONERY_ITEMS.map(item => item.category))].sort();
}
