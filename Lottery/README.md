# Lottery Program

A desktop lottery application for Windows built with **PySide6 + pandas**, supporting **Excel import, random selection, rolling display, and result export**.

---

## Features

-  **Load numbers**: Import phone numbers from an Excel file (default column name `Numbers`, or automatically detect the first column)
- **Set draw count**: Freely input how many winners to draw
- **Rolling effect**: Numbers roll across the screen during drawing, simulating a live lottery atmosphere
- **Fixed results**: When stopped, show the actual winners
- **Export results**: Export winning numbers to Excel
- **UI customization**: Background image support, maximized window, adjustable number display area
- **Phone number masking**: Middle digits hidden automatically (e.g., `138****2468`)

---

## Requirements

Recommended: **Python 3.10+**. Run inside a virtual environment.

```bash
pip install -r requirements.txt
```

Key dependencies:

* `PySide6` — GUI development
* `pandas` — data processing
* `openpyxl` — Excel support

---

## Usage

1. **Clone the project**

```bash
git clone https://github.com/yourname/lottery-app.git
```

2. **Prepare your data**
   Excel file should have phone numbers in the first column:

    | Numbers     |
    | ----------- |
    | 13021083019 |
    | 17739966604 |
    | 17526303318 |

3. **Run the program**

```bash
python choujiang.py
```

4. **Steps**

   - Click **Select Excel File** → Import phone numbers
   - Set draw count → Click **Start Lottery**
   - Program displays **Drawing...** while rolling
   - Stop to reveal results, then export to Excel

---

## Configuration

You can adjust these in the code:

* **Font size for numbers**

```python
self.text.setStyleSheet("font-size: 22px;")
```

* **Number of columns**

```python
cols = 7
```

* **Display area margins**

```python
bg_layout.setContentsMargins(left, top, right, bottom)
```

---

## Project Structure

```
Lottery/
├── choujiang.py        # Main program
├── background.jpg         # Background image
├── requirements.txt    # Dependencies
└── README.md           # Documentation
```

---

## License

This project is licensed under the **MIT License** — free to modify and distribute.
